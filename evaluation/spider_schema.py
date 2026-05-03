"""Rich schema formatting for Spider evaluation prompts."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def build_rich_schema_context(db_path: Path) -> str:
    """
    Build schema context with tables, columns, types, PKs, and FKs.

    Format intentionally explicit to reduce column/join hallucination.
    """
    database_path = Path(db_path)
    if not database_path.exists():
        raise FileNotFoundError(f"Database not found: {database_path}")

    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        table_rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
            """
        ).fetchall()

        table_blocks: list[str] = []
        foreign_keys: list[str] = []

        for table_row in table_rows:
            table_name = str(table_row["name"])
            escaped_table = table_name.replace('"', '""')

            columns = conn.execute(f'PRAGMA table_info("{escaped_table}")').fetchall()
            fk_rows = conn.execute(f'PRAGMA foreign_key_list("{escaped_table}")').fetchall()

            column_lines: list[str] = []
            primary_keys: list[str] = []
            for column in columns:
                column_name = str(column["name"])
                column_type = str(column["type"] or "TEXT")
                pk_rank = int(column["pk"] or 0)
                not_null = int(column["notnull"] or 0) == 1

                tags: list[str] = []
                if pk_rank > 0:
                    tags.append(f"PK#{pk_rank}")
                    primary_keys.append(column_name)
                if not_null:
                    tags.append("NOT NULL")
                tag_suffix = f" [{' | '.join(tags)}]" if tags else ""
                column_lines.append(f"- {column_name} ({column_type}){tag_suffix}")

            block_lines = [
                f"Table: {table_name}",
                "Columns:",
                *column_lines,
                "Primary Keys:",
            ]
            if primary_keys:
                block_lines.extend(f"- {pk}" for pk in primary_keys)
            else:
                block_lines.append("- (none)")

            # Add sample data rows to help LLM understand actual values
            try:
                col_names = [str(c["name"]) for c in columns]
                sample_rows = conn.execute(
                    f'SELECT * FROM "{escaped_table}" LIMIT 3'
                ).fetchall()
                if sample_rows:
                    block_lines.append("Sample Data (first 3 rows):")
                    header = " | ".join(col_names)
                    block_lines.append(f"  {header}")
                    for row in sample_rows:
                        vals = []
                        for i, c in enumerate(col_names):
                            v = row[i]
                            s = str(v) if v is not None else "NULL"
                            if len(s) > 40:
                                s = s[:37] + "..."
                            vals.append(s)
                        block_lines.append(f"  {' | '.join(vals)}")
            except Exception:
                pass  # sample data is best-effort

            table_blocks.append("\n".join(block_lines))

            for fk in fk_rows:
                foreign_keys.append(
                    f"- {table_name}.{fk['from']} -> {fk['table']}.{fk['to']}"
                )

    parts = ["\n\n".join(table_blocks)]
    parts.append("Foreign Keys:")
    parts.append("\n".join(foreign_keys) if foreign_keys else "- (none)")
    return "\n\n".join(parts).strip()


def build_schema_dict(db_path: Path) -> dict[str, dict[str, list[str]]]:
    """
    Build a structured schema dictionary from a SQLite database.

    Returns: {'table_name': {'columns': ['col1', 'col2', ...]}}
    """
    database_path = Path(db_path)
    if not database_path.exists():
        return {}

    schema: dict[str, dict[str, list[str]]] = {}
    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        table_rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
            """
        ).fetchall()

        for table_row in table_rows:
            table_name = str(table_row["name"])
            escaped_table = table_name.replace('"', '""')
            columns = conn.execute(f'PRAGMA table_info("{escaped_table}")').fetchall()
            schema[table_name] = {
                "columns": [str(col["name"]) for col in columns],
            }

    return schema

