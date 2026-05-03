"""Plan generation helpers for plan-first Text-to-SQL system pipeline."""

from __future__ import annotations

import json
import re
from typing import Any

PLAN_KEYS = (
    "intent",
    "tables",
    "joins",
    "filters",
    "aggregations",
    "group_by",
    "order_by",
    "limit",
    "subqueries",
    "reasoning_steps",
)


def build_planner_prompt(schema: str, question: str) -> str:
    """Build planner prompt that requests strict JSON plan output."""
    return (
        "You are an expert SQL query planner.\n\n"
        "Your task is NOT to generate SQL.\n\n"
        "Your task is to deeply analyze the question and produce a precise "
        "execution plan that can be later converted into correct SQL.\n\n"
        "---\n\n"
        "INPUT:\n\n"
        "* Natural language question\n"
        "* Database schema\n\n"
        "---\n\n"
        "OBJECTIVE:\n\n"
        "Break the problem into structured reasoning steps.\n\n"
        "---\n\n"
        "OUTPUT FORMAT (STRICT JSON):\n\n"
        "{\n"
        "\"intent\": \"...\",\n"
        "\"tables\": [\"...\"],\n"
        "\"joins\": [\n"
        "{\"left\": \"...\", \"right\": \"...\", \"on\": \"...\"}\n"
        "],\n"
        "\"filters\": [\"...\"],\n"
        "\"aggregations\": [\"...\"],\n"
        "\"group_by\": [\"...\"],\n"
        "\"order_by\": [\"...\"],\n"
        "\"limit\": \"...\",\n"
        "\"subqueries\": [\"...\"],\n"
        "\"reasoning_steps\": [\"step1\", \"step2\", \"...\"]\n"
        "}\n\n"
        "---\n\n"
        "EXAMPLE 1 (simple):\n"
        "Schema: orders(order_id, customer_id, amount), customers(customer_id, name)\n"
        "Question: Find all customers who spent more than $500 total.\n"
        "Output: {\"intent\":\"filter+aggregate\",\"tables\":[\"orders\",\"customers\"],"
        "\"joins\":[{\"left\":\"orders\",\"right\":\"customers\","
        "\"on\":\"orders.customer_id=customers.customer_id\"}],"
        "\"filters\":[\"SUM(orders.amount) > 500\"],"
        "\"aggregations\":[\"SUM(orders.amount)\"],"
        "\"group_by\":[\"customers.customer_id\"],"
        "\"order_by\":[],\"limit\":\"\",\"subqueries\":[],"
        "\"reasoning_steps\":[\"Join orders to customers\","
        "\"Group by customer\",\"Filter by SUM > 500\"]}\n\n"
        "EXAMPLE 2 (complex with subquery, from Spider2):\n"
        "Schema: match(match_id, season_id), ball_by_ball(match_id, over_id, ball_id, innings_no, striker), "
        "batsman_scored(match_id, over_id, ball_id, innings_no, runs_scored), player(player_id, player_name)\n"
        "Question: Please help me find the names of top 5 players with the highest average runs per match in season 5.\n"
        "Output: {\"intent\":\"aggregation+ranking\",\"tables\":[\"match\",\"ball_by_ball\",\"batsman_scored\",\"player\"],"
        "\"joins\":[{\"left\":\"match\",\"right\":\"ball_by_ball\",\"on\":\"match.match_id=ball_by_ball.match_id\"},"
        "{\"left\":\"ball_by_ball\",\"right\":\"batsman_scored\",\"on\":\"ball_by_ball.match_id=batsman_scored.match_id AND "
        "ball_by_ball.over_id=batsman_scored.over_id AND ball_by_ball.ball_id=batsman_scored.ball_id AND "
        "ball_by_ball.innings_no=batsman_scored.innings_no\"},"
        "{\"left\":\"ball_by_ball\",\"right\":\"player\",\"on\":\"ball_by_ball.striker=player.player_id\"}],"
        "\"filters\":[\"match.season_id = 5\"],"
        "\"aggregations\":[\"SUM(batsman_scored.runs_scored)\",\"COUNT(DISTINCT match.match_id)\"],"
        "\"group_by\":[\"player.player_id\",\"player.player_name\"],"
        "\"order_by\":[\"SUM(batsman_scored.runs_scored) / COUNT(DISTINCT match.match_id) DESC\"],"
        "\"limit\":\"5\",\"subqueries\":[],"
        "\"reasoning_steps\":[\"Filter season 5 matches\",\"Join ball and scoring tables\",\"Aggregate runs and matches per player\","
        "\"Compute average runs per match\",\"Order descending and limit 5\"]}\n\n"
        "---\n\n"
        "PLANNING RULES (VERY IMPORTANT):\n\n"
        "1. INTENT UNDERSTANDING\n\n"
        "* Clearly identify what the question is asking\n"
        "* Identify if it is:\n\n"
        "  * filtering\n"
        "  * aggregation\n"
        "  * ranking\n"
        "  * comparison\n"
        "  * nested reasoning\n\n"
        "---\n\n"
        "2. TABLE SELECTION\n\n"
        "* ONLY include tables required\n"
        "* Use schema relationships\n"
        "* Avoid unnecessary tables\n\n"
        "---\n\n"
        "3. JOIN LOGIC\n\n"
        "* Identify foreign key relationships\n"
        "* Explicitly define join conditions\n"
        "* Avoid Cartesian joins\n\n"
        "---\n\n"
        "4. AGGREGATION LOGIC\n\n"
        "* Detect keywords:\n\n"
        "  * \"total\", \"sum\" -> SUM\n"
        "  * \"average\" -> AVG\n"
        "  * \"count\" -> COUNT\n"
        "  * \"top\", \"highest\" -> ORDER BY + LIMIT\n\n"
        "---\n\n"
        "5. GROUPING LOGIC\n\n"
        "* If aggregation per entity -> MUST include GROUP BY\n"
        "* Ensure correct grouping columns\n\n"
        "---\n\n"
        "6. NESTED / MULTI-STEP REASONING\n\n"
        "* If query requires:\n\n"
        "  * ranking within groups\n"
        "  * comparing aggregates\n"
        "  * filtering aggregated results\n\n"
        "-> MUST use subqueries or CTEs\n\n"
        "---\n\n"
        "7. VALIDATION (CRITICAL)\n\n"
        "Before returning:\n\n"
        "* Are all joins correct?\n"
        "* Are required tables included?\n"
        "* Is aggregation correct?\n"
        "* Is grouping correct?\n"
        "* Does plan match question EXACTLY?\n\n"
        "---\n\n"
        "IMPORTANT:\n\n"
        "* DO NOT generate SQL\n"
        "* DO NOT skip steps\n"
        "* BE PRECISE\n"
        "* THINK STEP BY STEP\n\n"
        "Respond ONLY with the JSON object. No text before or after. "
        "No markdown backticks.\n\n"
        "---\n\n"
        "Schema:\n"
        f"{schema.strip()}\n\n"
        "Question:\n"
        f"{question.strip()}\n"
    )



