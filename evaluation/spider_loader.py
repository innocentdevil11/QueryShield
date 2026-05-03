"""Spider dataset loading and DB path resolution utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SpiderExample:
    """One Spider-style text-to-SQL evaluation sample."""

    example_id: str
    db_id: str
    question: str
    gold_sql: str
    db_path: Path


def load_spider_examples(dataset_json: Path, db_root: Path) -> list[SpiderExample]:
    """
    Load Spider examples from JSON and resolve SQLite database paths.

    Supported JSON shapes:
    - list[dict]
    - {"examples": list[dict]}
    - {"data": list[dict]}
    - {"items": list[dict]}
    """
    dataset_path = Path(dataset_json)
    root = Path(db_root)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset JSON not found: {dataset_path}")
    if not root.exists():
        raise FileNotFoundError(f"Database root not found: {root}")

    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    rows = _extract_rows(payload)

    examples: list[SpiderExample] = []
    skipped = 0
    for index, row in enumerate(rows):
        db_id = str(row.get("db_id") or "").strip()
        question = _extract_question(row)
        gold_sql = _extract_gold_sql(row)
        if not db_id or not question or not gold_sql:
            skipped += 1
            continue

        db_path = _resolve_db_path(row=row, db_root=root, db_id=db_id)
        if db_path is None:
            skipped += 1
            continue

        example_id = str(row.get("id") or row.get("example_id") or f"{db_id}:{index}")
        examples.append(
            SpiderExample(
                example_id=example_id,
                db_id=db_id,
                question=question,
                gold_sql=gold_sql,
                db_path=db_path,
            )
        )

    if not examples:
        raise ValueError(
            "No valid Spider examples were loaded. "
            f"Checked {len(rows)} entries, skipped {skipped}."
        )
    return examples


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("examples", "data", "items"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    raise ValueError("Unsupported dataset JSON format.")


def _extract_question(row: dict[str, Any]) -> str:
    for key in ("question", "utterance", "nl_question", "prompt"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_gold_sql(row: dict[str, Any]) -> str:
    # Spider variants often have "query" as SQL string and "sql" as parsed AST.
    for key in ("query", "gold_sql", "SQL"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    sql_value = row.get("sql")
    if isinstance(sql_value, str) and sql_value.strip():
        return sql_value.strip()
    return ""


def _resolve_db_path(row: dict[str, Any], db_root: Path, db_id: str) -> Path | None:
    # Direct db_path/database_path in row.
    direct_path = row.get("db_path") or row.get("database_path")
    if isinstance(direct_path, str) and direct_path.strip():
        candidate = Path(direct_path.strip())
        if not candidate.is_absolute():
            candidate = db_root / candidate
        if candidate.exists():
            return candidate.resolve()

    # Common Spider layouts.
    candidates = [
        db_root / f"{db_id}.sqlite",
        db_root / f"{db_id}.db",
        db_root / db_id / f"{db_id}.sqlite",
        db_root / db_id / f"{db_id}.db",
        db_root / "database" / db_id / f"{db_id}.sqlite",
        db_root / "database" / db_id / f"{db_id}.db",
        db_root / "databases" / db_id / f"{db_id}.sqlite",
        db_root / "databases" / db_id / f"{db_id}.db",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None

