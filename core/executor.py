"""SQLite SQL execution utilities."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class SQLExecutor:
    """Execute SQL queries against a SQLite database."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)

    def execute(self, sql: str) -> dict[str, Any]:
        """
        Execute SQL and return structured response.

        Returns:
            {"rows": [...], "error": None} on success
            {"rows": [], "error": "..."} on failure
        """
        if not self.db_path.exists():
            return {"rows": [], "error": f"Database not found: {self.db_path}"}

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(sql)

                if self._is_read_query(sql):
                    rows = [dict(row) for row in cursor.fetchall()]
                    return {"rows": rows, "error": None}

                conn.commit()
                return {"rows": [{"affected_rows": cursor.rowcount}], "error": None}
        except sqlite3.Error as exc:
            return {"rows": [], "error": str(exc)}

    @staticmethod
    def _is_read_query(sql: str) -> bool:
        """Detect whether the query is expected to return rows."""
        normalized = sql.strip().lower()
        return normalized.startswith(("select", "with", "pragma"))

