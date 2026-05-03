"""Spider subset evaluation runner for QueryShield baseline-vs-system tests."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import time
from pathlib import Path
from typing import Any

from queryshield.core.llm import LLMClient
from queryshield.evaluation.error_router import DeterministicErrorRouter
from queryshield.evaluation.model_profiles import (
    apply_profile_to_timeout,
    get_model_profile,
    strip_thinking_blocks,
)
from queryshield.evaluation.planner import (
    assess_plan_quality,
    build_planner_prompt,
    parse_plan_response,
)
from queryshield.evaluation.plan_validator import validate_sql_plan
from queryshield.evaluation.retry_utils import (
    RETRY_DELAY_SECONDS,
    RequestThrottler,
    generate_with_retry,
)
from queryshield.evaluation.schema_validator import SchemaPreValidator
from queryshield.evaluation.semantic_loop import run_semantic_loop
from queryshield.evaluation.spider_execution import evaluate_sql_prediction, execute_sql
from queryshield.evaluation.spider_loader import SpiderExample, load_spider_examples
from queryshield.evaluation.spider_metrics import calculate_spider_metrics
from queryshield.evaluation.spider_prompts import (
    build_common_prompt,
    build_correction_prompt,
    build_enhanced_direct_prompt,
)
from queryshield.evaluation.spider_schema import build_rich_schema_context, build_schema_dict
from queryshield.evaluation.spider_subset import analyze_complexity, select_hard_subset
from queryshield.evaluation.sql_generator import (
    build_sql_fix_from_plan_prompt,
    build_sql_from_plan_prompt,
)
from queryshield.retrieval.schema_pruner import build_pruned_schema_context

MAX_CORRECTION_RETRIES = 2
MAX_SEMANTIC_RETRIES = 2
MAX_PLAN_VALIDATION_ATTEMPTS = 3
USE_SEMANTIC_LOOP = True
SYSTEM_PLAN_BASED = False
API_MAX_RETRIES = 1
API_RECOVERY_ROUNDS = 1
API_RECOVERY_COOLDOWN_SECONDS = 5
MIN_LLM_TIMEOUT_SECONDS = 35
DEFAULT_DATASET_JSON = Path("queryshield/data/spider2/spider2_local_subset.json")
DEFAULT_DB_ROOT = Path("queryshield/data/spider2")
DEFAULT_OUTPUT_PATH = Path("queryshield/evaluation/results/spider2_subset_results.json")
DEFAULT_THROTTLE_SECONDS = 2.5
DEFAULT_API_BUDGET_CLOUD = 10
DEFAULT_API_BUDGET_OLLAMA = 6
DEFAULT_FORCE_PIPELINE_MODE = None  # auto-detect
DEFAULT_RUN_PARALLEL = False
DEFAULT_TOP_K_TABLES = 5


class BudgetTracker:
    """Track and enforce per-query API call budget."""

    def __init__(self, max_calls: int):
        self.max_calls = max_calls
        self.used = 0
        self.stage_log: list[str] = []

    def consume(self, stage: str, n: int = 1) -> bool:
        """Returns True if budget available, False if exhausted."""
        if self.used + n > self.max_calls:
            self.stage_log.append(f"BUDGET_EXHAUSTED at {stage}")
            return False
        self.used += n
        self.stage_log.append(f"{stage}:{n}")
        return True

    @property
    def remaining(self) -> int:
        return self.max_calls - self.used

    @property
    def exhausted_stages(self) -> list[str]:
        return [e for e in self.stage_log if e.startswith("BUDGET_EXHAUSTED")]


class ModelCapabilityProbe:
    """Probe LLM capability to determine pipeline mode."""

    PROBE_QUESTION = "List all customers who placed more than 3 orders."
    PROBE_SCHEMA = (
        "Table: orders(order_id, customer_id, amount). "
        "Table: customers(customer_id, name)."
    )

    def probe(self, llm_client: LLMClient) -> str:
        """Returns 'full', 'lite', or 'direct'."""
        try:
            start = time.time()
            result = llm_client.generate_text(
                f"Schema: {self.PROBE_SCHEMA}\nQuestion: {self.PROBE_QUESTION}\n"
                f"Respond ONLY with a JSON object with keys: tables, joins, filters. No other text."
            )
            elapsed = time.time() - start

            try:
                cleaned = result.strip().strip('`').replace('json\n', '')
                parsed = json.loads(cleaned)
                has_structure = 'tables' in parsed and 'joins' in parsed
            except Exception:
                has_structure = False

            if elapsed > 200 or not has_structure:
                return 'lite'
            if elapsed > 400:
                return 'direct'
            return 'full'
        except Exception:
            return 'direct'


def run_spider_evaluation(
    dataset_json: Path,
    db_root: Path,
    output_path: Path,
    num_dbs: int = 3,
    num_queries: int = 24,
    llm_timeout_seconds: int = MIN_LLM_TIMEOUT_SECONDS,
    throttle_seconds: float = DEFAULT_THROTTLE_SECONDS,
    api_budget_per_query: int | None = None,
    force_pipeline_mode: str | None = DEFAULT_FORCE_PIPELINE_MODE,
    run_parallel: bool = DEFAULT_RUN_PARALLEL,
    top_k_tables: int = DEFAULT_TOP_K_TABLES,
) -> dict[str, Any]:
    """Run Spider subset evaluation and persist final report."""
    all_examples = load_spider_examples(dataset_json=dataset_json, db_root=db_root)
    selected_examples, subset_meta = select_hard_subset(
        examples=all_examples,
        num_dbs=num_dbs,
        num_queries=num_queries,
    )
    if not selected_examples:
        raise ValueError("No examples selected for Spider subset run.")

    # Apply model-specific timeout multiplier
    model_profile = get_model_profile(
        os.getenv("GROQ_MODEL", os.getenv("OLLAMA_MODEL", "unknown"))
    )
    effective_timeout = apply_profile_to_timeout(
        llm_timeout_seconds,
        os.getenv("GROQ_MODEL", os.getenv("OLLAMA_MODEL", "unknown")),
    )
    llm_client = LLMClient(timeout_seconds=effective_timeout)
    effective_throttle_seconds = max(0.0, float(throttle_seconds))
    throttler = RequestThrottler(min_interval_seconds=effective_throttle_seconds)
    print(f"[CONFIG] Model profile: {model_profile.get('validator_strictness', 'standard')} | "
          f"timeout: {effective_timeout}s | top_k_tables: {top_k_tables}")

    # Determine pipeline mode (Change 2)
    if force_pipeline_mode in ('full', 'lite', 'direct'):
        pipeline_mode = force_pipeline_mode
    else:
        try:
            pipeline_mode = ModelCapabilityProbe().probe(llm_client)
        except Exception:
            pipeline_mode = 'full'

    # Determine budget (Change 1)
    if api_budget_per_query is not None:
        effective_budget = api_budget_per_query
    elif llm_client.provider == 'ollama':
        effective_budget = DEFAULT_API_BUDGET_OLLAMA
    else:
        effective_budget = DEFAULT_API_BUDGET_CLOUD

    schema_cache: dict[str, str] = {}
    schema_dict_cache: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    api_failure_count = 0

    for idx, example in enumerate(selected_examples):
        rows.append(
            _evaluate_one_example(
                example=example,
                llm_client=llm_client,
                throttler=throttler,
                schema_cache=schema_cache,
                schema_dict_cache=schema_dict_cache,
                pipeline_mode=pipeline_mode,
                api_budget=effective_budget,
                run_parallel=run_parallel,
                llm_timeout_seconds=effective_timeout,
                top_k_tables=top_k_tables,
                model_profile=model_profile,
            )
        )

        # Adaptive downgrade after first 3 queries (Change 2)
        if idx == 2 and len(rows) >= 3:
            failures = sum(
                1 for r in rows
                if r.get('system_classification') == 'api_error'
                or r.get('baseline_classification') == 'api_error'
            )
            failure_rate = failures / len(rows)
            if failure_rate > 0.4:
                if pipeline_mode == 'full':
                    pipeline_mode = 'lite'
                    print(f"[DOWNGRADE] Pipeline mode downgraded to 'lite' (failure_rate={failure_rate:.2f})")
                elif pipeline_mode == 'lite':
                    pipeline_mode = 'direct'
                    print(f"[DOWNGRADE] Pipeline mode downgraded to 'direct' (failure_rate={failure_rate:.2f})")

        runtime_config = _build_runtime_config(
            llm_timeout_seconds, effective_throttle_seconds, effective_budget,
            pipeline_mode, run_parallel,
        )
        partial_metrics = calculate_spider_metrics(rows)
        partial_payload = {
            "experiment": "spider2_subset_fair_prompt",
            "status": "in_progress",
            "completed_queries": len(rows),
            "total_queries": len(selected_examples),
            "dataset_json": str(Path(dataset_json).resolve()),
            "db_root": str(Path(db_root).resolve()),
            "subset": subset_meta,
            "runtime_config": runtime_config,
            "results": rows,
            "metrics": partial_metrics,
        }
        _save_json(payload=partial_payload, output_path=output_path)

    metrics = calculate_spider_metrics(rows)
    adjusted_metrics = compute_adjusted_metrics(rows)
    runtime_config = _build_runtime_config(
        llm_timeout_seconds, effective_throttle_seconds, effective_budget,
        pipeline_mode, run_parallel,
    )
    payload = {
        "experiment": "spider2_subset_fair_prompt",
        "status": "completed",
        "dataset_json": str(Path(dataset_json).resolve()),
        "db_root": str(Path(db_root).resolve()),
        "subset": subset_meta,
        "runtime_config": runtime_config,
        "results": rows,
        "metrics": metrics,
        "adjusted_metrics": adjusted_metrics,
    }
    _save_json(payload=payload, output_path=output_path)
    _print_report(
        metrics=metrics, selected_count=len(selected_examples),
        subset_meta=subset_meta, adjusted_metrics=adjusted_metrics,
    )
    return payload


def _build_runtime_config(
    llm_timeout_seconds: int,
    throttle_seconds: float,
    api_budget: int,
    pipeline_mode: str,
    run_parallel: bool,
) -> dict[str, Any]:
    """Build the runtime_config dict for JSON output."""
    return {
        "llm_timeout_seconds": llm_timeout_seconds,
        "max_correction_retries": MAX_CORRECTION_RETRIES,
        "max_semantic_retries": MAX_SEMANTIC_RETRIES,
        "max_plan_validation_attempts": MAX_PLAN_VALIDATION_ATTEMPTS,
        "use_semantic_loop": USE_SEMANTIC_LOOP,
        "system_plan_based": True,
        "api_max_retries": API_MAX_RETRIES,
        "api_recovery_rounds": API_RECOVERY_ROUNDS,
        "api_recovery_cooldown_seconds": API_RECOVERY_COOLDOWN_SECONDS,
        "throttle_seconds": throttle_seconds,
        "api_budget_per_query": api_budget,
        "pipeline_mode": pipeline_mode,
        "run_parallel": run_parallel,
    }


def _evaluate_one_example(
    example: SpiderExample,
    llm_client: LLMClient,
    throttler: RequestThrottler,
    schema_cache: dict[str, str],
    schema_dict_cache: dict[str, dict[str, Any]] | None = None,
    pipeline_mode: str = 'full',
    api_budget: int = DEFAULT_API_BUDGET_CLOUD,
    run_parallel: bool = False,
    llm_timeout_seconds: int = MIN_LLM_TIMEOUT_SECONDS,
    top_k_tables: int = DEFAULT_TOP_K_TABLES,
    model_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    query_start = time.perf_counter()
    db_key = str(Path(example.db_path).resolve())
    full_schema_text = schema_cache.get(db_key)
    if full_schema_text is None:
        full_schema_text = build_rich_schema_context(example.db_path)
        schema_cache[db_key] = full_schema_text

    # Build schema dict for pre-validation (Change 7)
    schema_dict: dict[str, Any] = {}
    if schema_dict_cache is not None:
        schema_dict = schema_dict_cache.get(db_key, {})
        if not schema_dict:
            schema_dict = build_schema_dict(example.db_path)
            schema_dict_cache[db_key] = schema_dict
    else:
        schema_dict = build_schema_dict(example.db_path)

    # --- SCHEMA PRUNING (Step 1) ---
    # Prune the schema to only relevant tables before sending to LLM
    schema = build_pruned_schema_context(
        nl_query=example.question,
        full_schema=schema_dict,
        full_schema_text=full_schema_text,
        top_k=top_k_tables,
    )

    if pipeline_mode == 'direct':
        # --- DIRECT MODE: fair A/B test ---
        # 1. Generate SQL once (baseline)
        # 2. Run that SAME SQL through QueryShield pipeline (system)
        # This isolates the error correction value from LLM randomness.
        baseline_start = time.perf_counter()
        baseline = _run_baseline(
            example=example, schema=schema, llm_client=llm_client, throttler=throttler,
        )
        baseline_runtime_sec = round(time.perf_counter() - baseline_start, 3)
        system_start = time.perf_counter()
        system = _run_system(
            example=example, schema=schema, llm_client=llm_client, throttler=throttler,
            pipeline_mode=pipeline_mode, api_budget=api_budget, schema_dict=schema_dict,
            model_profile=model_profile,
            baseline_sql=baseline.get("sql", ""),
        )
        system_runtime_sec = round(time.perf_counter() - system_start, 3)
        if system.get('correct') and not baseline.get('correct'):
            parallel_winner = 'system'
        elif baseline.get('correct') and not system.get('correct'):
            parallel_winner = 'baseline'
        else:
            parallel_winner = 'tie'
    elif run_parallel:
        # Parallel execution mode (Change 6)
        # Ensure system and baseline get equal, halved time budget for fair comparison
        parallel_timeout_seconds = max(5, llm_timeout_seconds // 2)
        baseline_client = _clone_llm_client(llm_client)
        baseline_client.timeout_seconds = parallel_timeout_seconds
        system_client = _clone_llm_client(llm_client)
        system_client.timeout_seconds = parallel_timeout_seconds

        timeout = parallel_timeout_seconds * (MAX_CORRECTION_RETRIES + 2)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            baseline_throttler = RequestThrottler(min_interval_seconds=throttler.min_interval_seconds)
            system_throttler = RequestThrottler(min_interval_seconds=throttler.min_interval_seconds)
            baseline_future = executor.submit(
                _run_baseline, example, schema, baseline_client, baseline_throttler,
            )
            system_future = executor.submit(
                _run_system, example, schema, system_client, system_throttler,
                pipeline_mode, api_budget, schema_dict, model_profile,
            )
            first_success_time = None
            parallel_winner = 'tie'
            try:
                done, _ = concurrent.futures.wait(
                    [baseline_future, system_future],
                    timeout=timeout,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                first_done_time = time.perf_counter()
                # Get both results (wait for the other one too)
                baseline = baseline_future.result(timeout=max(timeout - (first_done_time - query_start), 5))
                system = system_future.result(timeout=max(timeout - (first_done_time - query_start), 5))
            except concurrent.futures.TimeoutError:
                baseline = baseline_future.result() if baseline_future.done() else _error_result('timeout')
                system = system_future.result() if system_future.done() else _error_result('timeout')

            if system.get('correct') and not baseline.get('correct'):
                parallel_winner = 'system'
            elif baseline.get('correct') and not system.get('correct'):
                parallel_winner = 'baseline'
            else:
                parallel_winner = 'tie'

        baseline_runtime_sec = 0.0  # not tracked separately in parallel
        system_runtime_sec = 0.0
    else:
        # Sequential execution (default)
        baseline_start = time.perf_counter()
        baseline = _run_baseline(
            example=example, schema=schema, llm_client=llm_client, throttler=throttler,
        )
        baseline_runtime_sec = round(time.perf_counter() - baseline_start, 3)
        system_start = time.perf_counter()
        system = _run_system(
            example=example, schema=schema, llm_client=llm_client, throttler=throttler,
            pipeline_mode=pipeline_mode, api_budget=api_budget, schema_dict=schema_dict,
            model_profile=model_profile,
        )
        system_runtime_sec = round(time.perf_counter() - system_start, 3)
        parallel_winner = 'n/a'

    query_runtime_sec = round(time.perf_counter() - query_start, 3)

    complexity = analyze_complexity(example.question, example.gold_sql)
    winner = _pick_winner(
        baseline_correct=baseline["correct"],
        system_correct=system["correct"],
        baseline_exec_success=baseline["execution_success"],
        system_exec_success=system["execution_success"],
    )

    return {
        "db_id": example.db_id,
        "example_id": example.example_id,
        "question": example.question,
        "gold_sql": example.gold_sql,
        "baseline_sql": baseline["sql"],
        "system_sql": system["sql"],
        "baseline_correct": baseline["correct"],
        "system_correct": system["correct"],
        "baseline_execution_success": baseline["execution_success"],
        "system_execution_success": system["execution_success"],
        "baseline_classification": baseline["classification"],
        "system_classification": system["classification"],
        "baseline_failure_type": baseline["failure_type"],
        "system_failure_type": system["failure_type"],
        "baseline_api_failures": baseline["api_failures"],
        "system_api_failures": system["api_failures"],
        "baseline_retries_used": baseline["retries_used"],
        "system_retries_used": system["retries_used"],
        "baseline_retry_success": baseline["retry_success"],
        "system_retry_success": system["retry_success"],
        "system_semantic_corrections_used": system["semantic_corrections_used"],
        "system_semantic_success": system["semantic_success"],
        "system_semantic_validation_decision": system["semantic_validation_decision"],
        "system_semantic_validation_reason": system["semantic_validation_reason"],
        "system_semantic_trace": system["semantic_trace"],
        "system_plan": system["plan"],
        "system_plan_raw": system["plan_raw"],
        "system_plan_parse_error": system["plan_parse_error"],
        "system_plan_quality": system["plan_quality"],
        "system_plan_quality_score": system["plan_quality_score"],
        "system_plan_quality_reasons": system["plan_quality_reasons"],
        "system_planner_api_failures": system["planner_api_failures"],
        "system_planner_retries_used": system["planner_retries_used"],
        "system_planner_retry_success": system["planner_retry_success"],
        "system_plan_validation_failures": system["plan_validation_failures"],
        "system_plan_correction_success": system["plan_correction_success"],
        "system_plan_validation_trace": system["plan_validation_trace"],
        "system_plan_validation_attempts_used": system["plan_validation_attempts_used"],
        "baseline_runtime_sec": baseline_runtime_sec,
        "system_runtime_sec": system_runtime_sec,
        "query_runtime_sec": query_runtime_sec,
        "attempts_used": system["attempts_used"],
        "winner": winner,
        "baseline_error": baseline["error"],
        "system_error": system["error"],
        "is_complex": complexity.is_complex,
        "complexity_score": complexity.score,
        "complexity_reasons": list(complexity.reasons),
        "notes": _build_notes(baseline=baseline, system=system, winner=winner),
        # Change 1: Budget tracking
        "budget_exhausted_stages": system.get("budget_exhausted_stages", []),
        "budget_log": system.get("budget_log", []),
        # Change 3: Confidence gating
        "plan_validator_confidence": system.get("plan_validator_confidence", None),
        "invalidation_severity_breakdown": system.get("invalidation_severity_breakdown", {}),
        # Change 5: Deterministic fixes
        "deterministic_fixes_applied": system.get("deterministic_fixes_applied", []),
        "llm_corrections_saved": system.get("llm_corrections_saved", 0),
        # Change 6: Parallel execution
        "parallel_winner": parallel_winner,
        # Change 7: Schema pre-validation
        "schema_pre_validation_result": system.get("schema_pre_validation_result", None),
        # Change 2: Pipeline mode
        "pipeline_mode": pipeline_mode,
    }


def _error_result(reason: str) -> dict[str, Any]:
    """Return a minimal error result dict for timeout/failure cases."""
    return {
        "sql": "", "error": reason, "execution_success": False, "correct": False,
        "classification": "api_error", "failure_type": "api_error",
        "api_failures": 1, "retries_used": 0, "retry_success": False,
        "attempts_used": 0, "semantic_corrections_used": 0, "semantic_success": False,
        "semantic_validation_decision": "NOT_RUN", "semantic_validation_reason": reason,
        "semantic_trace": [], "plan": {}, "plan_raw": "", "plan_parse_error": reason,
        "plan_quality": "low", "plan_quality_score": 0.0, "plan_quality_reasons": [],
        "planner_api_failures": 0, "planner_retries_used": 0, "planner_retry_success": False,
        "plan_validation_failures": 0, "plan_correction_success": False,
        "plan_validation_trace": [], "plan_validation_attempts_used": 0,
        "budget_exhausted_stages": [], "budget_log": [],
        "plan_validator_confidence": None, "invalidation_severity_breakdown": {},
        "deterministic_fixes_applied": [], "llm_corrections_saved": 0,
        "schema_pre_validation_result": None,
    }


def _run_baseline(
    example: SpiderExample,
    schema: str,
    llm_client: LLMClient,
    throttler: RequestThrottler,
) -> dict[str, Any]:
    """
    Baseline flow:
    - one LLM call with common prompt
    - no execution feedback loop
    - no correction retries
    """
    prompt = build_common_prompt(schema=schema, question=example.question)
    generation = _generate_with_resilience(
        llm_client=llm_client,
        prompt=prompt,
        throttler=throttler,
    )
    if generation["api_error"] is not None:
        return {
            "sql": "",
            "error": str(generation["api_error"]),
            "execution_success": False,
            "correct": False,
            "classification": "api_error",
            "failure_type": "api_error",
            "api_failures": 1,
            "retries_used": int(generation["retries_used"]),
            "retry_success": bool(generation["retry_success"]),
            "attempts_used": 1,
        }
    sql = str(generation["sql"]).strip()

    eval_result = evaluate_sql_prediction(
        db_path=example.db_path,
        predicted_sql=sql,
        gold_sql=example.gold_sql,
    )
    return {
        "sql": sql,
        "error": eval_result["predicted_error"],
        "execution_success": bool(eval_result["execution_success"]),
        "correct": bool(eval_result["correct"]),
        "classification": str(eval_result["classification"]),
        "failure_type": str(eval_result["failure_type"]),
        "api_failures": 0,
        "retries_used": int(generation["retries_used"]),
        "retry_success": bool(generation["retry_success"]),
        "attempts_used": 1,
    }


def _run_system(
    example: SpiderExample,
    schema: str,
    llm_client: LLMClient,
    throttler: RequestThrottler,
    pipeline_mode: str = 'full',
    api_budget: int = DEFAULT_API_BUDGET_CLOUD,
    schema_dict: dict[str, Any] | None = None,
    model_profile: dict[str, Any] | None = None,
    baseline_sql: str | None = None,
) -> dict[str, Any]:
    """
    System flow (plan-based with budget/mode/error-router/schema-validation):
    1. Question/schema -> plan (skip in 'direct' mode)
    2. Plan/schema -> SQL
    3. Schema pre-validate + deterministic fix
    4. Execute and compare
    5. If execution fails, deterministic fix then LLM correction retry
    """
    budget = BudgetTracker(max_calls=api_budget)
    error_router = DeterministicErrorRouter()
    schema_pre_validator = SchemaPreValidator()
    deterministic_fixes: list[str] = []
    llm_corrections_saved = 0
    schema_pre_val_result: dict[str, Any] | None = None
    plan_validator_confidence: float | None = None
    severity_breakdown: dict[str, int] = {}
    extra_fields: dict[str, Any] = {}

    # --- PLANNER STAGE ---
    if pipeline_mode == 'direct':
        # Skip planner entirely in direct mode
        plan = {"intent": example.question.strip(), "tables": [], "joins": [],
                "filters": [], "aggregations": [], "group_by": [], "order_by": [],
                "limit": "", "subqueries": [], "reasoning_steps": ["direct_mode"]}
        plan_raw = ""
        plan_parse_error = "direct_mode: planner skipped"
        planner_api_failures = 0
        planner_retries_used = 0
        planner_retry_success = False
    else:
        if not budget.consume("planner"):
            plan = {"intent": example.question.strip(), "tables": [], "joins": [],
                    "filters": [], "aggregations": [], "group_by": [], "order_by": [],
                    "limit": "", "subqueries": [], "reasoning_steps": ["budget_exhausted"]}
            plan_raw = ""
            plan_parse_error = "budget_exhausted"
            planner_api_failures = 0
            planner_retries_used = 0
            planner_retry_success = False
        else:
            planner_prompt = build_planner_prompt(schema=schema, question=example.question)
            planner_generation = _generate_text_with_resilience(
                llm_client=llm_client, prompt=planner_prompt, throttler=throttler,
            )
            planner_api_error = planner_generation["api_error"]
            planner_api_failures = 1 if planner_api_error is not None else 0
            planner_retries_used = int(planner_generation["retries_used"])
            planner_retry_success = bool(planner_generation["retry_success"])
            plan_raw = str(planner_generation.get("text") or "").strip()
            # Strip reasoning model thinking blocks (Step 2)
            if model_profile and model_profile.get("strip_thinking"):
                plan_raw = strip_thinking_blocks(plan_raw)
            if planner_api_error is None:
                plan, plan_parse_error = parse_plan_response(plan_raw)
            else:
                plan = {"intent": example.question.strip(), "tables": [], "joins": [],
                        "filters": [], "aggregations": [], "group_by": [], "order_by": [],
                        "limit": "", "subqueries": [],
                        "reasoning_steps": ["Planner failed due to API error. Fallback intent-only plan was used."]}
                plan_parse_error = f"planner_api_error: {planner_api_error}"

    plan_quality = assess_plan_quality(plan)
    planning_fields = {
        "plan": plan, "plan_raw": plan_raw, "plan_parse_error": plan_parse_error,
        "plan_quality": str(plan_quality["level"]),
        "plan_quality_score": float(plan_quality["score"]),
        "plan_quality_reasons": list(plan_quality["missing"]),
        "planner_api_failures": planner_api_failures,
        "planner_retries_used": planner_retries_used,
        "planner_retry_success": planner_retry_success,
    }

    # --- SQL GENERATION STAGE ---
    if pipeline_mode == 'direct':
        prompt = build_common_prompt(schema=schema, question=example.question)
    else:
        prompt = build_sql_from_plan_prompt(plan=plan, schema=schema)
    retries_used_total = 0
    retry_success = False
    plan_validation_failures_total = 0
    plan_correction_success_any = False
    plan_validation_attempts_used_total = 0
    plan_validation_trace_all: list[dict[str, Any]] = []

    for attempt in range(1, MAX_CORRECTION_RETRIES + 2):
        # --- DIRECT MODE: reuse baseline SQL, skip LLM generation ---
        if pipeline_mode == 'direct' and baseline_sql is not None and attempt == 1:
            generated_sql = baseline_sql.strip()
            budget.consume("sql_generation_reused")
        else:
            if not budget.consume("sql_generation"):
                break  # fall through to final return

            generation = _generate_with_resilience(
                llm_client=llm_client, prompt=prompt, throttler=throttler,
            )
            retries_used_total += int(generation["retries_used"])
            retry_success = retry_success or bool(generation["retry_success"])

            if generation["api_error"] is not None:
                if attempt <= MAX_CORRECTION_RETRIES:
                    continue
                return {
                    "sql": "", "error": str(generation["api_error"]),
                    "execution_success": False, "correct": False,
                    "classification": "api_error", "failure_type": "api_error",
                    "api_failures": 1, "retries_used": retries_used_total,
                    "retry_success": retry_success, "attempts_used": attempt,
                    "semantic_corrections_used": 0, "semantic_success": False,
                    "semantic_validation_decision": "NOT_RUN",
                    "semantic_validation_reason": "api_error", "semantic_trace": [],
                    "plan_validation_failures": plan_validation_failures_total,
                    "plan_correction_success": plan_correction_success_any,
                    "plan_validation_trace": plan_validation_trace_all,
                    "plan_validation_attempts_used": plan_validation_attempts_used_total,
                    "budget_exhausted_stages": budget.exhausted_stages,
                    "budget_log": budget.stage_log,
                    "plan_validator_confidence": plan_validator_confidence,
                    "invalidation_severity_breakdown": severity_breakdown,
                    "deterministic_fixes_applied": deterministic_fixes,
                    "llm_corrections_saved": llm_corrections_saved,
                    "schema_pre_validation_result": schema_pre_val_result,
                    **planning_fields,
                }

            generated_sql = str(generation["sql"]).strip()

        # --- PLAN VALIDATION STAGE (skip in lite/direct mode) ---
        if pipeline_mode == 'full' and budget.remaining >= 3:
            if budget.consume("plan_validation"):
                enforcement = _enforce_plan_constraints(
                    plan=plan, schema=schema, sql=generated_sql,
                    llm_client=llm_client, throttler=throttler, budget=budget,
                    validator_suffix=(
                        model_profile.get("validator_suffix", "") if model_profile else ""
                    ),
                )
                sql = str(enforcement["sql"]).strip()
                retries_used_total += int(enforcement["retries_used"])
                retry_success = retry_success or bool(enforcement["retry_success"])
                plan_validation_failures_total += int(enforcement["plan_validation_failures"])
                plan_validation_attempts_used_total += int(enforcement["attempts_used"])
                plan_correction_success_any = (
                    plan_correction_success_any or bool(enforcement["correction_success"])
                )
                plan_validation_trace_all.extend(list(enforcement["trace"]))
                plan_validator_confidence = enforcement.get("last_confidence")
                severity_breakdown = enforcement.get("severity_breakdown", {})

                if not bool(enforcement["is_valid"]):
                    if attempt <= MAX_CORRECTION_RETRIES:
                        issues = list(enforcement["issues"])
                        issue_strs = []
                        for iss in issues:
                            if isinstance(iss, dict):
                                issue_strs.append(iss.get("description", str(iss)))
                            else:
                                issue_strs.append(str(iss))
                        prompt = build_sql_fix_from_plan_prompt(
                            plan=plan, sql=sql, issues=issue_strs, schema=schema,
                        )
                        continue
                    return {
                        "sql": sql,
                        "error": "plan_validation_failed: " + "; ".join(
                            (x.get("description", str(x)) if isinstance(x, dict) else str(x))
                            for x in enforcement["issues"]
                        ),
                        "execution_success": False, "correct": False,
                        "classification": "incorrect_sql", "failure_type": "incorrect_sql",
                        "api_failures": 0, "retries_used": retries_used_total,
                        "retry_success": retry_success, "attempts_used": attempt,
                        "semantic_corrections_used": 0, "semantic_success": False,
                        "semantic_validation_decision": "NOT_RUN",
                        "semantic_validation_reason": "plan_validation_failed",
                        "semantic_trace": [],
                        "plan_validation_failures": plan_validation_failures_total,
                        "plan_correction_success": plan_correction_success_any,
                        "plan_validation_trace": plan_validation_trace_all,
                        "plan_validation_attempts_used": plan_validation_attempts_used_total,
                        "budget_exhausted_stages": budget.exhausted_stages,
                        "budget_log": budget.stage_log,
                        "plan_validator_confidence": plan_validator_confidence,
                        "invalidation_severity_breakdown": severity_breakdown,
                        "deterministic_fixes_applied": deterministic_fixes,
                        "llm_corrections_saved": llm_corrections_saved,
                        "schema_pre_validation_result": schema_pre_val_result,
                        **planning_fields,
                    }
            else:
                sql = generated_sql
        else:
            sql = generated_sql

        # --- SCHEMA PRE-VALIDATION (Change 7) ---
        if schema_dict:
            try:
                schema_pre_val_result = schema_pre_validator.validate(sql, schema_dict)
                if schema_pre_val_result.get("errors"):
                    fixable_errors = [e for e in schema_pre_val_result["errors"] if e.get("fixable")]
                    for err in fixable_errors:
                        fixed_sql, fix_desc = error_router.try_deterministic_fix(
                            sql, f"schema_pre_validation: {err['type']}: {err['detail']}", schema_dict,
                        )
                        if fixed_sql:
                            sql = fixed_sql
                            deterministic_fixes.append(fix_desc)
            except Exception:
                pass  # schema pre-validation is best-effort

        # --- EXECUTION ---
        eval_result = evaluate_sql_prediction(
            db_path=example.db_path, predicted_sql=sql, gold_sql=example.gold_sql,
        )
        classification = str(eval_result["classification"])

        if classification != "incorrect_sql":
            # --- SEMANTIC LOOP (strict gate: only if SQL ran but got ZERO rows) ---
            # NEVER run if SQL returned rows — it's likely correct.
            # NEVER run if SQL failed to execute — use execution correction instead.
            predicted_rows = list(eval_result.get("predicted_rows", []))
            result_row_count = len(predicted_rows)
            should_run_semantic = (
                USE_SEMANTIC_LOOP
                and pipeline_mode in ('full', 'direct')
                and budget.remaining >= 4
                and bool(eval_result.get("execution_success"))
                and result_row_count == 0
            )
            if not should_run_semantic:
                return {
                    "sql": sql, "error": eval_result["predicted_error"],
                    "execution_success": bool(eval_result["execution_success"]),
                    "correct": bool(eval_result["correct"]),
                    "classification": classification,
                    "failure_type": str(eval_result["failure_type"]),
                    "api_failures": 0, "retries_used": retries_used_total,
                    "retry_success": retry_success, "attempts_used": attempt,
                    "semantic_corrections_used": 0, "semantic_success": False,
                    "semantic_validation_decision": "NOT_RUN",
                    "semantic_validation_reason": "skipped",
                    "semantic_trace": [],
                    "plan_validation_failures": plan_validation_failures_total,
                    "plan_correction_success": plan_correction_success_any,
                    "plan_validation_trace": plan_validation_trace_all,
                    "plan_validation_attempts_used": plan_validation_attempts_used_total,
                    "budget_exhausted_stages": budget.exhausted_stages,
                    "budget_log": budget.stage_log,
                    "plan_validator_confidence": plan_validator_confidence,
                    "invalidation_severity_breakdown": severity_breakdown,
                    "deterministic_fixes_applied": deterministic_fixes,
                    "llm_corrections_saved": llm_corrections_saved,
                    "schema_pre_validation_result": schema_pre_val_result,
                    **planning_fields,
                }
            budget.consume("semantic_loop")
            semantic = run_semantic_loop(
                question=example.question, schema=schema,
                initial_sql=sql,
                initial_rows=list(eval_result.get("predicted_rows", [])),
                llm_client=llm_client, throttler=throttler,
                execute_sql=lambda candidate_sql: execute_sql(
                    db_path=example.db_path, sql=candidate_sql,
                ),
                max_semantic_retries=MAX_SEMANTIC_RETRIES,
                max_api_retries=API_MAX_RETRIES,
            )
            final_eval = evaluate_sql_prediction(
                db_path=example.db_path,
                predicted_sql=semantic["sql"],
                gold_sql=example.gold_sql,
            )
            return {
                "sql": semantic["sql"], "error": final_eval["predicted_error"],
                "execution_success": bool(final_eval["execution_success"]),
                "correct": bool(final_eval["correct"]),
                "classification": str(final_eval["classification"]),
                "failure_type": str(final_eval["failure_type"]),
                "api_failures": 0, "retries_used": retries_used_total,
                "retry_success": retry_success, "attempts_used": attempt,
                "semantic_corrections_used": semantic["semantic_corrections_used"],
                "semantic_success": semantic["semantic_success"],
                "semantic_validation_decision": semantic["validation_decision"],
                "semantic_validation_reason": semantic["validation_reason"],
                "semantic_trace": semantic["semantic_trace"],
                "plan_validation_failures": plan_validation_failures_total,
                "plan_correction_success": plan_correction_success_any,
                "plan_validation_trace": plan_validation_trace_all,
                "plan_validation_attempts_used": plan_validation_attempts_used_total,
                "budget_exhausted_stages": budget.exhausted_stages,
                "budget_log": budget.stage_log,
                "plan_validator_confidence": plan_validator_confidence,
                "invalidation_severity_breakdown": severity_breakdown,
                "deterministic_fixes_applied": deterministic_fixes,
                "llm_corrections_saved": llm_corrections_saved,
                "schema_pre_validation_result": schema_pre_val_result,
                **planning_fields,
            }

        # --- EXECUTION CORRECTION with deterministic fix first (Change 5) ---
        if attempt <= MAX_CORRECTION_RETRIES and budget.remaining >= 2:
            error_msg = str(eval_result["predicted_error"] or "Unknown execution error.")
            # Try deterministic fix first
            fixed_sql, fix_desc = error_router.try_deterministic_fix(sql, error_msg, schema_dict)
            if fixed_sql:
                det_eval = evaluate_sql_prediction(
                    db_path=example.db_path, predicted_sql=fixed_sql, gold_sql=example.gold_sql,
                )
                if det_eval["classification"] != "incorrect_sql":
                    deterministic_fixes.append(fix_desc)
                    llm_corrections_saved += 1
                    sql = fixed_sql
                    eval_result = det_eval
                    classification = str(eval_result["classification"])
                    # Return success with deterministic fix
                    return {
                        "sql": sql, "error": eval_result["predicted_error"],
                        "execution_success": bool(eval_result["execution_success"]),
                        "correct": bool(eval_result["correct"]),
                        "classification": classification,
                        "failure_type": str(eval_result["failure_type"]),
                        "api_failures": 0, "retries_used": retries_used_total,
                        "retry_success": retry_success, "attempts_used": attempt,
                        "semantic_corrections_used": 0, "semantic_success": False,
                        "semantic_validation_decision": "NOT_RUN",
                        "semantic_validation_reason": "deterministic_fix_applied",
                        "semantic_trace": [],
                        "plan_validation_failures": plan_validation_failures_total,
                        "plan_correction_success": plan_correction_success_any,
                        "plan_validation_trace": plan_validation_trace_all,
                        "plan_validation_attempts_used": plan_validation_attempts_used_total,
                        "budget_exhausted_stages": budget.exhausted_stages,
                        "budget_log": budget.stage_log,
                        "plan_validator_confidence": plan_validator_confidence,
                        "invalidation_severity_breakdown": severity_breakdown,
                        "deterministic_fixes_applied": deterministic_fixes,
                        "llm_corrections_saved": llm_corrections_saved,
                        "schema_pre_validation_result": schema_pre_val_result,
                        **planning_fields,
                    }
                else:
                    deterministic_fixes.append(f"{fix_desc}:still_failed")

            # Fall through to LLM correction
            budget.consume("execution_correction")
            prompt = build_correction_prompt(
                schema=schema, question=example.question,
                failed_sql=sql, error=error_msg,
            )
            continue

        return {
            "sql": sql, "error": eval_result["predicted_error"],
            "execution_success": False, "correct": False,
            "classification": classification,
            "failure_type": str(eval_result["failure_type"]),
            "api_failures": 0, "retries_used": retries_used_total,
            "retry_success": retry_success, "attempts_used": attempt,
            "semantic_corrections_used": 0, "semantic_success": False,
            "semantic_validation_decision": "NOT_RUN",
            "semantic_validation_reason": "execution_failed",
            "semantic_trace": [],
            "plan_validation_failures": plan_validation_failures_total,
            "plan_correction_success": plan_correction_success_any,
            "plan_validation_trace": plan_validation_trace_all,
            "plan_validation_attempts_used": plan_validation_attempts_used_total,
            "budget_exhausted_stages": budget.exhausted_stages,
            "budget_log": budget.stage_log,
            "plan_validator_confidence": plan_validator_confidence,
            "invalidation_severity_breakdown": severity_breakdown,
            "deterministic_fixes_applied": deterministic_fixes,
            "llm_corrections_saved": llm_corrections_saved,
            "schema_pre_validation_result": schema_pre_val_result,
            **planning_fields,
        }

    return {
        "sql": "", "error": "Unknown system execution state.",
        "execution_success": False, "correct": False,
        "classification": "incorrect_sql", "failure_type": "incorrect_sql",
        "api_failures": 0, "retries_used": retries_used_total,
        "retry_success": retry_success,
        "attempts_used": MAX_CORRECTION_RETRIES + 1,
        "semantic_corrections_used": 0, "semantic_success": False,
        "semantic_validation_decision": "NOT_RUN",
        "semantic_validation_reason": "unknown_state", "semantic_trace": [],
        "plan_validation_failures": plan_validation_failures_total,
        "plan_correction_success": plan_correction_success_any,
        "plan_validation_trace": plan_validation_trace_all,
        "plan_validation_attempts_used": plan_validation_attempts_used_total,
        "budget_exhausted_stages": budget.exhausted_stages,
        "budget_log": budget.stage_log,
        "plan_validator_confidence": plan_validator_confidence,
        "invalidation_severity_breakdown": severity_breakdown,
        "deterministic_fixes_applied": deterministic_fixes,
        "llm_corrections_saved": llm_corrections_saved,
        "schema_pre_validation_result": schema_pre_val_result,
        **planning_fields,
    }


def _enforce_plan_constraints(
    *,
    plan: dict[str, Any],
    schema: str,
    sql: str,
    llm_client: LLMClient,
    throttler: RequestThrottler,
    budget: BudgetTracker | None = None,
    validator_suffix: str = "",
) -> dict[str, Any]:
    """
    Strictly enforce SQL-plan alignment before execution.
    Uses confidence gating (Change 3): only invalidate if confidence >= 0.65
    and at least one CRITICAL issue exists.
    """
    current_sql = sql.strip()
    trace: list[dict[str, Any]] = []
    plan_validation_failures = 0
    retries_used_total = 0
    retry_success = False
    correction_success = False
    last_issues: list[Any] = []
    last_confidence: float | None = None
    severity_breakdown: dict[str, int] = {}

    for enforcement_attempt in range(1, MAX_PLAN_VALIDATION_ATTEMPTS + 1):
        sql_before = current_sql
        validation = validate_sql_plan(
            plan=plan, sql=sql_before,
            llm_client=llm_client, throttler=throttler,
            max_api_retries=API_MAX_RETRIES,
            validator_suffix=validator_suffix,
        )
        retries_used_total += int(validation["retries_used"])
        retry_success = retry_success or bool(validation["retry_success"])

        decision = str(validation["decision"])
        confidence = float(validation.get("confidence", 0.5))
        last_confidence = confidence
        issues = list(validation.get("issues", []))

        # Build severity breakdown
        for iss in issues:
            if isinstance(iss, dict):
                sev = iss.get("severity", "WARNING")
                severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1

        # Confidence gating (Change 3): only invalidate if confidence >= 0.65
        # and at least one CRITICAL issue
        has_critical = any(
            isinstance(iss, dict) and iss.get("severity") == "CRITICAL"
            for iss in issues
        )
        effective_invalid = (
            decision == "INVALID" and confidence >= 0.65 and has_critical
        )

        if not effective_invalid:
            # Treat as VALID (either truly valid, or low-confidence invalidation)
            trace.append({
                "attempts_used": enforcement_attempt, "decision": decision,
                "confidence": confidence,
                "sql_before": sql_before, "validation_issues": [],
                "sql_after": sql_before,
                "note": "valid" if decision == "VALID" else "low_confidence_invalidation",
            })
            if plan_validation_failures > 0:
                correction_success = True
            return {
                "sql": sql_before, "is_valid": True, "issues": [],
                "plan_validation_failures": plan_validation_failures,
                "correction_success": correction_success,
                "attempts_used": enforcement_attempt, "trace": trace,
                "retries_used": retries_used_total, "retry_success": retry_success,
                "last_confidence": last_confidence,
                "severity_breakdown": severity_breakdown,
            }

        plan_validation_failures += 1
        last_issues = issues if issues else [{"description": "SQL does not match plan constraints.", "severity": "CRITICAL"}]
        fix_suggestions = list(validation.get("fix_suggestions", []))
        next_sql = sql_before

        if enforcement_attempt < MAX_PLAN_VALIDATION_ATTEMPTS:
            # Convert issues to string list for fix prompt
            issue_strs = []
            for iss in (fix_suggestions or last_issues):
                if isinstance(iss, dict):
                    issue_strs.append(iss.get("description", str(iss)))
                else:
                    issue_strs.append(str(iss))
            regen_prompt = build_sql_fix_from_plan_prompt(
                plan=plan, sql=sql_before, issues=issue_strs, schema=schema,
            )
            if budget and not budget.consume("plan_validation_regen"):
                pass  # skip regen if budget exhausted
            else:
                regeneration = _generate_with_resilience(
                    llm_client=llm_client, prompt=regen_prompt, throttler=throttler,
                )
                retries_used_total += int(regeneration["retries_used"])
                retry_success = retry_success or bool(regeneration["retry_success"])
                if regeneration["api_error"] is None:
                    candidate_sql = str(regeneration["sql"]).strip()
                    if candidate_sql:
                        next_sql = candidate_sql
                else:
                    last_issues.append({"description": str(regeneration["api_error"]), "severity": "WARNING"})

        trace.append({
            "attempts_used": enforcement_attempt, "decision": "INVALID",
            "confidence": confidence,
            "sql_before": sql_before, "validation_issues": last_issues,
            "sql_after": next_sql,
        })
        current_sql = next_sql

    return {
        "sql": current_sql, "is_valid": False, "issues": last_issues,
        "plan_validation_failures": plan_validation_failures,
        "correction_success": correction_success,
        "attempts_used": MAX_PLAN_VALIDATION_ATTEMPTS, "trace": trace,
        "retries_used": retries_used_total, "retry_success": retry_success,
        "last_confidence": last_confidence,
        "severity_breakdown": severity_breakdown,
    }


def _pick_winner(
    baseline_correct: bool,
    system_correct: bool,
    baseline_exec_success: bool,
    system_exec_success: bool,
) -> str:
    if system_correct and not baseline_correct:
        return "system"
    if baseline_correct and not system_correct:
        return "baseline"
    if baseline_correct and system_correct:
        return "tie"
    if not baseline_exec_success and system_exec_success:
        return "system"
    if baseline_exec_success and not system_exec_success:
        return "baseline"
    return "tie"


def _build_notes(baseline: dict[str, Any], system: dict[str, Any], winner: str) -> str:
    baseline_error = baseline.get("error")
    system_error = system.get("error")

    if winner == "system":
        if baseline_error and not system_error:
            return f"System recovered baseline failure: {baseline_error}"
        return "System produced stronger final SQL."
    if winner == "baseline":
        if system_error and not baseline_error:
            return f"Baseline recovered system failure: {system_error}"
        return "Baseline produced stronger final SQL."
    if baseline_error and system_error:
        return f"Both failed (baseline: {baseline_error}; system: {system_error})"
    return "Both produced similar outcome."


def _generate_with_resilience(
    llm_client: LLMClient,
    prompt: str,
    throttler: RequestThrottler,
) -> dict[str, Any]:
    """
    Generate SQL with extra resilience for transient API/provider failures.

    Strategy:
    1. Use fixed-delay retry wrapper.
    2. If still failing, cool down and retry with a fresh client instance.
    """
    retries_used_total = 0
    retry_success = False
    api_error: str | None = None
    sql = ""
    active_client = llm_client

    for recovery_round in range(API_RECOVERY_ROUNDS):
        generation = generate_with_retry(
            llm=active_client,
            prompt=prompt,
            throttler=throttler,
            max_retries=API_MAX_RETRIES,
        )
        retries_used_total += int(generation["retries_used"])
        retry_success = retry_success or bool(generation["retry_success"])

        if generation["api_error"] is None:
            sql = str(generation["sql"])
            api_error = None
            break

        api_error = str(generation["api_error"])
        if recovery_round < API_RECOVERY_ROUNDS - 1:
            time.sleep(API_RECOVERY_COOLDOWN_SECONDS)
            active_client = _clone_llm_client(llm_client)

    return {
        "sql": sql,
        "api_error": api_error,
        "retries_used": retries_used_total,
        "retry_success": retry_success,
    }


def _generate_text_with_resilience(
    llm_client: LLMClient,
    prompt: str,
    throttler: RequestThrottler,
) -> dict[str, Any]:
    """
    Generate planner text with resilience for transient provider failures.

    Mirrors SQL retry/recovery behavior but calls `generate_text`.
    """
    retries_used_total = 0
    retry_success = False
    api_error: str | None = None
    text = ""
    active_client = llm_client

    for recovery_round in range(API_RECOVERY_ROUNDS):
        generation = _generate_text_with_retry(
            llm=active_client,
            prompt=prompt,
            throttler=throttler,
            max_retries=API_MAX_RETRIES,
        )
        retries_used_total += int(generation["retries_used"])
        retry_success = retry_success or bool(generation["retry_success"])

        if generation["api_error"] is None:
            text = str(generation["text"])
            api_error = None
            break

        api_error = str(generation["api_error"])
        if recovery_round < API_RECOVERY_ROUNDS - 1:
            time.sleep(API_RECOVERY_COOLDOWN_SECONDS)
            active_client = _clone_llm_client(llm_client)

    return {
        "text": text,
        "api_error": api_error,
        "retries_used": retries_used_total,
        "retry_success": retry_success,
    }


def _generate_text_with_retry(
    llm: LLMClient,
    prompt: str,
    throttler: RequestThrottler,
    max_retries: int,
) -> dict[str, Any]:
    """Generate raw model text with fixed-delay retry on provider failures."""
    retries_used = 0
    last_error = ""

    for retry_index in range(max_retries + 1):
        throttler.wait_turn()
        try:
            text = llm.generate_text(prompt)
            return {
                "text": text,
                "api_error": None,
                "retries_used": retries_used,
                "retry_success": retries_used > 0,
            }
        except Exception as exc:  # noqa: BLE001 - explicit provider failure handling
            last_error = str(exc)
            if retry_index < max_retries:
                time.sleep(RETRY_DELAY_SECONDS)
                retries_used += 1

    return {
        "text": "",
        "api_error": f"api_error: {last_error}",
        "retries_used": retries_used,
        "retry_success": False,
    }


def _clone_llm_client(llm_client: LLMClient) -> LLMClient:
    """Create a fresh client with the same provider/model settings."""
    return LLMClient(
        provider=llm_client.provider,
        model=llm_client.model,
        base_url=llm_client.base_url,
        api_key=",".join(llm_client.api_keys) if hasattr(llm_client, "api_keys") and llm_client.api_keys else None,
        timeout_seconds=max(llm_client.timeout_seconds, MIN_LLM_TIMEOUT_SECONDS),
    )


def _save_json(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def compute_adjusted_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute execution-adjusted accuracy metrics (Change 8).

    Accounts for both baseline and system performance to give a realistic picture.
    """
    total = len(rows)
    if total == 0:
        return {"adjusted_accuracy": 0.0, "system_exclusive_wins": 0,
                "baseline_exclusive_wins": 0, "both_correct": 0,
                "both_wrong": 0, "system_win_rate": 0.0,
                "baseline_fallback_rate": 0.0, "tie_rate": 0.0,
                "deterministic_fixes_total": 0, "llm_corrections_saved_total": 0,
                "budget_exhaustion_rate": 0.0}

    system_wins = sum(1 for r in rows if r.get("system_correct") and not r.get("baseline_correct"))
    baseline_wins = sum(1 for r in rows if r.get("baseline_correct") and not r.get("system_correct"))
    both_correct = sum(1 for r in rows if r.get("system_correct") and r.get("baseline_correct"))
    both_wrong = sum(1 for r in rows if not r.get("system_correct") and not r.get("baseline_correct"))

    # Adjusted accuracy: best-of-both (what would you get if you could pick the winner)
    adjusted_correct = system_wins + baseline_wins + both_correct
    adjusted_accuracy = round(adjusted_correct / total * 100, 2) if total else 0.0

    # Deterministic fix stats
    det_fixes_total = sum(len(r.get("deterministic_fixes_applied", [])) for r in rows)
    llm_saved_total = sum(r.get("llm_corrections_saved", 0) for r in rows)

    # Budget exhaustion rate
    budget_exhausted = sum(1 for r in rows if r.get("budget_exhausted_stages"))
    budget_exhaustion_rate = round(budget_exhausted / total * 100, 2)

    # Parallel winner stats (Change 6)
    parallel_rows = [r for r in rows if r.get("parallel_winner") not in (None, "n/a")]
    if parallel_rows:
        p_system = sum(1 for r in parallel_rows if r.get("parallel_winner") == "system")
        p_baseline = sum(1 for r in parallel_rows if r.get("parallel_winner") == "baseline")
        p_tie = sum(1 for r in parallel_rows if r.get("parallel_winner") == "tie")
        p_total = len(parallel_rows)
        system_win_rate = round(p_system / p_total * 100, 2)
        baseline_fallback_rate = round(p_baseline / p_total * 100, 2)
        tie_rate = round(p_tie / p_total * 100, 2)
    else:
        system_win_rate = round(system_wins / total * 100, 2)
        baseline_fallback_rate = round(baseline_wins / total * 100, 2)
        tie_rate = round((both_correct + both_wrong) / total * 100, 2)

    return {
        "adjusted_accuracy": adjusted_accuracy,
        "system_exclusive_wins": system_wins,
        "baseline_exclusive_wins": baseline_wins,
        "both_correct": both_correct,
        "both_wrong": both_wrong,
        "system_win_rate": system_win_rate,
        "baseline_fallback_rate": baseline_fallback_rate,
        "tie_rate": tie_rate,
        "deterministic_fixes_total": det_fixes_total,
        "llm_corrections_saved_total": llm_saved_total,
        "budget_exhaustion_rate": budget_exhaustion_rate,
    }


