"""SQL safety validation for QueryShield."""

from __future__ import annotations

import re

# Keywords that should be screened before query execution.
DANGEROUS_KEYWORDS = {
    "DROP",
    "DELETE",
    "TRUNCATE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "CREATE",
    "RENAME",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "CALL",
}

# Admin mode allows data mutations but still blocks destructive schema operations.
ADMIN_ALLOWED_KEYWORDS = {"INSERT", "UPDATE", "DELETE"}
ADMIN_BLOCKED_KEYWORDS = DANGEROUS_KEYWORDS - ADMIN_ALLOWED_KEYWORDS


def validate_sql(sql: str, mode: str = "safe") -> tuple[bool, str]:
    """
    Validate SQL based on execution mode.

    Safe mode:
    - query must start with SELECT
    - only one statement allowed
    - all dangerous keywords are blocked

    Admin mode:
    - INSERT/UPDATE/DELETE are allowed
    - DROP/TRUNCATE/ALTER and other blocked keywords are denied
    """
    normalized_mode = (mode or "safe").strip().lower()
    query = (sql or "").strip()

    if not query:
        return False, "SQL is empty."

    # Explicitly block statement chaining attempts such as `SELECT ...; DELETE ...;`
    if query.count(";") > 1:
        return False, "Multiple SQL statements are not allowed."

    if normalized_mode == "safe":
        if not query.upper().startswith("SELECT"):
            return False, "Safe mode allows only SELECT queries."
        return _validate_keywords(query, DANGEROUS_KEYWORDS)

    if normalized_mode == "admin":
        return _validate_keywords(query, ADMIN_BLOCKED_KEYWORDS)

    return False, "Invalid mode. Use 'safe' or 'admin'."


def _validate_keywords(sql: str, blocked_keywords: set[str]) -> tuple[bool, str]:
    """Check whether blocked keywords are present in a query."""
    upper_sql = sql.upper()

    for keyword in sorted(blocked_keywords):
        # Word boundary prevents false matches in longer identifiers.
        if re.search(rf"\b{re.escape(keyword)}\b", upper_sql):
            return False, f"Blocked keyword detected: {keyword}"

    return True, ""

