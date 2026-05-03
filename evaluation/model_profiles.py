"""Model-specific prompt configuration profiles.

Different LLMs have dramatically different personalities when it comes to
strict validation tasks. LLaMA 3.3 is overly pedantic, DeepSeek-R1 wraps
answers in <think> blocks, and Gemma prefers lenient validators.

This module provides per-model profile overrides that are applied at
runtime to adapt prompts, timeouts, and validator strictness to the
active model — eliminating the "one-size-fits-all" prompt problem that
caused accuracy drops in our benchmarks.
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Model profile definitions
# ---------------------------------------------------------------------------

MODEL_PROFILES: dict[str, dict[str, Any]] = {
    # ---- Cloud / Groq models ----
    "llama-3.3-70b-versatile": {
        "validator_strictness": "lenient",
        "validator_suffix": (
            "Be lenient. If the SQL accomplishes the core intent of the plan, "
            "return VALID. Do not flag cosmetic differences like column aliases, "
            "ordering direction, or minor filter phrasing. Only mark INVALID "
            "for genuinely wrong tables, missing joins, or wrong aggregation types."
        ),
        "planner_format": "standard",
        "timeout_multiplier": 1,
        "strip_thinking": False,
    },
    "llama-3.1-8b-instant": {
        "validator_strictness": "lenient",
        "validator_suffix": (
            "Be lenient. If SQL achieves the core intent, return VALID."
        ),
        "planner_format": "standard",
        "timeout_multiplier": 1,
        "strip_thinking": False,
    },
    "llama3-70b-8192": {
        "validator_strictness": "lenient",
        "validator_suffix": (
            "Be lenient. If SQL achieves the core intent, return VALID."
        ),
        "planner_format": "standard",
        "timeout_multiplier": 1,
        "strip_thinking": False,
    },

    # ---- Mistral / Mixtral ----
    "mistral-saba-24b": {
        "validator_strictness": "standard",
        "validator_suffix": "",
        "planner_format": "standard",
        "timeout_multiplier": 1,
        "strip_thinking": False,
    },
    "mixtral-8x7b-32768": {
        "validator_strictness": "standard",
        "validator_suffix": "",
        "planner_format": "standard",
        "timeout_multiplier": 1,
        "strip_thinking": False,
    },

    # ---- DeepSeek reasoning ----
    "deepseek-r1-distill-llama-70b": {
        "validator_strictness": "standard",
        "validator_suffix": "",
        "planner_format": "reasoning",
        "timeout_multiplier": 5,
        "strip_thinking": True,
    },
    "deepseek-r1:8b": {
        "validator_strictness": "standard",
        "validator_suffix": "",
        "planner_format": "reasoning",
        "timeout_multiplier": 5,
        "strip_thinking": True,
    },

    # ---- Gemma (local Ollama) ----
    "gemma4:e4b": {
        "validator_strictness": "lenient",
        "validator_suffix": (
            "Be lenient. If SQL achieves the core intent, return VALID."
        ),
        "planner_format": "standard",
        "timeout_multiplier": 4,
        "strip_thinking": False,
    },
    "gemma4:31b-cloud": {
        "validator_strictness": "lenient",
        "validator_suffix": (
            "Be lenient. If SQL achieves the core intent, return VALID."
        ),
        "planner_format": "standard",
        "timeout_multiplier": 3,
        "strip_thinking": False,
    },

    # ---- Qwen (local Ollama) ----
    "qwen2.5:3b": {
        "validator_strictness": "lenient",
        "validator_suffix": (
            "Be lenient. If SQL achieves the core intent, return VALID."
        ),
        "planner_format": "standard",
        "timeout_multiplier": 2,
        "strip_thinking": False,
    },
}


# Default profile for unknown models
_DEFAULT_PROFILE: dict[str, Any] = {
    "validator_strictness": "standard",
    "validator_suffix": "",
    "planner_format": "standard",
    "timeout_multiplier": 1,
    "strip_thinking": False,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_model_profile(model_name: str) -> dict[str, Any]:
    """Return the profile for a given model name.

    First tries an exact match, then a fuzzy prefix match
    (e.g. "llama-3.3-70b-versatile" matches "llama-3.3").
    Falls back to the default profile if no match is found.
    """
    if model_name in MODEL_PROFILES:
        return {**_DEFAULT_PROFILE, **MODEL_PROFILES[model_name]}

    # Fuzzy prefix match: "llama-3.3-70b-versatile" → try "llama-3.3"
    for key in MODEL_PROFILES:
        if model_name.startswith(key) or key.startswith(model_name):
            return {**_DEFAULT_PROFILE, **MODEL_PROFILES[key]}

    # Check for family name match (e.g. "llama" in model_name)
    model_lower = model_name.lower()
    for key in MODEL_PROFILES:
        family = key.split("-")[0].split(":")[0].lower()
        if family in model_lower:
            return {**_DEFAULT_PROFILE, **MODEL_PROFILES[key]}

    return dict(_DEFAULT_PROFILE)


def strip_thinking_blocks(text: str) -> str:
    """Remove <think>...</think> blocks from reasoning model output.

    DeepSeek-R1 and similar models generate invisible chain-of-thought
    wrapped in <think> tags before the actual answer. This function
    strips those blocks so JSON parsers don't choke.
    """
    # Remove <think>...</think> blocks (greedy within each block)
    cleaned = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return cleaned.strip()


def apply_profile_to_timeout(
    base_timeout: int,
    model_name: str,
) -> int:
    """Apply the model's timeout multiplier to a base timeout."""
    profile = get_model_profile(model_name)
    multiplier = profile.get("timeout_multiplier", 1)
    return int(base_timeout * multiplier)