def parse_plan_response(raw_text: str) -> tuple[dict[str, Any], str]:
    """
    Parse planner output to normalized plan JSON.

    Returns:
    - normalized plan object
    - parse_error message (empty on success)
    """
    candidate = _strip_code_fences(raw_text or "")
    parse_error = ""

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        extracted = _extract_json_object(candidate)
        if extracted is None:
            return _empty_plan(), f"plan_parse_error: {exc}"
        try:
            parsed = json.loads(extracted)
        except json.JSONDecodeError as nested_exc:
            return _empty_plan(), f"plan_parse_error: {nested_exc}"

    if not isinstance(parsed, dict):
        return _empty_plan(), "plan_parse_error: planner output is not a JSON object."

    normalized = _normalize_plan(parsed)
    if not normalized["intent"]:
        parse_error = "plan_parse_warning: missing intent."
    return normalized, parse_error


def assess_plan_quality(plan: dict[str, Any]) -> dict[str, Any]:
    """Compute lightweight plan quality score for experiment tracking."""
    checks = [
        ("intent", _is_non_empty_string(plan.get("intent"))),
        ("tables", _is_non_empty_list(plan.get("tables"))),
        ("joins", isinstance(plan.get("joins"), list)),
        ("filters", isinstance(plan.get("filters"), list)),
        ("aggregations", isinstance(plan.get("aggregations"), list)),
        ("group_by", isinstance(plan.get("group_by"), list)),
        ("order_by", isinstance(plan.get("order_by"), list)),
        ("limit", isinstance(plan.get("limit"), str)),
        ("subqueries", isinstance(plan.get("subqueries"), list)),
        ("reasoning_steps", _is_non_empty_list(plan.get("reasoning_steps"))),
    ]
    satisfied = [name for name, ok in checks if ok]
    missing = [name for name, ok in checks if not ok]
    score = len(satisfied) / len(checks)
    if score >= 0.8:
        level = "high"
    elif score >= 0.5:
        level = "medium"
    else:
        level = "low"
    return {
        "score": round(score, 4),
        "level": level,
        "missing": missing,
    }


def _normalize_plan(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "intent": _to_string(payload.get("intent")),
        "tables": _to_string_list(payload.get("tables")),
        "joins": _to_join_list(payload.get("joins")),
        "filters": _to_string_list(payload.get("filters")),
        "aggregations": _to_string_list(payload.get("aggregations")),
        "group_by": _to_string_list(payload.get("group_by")),
        "order_by": _to_string_list(payload.get("order_by")),
        "limit": _to_string(payload.get("limit")),
        "subqueries": _to_string_list(payload.get("subqueries")),
        "reasoning_steps": _to_string_list(payload.get("reasoning_steps")),
    }


def _empty_plan() -> dict[str, Any]:
    return {
        "intent": "",
        "tables": [],
        "joins": [],
        "filters": [],
        "aggregations": [],
        "group_by": [],
        "order_by": [],
        "limit": "",
        "subqueries": [],
        "reasoning_steps": [],
    }


def _strip_code_fences(text: str) -> str:
    candidate = (text or "").strip()
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", candidate, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced[0].strip()
    return candidate


def _extract_json_object(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1].strip()


def _to_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    item = str(value).strip()
    return [item] if item else []


def _to_join_list(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    joins: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            joins.append(
                {
                    "left": _to_string(item.get("left")),
                    "right": _to_string(item.get("right")),
                    "on": _to_string(item.get("on")),
                }
            )
        else:
            text = _to_string(item)
            if text:
                joins.append({"left": "", "right": "", "on": text})
    return joins


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0
