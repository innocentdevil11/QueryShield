# QueryShield Project Progress Structured Report (Expanded)

Generated on: 2026-05-03
Report source: repository artifacts in `queryshield/evaluation` and related core/app modules.

## 1) What This Document Covers

This file is a comprehensive, structured audit of what has been built and benchmarked so far in QueryShield, including:

1. Project evolution and design decisions from baseline comparator to strict plan-enforced SQL generation.
2. Complete benchmark registry discovered in the repository (including archive and in-progress outputs).
3. Runtime configs and metrics used across runs.
4. Detailed code-level map of the evaluation stack and its current behavior.
5. Current limitations, observed failure patterns, and next-step priorities.

## 2) User-Driven Objective Timeline (Conversation-Derived)

The workstream followed these user-driven priorities in sequence:

1. Run fair baseline vs system comparisons with same prompt/model.
2. Move to Spider2 subset benchmarking for harder, multi-domain SQL tasks.
3. Use local Ollama model (`gemma4:e4b`) at full throughput to avoid cloud API/rate-limit issues.
4. Investigate speed bottlenecks (GPU load, VRAM pressure, runtime estimations).
5. Try cloud path where possible and monitor API failures/recovery behavior.
6. Introduce plan-based generation (`NL -> PLAN -> SQL`).
7. Diagnose plan-quality-vs-SQL-compliance gap and implement strict plan enforcement.
8. Re-run tests with updated architecture and expanded metrics.

## 3) High-Level Architecture Evolution

### 3.1 Legacy Core Pipeline (`queryshield/app/pipeline.py`)

Pipeline shape: `Question -> Prompt -> SQL -> Safety check -> Execute -> Optional correction retry`

Characteristics:

1. Uses `QueryPipeline.MAX_RETRIES = 2` correction loop.
2. Safety layer blocks dangerous SQL in safe mode and partially restricts in admin mode.
3. Logs every run to `logs/run_logs.json`.
4. Works as practical app flow, separate from benchmark harness design.

### 3.2 Evaluation Pipeline (Pre-Plan)

Files: `runner.py`, `runner_same_prompt.py`, `comparator.py`, `comparator_same_prompt.py`

Characteristics:

1. Baseline/system scoring on custom and hard query suites.
2. Fairness mode ensures same prompt/model for baseline and system.
3. Metrics include correctness, partial correctness, retry success, safety blocks.

### 3.3 Spider2 Evaluation Harness (Current main benchmark harness)

Primary file: `queryshield/evaluation/spider_runner.py`

System pipeline now:

`NL -> PLAN -> SQL -> PLAN VALIDATOR -> (regen loop) -> EXECUTION -> (optional semantic loop)`

Baseline remains unchanged by design:

`NL -> SQL (single prompt family) -> execution/evaluation`

## 4) Strict Plan Enforcement Layer (What Was Added)

### 4.1 New module: `plan_validator.py`

Behavior:

1. Builds strict validator prompt checking tables/joins/aggregations/group_by/filters/logic.
2. Requires strict JSON output:
   - `decision`: `VALID` or `INVALID`
   - `issues`: list
   - `fix_suggestions`: list
3. Treats malformed validator output as `INVALID` (strict-by-default).
4. Has retry logic for validator API failures using throttler + delay.

### 4.2 Updated module: `sql_generator.py`

Behavior:

1. Primary generation prompt changed to strict SQL compiler framing:
   - must follow plan exactly
   - must include all joins/aggregations/group_by/filters
   - must not add new logic
2. Added `build_sql_fix_from_plan_prompt(...)` for targeted regeneration using validator issues.

### 4.3 Updated module: `spider_runner.py`

Major updates:

1. Added `MAX_PLAN_VALIDATION_ATTEMPTS` runtime knob.
2. Added `_enforce_plan_constraints(...)` loop before execution.
3. Tracks new per-query fields:
   - `system_plan_validation_failures`
   - `system_plan_correction_success`
   - `system_plan_validation_trace`
   - `system_plan_validation_attempts_used`
4. Returns `plan_validation_failed` terminal failure if SQL cannot be aligned in strict loop.

### 4.4 Updated module: `spider_metrics.py`

Added metrics:

1. `final_accuracy` (aliased to current system accuracy)
2. `plan_validation_failures` (sum across rows)
3. `plan_correction_success_rate` (ratio of rows corrected after validation failure)

## 5) Prompt Catalog (Current Canonical Prompts)

