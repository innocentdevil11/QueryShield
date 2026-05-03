"""Prompt builders for Spider fair baseline-vs-system evaluation."""

from __future__ import annotations


def build_common_prompt(schema: str, question: str) -> str:
    """Prompt shared by both baseline and system."""
    return (
        "You are an expert SQLite SQL generator.\n\n"
        "TASK:\n"
        "Generate a single correct SQLite query to answer the question.\n\n"
        "SQLITE DIALECT (NEVER VIOLATE):\n"
        "* Use strftime('%Y', col) instead of YEAR(col)\n"
        "* Use strftime('%m', col) instead of MONTH(col)\n"
        "* Use LOWER(col) LIKE pattern instead of ILIKE\n"
        "* Do NOT use PERCENTILE_CONT, MEDIAN, or INTERVAL — they do not exist in SQLite\n"
        "* Do NOT use AS aliases on subqueries in FROM (SQLite requires them but do not use the keyword AS for derived tables)\n"
        "* Use julianday() for date arithmetic\n\n"
        "RULES:\n"
        "* Use ONLY tables and columns shown in the schema below\n"
        "* Check the sample data to understand column names and value formats\n"
        "* Use correct joins using foreign keys\n"
        "* Qualify all column names with table aliases to avoid ambiguity\n"
        "* Ensure aggregation correctness\n\n"
        "IMPORTANT:\n"
        "* Do NOT invent or guess column names — use ONLY those listed in the schema\n"
        "* Return ONLY the SQL query, no explanation\n\n"
        "Schema:\n"
        f"{schema.strip()}\n\n"
        "Question:\n"
        f"{question.strip()}\n"
    )


def build_correction_prompt(
    schema: str,
    question: str,
    failed_sql: str,
    error: str,
) -> str:
    """Correction prompt used only by system retries."""
    return (
        "You are an expert SQLite SQL debugger.\n\n"
        "The previous query FAILED with an error.\n\n"
        "Schema:\n"
        f"{schema.strip()}\n\n"
        "Question:\n"
        f"{question.strip()}\n\n"
        "Failed SQL:\n"
        f"{failed_sql.strip()}\n\n"
        "Error:\n"
        f"{error.strip()}\n\n"
        "Fix the query by:\n"
        "* Using ONLY columns that exist in the schema above\n"
        "* Qualifying column names with table aliases\n"
        "* Using SQLite-compatible functions (strftime, julianday, etc.)\n\n"
        "Return ONLY the corrected SQL query.\n"
    )


def build_enhanced_direct_prompt(schema: str, question: str) -> str:
    """Enhanced direct SQL generation prompt (used in 'direct' pipeline mode).

    Includes SQLite-specific rules to reduce common errors.
    """
    return (
        "You are an expert SQL generator for SQLite databases.\n\n"
        "TASK:\n"
        "Generate a correct SQLite SQL query to answer the question.\n\n"
        "Schema:\n"
        f"{schema.strip()}\n\n"
        "CRITICAL RULES FOR SQLITE (NEVER VIOLATE):\n"
        "1. Never use YEAR(col) — use strftime('%Y', col) instead\n"
        "2. Never use QUALIFY — use a subquery with WHERE instead\n"
        "3. ORDER BY must come AFTER the final UNION/UNION ALL, not before\n"
        "4. Never reference columns not explicitly listed in the schema above\n"
        "5. Never use ILIKE — use LOWER(col) LIKE LOWER(pattern) instead\n\n"
        "RULES:\n"
        "* Use ONLY provided schema\n"
        "* Verify column existence strictly\n"
        "* Use correct joins using foreign keys\n"
        "* Ensure aggregation correctness\n"
        "* Ensure logical correctness for complex queries\n\n"
        "Return ONLY the SQL query. No explanation. No markdown. No backticks.\n\n"
        "Question:\n"
        f"{question.strip()}\n"
    )
