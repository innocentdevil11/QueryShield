"""Strict SQL-plan validation for plan-enforced Text-to-SQL pipeline."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from queryshield.core.llm import LLMClient
from queryshield.evaluation.retry_utils import (
    DEFAULT_MAX_API_RETRIES,
    RETRY_DELAY_SECONDS,
    RequestThrottler,
)


def build_plan_validation_prompt(
    plan: dict[str, Any],
    sql: str,
    validator_suffix: str = "",
) -> str:
    """Build strict SQL-plan validator prompt with severity classification."""
    plan_payload = json.dumps(plan, ensure_ascii=True, indent=2)
    return (
        "You are a strict SQL-plan validator.\n\n"
        "Given:\n"
        "* Plan\n"
        "* SQL query\n\n"
        "Check:\n\n"
        "1. Tables:\n"
        "* Missing tables?\n"
        "* Extra tables?\n\n"
        "2. Joins:\n"
        "* All joins present?\n"
        "* Correct join conditions?\n\n"
        "3. Aggregation:\n"
        "* Correct function used? (SUM vs MAX etc)\n"
        "* Missing aggregation?\n\n"
        "4. Group By:\n"
        "* Matches plan exactly?\n\n"
        "5. Filters:\n"
        "* Applied correctly?\n\n"
        "6. Logic:\n"
        "* Does SQL fully implement plan?\n\n"
        "For each issue found, classify severity:\n"
        "- CRITICAL: wrong table used, required join missing, wrong aggregation type, wrong GROUP BY\n"
        "- WARNING: suboptimal join, minor filter imprecision, extra columns selected\n"
        "- COSMETIC: alias naming, column order, whitespace\n\n"
        "Only set decision=INVALID if you found at least one CRITICAL issue.\n\n"
        'OUTPUT FORMAT (STRICT JSON):\n'
        '{\n'
        '  "decision": "VALID" or "INVALID",\n'
        '  "confidence": 0.0 to 1.0,\n'
        '  "issues": [\n'
        '    {"description": "...", "severity": "CRITICAL" or "WARNING" or "COSMETIC"}\n'
        '  ],\n'
        '  "fix_suggestions": ["..."]\n'
        '}\n\n'
        "Set confidence to reflect your certainty that the SQL violates the plan "
        "(0=unsure, 1=certain).\n"
        "Only set decision=INVALID if at least one CRITICAL issue exists AND confidence >= 0.65.\n\n"
        "Return JSON only.\n\n"
        "Plan:\n"
        f"{plan_payload}\n\n"
        "SQL query:\n"
        f"{sql.strip()}\n"
        + (f"\n{validator_suffix.strip()}\n" if validator_suffix else "")
    )


def validate_sql_plan(
    *,
    plan: dict[str, Any],
    sql: str,
    llm_client: LLMClient,
    throttler: RequestThrottler,
    max_api_retries: int = DEFAULT_MAX_API_RETRIES,
    validator_suffix: str = "",
) -> dict[str, Any]:
    """Validate whether SQL strictly matches plan using an LLM validator."""
    prompt = build_plan_validation_prompt(plan=plan, sql=sql, validator_suffix=validator_suffix)
    generation = _generate_text_with_retry(
        llm=llm_client,
        prompt=prompt,
        throttler=throttler,
        max_retries=max_api_retries,
    )

    if generation["api_error"] is not None:
        # Fail-open on validator API failure (matching semantic validator behavior)
        return {
            "decision": "VALID",
            "confidence": 0.5,
            "issues": [],
            "fix_suggestions": [],
            "is_valid": True,
            "raw_response": "",
            "api_error": generation["api_error"],
            "retries_used": int(generation["retries_used"]),
            "retry_success": bool(generation["retry_success"]),
        }

    parsed = _parse_validation_json(str(generation["text"]))
    return {
        "decision": parsed["decision"],
        "confidence": parsed["confidence"],
        "issues": parsed["issues"],
        "fix_suggestions": parsed["fix_suggestions"],
        "is_valid": parsed["decision"] == "VALID",
        "raw_response": str(generation["text"]),
        "api_error": None,
        "retries_used": int(generation["retries_used"]),
        "retry_success": bool(generation["retry_success"]),
    }


def _parse_validation_json(raw_text: str) -> dict[str, Any]:
    text = _strip_code_fences(raw_text or "")
    payload: dict[str, Any] | None = None

    try:
        candidate = json.loads(text)
        if isinstance(candidate, dict):
            payload = candidate
    except json.JSONDecodeError:
        extracted = _extract_json_object(text)
        if extracted is not None:
            try:
                candidate = json.loads(extracted)
                if isinstance(candidate, dict):
                    payload = candidate
            except json.JSONDecodeError:
                payload = None

    if payload is None:
        return {
            "decision": "INVALID",
            "confidence": 0.5,
            "issues": [{"description": "plan_validator_parse_error: output was not valid JSON.", "severity": "CRITICAL"}],
            "fix_suggestions": ["Regenerate SQL using strict plan constraints."],
        }

    decision = str(payload.get("decision", "")).strip().upper()
    if decision not in {"VALID", "INVALID"}:
        decision = "INVALID"

    # Parse confidence
    raw_confidence = payload.get("confidence", 0.5)
    try:
        confidence = max(0.0, min(1.0, float(raw_confidence)))
    except (TypeError, ValueError):
        confidence = 0.5

    # Parse issues with severity
    raw_issues = payload.get("issues", [])
    issues: list[dict[str, str]] = []
    if isinstance(raw_issues, list):
        for item in raw_issues:
            if isinstance(item, dict):
                issues.append({
                    "description": str(item.get("description", item.get("issue", str(item)))).strip(),
                    "severity": _normalize_severity(item.get("severity", "WARNING")),
                })
            elif isinstance(item, str) and item.strip():
                issues.append({"description": item.strip(), "severity": "WARNING"})

    fix_suggestions = _to_string_list(payload.get("fix_suggestions"))
    if decision == "INVALID" and not issues:
        issues = [{"description": "SQL does not fully align with plan constraints.", "severity": "CRITICAL"}]
    if decision == "INVALID" and not fix_suggestions:
        fix_suggestions = ["Align joins, filters, aggregations, group_by, and ordering with plan."]

    return {
        "decision": decision,
        "confidence": confidence,
        "issues": issues,
        "fix_suggestions": fix_suggestions,
    }


def _normalize_severity(value: Any) -> str:
    """Normalize severity string to CRITICAL/WARNING/COSMETIC."""
    s = str(value).strip().upper()
    if s in {"CRITICAL", "WARNING", "COSMETIC"}:
        return s
    return "WARNING"


def _strip_code_fences(text: str) -> str:
    cleaned = (text or "").strip()
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced[0].strip()
    return cleaned


def _extract_json_object(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1].strip()


def _to_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    single = str(value).strip()
    return [single] if single else []


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
