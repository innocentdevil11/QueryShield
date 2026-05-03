"""Metrics utilities for baseline vs QueryShield evaluation."""

from __future__ import annotations

from typing import Any


def calculate_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Calculate aggregate benchmarking metrics.

    Accuracy policy:
    - baseline_accuracy = baseline_correct / (total_queries - baseline_api_failures)
    - system_accuracy = system_correct / total_queries
    """
    total_queries = len(results)
    if total_queries == 0:
        return _zero_metrics()

    baseline_correct = 0
    system_correct = 0
    baseline_api_failures = 0
    system_api_failures = 0
    safety_blocks = 0

    baseline_incorrect_sql = 0
    system_incorrect_sql = 0
    baseline_wrong_results = 0
    system_wrong_results = 0
    baseline_partial_correct = 0
    system_partial_correct = 0

    retry_success_count = 0
    retried_calls_total = 0
    semantic_corrections_used = 0
    semantic_success_count = 0
    semantic_attempted_rows = 0

    for row in results:
        baseline_class = _read_classification(
            row, "baseline_classification", "baseline_failure_type"
        )
        system_class = _read_classification(
            row, "system_classification", "system_failure_type"
        )

        baseline_is_correct = bool(row.get("baseline_correct"))
        system_is_correct = bool(row.get("system_correct"))
        if baseline_is_correct:
            baseline_correct += 1
        if system_is_correct:
            system_correct += 1

        if baseline_class == "api_error":
            baseline_api_failures += 1
        if system_class == "api_error":
            system_api_failures += 1

        if baseline_class == "incorrect_sql":
            baseline_incorrect_sql += 1
        elif baseline_class == "wrong_results":
            baseline_wrong_results += 1
        elif baseline_class == "partial_correct":
            baseline_partial_correct += 1

        if system_class == "incorrect_sql":
            system_incorrect_sql += 1
        elif system_class == "wrong_results":
            system_wrong_results += 1
        elif system_class == "partial_correct":
            system_partial_correct += 1

        system_error = str(row.get("system_error") or "")
        if system_error.startswith("Blocked by safety layer"):
            safety_blocks += 1

        baseline_retries = int(row.get("baseline_retries_used") or 0)
        system_retries = int(row.get("system_retries_used") or 0)
        if baseline_retries > 0:
            retried_calls_total += 1
            if bool(row.get("baseline_retry_success")):
                retry_success_count += 1
        if system_retries > 0:
            retried_calls_total += 1
            if bool(row.get("system_retry_success")):
                retry_success_count += 1

        semantic_used = int(row.get("system_semantic_corrections_used") or 0)
        semantic_corrections_used += semantic_used
        if semantic_used > 0:
            semantic_attempted_rows += 1
            if bool(row.get("system_semantic_success")):
                semantic_success_count += 1

    baseline_denom = max(total_queries - baseline_api_failures, 1)
    baseline_accuracy = baseline_correct / baseline_denom
    system_accuracy = system_correct / total_queries
    improvement = system_accuracy - baseline_accuracy
    retry_success_rate = (
        retry_success_count / retried_calls_total
        if retried_calls_total > 0
        else 0.0
    )
    semantic_success_rate = (
        semantic_success_count / semantic_attempted_rows
        if semantic_attempted_rows > 0
        else 0.0
    )
    logical_error_reduction = (
        (baseline_wrong_results - system_wrong_results) / baseline_wrong_results
        if baseline_wrong_results > 0
        else 0.0
    )

    return {
        "total_queries": total_queries,
        "baseline_correct": baseline_correct,
        "system_correct": system_correct,
        "baseline_accuracy": round(baseline_accuracy, 4),
        "system_accuracy": round(system_accuracy, 4),
        "improvement": round(improvement, 4),
        "improvement_percent": round(improvement * 100, 2),
        "baseline_incorrect_sql": baseline_incorrect_sql,
        "system_incorrect_sql": system_incorrect_sql,
        "baseline_wrong_results": baseline_wrong_results,
        "system_wrong_results": system_wrong_results,
        "baseline_partial_correct": baseline_partial_correct,
        "system_partial_correct": system_partial_correct,
        "safety_blocks": safety_blocks,
        "baseline_api_failures": baseline_api_failures,
        "system_api_failures": system_api_failures,
        "api_failures": baseline_api_failures + system_api_failures,
        "retry_success_count": retry_success_count,
        "retry_success_rate": round(retry_success_rate, 4),
        "semantic_corrections_used": semantic_corrections_used,
        "semantic_success_rate": round(semantic_success_rate, 4),
        "logical_error_reduction": round(logical_error_reduction, 4),
    }


def _read_classification(
    row: dict[str, Any],
    primary_key: str,
    fallback_key: str,
) -> str:
    value = str(row.get(primary_key) or row.get(fallback_key) or "").strip().lower()
    if value in {"none", "success"}:
        return "success"
    if value in {"partial", "partial_correctness", "partial_correct"}:
        return "partial_correct"
    if value in {"api", "api_error"}:
        return "api_error"
    if value in {"incorrect_sql", "wrong_results"}:
        return value
    return "success"


def _zero_metrics() -> dict[str, Any]:
    return {
        "total_queries": 0,
        "baseline_correct": 0,
        "system_correct": 0,
        "baseline_accuracy": 0.0,
        "system_accuracy": 0.0,
        "improvement": 0.0,
        "improvement_percent": 0.0,
        "baseline_incorrect_sql": 0,
        "system_incorrect_sql": 0,
        "baseline_wrong_results": 0,
        "system_wrong_results": 0,
        "baseline_partial_correct": 0,
        "system_partial_correct": 0,
        "safety_blocks": 0,
        "baseline_api_failures": 0,
        "system_api_failures": 0,
        "api_failures": 0,
        "retry_success_count": 0,
        "retry_success_rate": 0.0,
        "semantic_corrections_used": 0,
        "semantic_success_rate": 0.0,
        "logical_error_reduction": 0.0,
    }
