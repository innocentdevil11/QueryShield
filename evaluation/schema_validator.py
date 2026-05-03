"""Schema-aware pre-validation using sqlglot for SQL queries."""

from __future__ import annotations

from typing import Any

import sqlglot
import sqlglot.expressions as exp


class SchemaPreValidator:
    """Validate SQL against known schema before execution."""

    SQLITE_UNSUPPORTED_FUNCTIONS = {
        'year', 'month', 'day', 'ilike', 'qualify', 'pivot', 'unpivot',
    }

    def validate(self, sql: str, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Returns:
        {
          'valid': bool,
          'errors': [{'type': str, 'detail': str, 'fixable': bool}],
          'warnings': [str]
        }
        schema format: {'table_name': {'columns': ['col1','col2',...], 'aliases': [...]}}
        """
        errors: list[dict[str, Any]] = []
        warnings: list[str] = []

        try:
            tree = sqlglot.parse_one(sql, dialect='sqlite')
        except sqlglot.errors.ParseError as e:
            return {
                'valid': False,
                'errors': [{'type': 'parse_error', 'detail': str(e), 'fixable': False}],
                'warnings': [],
            }

        schema_lower = {k.lower(): v for k, v in schema.items()}

        # Check all referenced tables exist
        for table in tree.find_all(exp.Table):
            tname = table.name.lower() if table.name else ''
            if tname and tname not in schema_lower:
                # Skip common subquery aliases
                if not _is_subquery_alias(table, tree):
                    errors.append({
                        'type': 'unknown_table',
                        'detail': tname,
                        'fixable': False,
                    })

        # Check all referenced columns exist in their table
        for col in tree.find_all(exp.Column):
            col_name = col.name.lower() if col.name else ''
            table_ref = col.table.lower() if col.table else None
            if table_ref and table_ref in schema_lower:
                schema_entry = schema_lower[table_ref]
                if isinstance(schema_entry, dict):
                    known_cols = [c.lower() for c in schema_entry.get('columns', [])]
                    if col_name and col_name not in known_cols:
                        errors.append({
                            'type': 'unknown_column',
                            'detail': f'{table_ref}.{col_name}',
                            'fixable': True,
                        })

        # Check for unsupported SQLite functions
        for func in tree.find_all(exp.Anonymous):
            fname = func.name.lower() if hasattr(func, 'name') and func.name else ''
            if fname in self.SQLITE_UNSUPPORTED_FUNCTIONS:
                errors.append({
                    'type': 'unsupported_function',
                    'detail': fname,
                    'fixable': True,
                })

        # Also check known function types that sqlglot recognizes
        for func in tree.find_all(exp.Func):
            fname = ''
            if hasattr(func, 'sql_name'):
                fname = func.sql_name().lower()
            elif hasattr(func, 'key'):
                fname = func.key.lower()
            if fname in self.SQLITE_UNSUPPORTED_FUNCTIONS:
                errors.append({
                    'type': 'unsupported_function',
                    'detail': fname,
                    'fixable': True,
                })

        unfixable = [e for e in errors if not e.get('fixable', False)]
        return {
            'valid': len(unfixable) == 0,
            'errors': errors,
            'warnings': warnings,
        }


def _is_subquery_alias(table: exp.Table, tree: exp.Expression) -> bool:
    """Check if a table reference is actually a subquery alias (CTE or derived table)."""
    tname = table.name.lower() if table.name else ''
    if not tname:
        return False
    # Check CTEs
    for cte in tree.find_all(exp.CTE):
        if hasattr(cte, 'alias') and cte.alias and cte.alias.lower() == tname:
            return True
    # Check subquery aliases
    for subq in tree.find_all(exp.Subquery):
        if hasattr(subq, 'alias') and subq.alias and str(subq.alias).lower() == tname:
            return True
    return False
