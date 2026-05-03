"""SQL generation prompt builder for plan-based system pipeline."""

from __future__ import annotations

import json
from typing import Any


def build_sql_from_plan_prompt(plan: dict[str, Any], schema: str) -> str:
    """Build strict SQL generation prompt from normalized plan JSON."""
    plan_payload = json.dumps(plan, ensure_ascii=True, indent=2)
    return (
        "You are a strict SQL compiler.\n\n"
        "Rules:\n\n"
        "* MUST follow plan EXACTLY\n"
        "* MUST include ALL joins\n"
        "* MUST include ALL aggregations\n"
        "* MUST include ALL group_by fields\n"
        "* MUST include ALL filters\n"
        "* MUST NOT add new logic\n"
        "* MUST NOT change aggregation type\n\n"
        "If plan says SUM -> SQL MUST use SUM.\n"
        "If plan says GROUP BY -> SQL MUST match exactly.\n\n"
        "---\n\n"
        "Use only the plan and schema below.\n\n"
        "Plan:\n"
        f"{plan_payload}\n\n"
        "Schema:\n"
        f"{schema.strip()}\n\n"
        "CRITICAL RULES FOR SQLITE (NEVER VIOLATE):\n"
        "1. Never use YEAR(col) — use strftime('%Y', col) instead\n"
        "2. Never use QUALIFY — use a subquery with WHERE instead\n"
        "3. ORDER BY must come AFTER the final UNION/UNION ALL, not before\n"
        "4. Never reference columns not explicitly listed in the schema above\n"
        "5. Never use ILIKE — use LOWER(col) LIKE LOWER(pattern) instead\n\n"
        "Return ONLY the SQL query. No explanation. No markdown. No backticks.\n"
    )


def build_sql_fix_from_plan_prompt(
    plan: dict[str, Any],
    sql: str,
    issues: list[str],
    schema: str,
) -> str:
    """Build strict SQL regeneration prompt from plan-validation feedback."""
    plan_payload = json.dumps(plan, ensure_ascii=True, indent=2)
    issue_lines = "\n".join(f"- {item}" for item in issues if str(item).strip())
    if not issue_lines:
        issue_lines = "- SQL does not strictly match plan."
    return (
        "You are fixing SQL to match a plan.\n\n"
        "Plan:\n"
        f"{plan_payload}\n\n"
        "Previous SQL:\n"
        f"{sql.strip()}\n\n"
        "Issues:\n"
        f"{issue_lines}\n\n"
        "Fix the SQL STRICTLY to match the plan.\n\n"
        "Rules:\n\n"
        "* Do NOT change intent\n"
        "* Fix only incorrect parts\n"
        "* Ensure ALL plan constraints are satisfied\n\n"
        "Schema:\n"
        f"{schema.strip()}\n\n"
        "Return ONLY SQL.\n"
    )
