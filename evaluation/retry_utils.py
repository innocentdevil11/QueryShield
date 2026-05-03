"""Shared throttling and API retry utilities for evaluation."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from queryshield.core.llm import LLMClient

THROTTLE_SECONDS = 2.5
DEFAULT_MAX_API_RETRIES = 3
RETRY_DELAY_SECONDS = 5.0


class RequestThrottler:
    """Ensures fixed delay between every LLM request."""

    def __init__(self, min_interval_seconds: float = THROTTLE_SECONDS) -> None:
        self.min_interval_seconds = min_interval_seconds
        self._last_call_ts: float | None = None

    def wait_turn(self) -> None:
        """Sleep if required to preserve minimum interval between calls."""
        now = time.monotonic()
        if self._last_call_ts is not None:
            elapsed = now - self._last_call_ts
            if elapsed < self.min_interval_seconds:
                time.sleep(self.min_interval_seconds - elapsed)
        self._last_call_ts = time.monotonic()


_DEFAULT_THROTTLER = RequestThrottler()


def get_default_throttler() -> RequestThrottler:
    """Return singleton throttler shared by baseline and system calls."""
    return _DEFAULT_THROTTLER


@dataclass
class RetryOutcome:
    """Normalized output from API retry wrapper."""

    sql: str
    api_error: str | None
    retries_used: int
    retry_success: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "sql": self.sql,
            "api_error": self.api_error,
            "retries_used": self.retries_used,
            "retry_success": self.retry_success,
        }


def generate_with_retry(
    llm: LLMClient,
    prompt: str,
    throttler: RequestThrottler,
    max_retries: int = DEFAULT_MAX_API_RETRIES,
    retry_delay_seconds: float = RETRY_DELAY_SECONDS,
) -> dict[str, Any]:
    """
    Generate SQL with fixed-delay retry for API failures.

    Retry waits:
    - every retry waits `retry_delay_seconds` (default: 5s)
    """
    retries_used = 0
    last_error = ""

    # Total attempts = initial call + max_retries.
    for retry_index in range(max_retries + 1):
        throttler.wait_turn()
        try:
            sql = llm.generate_sql(prompt)
            return RetryOutcome(
                sql=sql,
                api_error=None,
                retries_used=retries_used,
                retry_success=retries_used > 0,
            ).as_dict()
        except Exception as exc:  # noqa: BLE001 - explicit API failure handling
            last_error = str(exc)
            if retry_index < max_retries:
                time.sleep(retry_delay_seconds)
                retries_used += 1

    return RetryOutcome(
        sql="",
        api_error=f"api_error: {last_error}",
        retries_used=retries_used,
        retry_success=False,
    ).as_dict()
