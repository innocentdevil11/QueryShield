"""Hard-subset selection for Spider evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from queryshield.evaluation.spider_loader import SpiderExample


@dataclass(frozen=True)
class ComplexityInfo:
    """Complexity analysis metadata for a Spider example."""

    score: int
    is_complex: bool
    reasons: tuple[str, ...]


def analyze_complexity(question: str, sql: str) -> ComplexityInfo:
    """Compute a deterministic complexity score from NL + SQL signals."""
    sql_upper = f" {sql.upper()} "
    question_lower = f" {question.lower()} "

    score = 0
    reasons: list[str] = []

    join_count = sql_upper.count(" JOIN ")
    if join_count > 0:
        score += min(join_count, 4) * 2
        reasons.append(f"joins:{join_count}")

    nested_count = max(sql_upper.count(" SELECT ") - 1, 0)
    if nested_count > 0:
        score += 3
        reasons.append("nested-select")

    if " GROUP BY " in sql_upper:
        score += 2
        reasons.append("group-by")
    if " HAVING " in sql_upper:
        score += 1
        reasons.append("having")

    if " ORDER BY " in sql_upper:
        score += 1
        reasons.append("order-by")
    if " LIMIT " in sql_upper:
        score += 1
        reasons.append("limit")

    if any(token in sql_upper for token in (" UNION ", " INTERSECT ", " EXCEPT ")):
        score += 3
        reasons.append("set-operation")

    if any(token in sql_upper for token in (" EXISTS ", " NOT EXISTS ", " IN (SELECT")):
        score += 2
        reasons.append("subquery-filter")

    if any(token in sql_upper for token in (" COUNT(", " AVG(", " SUM(", " MAX(", " MIN(")):
        score += 1
        reasons.append("aggregation")

    # Natural-language ambiguity and reasoning signals.
    if any(
        token in question_lower
        for token in (
            " best ",
            " top ",
            " better ",
            " above average ",
            " per ",
            " each ",
            " never ",
            " every ",
            " improved ",
            " highest ",
            " lowest ",
        )
    ):
        score += 1
        reasons.append("ambiguous-nl")

    is_complex = score >= 6 or join_count >= 2 or nested_count >= 1
    return ComplexityInfo(score=score, is_complex=is_complex, reasons=tuple(reasons))


def select_hard_subset(
    examples: list[SpiderExample],
    num_dbs: int = 3,
    num_queries: int = 24,
) -> tuple[list[SpiderExample], dict[str, Any]]:
    """
    Select hard queries from 2-3 DBs with complexity-first ranking.

    Returns:
        (selected_examples, metadata)
    """
    if not examples:
        return [], {"selected_db_ids": [], "selected_count": 0}

    # Allow both quick profiling runs (1 query/DB) and broader experiments.
    bounded_num_dbs = max(1, min(20, num_dbs))
    bounded_num_queries = max(1, min(300, num_queries))

    ranked_rows = [
        (example, analyze_complexity(example.question, example.gold_sql))
        for example in examples
    ]
    grouped: dict[str, list[tuple[SpiderExample, ComplexityInfo]]] = {}
    for example, info in ranked_rows:
        grouped.setdefault(example.db_id, []).append((example, info))

    # Keep DBs with enough rows for meaningful evaluation.
    db_candidates: list[tuple[str, int, float]] = []
    for db_id, rows in grouped.items():
        rows.sort(
            key=lambda item: (
                item[1].score,
                len(item[0].gold_sql),
                len(item[0].question),
            ),
            reverse=True,
        )
        complex_count = sum(1 for _, info in rows if info.is_complex)
        avg_score = sum(info.score for _, info in rows) / max(len(rows), 1)
        db_candidates.append((db_id, complex_count, avg_score))

    db_candidates.sort(key=lambda item: (item[1], item[2], item[0]), reverse=True)
    selected_db_ids = [item[0] for item in db_candidates[:bounded_num_dbs]]
    if not selected_db_ids:
        return [], {"selected_db_ids": [], "selected_count": 0}

    # Round-robin allocation so we actually cover 2-3 distinct databases.
    selected: list[SpiderExample] = []
    per_db_indexes = {db_id: 0 for db_id in selected_db_ids}
    while len(selected) < bounded_num_queries:
        progressed = False
        for db_id in selected_db_ids:
            rows = grouped[db_id]
            idx = per_db_indexes[db_id]
            if idx < len(rows):
                selected.append(rows[idx][0])
                per_db_indexes[db_id] = idx + 1
                progressed = True
                if len(selected) >= bounded_num_queries:
                    break
        if not progressed:
            break

    metadata = {
        "selected_db_ids": selected_db_ids,
        "selected_count": len(selected),
        "requested_num_dbs": bounded_num_dbs,
        "requested_num_queries": bounded_num_queries,
    }
    return selected, metadata
