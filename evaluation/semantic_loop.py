"""Semantic validation and correction loop for SQL system outputs."""

from __future__ import annotations

from typing import Any, Callable

from queryshield.core.llm import LLMClient
from queryshield.evaluation.retry_utils import (
    DEFAULT_MAX_API_RETRIES,
    RequestThrottler,
    generate_with_retry,
)
from queryshield.evaluation.validator import format_result_preview, validate_semantics


def run_semantic_loop(
    *,
    question: str,
    schema: str,
    initial_sql: str,
    initial_rows: list[dict[str, Any]],
    llm_client: LLMClient,
    throttler: RequestThrottler,
    execute_sql: Callable[[str], dict[str, Any]],
    max_semantic_retries: int = 2,
    max_api_retries: int = DEFAULT_MAX_API_RETRIES,
) -> dict[str, Any]:
    """
    Run semantic validation after successful execution and correct if needed.

    The initial SQL/result is assumed executable.
    """
    corrections_used = 0
    semantic_api_failures = 0
    semantic_retry_success = False
    semantic_trace: list[dict[str, Any]] = []

    current_sql = initial_sql
    current_rows = initial_rows
    final_decision = "VALID"
    final_reason = ""

    initial_validation = validate_semantics(
        question=question,
        schema=schema,
        sql=current_sql,
        rows=current_rows,
        llm_client=llm_client,
        throttler=throttler,
        max_api_retries=max_api_retries,
    )
    semantic_trace.append(
        {
            "step": "initial_validation",
            "decision": initial_validation["decision"],
            "reason": initial_validation["reason"],
            "sql_before": current_sql,
            "sql_after": current_sql,
            "result_row_count": len(current_rows),
            "validator_api_error": initial_validation["api_error"],
        }
    )

    if initial_validation["is_valid"]:
        return {
            "sql": current_sql,
            "rows": current_rows,
            "error": None,
            "validation_decision": "VALID",
            "validation_reason": "",
            "semantic_corrections_used": 0,
            "semantic_success": False,
            "semantic_api_failures": int(initial_validation["api_error"] is not None),
            "semantic_retry_success": bool(initial_validation["retry_success"]),
            "semantic_trace": semantic_trace,
        }

    final_decision = "INVALID"
    final_reason = str(initial_validation["reason"] or "validator_marked_invalid")
    if initial_validation["api_error"] is not None:
        semantic_api_failures += 1
    semantic_retry_success = semantic_retry_success or bool(
        initial_validation["retry_success"]
    )

    # Keep best executable attempt: initial SQL is executable by contract.
    best_sql = current_sql
    best_rows = current_rows

    feedback = final_reason
    for semantic_attempt in range(1, max_semantic_retries + 1):
        prompt = build_semantic_correction_prompt(
            question=question,
            schema=schema,
            sql=best_sql,
            rows=best_rows,
            feedback=feedback,
        )
        correction = generate_with_retry(
            llm=llm_client,
            prompt=prompt,
            throttler=throttler,
            max_retries=max_api_retries,
        )
        semantic_retry_success = semantic_retry_success or bool(correction["retry_success"])
        if correction["api_error"] is not None:
            semantic_api_failures += 1
            semantic_trace.append(
                {
                    "step": "semantic_correction",
                    "attempt": semantic_attempt,
                    "decision": "INVALID",
                    "reason": feedback,
                    "sql_before": best_sql,
                    "sql_after": "",
                    "correction_api_error": correction["api_error"],
                }
            )
            continue

        candidate_sql = str(correction["sql"]).strip()
        corrections_used += 1
        execution = execute_sql(candidate_sql)
        exec_error = execution.get("error")
        exec_rows = execution.get("rows", []) if exec_error is None else []
        if exec_error is not None:
            feedback = f"Execution failed after semantic correction: {exec_error}"
            final_decision = "INVALID"
            final_reason = feedback
            semantic_trace.append(
                {
                    "step": "semantic_correction",
                    "attempt": semantic_attempt,
                    "decision": "INVALID",
                    "reason": feedback,
                    "sql_before": best_sql,
                    "sql_after": candidate_sql,
                    "execution_error": exec_error,
                }
            )
            continue

        post_validation = validate_semantics(
            question=question,
            schema=schema,
            sql=candidate_sql,
            rows=exec_rows,
            llm_client=llm_client,
            throttler=throttler,
            max_api_retries=max_api_retries,
        )
        semantic_retry_success = semantic_retry_success or bool(
            post_validation["retry_success"]
        )
        if post_validation["api_error"] is not None:
            semantic_api_failures += 1

        semantic_trace.append(
            {
                "step": "semantic_correction",
                "attempt": semantic_attempt,
                "decision": post_validation["decision"],
                "reason": post_validation["reason"],
                "sql_before": best_sql,
                "sql_after": candidate_sql,
                "result_row_count": len(exec_rows),
                "validator_api_error": post_validation["api_error"],
            }
        )

        # Update "best attempt" to latest executable SQL.
        best_sql = candidate_sql
        best_rows = exec_rows

        if post_validation["is_valid"]:
            return {
                "sql": best_sql,
                "rows": best_rows,
                "error": None,
                "validation_decision": "VALID",
                "validation_reason": "",
                "semantic_corrections_used": corrections_used,
                "semantic_success": True,
                "semantic_api_failures": semantic_api_failures,
                "semantic_retry_success": semantic_retry_success,
                "semantic_trace": semantic_trace,
            }

        final_decision = "INVALID"
        final_reason = str(
            post_validation["reason"] or "validator_marked_invalid_after_correction"
        )
        feedback = final_reason

    return {
        "sql": best_sql,
        "rows": best_rows,
        "error": None,
        "validation_decision": final_decision,
        "validation_reason": final_reason,
        "semantic_corrections_used": corrections_used,
        "semantic_success": False,
        "semantic_api_failures": semantic_api_failures,
        "semantic_retry_success": semantic_retry_success,
        "semantic_trace": semantic_trace,
    }


def build_semantic_correction_prompt(
    *,
    question: str,
    schema: str,
    sql: str,
    rows: list[dict[str, Any]],
    feedback: str,
) -> str:
    """Prompt for semantic correction when SQL executed but was logically wrong."""
    result_preview = format_result_preview(rows)
    return (
        "You are a SQL expert.\n\n"
        "The previous query executed but is LOGICALLY WRONG.\n\n"
        "Question:\n"
        f"{question.strip()}\n\n"
        "Schema:\n"
        f"{schema.strip()}\n\n"
        "Previous SQL:\n"
        f"{sql.strip()}\n\n"
        "Result:\n"
        f"{result_preview}\n\n"
        "Validation Feedback:\n"
        f"{feedback.strip()}\n\n"
        "Fix the SQL so that:\n"
        "* it matches the intent\n"
        "* correct aggregation\n"
        "* correct joins\n"
        "* correct filtering\n\n"
        "Return ONLY corrected SQL.\n"
    )

