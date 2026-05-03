"""Structured schema context builder for evaluation prompts."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def build_structured_schema(db_path: Path) -> str:
    """
    Build a compact, structured schema description from SQLite metadata.

    Example style:
    students(id, name, email, department)
    scores(student_id -> students.id, course_id -> courses.id, marks)
    """
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
            """
        ).fetchall()

        table_names = [row["name"] for row in tables]
        table_lines: list[str] = []
        relationship_lines: list[str] = []

        for table in table_names:
            escaped = table.replace('"', '""')
            columns = conn.execute(f'PRAGMA table_info("{escaped}")').fetchall()
            fks = conn.execute(f'PRAGMA foreign_key_list("{escaped}")').fetchall()
            fk_map = {row["from"]: f"{row['table']}.{row['to']}" for row in fks}

            rendered_columns: list[str] = []
            for column in columns:
                name = str(column["name"])
                if name in fk_map:
                    rendered_columns.append(f"{name} -> {fk_map[name]}")
                else:
                    rendered_columns.append(name)

            table_lines.append(f"{table}({', '.join(rendered_columns)})")

            for fk_col, target in fk_map.items():
                relationship_lines.append(f"* {table}.{fk_col} references {target}")

    schema_block = "TABLES:\n" + "\n".join(table_lines)
    rel_block = "IMPORTANT RELATIONSHIPS:\n"
    rel_block += "\n".join(relationship_lines) if relationship_lines else "* None"

    return f"{schema_block}\n\n{rel_block}"