def _print_report(
    metrics: dict[str, Any],
    selected_count: int,
    subset_meta: dict[str, Any],
    adjusted_metrics: dict[str, Any] | None = None,
) -> None:
    print("Spider 2.0 Subset Evaluation Summary")
    print(f"- selected_queries: {selected_count}")
    print(f"- selected_db_ids: {subset_meta.get('selected_db_ids', [])}")
    print(f"- baseline_accuracy: {metrics['baseline_accuracy']}")
    print(f"- system_accuracy: {metrics['system_accuracy']}")
    print(f"- final_accuracy: {metrics.get('final_accuracy', metrics['system_accuracy'])}")
    print(f"- improvement %: {metrics['improvement_percent']}")
    print(
        f"- runtime: total_sec={metrics['total_runtime_sec']}, "
        f"avg_query_sec={metrics['avg_query_runtime_sec']}"
    )
    print(
        "- execution_success_rate: "
        f"baseline={metrics['baseline_execution_success_rate']}, "
        f"system={metrics['system_execution_success_rate']}"
    )
    print(
        "- complex_query_accuracy: "
        f"baseline={metrics['baseline_complex_query_accuracy']}, "
        f"system={metrics['system_complex_query_accuracy']}"
    )
    print(
        "- failures: "
        f"baseline_incorrect_sql={metrics['baseline_incorrect_sql']}, "
        f"system_incorrect_sql={metrics['system_incorrect_sql']}, "
        f"baseline_wrong_results={metrics['baseline_wrong_results']}, "
        f"system_wrong_results={metrics['system_wrong_results']}"
    )
    print(f"- retry_success_rate: {metrics['retry_success_rate']}")
    print(f"- semantic_corrections_used: {metrics['semantic_corrections_used']}")
    print(f"- semantic_success_rate: {metrics['semantic_success_rate']}")
    print(f"- plan_quality_avg: {metrics.get('plan_quality_avg', 0.0)}")
    print(
        "- plan_enforcement: "
        f"plan_validation_failures={metrics.get('plan_validation_failures', 0)}, "
        f"plan_correction_success_rate={metrics.get('plan_correction_success_rate', 0.0)}"
    )
    print(f"- logical_error_reduction: {metrics['logical_error_reduction']}")

    # Adjusted metrics (Change 8)
    if adjusted_metrics:
        print("--- Adjusted Metrics ---")
        print(f"- adjusted_accuracy: {adjusted_metrics['adjusted_accuracy']}%")
        print(f"- system_exclusive_wins: {adjusted_metrics['system_exclusive_wins']}")
        print(f"- baseline_exclusive_wins: {adjusted_metrics['baseline_exclusive_wins']}")
        print(f"- both_correct: {adjusted_metrics['both_correct']}")
        print(f"- both_wrong: {adjusted_metrics['both_wrong']}")
        print(f"- system_win_rate: {adjusted_metrics['system_win_rate']}%")
        print(f"- baseline_fallback_rate: {adjusted_metrics['baseline_fallback_rate']}%")
        print(f"- deterministic_fixes_total: {adjusted_metrics['deterministic_fixes_total']}")
        print(f"- llm_corrections_saved_total: {adjusted_metrics['llm_corrections_saved_total']}")
        print(f"- budget_exhaustion_rate: {adjusted_metrics['budget_exhaustion_rate']}%")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Spider 2.0 subset fair baseline-vs-system evaluation."
    )
    parser.add_argument(
        "--dataset-json",
        default=str(DEFAULT_DATASET_JSON),
        help="Path to Spider 2.0 subset JSON file.",
    )
    parser.add_argument(
        "--db-root",
        default=str(DEFAULT_DB_ROOT),
        help="Root directory that contains Spider SQLite databases.",
    )
    parser.add_argument(
        "--num-dbs",
        type=int,
        default=3,
        help="How many DBs to include in subset (>=1).",
    )
    parser.add_argument(
        "--num-queries",
        type=int,
        default=24,
        help="How many queries to include (>=1).",
    )
    parser.add_argument(
        "--llm-timeout-seconds",
        type=int,
        default=MIN_LLM_TIMEOUT_SECONDS,
        help="Per-LLM request timeout in seconds.",
    )
    parser.add_argument(
        "--api-max-retries",
        type=int,
        default=API_MAX_RETRIES,
        help="Max API retries per generation call.",
    )
    parser.add_argument(
        "--api-recovery-rounds",
        type=int,
        default=API_RECOVERY_ROUNDS,
        help="How many recovery rounds to attempt after API failure.",
    )
    parser.add_argument(
        "--api-recovery-cooldown-seconds",
        type=int,
        default=API_RECOVERY_COOLDOWN_SECONDS,
        help="Cooldown between API recovery rounds.",
    )
    parser.add_argument(
        "--max-correction-retries",
        type=int,
        default=MAX_CORRECTION_RETRIES,
        help="Max SQL correction retries after execution errors.",
    )
    parser.add_argument(
        "--max-semantic-retries",
        type=int,
        default=MAX_SEMANTIC_RETRIES,
        help="Max semantic correction retries after successful execution.",
    )
    parser.add_argument(
        "--max-plan-validation-attempts",
        type=int,
        default=MAX_PLAN_VALIDATION_ATTEMPTS,
        help="Max strict plan-validation attempts (validate + regenerate).",
    )
    parser.add_argument(
        "--disable-semantic-loop",
        action="store_true",
        help="Disable semantic validation/correction loop for comparator-style runs.",
    )
    parser.add_argument(
        "--throttle-seconds",
        type=float,
        default=DEFAULT_THROTTLE_SECONDS,
        help="Minimum delay between LLM requests in seconds (use 0 for full throttle).",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Where to save evaluation JSON output.",
    )
    # New args for Changes 1, 2, 6
    parser.add_argument(
        "--api-budget",
        type=int,
        default=None,
        help="Max LLM calls per query (default: 10 cloud, 6 ollama).",
    )
    parser.add_argument(
        "--pipeline-mode",
        type=str,
        default=None,
        choices=["full", "lite", "direct"],
        help="Force pipeline mode (auto-detect if omitted).",
    )
    parser.add_argument(
        "--run-parallel",
        action="store_true",
        help="Run baseline and system in parallel.",
    )
    parser.add_argument(
        "--top-k-tables",
        type=int,
        default=DEFAULT_TOP_K_TABLES,
        help="Max tables to keep after schema pruning (default 5).",
    )
    return parser.parse_args()


