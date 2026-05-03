"""SQL execution and result-comparison helpers for Spider evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from queryshield.core.executor import SQLExecutor


def execute_sql(db_path: Path, sql: str) -> dict[str, Any]:
    """Run SQL against a DB and return executor response."""
    return SQLExecutor(db_path=db_path).execute(sql)


def evaluate_sql_prediction(
    db_path: Path,
    predicted_sql: str,
    gold_sql: str,
) -> dict[str, Any]:
    """
    Evaluate predicted SQL by execution-equivalence with gold SQL.

    Categories:
    - success
    - incorrect_sql
    - wrong_results
    - api_error
    """
    predicted = execute_sql(db_path=db_path, sql=predicted_sql)
    gold = execute_sql(db_path=db_path, sql=gold_sql)

    predicted_error = predicted["error"]
    if isinstance(predicted_error, str) and predicted_error.startswith("api_error:"):
        return {
            "execution_success": False,
            "correct": False,
            "classification": "api_error",
            "failure_type": "api_error",
            "predicted_error": predicted_error,
            "gold_error": gold.get("error"),
            "predicted_rows": [],
            "gold_rows": gold.get("rows", []),
        }

    if predicted_error is not None:
        return {
            "execution_success": False,
            "correct": False,
            "classification": "incorrect_sql",
            "failure_type": "incorrect_sql",
            "predicted_error": predicted_error,
            "gold_error": gold.get("error"),
            "predicted_rows": [],
            "gold_rows": gold.get("rows", []),
        }

    if gold["error"] is not None:
        # Gold SQL should normally execute; mark as wrong_results to avoid silent success.
        return {
            "execution_success": True,
            "correct": False,
            "classification": "wrong_results",
            "failure_type": "wrong_results",
            "predicted_error": None,
            "gold_error": gold["error"],
            "predicted_rows": predicted.get("rows", []),
            "gold_rows": [],
        }

    predicted_rows = predicted.get("rows", [])
    gold_rows = gold.get("rows", [])
    is_equal = _normalized_rows(predicted_rows) == _normalized_rows(gold_rows)
    classification = "success" if is_equal else "wrong_results"
    return {
        "execution_success": True,
        "correct": is_equal,
        "classification": classification,
        "failure_type": classification,
        "predicted_error": None,
        "gold_error": None,
        "predicted_rows": predicted_rows,
        "gold_rows": gold_rows,
    }


def _normalized_rows(rows: list[dict[str, Any]]) -> list[str]:
    """Canonicalize row dictionaries so unordered row sets can be compared safely."""
    normalized: list[str] = []
    for row in rows:
        payload = {str(key): _normalize_scalar(value) for key, value in row.items()}
        normalized.append(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return sorted(normalized)


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    return value
