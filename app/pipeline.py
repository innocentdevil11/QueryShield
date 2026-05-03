"""End-to-end query pipeline for text-to-SQL."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from queryshield.core.executor import SQLExecutor
from queryshield.core.llm import LLMClient
from queryshield.core.prompt_builder import PromptBuilder
from queryshield.core.safety import validate_sql
from queryshield.core.schema_loader import SchemaLoader


class QueryPipeline:
    """Orchestrates schema loading, prompting, SQL generation, and execution."""
    MAX_RETRIES = 2

    def __init__(
        self,
        db_path: Path,
        schema_file: Path | None = None,
        llm_client: LLMClient | None = None,
        log_file: Path | None = None,
    ) -> None:
        self.schema_loader = SchemaLoader(db_path=db_path, schema_file=schema_file)
        self.prompt_builder = PromptBuilder()
        self.llm_client = llm_client or LLMClient()
        self.executor = SQLExecutor(db_path=db_path)
        self.log_file = log_file or Path(__file__).resolve().parents[1] / "logs" / "run_logs.json"

    def run(self, question: str, mode: str = "safe") -> dict[str, Any]:
        """Run a full text-to-SQL cycle with safety checks and retry correction."""
        cleaned_question = question.strip()
        if not cleaned_question:
            raise ValueError("Question cannot be empty.")
        normalized_mode = (mode or "safe").strip().lower()
        if normalized_mode not in {"safe", "admin"}:
            raise ValueError("Mode must be 'safe' or 'admin'.")

        schema = self.schema_loader.load_schema()
        prompt = self.prompt_builder.build_prompt(schema=schema, question=cleaned_question)
        final_sql = ""
        final_error: str | None = None
        attempts_used = 0

        for attempt in range(1, self.MAX_RETRIES + 2):
            attempts_used = attempt

            try:
                generated_sql = self.llm_client.generate_sql(prompt=prompt).strip()
            except Exception as exc:  # noqa: BLE001 - keep pipeline resilient
                final_error = f"SQL generation failed: {exc}"
                break

            final_sql = generated_sql
            is_valid, reason = validate_sql(generated_sql, mode=normalized_mode)

            if not is_valid:
                final_error = f"Blocked by safety layer: {reason}"
                if attempt <= self.MAX_RETRIES:
                    prompt = self.prompt_builder.build_correction_prompt(
                        schema=schema,
                        question=cleaned_question,
                        failed_sql=generated_sql,
                        error=final_error,
                    )
                    continue
                break

            execution = self.executor.execute(generated_sql)
            if execution["error"] is None:
                output = {
                    "sql": generated_sql,
                    "result": execution["rows"],
                    "error": None,
                    "attempts_used": attempts_used,
                }
                self._append_run_log(
                    question=cleaned_question,
                    sql=generated_sql,
                    error=None,
                    retries=attempts_used - 1,
                    mode=normalized_mode,
                )
                return output

            final_error = execution["error"] or "Unknown SQL execution error."
            if attempt <= self.MAX_RETRIES:
                prompt = self.prompt_builder.build_correction_prompt(
                    schema=schema,
                    question=cleaned_question,
                    failed_sql=generated_sql,
                    error=final_error,
                )
                continue
            break

        output = {
            "sql": final_sql,
            "result": [],
            "error": final_error,
            "attempts_used": attempts_used,
        }
        self._append_run_log(
            question=cleaned_question,
            sql=final_sql,
            error=final_error,
            retries=max(attempts_used - 1, 0),
            mode=normalized_mode,
        )
        return output

    def _append_run_log(
        self,
        question: str,
        sql: str,
        error: str | None,
        retries: int,
        mode: str,
    ) -> None:
        """Append one run record to logs/run_logs.json."""
        entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "question": question,
            "sql": sql,
            "error": error,
            "retries": retries,
        }

        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        records: list[dict[str, Any]] = []

        if self.log_file.exists():
            try:
                data = json.loads(self.log_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    records = data
            except (json.JSONDecodeError, OSError):
                # If log file is malformed or temporarily unreadable, reset cleanly.
                records = []

        records.append(entry)
        self.log_file.write_text(
            json.dumps(records, indent=2),
            encoding="utf-8",
        )