def main() -> None:
    global API_MAX_RETRIES, API_RECOVERY_ROUNDS, API_RECOVERY_COOLDOWN_SECONDS
    global MAX_CORRECTION_RETRIES, MAX_SEMANTIC_RETRIES, MAX_PLAN_VALIDATION_ATTEMPTS
    global USE_SEMANTIC_LOOP
    args = _parse_args()
    API_MAX_RETRIES = max(0, int(args.api_max_retries))
    API_RECOVERY_ROUNDS = max(1, int(args.api_recovery_rounds))
    API_RECOVERY_COOLDOWN_SECONDS = max(0, int(args.api_recovery_cooldown_seconds))
    MAX_CORRECTION_RETRIES = max(0, int(args.max_correction_retries))
    MAX_SEMANTIC_RETRIES = max(0, int(args.max_semantic_retries))
    MAX_PLAN_VALIDATION_ATTEMPTS = max(1, int(args.max_plan_validation_attempts))
    USE_SEMANTIC_LOOP = not bool(args.disable_semantic_loop)
    run_spider_evaluation(
        dataset_json=Path(args.dataset_json),
        db_root=Path(args.db_root),
        output_path=Path(args.output),
        num_dbs=args.num_dbs,
        num_queries=args.num_queries,
        llm_timeout_seconds=max(5, int(args.llm_timeout_seconds)),
        throttle_seconds=max(0.0, float(args.throttle_seconds)),
        api_budget_per_query=args.api_budget,
        force_pipeline_mode=args.pipeline_mode,
        run_parallel=args.run_parallel,
        top_k_tables=max(1, int(args.top_k_tables)),
    )


if __name__ == "__main__":
    main()
