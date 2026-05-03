"""Metrics computation for Spider baseline-vs-system evaluation."""

from __future__ import annotations

from typing import Any


def calculate_spider_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute evaluation metrics requested for Spider experiments."""
    total = len(results)
    if total == 0:
        return _zero_metrics()

    baseline_correct = 0
    system_correct = 0
    baseline_exec_success = 0
    system_exec_success = 0
    baseline_api_failures = 0
    system_api_failures = 0

    baseline_incorrect_sql = 0
    system_incorrect_sql = 0
    baseline_wrong_results = 0
    system_wrong_results = 0

    complex_total = 0
    complex_baseline_correct = 0
    complex_system_correct = 0

    system_retry_success_count = 0
    system_retry_calls = 0
    semantic_corrections_used = 0
    semantic_success_count = 0
    semantic_attempted_rows = 0
    plan_quality_score_sum = 0.0
    plan_quality_count = 0
    plan_quality_high_count = 0
    plan_validation_failures = 0
    plan_correction_attempted_rows = 0
    plan_correction_success_count = 0
    total_runtime_sec = 0.0

    for row in results:
        baseline_class = str(row.get("baseline_classification") or "").lower()
        system_class = str(row.get("system_classification") or "").lower()

        baseline_is_correct = bool(row.get("baseline_correct"))
        system_is_correct = bool(row.get("system_correct"))
        if baseline_is_correct:
            baseline_correct += 1
        if system_is_correct:
            system_correct += 1

        if bool(row.get("baseline_execution_success")):
            baseline_exec_success += 1
        if bool(row.get("system_execution_success")):
            system_exec_success += 1

        if baseline_class == "api_error":
            baseline_api_failures += 1
        if system_class == "api_error":
            system_api_failures += 1

        if baseline_class == "incorrect_sql":
            baseline_incorrect_sql += 1
        elif baseline_class == "wrong_results":
            baseline_wrong_results += 1

        if system_class == "incorrect_sql":
            system_incorrect_sql += 1
        elif system_class == "wrong_results":
            system_wrong_results += 1

        is_complex = bool(row.get("is_complex"))
        if is_complex:
            complex_total += 1
            if baseline_is_correct:
                complex_baseline_correct += 1
            if system_is_correct:
                complex_system_correct += 1

        system_retries_used = int(row.get("system_retries_used") or 0)
        if system_retries_used > 0:
            system_retry_calls += 1
            if bool(row.get("system_retry_success")):
                system_retry_success_count += 1

        semantic_used = int(row.get("system_semantic_corrections_used") or 0)
        semantic_corrections_used += semantic_used
        if semantic_used > 0:
            semantic_attempted_rows += 1
            if bool(row.get("system_semantic_success")):
                semantic_success_count += 1

        raw_plan_quality = row.get("system_plan_quality_score")
        if isinstance(raw_plan_quality, (int, float)):
            plan_quality_value = float(raw_plan_quality)
            plan_quality_score_sum += plan_quality_value
            plan_quality_count += 1
            if plan_quality_value >= 0.8:
                plan_quality_high_count += 1

        row_plan_failures = int(row.get("system_plan_validation_failures") or 0)
        plan_validation_failures += row_plan_failures
        if row_plan_failures > 0:
            plan_correction_attempted_rows += 1
            if bool(row.get("system_plan_correction_success")):
                plan_correction_success_count += 1

        total_runtime_sec += float(row.get("query_runtime_sec") or 0.0)

    baseline_denom = max(total - baseline_api_failures, 1)
    system_denom = max(total - system_api_failures, 1)
    baseline_accuracy = baseline_correct / baseline_denom
    system_accuracy = system_correct / system_denom
    improvement = system_accuracy - baseline_accuracy

    complex_baseline_accuracy = (
        complex_baseline_correct / complex_total if complex_total > 0 else 0.0
    )
    complex_system_accuracy = (
        complex_system_correct / complex_total if complex_total > 0 else 0.0
    )
    retry_success_rate = (
        system_retry_success_count / system_retry_calls if system_retry_calls > 0 else 0.0
    )
    semantic_success_rate = (
        semantic_success_count / semantic_attempted_rows
        if semantic_attempted_rows > 0
        else 0.0
    )
    plan_quality_avg = (
        plan_quality_score_sum / plan_quality_count if plan_quality_count > 0 else 0.0
    )
    plan_quality_high_rate = (
        plan_quality_high_count / plan_quality_count if plan_quality_count > 0 else 0.0
    )
    plan_correction_success_rate = (
        plan_correction_success_count / plan_correction_attempted_rows
        if plan_correction_attempted_rows > 0
        else 0.0
    )
    logical_error_reduction = (
        (baseline_wrong_results - system_wrong_results) / baseline_wrong_results
        if baseline_wrong_results > 0
        else 0.0
    )

    return {
        "total_queries": total,
        "complex_queries": complex_total,
        "total_runtime_sec": round(total_runtime_sec, 3),
        "avg_query_runtime_sec": round(total_runtime_sec / total, 3),
        "baseline_accuracy": round(baseline_accuracy, 4),
        "system_accuracy": round(system_accuracy, 4),
        "final_accuracy": round(system_accuracy, 4),
        "improvement": round(improvement, 4),
        "improvement_percent": round(improvement * 100, 2),
        "baseline_execution_success_rate": round(baseline_exec_success / total, 4),
        "system_execution_success_rate": round(system_exec_success / total, 4),
        "baseline_incorrect_sql": baseline_incorrect_sql,
        "system_incorrect_sql": system_incorrect_sql,
        "baseline_wrong_results": baseline_wrong_results,
        "system_wrong_results": system_wrong_results,
        "baseline_complex_query_accuracy": round(complex_baseline_accuracy, 4),
        "system_complex_query_accuracy": round(complex_system_accuracy, 4),
        "complex_query_accuracy": {
            "baseline": round(complex_baseline_accuracy, 4),
            "system": round(complex_system_accuracy, 4),
        },
        "baseline_api_failures": baseline_api_failures,
        "system_api_failures": system_api_failures,
        "api_failures": baseline_api_failures + system_api_failures,
        "retry_success_rate": round(retry_success_rate, 4),
        "semantic_corrections_used": semantic_corrections_used,
        "semantic_success_rate": round(semantic_success_rate, 4),
        "plan_quality": {
            "avg_score": round(plan_quality_avg, 4),
            "high_rate": round(plan_quality_high_rate, 4),
            "count": plan_quality_count,
        },
        "plan_quality_avg": round(plan_quality_avg, 4),
        "plan_validation_failures": plan_validation_failures,
        "plan_correction_success_rate": round(plan_correction_success_rate, 4),
        "logical_error_reduction": round(logical_error_reduction, 4),
    }


def _zero_metrics() -> dict[str, Any]:
    return {
        "total_queries": 0,
        "complex_queries": 0,
        "total_runtime_sec": 0.0,
        "avg_query_runtime_sec": 0.0,
        "baseline_accuracy": 0.0,
        "system_accuracy": 0.0,
        "final_accuracy": 0.0,
        "improvement": 0.0,
        "improvement_percent": 0.0,
        "baseline_execution_success_rate": 0.0,
        "system_execution_success_rate": 0.0,
        "baseline_incorrect_sql": 0,
        "system_incorrect_sql": 0,
        "baseline_wrong_results": 0,
        "system_wrong_results": 0,
        "baseline_complex_query_accuracy": 0.0,
        "system_complex_query_accuracy": 0.0,
        "complex_query_accuracy": {"baseline": 0.0, "system": 0.0},
        "baseline_api_failures": 0,
        "system_api_failures": 0,
        "api_failures": 0,
        "retry_success_rate": 0.0,
        "semantic_corrections_used": 0,
        "semantic_success_rate": 0.0,
        "plan_quality": {"avg_score": 0.0, "high_rate": 0.0, "count": 0},
        "plan_quality_avg": 0.0,
        "plan_validation_failures": 0,
        "plan_correction_success_rate": 0.0,
        "logical_error_reduction": 0.0,
    }
