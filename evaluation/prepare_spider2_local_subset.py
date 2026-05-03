"""Prepare a SQLite-backed Spider2-lite local subset for QueryShield evaluation."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_REPO_ROOT = Path("queryshield/data/spider2_repo/spider2-lite")
DEFAULT_OUTPUT_JSON = Path("queryshield/data/spider2/spider2_local_subset.json")
DEFAULT_SQLITE_OUT = Path("queryshield/data/spider2/local_sqlite_dbs")


def prepare_spider2_local_subset(
    repo_root: Path,
    output_json: Path,
    sqlite_out_dir: Path,
) -> dict[str, Any]:
    """
    Build local SQLite DB files from Spider2-lite local table dumps and write subset JSON.

    Output JSON format:
    [
      {
        "id": "...",
        "db_id": "...",
        "question": "...",
        "query": "...",
        "db_path": "..."
      }
    ]
    """
    root = Path(repo_root)
    if not root.exists():
        raise FileNotFoundError(f"Spider2-lite root not found: {root}")

    jsonl_path = root / "spider2-lite.jsonl"
    gold_sql_dir = root / "evaluation_suite" / "gold" / "sql"
    local_db_dir = root / "resource" / "databases" / "sqlite"

    if not jsonl_path.exists():
        raise FileNotFoundError(f"Missing file: {jsonl_path}")
    if not gold_sql_dir.exists():
        raise FileNotFoundError(f"Missing directory: {gold_sql_dir}")
    if not local_db_dir.exists():
        raise FileNotFoundError(f"Missing directory: {local_db_dir}")

    local_gold_ids = {path.stem for path in gold_sql_dir.glob("local*.sql")}
    examples = _load_local_examples(jsonl_path=jsonl_path, local_gold_ids=local_gold_ids)
    if not examples:
        raise ValueError("No local Spider2 examples with gold SQL found.")

    available_db_dirs = [path for path in local_db_dir.iterdir() if path.is_dir()]
    folder_lookup = {_normalize_name(path.name): path for path in available_db_dirs}

    sqlite_out_dir = Path(sqlite_out_dir)
    sqlite_out_dir.mkdir(parents=True, exist_ok=True)

    db_id_to_path: dict[str, Path] = {}
    missing_dbs: set[str] = set()
    for db_id in sorted({example["db_id"] for example in examples}):
        db_folder = folder_lookup.get(_normalize_name(db_id))
        if db_folder is None:
            missing_dbs.add(db_id)
            continue
        sqlite_path = sqlite_out_dir / f"{db_id}.sqlite"
        _build_sqlite_db_from_folder(db_folder=db_folder, sqlite_path=sqlite_path)
        db_id_to_path[db_id] = sqlite_path.resolve()

    subset_rows: list[dict[str, Any]] = []
    skipped_missing_db = 0
    for example in examples:
        db_id = example["db_id"]
        if db_id not in db_id_to_path:
            skipped_missing_db += 1
            continue
        subset_rows.append(
            {
                "id": example["instance_id"],
                "db_id": db_id,
                "question": example["question"],
                "query": example["gold_sql"],
                "db_path": str(db_id_to_path[db_id]),
            }
        )

    output_json = Path(output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(subset_rows, indent=2), encoding="utf-8")

    return {
        "output_json": str(output_json.resolve()),
        "total_examples": len(examples),
        "subset_examples": len(subset_rows),
        "unique_dbs": len({row["db_id"] for row in subset_rows}),
        "missing_db_count": len(missing_dbs),
        "skipped_missing_db_examples": skipped_missing_db,
        "missing_db_ids": sorted(missing_dbs),
    }


def _load_local_examples(jsonl_path: Path, local_gold_ids: set[str]) -> list[dict[str, str]]:
    by_instance: dict[str, dict[str, str]] = {}
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            instance_id = str(item.get("instance_id") or "").strip()
            if instance_id not in local_gold_ids:
                continue
            db_id = str(item.get("db") or "").strip()
            question = str(item.get("question") or "").strip()
            if not db_id or not question:
                continue
            by_instance[instance_id] = {
                "instance_id": instance_id,
                "db_id": db_id,
                "question": question,
            }

    examples: list[dict[str, str]] = []
    gold_sql_dir = jsonl_path.parent / "evaluation_suite" / "gold" / "sql"
    for instance_id, item in sorted(by_instance.items()):
        sql_path = gold_sql_dir / f"{instance_id}.sql"
        if not sql_path.exists():
            continue
        gold_sql = sql_path.read_text(encoding="utf-8").strip()
        if not gold_sql:
            continue
        examples.append(
            {
                "instance_id": instance_id,
                "db_id": item["db_id"],
                "question": item["question"],
                "gold_sql": gold_sql,
            }
        )
    return examples


def _build_sqlite_db_from_folder(db_folder: Path, sqlite_path: Path) -> None:
    if sqlite_path.exists():
        sqlite_path.unlink()

    with sqlite3.connect(sqlite_path) as conn:
        conn.execute("PRAGMA foreign_keys = OFF;")
        _create_tables_from_json_metadata(conn=conn, db_folder=db_folder)
        _load_sample_rows(conn=conn, db_folder=db_folder)
        conn.commit()


def _create_tables_from_json_metadata(conn: sqlite3.Connection, db_folder: Path) -> None:
    """
    Create tables from table JSON metadata.

    We avoid raw DDL parsing because some Spider2 DDL entries include
    non-SQLite-safe constructs and reserved identifiers.
    """
    # Optional type hints from DDL.csv.
    ddl_types: dict[str, list[tuple[str, str]]] = {}
    ddl_path = db_folder / "DDL.csv"
    if ddl_path.exists():
        ddl_types = _parse_ddl_column_types(ddl_path)

    for table_json in sorted(db_folder.glob("*.json")):
        payload = json.loads(table_json.read_text(encoding="utf-8"))
        table_name = str(payload.get("table_name") or table_json.stem).strip()
        if not table_name or table_name.lower().startswith("sqlite_"):
            continue

        columns = payload.get("column_names")
        column_types = payload.get("column_types")
        column_defs: list[tuple[str, str]] = []

        if isinstance(columns, list) and columns:
            for idx, column in enumerate(columns):
                name = str(column)
                if not name:
                    continue
                dtype = "TEXT"
                if isinstance(column_types, list) and idx < len(column_types):
                    dtype = _normalize_sqlite_type(str(column_types[idx]))
                column_defs.append((name, dtype))

        # Fallback to parsed DDL column types if metadata is incomplete.
        if not column_defs and table_name in ddl_types:
            column_defs = ddl_types[table_name]

        # Last fallback: infer columns from sample rows.
        if not column_defs:
            sample_rows = payload.get("sample_rows") or []
            if isinstance(sample_rows, list) and sample_rows and isinstance(sample_rows[0], dict):
                column_defs = [(str(key), "TEXT") for key in sample_rows[0].keys()]

        if not column_defs:
            continue

        columns_sql = ", ".join(
            f'{_quote_identifier(column)} {dtype}' for column, dtype in column_defs
        )
        conn.execute(f"CREATE TABLE IF NOT EXISTS {_quote_identifier(table_name)} ({columns_sql});")


def _load_sample_rows(conn: sqlite3.Connection, db_folder: Path) -> None:
    for table_json in sorted(db_folder.glob("*.json")):
        if table_json.name.lower() == "ddl.json":
            continue
        payload = json.loads(table_json.read_text(encoding="utf-8"))
        table_name = str(payload.get("table_name") or table_json.stem).strip()
        if table_name.lower().startswith("sqlite_"):
            continue
        sample_rows = payload.get("sample_rows") or []
        if not table_name or not isinstance(sample_rows, list) or not sample_rows:
            continue

        # Keep columns in table schema order when available.
        schema_columns = _get_table_columns(conn=conn, table_name=table_name)
        if schema_columns:
            columns = [column for column in schema_columns if any(column in row for row in sample_rows)]
        else:
            columns = list(sample_rows[0].keys())
        if not columns:
            continue

        placeholders = ", ".join("?" for _ in columns)
        quoted_columns = ", ".join(_quote_identifier(column) for column in columns)
        insert_sql = (
            f"INSERT INTO {_quote_identifier(table_name)} ({quoted_columns}) "
            f"VALUES ({placeholders});"
        )
        values_batch: list[tuple[Any, ...]] = []
        for row in sample_rows:
            if not isinstance(row, dict):
                continue
            values_batch.append(tuple(_normalize_value(row.get(column)) for column in columns))
        if values_batch:
            conn.executemany(insert_sql, values_batch)


def _get_table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    escaped = table_name.replace('"', '""')
    rows = conn.execute(f'PRAGMA table_info("{escaped}")').fetchall()
    return [str(row[1]) for row in rows]


def _normalize_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _parse_ddl_column_types(ddl_path: Path) -> dict[str, list[tuple[str, str]]]:
    """
    Best-effort parser for `CREATE TABLE ...` column definitions in DDL.csv.

    This is only used as fallback metadata and intentionally ignores constraints.
    """
    table_columns: dict[str, list[tuple[str, str]]] = {}
    with ddl_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            table_name = str(row.get("table_name") or "").strip()
            ddl = str(row.get("DDL") or "")
            if not table_name or "CREATE TABLE" not in ddl.upper():
                continue

            open_idx = ddl.find("(")
            close_idx = ddl.rfind(")")
            if open_idx < 0 or close_idx <= open_idx:
                continue
            inside = ddl[open_idx + 1 : close_idx]
            columns: list[tuple[str, str]] = []
            for raw_line in inside.splitlines():
                line = raw_line.strip().rstrip(",")
                if not line:
                    continue
                upper = line.upper()
                if upper.startswith(("PRIMARY KEY", "FOREIGN KEY", "CONSTRAINT", "UNIQUE", "CHECK")):
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                column_name = parts[0].strip('`"[]')
                dtype = _normalize_sqlite_type(parts[1])
                columns.append((column_name, dtype))
            if columns:
                table_columns[table_name] = columns
    return table_columns


def _normalize_sqlite_type(raw_dtype: str) -> str:
    dtype = raw_dtype.upper().strip()
    if any(token in dtype for token in ("INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT")):
        return "INTEGER"
    if any(token in dtype for token in ("REAL", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC")):
        return "REAL"
    if "BLOB" in dtype:
        return "BLOB"
    return "TEXT"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a Spider2-lite local subset with generated SQLite DBs."
    )
    parser.add_argument(
        "--repo-root",
        default=str(DEFAULT_REPO_ROOT),
        help="Path to cloned spider2-lite repo root.",
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON),
        help="Where to write the prepared subset JSON.",
    )
    parser.add_argument(
        "--sqlite-out",
        default=str(DEFAULT_SQLITE_OUT),
        help="Directory to write generated SQLite DB files.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    summary = prepare_spider2_local_subset(
        repo_root=Path(args.repo_root),
        output_json=Path(args.output_json),
        sqlite_out_dir=Path(args.sqlite_out),
    )
    print("Spider2 local subset prepared.")
    for key, value in summary.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
