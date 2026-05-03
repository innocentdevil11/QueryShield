"""Schema loading utilities for prompt grounding."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class SchemaLoader:
    """Load a schema description from a file or directly from SQLite metadata."""

    def __init__(self, db_path: Path, schema_file: Path | None = None) -> None:
        self.db_path = Path(db_path)
        self.schema_file = Path(schema_file) if schema_file else None

    def load_schema(self) -> str:
        """
        Return a prompt-ready schema string.

        Priority:
        1. Use schema file if provided and available.
        2. Fall back to live DB introspection.
        """
        if self.schema_file and self.schema_file.exists():
            return self._load_from_file(self.schema_file)

        return self._load_from_db(self.db_path)

    @staticmethod
    def _load_from_file(schema_path: Path) -> str:
        """Read schema text from disk."""
        return schema_path.read_text(encoding="utf-8").strip()

    def _load_from_db(self, db_path: Path) -> str:
        """Inspect SQLite metadata tables and format a compact schema view."""
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

        with sqlite3.connect(db_path) as conn:
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

            table_names = [row["name"] for row in table_rows]
            table_blocks: list[str] = []
            foreign_keys: list[str] = []

            for table_name in table_names:
                columns = self._get_columns(conn, table_name)
                table_blocks.append(
                    f"Table: {table_name}\nColumns: {', '.join(columns)}"
                )

                for fk in self._get_foreign_keys(conn, table_name):
                    foreign_keys.append(
                        "Foreign Key: "
                        f"{table_name}.{fk['from']} -> {fk['table']}.{fk['to']}"
                    )

        sections: list[str] = []
        if table_blocks:
            sections.append("\n\n".join(table_blocks))
        if foreign_keys:
            sections.append("\n".join(foreign_keys))

        return "\n\n".join(sections).strip()

    @staticmethod
    def _get_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
        """Return all column names for a table."""
        escaped_table = table_name.replace('"', '""')
        rows = conn.execute(f'PRAGMA table_info("{escaped_table}")').fetchall()
        return [row["name"] for row in rows]

    @staticmethod
    def _get_foreign_keys(
        conn: sqlite3.Connection, table_name: str
    ) -> list[dict[str, Any]]:
        """Return foreign key metadata for a table."""
        escaped_table = table_name.replace('"', '""')
        rows = conn.execute(f'PRAGMA foreign_key_list("{escaped_table}")').fetchall()
        return [dict(row) for row in rows]

