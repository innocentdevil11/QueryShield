"""Prompt construction for schema-aware SQL generation."""

from __future__ import annotations


class PromptBuilder:
    """Create strong prompts that constrain the model to valid SQL output."""

    SYSTEM_INSTRUCTION = "You are an expert SQL generator."

    def build_prompt(self, schema: str, question: str) -> str:
        """Build a deterministic SQL-only prompt."""
        cleaned_question = question.strip()
        cleaned_schema = schema.strip()

        return (
            f"{self.SYSTEM_INSTRUCTION}\n\n"
            "STRICT RULES:\n"
            "1. Output only one valid SQLite SQL query.\n"
            "2. Do not include markdown, comments, or explanations.\n"
            "3. Use only table and column names present in the schema.\n"
            "4. Prefer explicit JOIN conditions when multiple tables are involved.\n"
            "5. End the SQL statement with a semicolon.\n\n"
            "### Database Schema:\n"
            f"{cleaned_schema}\n\n"
            "### User Question:\n"
            f"{cleaned_question}\n\n"
            "### SQL Query:\n"
        )

    def build_correction_prompt(
        self,
        schema: str,
        question: str,
        failed_sql: str,
        error: str,
    ) -> str:
        """Build a retry prompt that asks the model to fix failed SQL."""
        cleaned_schema = schema.strip()
        cleaned_question = question.strip()
        cleaned_failed_sql = failed_sql.strip()
        cleaned_error = error.strip()

        return (
            "You are an expert SQL debugger.\n\n"
            "The following SQL query failed:\n\n"
            "SQL:\n"
            f"{cleaned_failed_sql}\n\n"
            "Error:\n"
            f"{cleaned_error}\n\n"
            "Fix the SQL query using the schema below.\n\n"
            "STRICT RULES:\n"
            "* Return ONLY SQL\n"
            "* No explanation\n"
            "* Use correct tables/columns\n\n"
            "Schema:\n"
            f"{cleaned_schema}\n\n"
            "Question:\n"
            f"{cleaned_question}\n\n"
            "Corrected SQL:\n"
        )
