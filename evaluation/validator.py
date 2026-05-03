"""LLM-based semantic validation utilities for SQL evaluation."""

from __future__ import annotations

import json
import time
from typing import Any

from queryshield.core.llm import LLMClient
from queryshield.evaluation.retry_utils import (
    DEFAULT_MAX_API_RETRIES,
    RequestThrottler,
    RETRY_DELAY_SECONDS,
)

MAX_RESULT_ROWS_FOR_VALIDATION = 10
MAX_VALUE_CHARS = 160


def validate_semantics(
    *,
    question: str,
    schema: str,
    sql: str,
    rows: list[dict[str, Any]],
    llm_client: LLMClient,
    throttler: RequestThrottler,
    max_api_retries: int = DEFAULT_MAX_API_RETRIES,
) -> dict[str, Any]:
    """
    Validate whether SQL result logically matches question intent.

    Returns a normalized payload:
    {
      "decision": "VALID|INVALID",
      "reason": "...",
      "is_valid": bool,
      "raw_response": "...",
      "api_error": "...|None",
      "retries_used": int,
      "retry_success": bool
    }
    """
    prompt = _build_validation_prompt(
        question=question,
        schema=schema,
        sql=sql,
        rows=rows,
    )
    generation = _generate_text_with_retry(
        llm=llm_client,
        prompt=prompt,
        throttler=throttler,
        max_retries=max_api_retries,
    )
    if generation["api_error"] is not None:
        # Fail-open on validator API failure so execution-successful SQL can proceed.
        return {
            "decision": "VALID",
            "reason": f"validator_api_error: {generation['api_error']}",
            "is_valid": True,
            "raw_response": "",
            "api_error": generation["api_error"],
            "retries_used": int(generation["retries_used"]),
            "retry_success": bool(generation["retry_success"]),
        }

    decision, reason = _parse_validation_response(str(generation["text"]))
    return {
        "decision": decision,
        "reason": reason,
        "is_valid": decision == "VALID",
        "raw_response": str(generation["text"]),
        "api_error": None,
        "retries_used": int(generation["retries_used"]),
        "retry_success": bool(generation["retry_success"]),
    }


def format_result_preview(rows: list[dict[str, Any]]) -> str:
    """Format query result (count + sample rows) for prompts."""
    safe_rows = rows if isinstance(rows, list) else []
    preview_rows = [_trim_row(row) for row in safe_rows[:MAX_RESULT_ROWS_FOR_VALIDATION]]
    payload = {
        "row_count": len(safe_rows),
        "sample_rows": preview_rows,
    }
    return json.dumps(payload, ensure_ascii=True)


def _build_validation_prompt(
    *,
    question: str,
    schema: str,
    sql: str,
    rows: list[dict[str, Any]],
) -> str:
    result_preview = format_result_preview(rows)
    return (
        "You are a SQL validator.\n\n"
        "You are given:\n"
        "* Question\n"
        "* SQL Query\n"
        "* Query Result\n\n"
        "Your task:\n"
        "Determine if the SQL correctly answers the question.\n\n"
        "Check:\n"
        "* Is aggregation correct?\n"
        "* Is grouping correct?\n"
        "* Are joins logically correct?\n"
        "* Does result size make sense?\n"
        "* Does query match intent?\n\n"
        "Return ONLY one line in this format:\n"
        "VALID\n"
        "or\n"
        "INVALID: <short reason>\n\n"
        "Question:\n"
        f"{question.strip()}\n\n"
        "Schema:\n"
        f"{schema.strip()}\n\n"
        "SQL Query:\n"
        f"{sql.strip()}\n\n"
        "Query Result:\n"
        f"{result_preview}\n"
    )


def _parse_validation_response(raw_response: str) -> tuple[str, str]:
    """Parse validator response into a strict decision + reason."""
    text = (raw_response or "").strip()
    if not text:
        return "VALID", "validator_empty_response"

    upper = text.upper()
    if upper.startswith("VALID"):
        return "VALID", ""
    if upper.startswith("INVALID"):
        reason = _extract_reason(text)
        return "INVALID", reason or "validator_marked_invalid"

    # Fail-open for malformed outputs to avoid damaging already executable SQL.
    return "VALID", f"validator_unparseable_response: {text[:120]}"


def _extract_reason(text: str) -> str:
    if ":" in text:
        return text.split(":", 1)[1].strip()[:240]
    if "-" in text:
        return text.split("-", 1)[1].strip()[:240]
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
        return parts[1].strip()[:240]
    return ""


def _trim_row(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"value": _trim_scalar(row)}
    return {str(k): _trim_scalar(v) for k, v in row.items()}


def _trim_scalar(value: Any) -> Any:
    if isinstance(value, str) and len(value) > MAX_VALUE_CHARS:
        return value[:MAX_VALUE_CHARS] + "..."
    return value


def _generate_text_with_retry(
    *,
    llm: LLMClient,
    prompt: str,
    throttler: RequestThrottler,
    max_retries: int,
) -> dict[str, Any]:
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
        except Exception as exc:  # noqa: BLE001 - provider-specific failures
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
