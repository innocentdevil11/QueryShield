"""Baseline text-to-SQL flow with fair schema context."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from queryshield.core.executor import SQLExecutor
from queryshield.core.llm import LLMClient
from queryshield.evaluation.schema_context import build_structured_schema
from queryshield.evaluation.retry_utils import (
    DEFAULT_MAX_API_RETRIES,
    RequestThrottler,
    generate_with_retry,
    get_default_throttler,
)


def build_baseline_prompt(schema: str, question: str) -> str:
    """
    Build a fair baseline prompt with the same schema context as system.

    Baseline still has:
    - no safety validation
    - no correction loop
    """
    return (
        "You are an expert SQL generator and verifier.\n\n"
        "TASK:\n"
        "Generate SQL and VERIFY it before returning.\n\n"
        "RULES:\n"
        "* Use ONLY schema tables and columns\n"
        "* Verify all columns exist\n"
        "* Ensure correct JOIN conditions using foreign keys\n"
        "* If aggregation -> MUST include GROUP BY\n"
        "* If ranking/top -> MUST include ORDER BY + LIMIT\n"
        "* If 'per' or 'each' -> MUST group accordingly\n\n"
        "SELF-CHECK:\n"
        "* Check if query would execute without error\n"
        "* Check if logic matches question intent\n"
        "* Fix any issues BEFORE returning\n\n"
        "Schema:\n"
        f"{schema.strip()}\n\n"
        "Question:\n"
        f"{question.strip()}\n\n"
        "Return ONLY final SQL.\n"
    )


@lru_cache(maxsize=1)
def _get_llm_client() -> LLMClient:
    """Reuse one client instance across baseline calls."""
    return LLMClient()


def run_baseline(
    question: str,
    db_path: Path,
    schema_file: Path | None = None,
    schema: str | None = None,
    llm_client: LLMClient | None = None,
    throttler: RequestThrottler | None = None,
) -> dict[str, Any]:
    """
    Run baseline SQL generation and execution.

    Behavior:
    - same model and same schema context as system
    - same API retry policy for request failures
    - no safety checks
    - no correction loop
    """
    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValueError("Question cannot be empty.")

    # Keep baseline and system fair by using the same structured schema format.
    # If comparator already passes schema, we reuse it as-is.
    if schema is not None:
        shared_schema = schema
    elif schema_file is not None and Path(schema_file).exists():
        shared_schema = Path(schema_file).read_text(encoding="utf-8").strip()
    else:
        shared_schema = build_structured_schema(Path(db_path))
    prompt = build_baseline_prompt(schema=shared_schema, question=cleaned_question)

    client = llm_client or _get_llm_client()
    rate_limiter = throttler or get_default_throttler()
    retry_outcome = generate_with_retry(
        llm=client,
        prompt=prompt,
        throttler=rate_limiter,
        max_retries=DEFAULT_MAX_API_RETRIES,
    )

    if retry_outcome["api_error"] is not None:
        return {
            "sql": "",
            "result": [],
            "error": retry_outcome["api_error"],
            "api_failures": 1,
            "retries_used": retry_outcome["retries_used"],
            "retry_success": False,
        }

    sql = str(retry_outcome["sql"])
    execution = SQLExecutor(Path(db_path)).execute(sql)
    return {
        "sql": sql,
        "result": execution["rows"],
        "error": execution["error"],
        "api_failures": 0,
        "retries_used": retry_outcome["retries_used"],
        "retry_success": bool(retry_outcome["retry_success"]),
    }