### 5.1 Common fair prompt (`spider_prompts.py`)

Intent: same high-quality SQL generation prompt shared by baseline and system for fair comparison.

Key constraints:

1. Use only provided schema.
2. Verify column existence and joins strictly.
3. Self-check grouping/logic and return only SQL.

### 5.2 Execution correction prompt (`spider_prompts.py`)

Intent: fix failed SQL using execution error feedback.

Required fixes:

1. Correct column names.
2. Fix joins.
3. Fix aggregation.

### 5.3 Planner prompt (`planner.py`)

Intent: produce strict JSON plan, no SQL generation allowed.

Plan schema fields:

1. `intent`
2. `tables`
3. `joins`
4. `filters`
5. `aggregations`
6. `group_by`
7. `order_by`
8. `limit`
9. `subqueries`
10. `reasoning_steps`

### 5.4 SQL compiler prompt (`sql_generator.py`)

Intent: enforce exact translation from plan to SQL.

Strict rules include:

1. include all joins/aggregations/grouping/filters from plan.
2. do not add new logic.
3. do not change aggregation type.

### 5.5 Plan validator prompt (`plan_validator.py`)

Intent: verify whether SQL fully implements plan and return strict JSON decision + issues + fix suggestions.

### 5.6 SQL regeneration prompt (`sql_generator.py`)

Intent: patch only non-compliant parts to satisfy validator issues while keeping intent unchanged.

## 6) Evaluation Runtime Controls (Current `spider_runner.py` knobs)

Global/runtime knobs exposed:

1. `--llm-timeout-seconds`
2. `--api-max-retries`
3. `--api-recovery-rounds`
4. `--api-recovery-cooldown-seconds`
5. `--max-correction-retries`
6. `--max-semantic-retries`
7. `--max-plan-validation-attempts`
8. `--disable-semantic-loop`
9. `--throttle-seconds`
10. `--num-dbs`, `--num-queries`, dataset/db/output paths

Design intent of these knobs:

1. Separate API resilience from SQL correction logic.
2. Allow reproducible fairness runs by pinning retry budgets.
3. Support local full-throttle mode (`throttle_seconds=0`) for Ollama runs.

## 7) Repository Footprint (Relevant to this project)

Top-level QueryShield module directories: `app`, `core`, `evaluation`, `data`, `logs`.

Observed file counts (snapshot):

1. `app`: 3 files
2. `core`: 10 files
3. `evaluation`: 94 files
4. `data/spider2/local_sqlite_dbs`: 16 SQLite databases

Spider2 DB IDs used in balanced runs:

1. IPL
2. E_commerce
3. sqlite-sakila
4. Pagila
5. modern_data
6. f1
7. California_Traffic_Collision
8. WWE
9. EU_soccer
10. Brazilian_E_Commerce
11. delivery_center
12. Baseball
13. education_business
14. bank_sales_trading
15. EntertainmentAgency
16. Db-IMDB

## 8) Complete Benchmark Registry (Discovered JSON Runs)

Legend:

1. `Imp%` = improvement percent (or derived from improvement ratio when only ratio exists).
2. `BExec`/`SExec` = baseline/system execution success rate.
3. `API` = total API failures (baseline + system where explicit total not stored).
4. `PlanQ`/`PlanValFail`/`PlanCorr` are populated only for plan-aware runs.

