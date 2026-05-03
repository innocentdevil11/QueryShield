"""Deterministic error repair router for well-known SQLite errors."""

from __future__ import annotations

import re
from typing import Any


class DeterministicErrorRouter:
    """Fixes well-known SQLite errors without LLM calls."""

    PATTERNS = [
        # ORDER BY before UNION — pure regex fix
        (r'ORDER BY clause should come after UNION', 'union_orderby'),
        # SQLite function not available
        (r'no such function: YEAR', 'year_function'),
        (r'no such function: MONTH', 'month_function'),
        (r'no such function: DAY', 'day_function'),
        # Column not found
        (r'no such column: (.+)', 'column_missing'),
        # Table not found
        (r'no such table: (.+)', 'table_missing'),
        # Syntax errors
        (r'near "(.+)": syntax error', 'syntax_error'),
        # Aggregate misuse
        (r'misuse of aggregate function', 'aggregate_misuse'),
    ]

    def classify(self, error_msg: str) -> tuple[str, str]:
        """Returns (error_class, extracted_detail)."""
        for pattern, cls in self.PATTERNS:
            m = re.search(pattern, error_msg, re.IGNORECASE)
            if m:
                return cls, m.group(1) if m.lastindex else ''
        return 'unknown', ''

    def try_deterministic_fix(
        self, sql: str, error_msg: str, schema: dict[str, Any] | None = None
    ) -> tuple[str | None, str]:
        """
        Returns (fixed_sql, fix_description) or (None, reason_why_not_fixed).
        Deterministic fixes require no LLM call.
        """
        error_class, detail = self.classify(error_msg)

        if error_class == 'union_orderby':
            fixed = self._fix_union_orderby(sql)
            if fixed and fixed != sql:
                return fixed, 'deterministic:union_orderby_reorder'
            return None, 'no_deterministic_fix_for:union_orderby_parse_failed'

        if error_class == 'year_function':
            fixed = re.sub(
                r'\bYEAR\s*\(([^)]+)\)',
                r"strftime('%Y', \1)",
                sql,
                flags=re.IGNORECASE,
            )
            return fixed, 'deterministic:year_to_strftime'

        if error_class == 'month_function':
            fixed = re.sub(
                r'\bMONTH\s*\(([^)]+)\)',
                r"strftime('%m', \1)",
                sql,
                flags=re.IGNORECASE,
            )
            return fixed, 'deterministic:month_to_strftime'

        if error_class == 'day_function':
            fixed = re.sub(
                r'\bDAY\s*\(([^)]+)\)',
                r"strftime('%d', \1)",
                sql,
                flags=re.IGNORECASE,
            )
            return fixed, 'deterministic:day_to_strftime'

        if error_class == 'column_missing' and detail and schema:
            fixed = self._try_column_fuzzy_fix(sql, detail.strip(), schema)
            if fixed:
                return fixed, f'deterministic:column_fuzzy_match:{detail.strip()}'

        return None, f'no_deterministic_fix_for:{error_class}'

    def _fix_union_orderby(self, sql: str) -> str | None:
        """Attempt to fix ORDER BY before UNION using sqlglot."""
        try:
            import sqlglot

            result = sqlglot.transpile(sql, read='sqlite', write='sqlite')
            if result:
                return result[0]
        except Exception:
            pass
        return None

    def _try_column_fuzzy_fix(
        self, sql: str, bad_col: str, schema: dict[str, Any]
    ) -> str | None:
        """Attempt to fix column name by fuzzy-matching against schema."""
        from difflib import get_close_matches

        all_cols: list[str] = []
        for table_info in schema.values():
            if isinstance(table_info, dict):
                all_cols.extend(table_info.get('columns', []))

        # Strip table prefix if present
        col_name = bad_col.split('.')[-1]
        matches = get_close_matches(col_name, all_cols, n=1, cutoff=0.8)
        if matches:
            return sql.replace(bad_col, matches[0])
        return None
