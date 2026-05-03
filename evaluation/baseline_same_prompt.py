"""Baseline generation flow for the same-prompt fair experiment."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from queryshield.core.llm import LLMClient
from queryshield.evaluation.retry_utils import RequestThrottler, get_default_throttler


def build_common_prompt(schema: str, question: str) -> str:
    """Build the exact common prompt shared by baseline and system."""
    return (
        "You are an expert SQL generator and verifier.\n\n"
        "TASK:\n"
        "Generate SQL and internally verify it before returning.\n\n"
        "RULES:\n"
        "* Use ONLY provided schema\n"
        "* Verify all column names exist\n"
        "* Ensure correct JOIN conditions using foreign keys\n"
        "* If aggregation -> MUST include GROUP BY\n"
        "* If ranking -> MUST include ORDER BY + LIMIT\n\n"
        "SELF-CHECK:\n"
        "* Check if SQL would execute without error\n"
        "* Check if logic matches the question\n"
        "* Fix mistakes BEFORE returning\n\n"
        "IMPORTANT:\n"
        "* Do NOT hallucinate columns\n"
        "* Return ONLY final SQL\n\n"
        "Schema:\n"
        f"{schema.strip()}\n\n"
        "Question:\n"
        f"{question.strip()}\n\n"
        "Return SQL only.\n"
    )


@lru_cache(maxsize=1)
def _get_llm_client() -> LLMClient:
    """Reuse a single LLM client for sequential baseline calls."""
    return LLMClient()


def run_baseline_generation(
    question: str,
    schema: str,
    llm_client: LLMClient | None = None,
    throttler: RequestThrottler | None = None,
) -> dict[str, Any]:
    """
    Run baseline generation with a single LLM call.

    Constraints for this experiment:
    - same common prompt as system
    - one call only
    - no execution inside baseline
    - no retry
    - no correction loop
    """
    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValueError("Question cannot be empty.")

    prompt = build_common_prompt(schema=schema, question=cleaned_question)
    client = llm_client or _get_llm_client()
    rate_limiter = throttler or get_default_throttler()

    # Keep global request spacing deterministic for fairness.
    rate_limiter.wait_turn()
    try:
        sql = client.generate_sql(prompt).strip()
    except Exception as exc:  # noqa: BLE001 - explicit API error tracking
        return {
            "sql": "",
            "error": f"api_error: {exc}",
            "api_failures": 1,
            "retries_used": 0,
            "retry_success": False,
        }

    return {
        "sql": sql,
        "error": None,
        "api_failures": 0,
        "retries_used": 0,
        "retry_success": False,
    }