| File | Family | Status | Q | BAcc | SAcc | Imp% | BExec | SExec | API | TotalSec | AvgSec | PlanQ | PlanValFail | PlanCorr | Retry | Semantic |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `queryshield/evaluation/groq_hard_results.json` | custom_query_benchmarks | - | 20 | 0.35 | 0.6 | 25 | - | - | 0 | - | - | - | - | - | 1 | - |
| `queryshield/evaluation/groq_hard_results_saved_copy.json` | custom_query_benchmarks | - | 20 | 0.4 | 0.6 | 20 | - | - | 0 | - | - | - | - | - | 0 | - |
| `queryshield/evaluation/results_groq_all.json` | custom_query_benchmarks | - | 26 | 0.0769 | 0.5 | 42.31 | - | - | 0 | - | - | - | - | - | 0.6667 | - |
| `queryshield/evaluation/results_groq_all_fair.json` | custom_query_benchmarks | - | 26 | 0.6538 | 0.5385 | -11.54 | - | - | 0 | - | - | - | - | - | 1 | - |
| `queryshield/evaluation/results_mistral_all.json` | custom_query_benchmarks | - | 26 | 0.0769 | 0.6538 | 57.69 | - | - | 0 | - | - | - | - | - | 0.2727 | - |
| `queryshield/evaluation/results_mistral_all_fair.json` | custom_query_benchmarks | - | 26 | 0.3846 | 0.6538 | 26.92 | - | - | 0 | - | - | - | - | - | 0.2727 | - |
| `queryshield/evaluation/spider2_best_same_prompt_efficiency.json` | spider2_same_prompt | in_progress | 10 | 0 | 0 | 0 | 0 | 0 | 20 | 3799.026 | 379.903 | - | - | - | 0 | 0 |
| `queryshield/evaluation/spider2_best_same_prompt_efficiency_v2.json` | spider2_same_prompt | completed | 24 | 0 | 0 | 0 | 0 | 0 | 48 | 3333.327 | 138.889 | - | - | - | 0 | 0 |
| `queryshield/evaluation/spider2_cloud_balanced_24q.json` | spider2_balanced | completed | 24 | 0.5 | 0.5 | 0 | 0.7917 | 0.9583 | 0 | 756.399 | 31.517 | - | - | - | 0 | 0 |
| `queryshield/evaluation/spider2_cloud_planbased_24q.json` | spider2_plan_based | completed | 24 | 0.5 | 0.4167 | -8.33 | 0.8333 | 0.9583 | 0 | 1017.531 | 42.397 | 1 | - | - | 0 | 0 |
| `queryshield/evaluation/spider2_cloud_planbased_smoke_1q.json` | spider2_plan_based | completed | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 64.803 | 64.803 | 1 | - | - | 0 | 0 |
| `queryshield/evaluation/spider2_cloud_planenforced_smoke_1q.json` | spider2_plan_enforced | completed | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 152.679 | 152.679 | 0.9 | 0 | 0 | 0 | 0 |
| `queryshield/evaluation/spider2_cloud_smoke_1q.json` | spider2_smoke | completed | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 26.683 | 26.683 | - | - | - | 0 | 0 |
| `queryshield/evaluation/spider2_comparator_same_prompt_efficiency_v2.json` | spider2_same_prompt | completed | 24 | 0 | 0 | 0 | 0 | 0 | 48 | 8290.149 | 345.423 | - | - | - | 0 | 0 |
| `queryshield/evaluation/spider2_gemma4e4b_same_prompt_maxacc.json` | spider2_same_prompt | in_progress | 4 | 0.75 | 0.6667 | -8.33 | 1 | 0.75 | 1 | 2354.444 | 588.611 | - | - | - | 0 | 0 |
| `queryshield/evaluation/spider2_ollama_planenforced_24q.json` | spider2_plan_enforced | in_progress | 2 | 0.5 | 0.5 | 0 | 1 | 1 | 0 | 4937.072 | 2468.536 | 1 | 0 | 0 | 1 | 0 |
| `queryshield/evaluation/spider2_ollama_planenforced_smoke_1q.json` | spider2_plan_enforced | completed | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 809.642 | 809.642 | 1 | 0 | 0 | 0 | 0 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_profile.json` | spider2_archive_validation | completed | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 37.636 | 37.636 | - | - | - | 0 | 0 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_profile_after_fix.json` | spider2_archive_validation | completed | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 18.606 | 18.606 | - | - | - | 0 | 0 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_profile_retry0.json` | spider2_archive_validation | completed | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 4.54 | 4.54 | - | - | - | 0 | 0 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_smoke_70b.json` | spider2_archive_validation | completed | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 74.956 | 74.956 | - | - | - | 0 | 0 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_smoke_8b.json` | spider2_archive_validation | completed | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 74.942 | 74.942 | - | - | - | 0 | 0 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_smoke_8b_proxyfix.json` | spider2_archive_validation | completed | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 15.494 | 15.494 | - | - | - | 0 | 0 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_smoke_8b_r2r1.json` | spider2_archive_validation | completed | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 32.754 | 32.754 | - | - | - | 0 | 0 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix.json` | spider2_archive_validation | completed | 24 | 0.2273 | 0.5455 | 31.82 | 0.4583 | 0.4583 | 15 | 778.28 | 32.428 | - | - | - | 0.7 | 0.4286 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix_r3.json` | spider2_archive_validation | completed | 24 | 0.1579 | 0.4375 | 27.96 | 0.375 | 0.5417 | 13 | 1425.77 | 59.407 | - | - | - | 0.75 | 0.25 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix_rerun.json` | spider2_archive_validation | completed | 24 | 0.2 | 0.5 | 30 | 0.4167 | 0.7083 | 8 | 997.216 | 41.551 | - | - | - | 0.9048 | 0.2857 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix_strictvalidator.json` | spider2_archive_validation | completed | 24 | 0.1667 | 0.35 | 18.33 | 0.375 | 0.5833 | 10 | 1031.973 | 42.999 | - | - | - | 0.9048 | 0.6667 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_run.json` | spider2_archive_validation | completed | 24 | 0 | 0 | 0 | 0 | 0 | 48 | 795.623 | 33.151 | - | - | - | 0 | 0 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_robust.json` | spider2_archive_validation | - | 24 | 0.2917 | 0.4348 | 14.31 | 0.5417 | 0.7083 | 1 | - | - | - | - | - | 1 | - |
| `queryshield/evaluation/validation_layer_best_20260403_200856/spider2_subset_results.json` | spider2_archive_best | - | 24 | 0.25 | 0.5714 | 32.14 | 0.2917 | 0.5833 | 22 | - | - | - | - | - | 0.7619 | - |

## 9) Highlighted Benchmark Outcomes (Interpreted)

Best observed system accuracy (completed/archived runs): `0.6538` in `queryshield/evaluation/results_mistral_all.json`.
Best observed improvement percent: `57.69` in `queryshield/evaluation/results_mistral_all.json`.
Worst observed improvement percent: `-11.54` in `queryshield/evaluation/results_groq_all_fair.json`.

### 9.1 Custom Fair Benchmarks

- `results_mistral_all_fair.json`: BAcc=0.3846, SAcc=0.6538, Imp%=26.92, Retry=0.2727
- `results_groq_all_fair.json`: BAcc=0.6538, SAcc=0.5385, Imp%=-11.54, Retry=1

Takeaway: fairness setup can produce either positive or negative system delta depending on model/prompt behavior; fairness itself does not guarantee system win.

### 9.2 Spider2 Balanced vs Plan-Based (Cloud)

- Balanced 24Q: BAcc=0.5, SAcc=0.5, SExec=0.9583, TotalSec=756.399
- Plan-based 24Q: BAcc=0.5, SAcc=0.4167, SExec=0.9583, PlanQ=1, TotalSec=1017.531

Takeaway: execution success improved in both variants, but plan-based run showed that high plan quality alone does not guarantee final correctness.

### 9.3 Strict Plan-Enforcement Smoke Results

- `spider2_cloud_planenforced_smoke_1q.json`: BExec=0, SExec=0, PlanValFail=0, TotalSec=152.679
- `spider2_ollama_planenforced_smoke_1q.json`: BExec=1, SExec=1, PlanValFail=0, TotalSec=809.642

Takeaway: strict layer is integrated and emitting enforcement metrics; cloud smoke captured API instability case, local smoke captured high-latency stable case.

### 9.4 In-Progress Runs

- `queryshield/evaluation/spider2_best_same_prompt_efficiency.json`: completed=10/24, current SAcc=0, AvgSec=379.903
- `queryshield/evaluation/spider2_gemma4e4b_same_prompt_maxacc.json`: completed=4/24, current SAcc=0.6667, AvgSec=588.611
- `queryshield/evaluation/spider2_ollama_planenforced_24q.json`: completed=2/24, current SAcc=0.5, AvgSec=2468.536

## 10) Failure Modes Observed Across Runs

Primary recurring failure classes:

1. `incorrect_sql` (schema/column/join issues).
2. `wrong_results` (logic mismatch despite executable SQL).
3. API/provider failures in unstable cloud configurations.
4. Runtime blow-up on local large-model path due multi-stage loops.

Important empirical pattern:

1. Execution success frequently improves before accuracy does.
2. This indicates syntax repair and join correction help, but semantic intent translation remains the harder bottleneck.

## 11) What Was Changed Specifically for Strict Plan Compliance

Implementation checklist (requested and now implemented):

1. Added plan-validator component file: `plan_validator.py`.
2. Added strict SQL compiler prompt in `sql_generator.py`.
3. Added SQL-regeneration-by-issues prompt in `sql_generator.py`.
4. Integrated enforcement loop in `spider_runner.py` with max attempts.
5. Added trace logging fields for each enforcement attempt.
6. Added metrics for validation failures and correction success rate.
7. Kept baseline pipeline unchanged for fairness.

## 12) Operational Constraints and Performance Notes

1. Cloud path: vulnerable to API/network/provider failures; recovery logic mitigates but does not eliminate risk.
2. Local Ollama path (`gemma4:e4b`): stable from API-limit perspective but significantly slower for full benchmark.
3. Multi-stage plan enforcement + correction + semantic loops multiplies token/runtime cost per query.
4. High timeout and zero throttle are useful for throughput attempts, but not enough to avoid heavy-query latency on limited hardware.

## 13) Reproducibility Commands (Representative)

### 13.1 Spider2 balanced cloud run template
```powershell
python -m queryshield.evaluation.spider_runner --dataset-json queryshield/data/spider2/spider2_local_subset.json --db-root queryshield/data/spider2/local_sqlite_dbs --num-dbs 16 --num-queries 24 --llm-timeout-seconds 180 --api-max-retries 1 --api-recovery-rounds 2 --api-recovery-cooldown-seconds 20 --max-correction-retries 1 --max-semantic-retries 0 --throttle-seconds 0 --output queryshield/evaluation/spider2_cloud_balanced_24q.json
```

### 13.2 Plan-based run template
```powershell
python -m queryshield.evaluation.spider_runner --dataset-json queryshield/data/spider2/spider2_local_subset.json --db-root queryshield/data/spider2/local_sqlite_dbs --num-dbs 16 --num-queries 24 --llm-timeout-seconds 180 --api-max-retries 1 --api-recovery-rounds 2 --api-recovery-cooldown-seconds 20 --max-correction-retries 1 --max-semantic-retries 0 --throttle-seconds 0 --output queryshield/evaluation/spider2_cloud_planbased_24q.json
```

### 13.3 Strict plan-enforced local run template (Ollama)
```powershell
$env:LLM_PROVIDER="ollama"
$env:OLLAMA_MODEL="gemma4:e4b"
python -m queryshield.evaluation.spider_runner --dataset-json queryshield/data/spider2/spider2_local_subset.json --db-root queryshield/data/spider2/local_sqlite_dbs --num-dbs 16 --num-queries 24 --llm-timeout-seconds 240 --api-max-retries 1 --api-recovery-rounds 2 --api-recovery-cooldown-seconds 20 --max-correction-retries 1 --max-semantic-retries 0 --max-plan-validation-attempts 3 --throttle-seconds 0 --output queryshield/evaluation/spider2_ollama_planenforced_24q.json
```

## 14) Module and Function Inventory (Evaluation Stack)

### 14.1 `__init__.py`

- Path: `queryshield/evaluation/__init__.py`
- Size: `63 bytes`
- Last modified: `2026-04-01 05:02:38`
- Functions (0):
  - (no top-level functions)

### 14.2 `baseline.py`

- Path: `queryshield/evaluation/baseline.py`
- Size: `3702 bytes`
- Last modified: `2026-04-03 02:17:56`
- Functions (3):
  - `build_baseline_prompt`
  - `_get_llm_client`
  - `run_baseline`

### 14.3 `baseline_same_prompt.py`

- Path: `queryshield/evaluation/baseline_same_prompt.py`
- Size: `2713 bytes`
- Last modified: `2026-04-03 02:49:11`
- Functions (3):
  - `build_common_prompt`
  - `_get_llm_client`
  - `run_baseline_generation`

### 14.4 `comparator.py`

- Path: `queryshield/evaluation/comparator.py`
- Size: `23635 bytes`
- Last modified: `2026-04-03 04:19:50`
- Functions (19):
  - `_shared_llm_client`
  - `compare`
  - `_run_system`
  - `_build_system_prompt`
  - `_build_system_correction_prompt`
  - `_evaluate_output`
  - `_build_query_type_hint`
  - `_resolve_mode`
  - `_create_workspace_tmp_paths`
  - `_cleanup_tmp_files`
  - `_is_correct`
  - `_is_partial`
  - `_default_validator`
  - `_has_rows`
  - `_rows_count`
  - `_sql_contains`
  - `_blocked_by_safety`
  - `_affected_rows_at_least`
  - `_pick_winner`

### 14.5 `comparator_same_prompt.py`

- Path: `queryshield/evaluation/comparator_same_prompt.py`
- Size: `17625 bytes`
- Last modified: `2026-04-03 02:50:47`
- Functions (15):
  - `_shared_llm_client`
  - `compare`
  - `_run_baseline_execution`
  - `_run_system`
  - `_build_correction_prompt`
  - `_evaluate_output`
  - `_create_workspace_tmp_paths`
  - `_cleanup_tmp_files`
  - `_is_correct`
  - `_is_partial`
  - `_default_validator`
  - `_has_rows`
  - `_rows_count`
  - `_sql_contains`
  - `_pick_winner`

### 14.6 `metrics.py`

- Path: `queryshield/evaluation/metrics.py`
- Size: `6364 bytes`
- Last modified: `2026-04-03 04:20:21`
- Functions (3):
  - `calculate_metrics`
  - `_read_classification`
  - `_zero_metrics`

### 14.7 `plan_validator.py`

- Path: `queryshield/evaluation/plan_validator.py`
- Size: `6151 bytes`
- Last modified: `2026-04-12 16:15:10`
- Functions (7):
  - `build_plan_validation_prompt`
  - `validate_sql_plan`
  - `_parse_validation_json`
  - `_strip_code_fences`
  - `_extract_json_object`
  - `_to_string_list`
  - `_generate_text_with_retry`

### 14.8 `planner.py`

- Path: `queryshield/evaluation/planner.py`
- Size: `8287 bytes`
- Last modified: `2026-04-12 15:22:40`
- Functions (12):
  - `build_planner_prompt`
  - `parse_plan_response`
  - `assess_plan_quality`
  - `_normalize_plan`
  - `_empty_plan`
  - `_strip_code_fences`
  - `_extract_json_object`
  - `_to_string`
  - `_to_string_list`
  - `_to_join_list`
  - `_is_non_empty_string`
  - `_is_non_empty_list`

### 14.9 `prepare_spider2_local_subset.py`

- Path: `queryshield/evaluation/prepare_spider2_local_subset.py`
- Size: `12723 bytes`
- Last modified: `2026-04-03 03:23:11`
- Functions (13):
  - `prepare_spider2_local_subset`
  - `_load_local_examples`
  - `_build_sqlite_db_from_folder`
  - `_create_tables_from_json_metadata`
  - `_load_sample_rows`
  - `_get_table_columns`
  - `_normalize_value`
  - `_quote_identifier`
  - `_normalize_name`
  - `_parse_ddl_column_types`
  - `_normalize_sqlite_type`
  - `_parse_args`
  - `main`

### 14.10 `retry_utils.py`

- Path: `queryshield/evaluation/retry_utils.py`
- Size: `2767 bytes`
- Last modified: `2026-04-03 06:40:25`
- Functions (2):
  - `get_default_throttler`
  - `generate_with_retry`

### 14.11 `runner.py`

- Path: `queryshield/evaluation/runner.py`
- Size: `10481 bytes`
- Last modified: `2026-04-03 04:20:05`
- Functions (12):
  - `run_evaluation`
  - `_build_row`
  - `_save_results`
  - `_print_table`
  - `_print_final_summary`
  - `_shorten`
  - `_build_notes`
  - `_reset_log_files`
  - `_append_jsonl`
  - `_log_row`
  - `_parse_args`
  - `main`

### 14.12 `runner_same_prompt.py`

- Path: `queryshield/evaluation/runner_same_prompt.py`
- Size: `8683 bytes`
- Last modified: `2026-04-03 02:51:29`
- Functions (12):
  - `run_evaluation`
  - `_build_row`
  - `_save_results`
  - `_print_table`
  - `_print_final_summary`
  - `_shorten`
  - `_build_notes`
  - `_reset_log_files`
  - `_append_jsonl`
  - `_log_row`
  - `_parse_args`
  - `main`

### 14.13 `schema_context.py`

- Path: `queryshield/evaluation/schema_context.py`
- Size: `2048 bytes`
- Last modified: `2026-04-03 02:14:20`
- Functions (1):
  - `build_structured_schema`

### 14.14 `semantic_loop.py`

- Path: `queryshield/evaluation/semantic_loop.py`
- Size: `7921 bytes`
- Last modified: `2026-04-03 04:19:19`
- Functions (2):
  - `run_semantic_loop`
  - `build_semantic_correction_prompt`

### 14.15 `spider_execution.py`

- Path: `queryshield/evaluation/spider_execution.py`
- Size: `3217 bytes`
- Last modified: `2026-04-03 03:08:05`
- Functions (4):
  - `execute_sql`
  - `evaluate_sql_prediction`
  - `_normalized_rows`
  - `_normalize_scalar`

### 14.16 `spider_loader.py`

- Path: `queryshield/evaluation/spider_loader.py`
- Size: `4201 bytes`
- Last modified: `2026-04-03 03:06:16`
- Functions (5):
  - `load_spider_examples`
  - `_extract_rows`
  - `_extract_question`
  - `_extract_gold_sql`
  - `_resolve_db_path`

### 14.17 `spider_metrics.py`

- Path: `queryshield/evaluation/spider_metrics.py`
- Size: `8413 bytes`
- Last modified: `2026-04-12 16:21:49`
- Functions (2):
  - `calculate_spider_metrics`
  - `_zero_metrics`

### 14.18 `spider_prompts.py`

- Path: `queryshield/evaluation/spider_prompts.py`
- Size: `1563 bytes`
- Last modified: `2026-04-12 13:10:44`
- Functions (2):
  - `build_common_prompt`
  - `build_correction_prompt`

### 14.19 `spider_runner.py`

- Path: `queryshield/evaluation/spider_runner.py`
- Size: `38135 bytes`
- Last modified: `2026-04-12 16:21:04`
- Functions (15):
  - `run_spider_evaluation`
  - `_evaluate_one_example`
  - `_run_baseline`
  - `_run_system`
  - `_enforce_plan_constraints`
  - `_pick_winner`
  - `_build_notes`
  - `_generate_with_resilience`
  - `_generate_text_with_resilience`
  - `_generate_text_with_retry`
  - `_clone_llm_client`
  - `_save_json`
  - `_print_report`
  - `_parse_args`
  - `main`

### 14.20 `spider_schema.py`

- Path: `queryshield/evaluation/spider_schema.py`
- Size: `2708 bytes`
- Last modified: `2026-04-03 03:06:55`
- Functions (1):
  - `build_rich_schema_context`

### 14.21 `spider_subset.py`

- Path: `queryshield/evaluation/spider_subset.py`
- Size: `4939 bytes`
- Last modified: `2026-04-03 08:08:12`
- Functions (2):
  - `analyze_complexity`
  - `select_hard_subset`

### 14.22 `sql_generator.py`

- Path: `queryshield/evaluation/sql_generator.py`
- Size: `1985 bytes`
- Last modified: `2026-04-12 16:24:02`
- Functions (2):
  - `build_sql_from_plan_prompt`
  - `build_sql_fix_from_plan_prompt`

### 14.23 `validator.py`

- Path: `queryshield/evaluation/validator.py`
- Size: `5727 bytes`
- Last modified: `2026-04-03 09:31:59`
- Functions (8):
  - `validate_semantics`
  - `format_result_preview`
  - `_build_validation_prompt`
  - `_parse_validation_response`
  - `_extract_reason`
  - `_trim_row`
  - `_trim_scalar`
  - `_generate_text_with_retry`

## 15) Current State Assessment

Status by objective:

1. Fair baseline/system setup: complete.
2. Spider2 benchmark harness: complete.
3. Plan-based generation: complete.
4. Strict plan enforcement layer: code complete and smoke-validated.
5. Full strict-enforcement 24Q local result: incomplete (in-progress artifact present).

Primary pending deliverable:

1. Finish one full 24-query strict plan-enforced run on the same subset to produce a final A/B accuracy delta vs `spider2_cloud_planbased_24q.json` and `spider2_cloud_balanced_24q.json`.

## 16) Suggested Next Actions (Prioritized)

1. Resume `spider2_ollama_planenforced_24q.json` until completion with unchanged settings for comparability.
2. Freeze a canonical benchmark manifest labeling each run as `final`, `partial`, `archived`, or `diagnostic` to prevent confusion.
3. Add per-query latency decomposition (planning vs generation vs validation vs execution) to identify strict-loop bottlenecks.
4. Add deterministic seed/control where possible for run-to-run variance tracking.
5. Run matched triplet comparison on same subset and same retries:
   - no plan
   - plan-based (no strict enforcement)
   - plan + strict enforcement

## 17) Change Log of This Report

This expanded edition adds:

1. Full benchmark registry across all JSON run artifacts discovered in repository.
2. Detailed architecture and prompt catalog for current system.
3. Module-level function inventory for the evaluation stack.
4. Explicit operational constraints and reproducibility command templates.
5. Clear pending deliverables and prioritization plan.
