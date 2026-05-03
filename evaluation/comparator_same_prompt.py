"""Fair same-prompt comparator: baseline vs execution-correction system."""

from __future__ import annotations

import gc
import shutil
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from queryshield.core.executor import SQLExecutor
from queryshield.core.llm import LLMClient
from queryshield.evaluation.baseline_same_prompt import (
    build_common_prompt,
    run_baseline_generation,
)
from queryshield.evaluation.retry_utils import (
    DEFAULT_MAX_API_RETRIES,
    RequestThrottler,
    generate_with_retry,
    get_default_throttler,
)
from queryshield.evaluation.schema_context import build_structured_schema

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = BASE_DIR / "data" / "sample.db"

MAX_CORRECTION_RETRIES = 2

# Existing core benchmark set (14 queries).
CORE_EVAL_QUERIES = [
    "Show all students",
    "List all courses",
    "Top scoring student",
    "Show student name with course and marks",
    "List students and their courses",
    "Average marks per student",
    "Top 3 students by marks",
    "student_name instead of name",
    "student_scores instead of scores",
    "Delete all students",
    "Show students; DROP TABLE students",
    "Insert temporary student",
    "Delete temporary student",
    "Drop students table",
]

# Hard-set focused on ambiguity, schema confusion, and multi-step reasoning.
HARD_EVAL_QUERIES = [
    "Show best student",
    "Top performer",
    "High scoring students",
    "List student emails with course names and marks above average",
    "Students who performed better than average in each course",
    "Find students who scored above average in at least 2 courses",
    "Top department based on average marks",
    "student_name list",
    "course score data",
    "List students whose average marks are above the overall average",
    "Show course-wise toppers with student names",
    "Count students scoring above 90 in each course",
    "Students who never enrolled in any course",
    "Courses where average marks are above overall average",
    "Show top 3 students per course",
    "Find students with highest marks in each department",
    "List students whose marks improved over time",
    "Show departments with more than 5 students scoring above 80",
    "Courses taken by all Computer Science students",
    "Students who scored in every course",
]

ALL_EVAL_QUERIES = CORE_EVAL_QUERIES + HARD_EVAL_QUERIES
EVAL_QUERIES = CORE_EVAL_QUERIES

QUERY_SETS: dict[str, list[str]] = {
    "core": CORE_EVAL_QUERIES,
    "hard": HARD_EVAL_QUERIES,
    "all": ALL_EVAL_QUERIES,
}


@lru_cache(maxsize=1)
def _shared_llm_client() -> LLMClient:
    """Shared LLM client for sequential benchmark runs."""
    return LLMClient()


def compare(question: str) -> dict[str, Any]:
    """
    Compare baseline and system for one question under exact same prompt.

    Baseline:
    - one LLM call with common prompt
    - no retry
    - no correction loop

    System:
    - first call uses same common prompt
    - execute SQL
    - correction prompt on execution failure
    - max 2 correction retries
    """
    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValueError("Question cannot be empty.")

    tmp_base, baseline_db, system_db = _create_workspace_tmp_paths()
    try:
        shutil.copy2(DEFAULT_DB_PATH, baseline_db)
        shutil.copy2(DEFAULT_DB_PATH, system_db)

        shared_schema = build_structured_schema(system_db)
        llm_client = _shared_llm_client()
        throttler = get_default_throttler()

        baseline_generation = run_baseline_generation(
            question=cleaned_question,
            schema=shared_schema,
            llm_client=llm_client,
            throttler=throttler,
        )
        baseline_output = _run_baseline_execution(
            generated=baseline_generation,
            db_path=baseline_db,
        )
        system_output = _run_system(
            question=cleaned_question,
            schema=shared_schema,
            db_path=system_db,
            llm_client=llm_client,
            throttler=throttler,
        )
    finally:
        _cleanup_tmp_files(tmp_base, baseline_db, system_db)

    baseline_eval = _evaluate_output(cleaned_question, baseline_output)
    system_eval = _evaluate_output(cleaned_question, system_output)

    winner = _pick_winner(
        baseline_correct=baseline_eval["correct"],
        system_correct=system_eval["correct"],
        baseline_exec_success=baseline_eval["execution_success"],
        system_exec_success=system_eval["execution_success"],
    )

    return {
        "question": cleaned_question,
        "baseline": {
            **baseline_output,
            **baseline_eval,
        },
        "system": {
            **system_output,
            **system_eval,
        },
        "winner": winner,
    }


def _run_baseline_execution(generated: dict[str, Any], db_path: Path) -> dict[str, Any]:
    """
    Execute baseline SQL for evaluation only.

    Baseline generation itself remains no-execution and single-call.
    """
    sql = str(generated.get("sql") or "")
    error = generated.get("error")
    if error is not None:
        return {
            "sql": sql,
            "result": [],
            "error": str(error),
            "attempts_used": 1,
            "api_failures": int(generated.get("api_failures") or 0),
            "retries_used": int(generated.get("retries_used") or 0),
            "retry_success": bool(generated.get("retry_success")),
        }

    execution = SQLExecutor(db_path).execute(sql)
    return {
        "sql": sql,
        "result": execution["rows"],
        "error": execution["error"],
        "attempts_used": 1,
        "api_failures": int(generated.get("api_failures") or 0),
        "retries_used": int(generated.get("retries_used") or 0),
        "retry_success": bool(generated.get("retry_success")),
    }


def _run_system(
    question: str,
    schema: str,
    db_path: Path,
    llm_client: LLMClient,
    throttler: RequestThrottler,
) -> dict[str, Any]:
    """Run execution-driven correction flow."""
    executor = SQLExecutor(db_path=db_path)
    prompt = build_common_prompt(schema=schema, question=question)

    final_sql = ""
    final_error: str | None = None
    attempts_used = 0
    api_failures = 0
    retries_used_total = 0
    retry_success = False

    # initial attempt + 2 correction retries
    for attempt in range(1, MAX_CORRECTION_RETRIES + 2):
        attempts_used = attempt
        retry_outcome = generate_with_retry(
            llm=llm_client,
            prompt=prompt,
            throttler=throttler,
            max_retries=DEFAULT_MAX_API_RETRIES,
        )
        retries_used_total += int(retry_outcome["retries_used"])
        retry_success = retry_success or bool(retry_outcome["retry_success"])

        if retry_outcome["api_error"] is not None:
            api_failures += 1
            final_error = str(retry_outcome["api_error"])
            break

        generated_sql = str(retry_outcome["sql"]).strip()
        final_sql = generated_sql
        execution = executor.execute(generated_sql)

        if execution["error"] is None:
            return {
                "sql": generated_sql,
                "result": execution["rows"],
                "error": None,
                "attempts_used": attempts_used,
                "api_failures": api_failures,
                "retries_used": retries_used_total,
                "retry_success": retry_success,
            }

        final_error = execution["error"] or "Unknown SQL execution error."
        if attempt <= MAX_CORRECTION_RETRIES:
            prompt = _build_correction_prompt(
                failed_sql=generated_sql,
                error=final_error,
            )
            continue
        break

    return {
        "sql": final_sql,
        "result": [],
        "error": final_error,
        "attempts_used": attempts_used,
        "api_failures": api_failures,
        "retries_used": retries_used_total,
        "retry_success": retry_success,
    }


def _build_correction_prompt(failed_sql: str, error: str) -> str:
    """Prompt used by system correction retries."""
    return (
        "You are a strict SQL debugger.\n\n"
        "The query FAILED.\n\n"
        "Failed SQL:\n"
        f"{failed_sql.strip()}\n\n"
        "Error:\n"
        f"{error.strip()}\n\n"
        "Fix the query:\n\n"
        "* Use correct schema columns\n"
        "* Fix joins and aggregation\n"
        "* Ensure query executes successfully\n\n"
        "Return ONLY corrected SQL.\n"
    )


def _evaluate_output(question: str, output: dict[str, Any]) -> dict[str, Any]:
    """
    Compute canonical classification for one output.

    Categories:
    - success
    - api_error
    - incorrect_sql
    - wrong_results
    - partial_correct
    """
    error_text = str(output.get("error") or "")
    execution_success = output.get("error") is None
    correct = _is_correct(question, output)

    if error_text.startswith("api_error:"):
        classification = "api_error"
    elif correct:
        classification = "success"
    elif not execution_success:
        classification = "incorrect_sql"
    elif _is_partial(question, output):
        classification = "partial_correct"
    else:
        classification = "wrong_results"

    return {
        "execution_success": execution_success,
        "success": execution_success,
        "correct": correct,
        "partial_correct": classification == "partial_correct",
        "classification": classification,
        "failure_type": classification,
    }


def _create_workspace_tmp_paths() -> tuple[Path, Path, Path]:
    """Create temporary DB file paths under the project workspace."""
    tmp_base = BASE_DIR / "evaluation" / ".tmp_same_prompt"
    tmp_base.mkdir(parents=True, exist_ok=True)
    token = uuid4().hex
    baseline_db = tmp_base / f"baseline_{token}.db"
    system_db = tmp_base / f"system_{token}.db"
    return tmp_base, baseline_db, system_db


def _cleanup_tmp_files(tmp_base: Path, baseline_db: Path, system_db: Path) -> None:
    """Best-effort cleanup with retries for transient Windows file locks."""
    for _ in range(15):
        gc.collect()
        try:
            if baseline_db.exists():
                baseline_db.chmod(0o666)
                baseline_db.unlink()
            if system_db.exists():
                system_db.chmod(0o666)
                system_db.unlink()
            break
        except OSError:
            time.sleep(0.2)
    try:
        if tmp_base.exists() and not any(tmp_base.iterdir()):
            tmp_base.rmdir()
    except OSError:
        pass


def _is_correct(question: str, output: dict[str, Any]) -> bool:
    """Question-aware correctness check."""
    validator = _QUESTION_VALIDATORS.get(question.strip().lower(), _default_validator)
    return validator(output)


def _is_partial(question: str, output: dict[str, Any]) -> bool:
    """Heuristic for partial correctness when output is not fully correct."""
    if output.get("error") is not None:
        return False

    question_key = question.strip().lower()
    sql = (output.get("sql") or "").upper()
    hints = _PARTIAL_SQL_HINTS.get(question_key, [])
    if not hints:
        return _has_rows(output)

    matched = sum(1 for hint in hints if hint in sql)
    return matched > 0


def _default_validator(output: dict[str, Any]) -> bool:
    """Fallback correctness rule when no specific validator is configured."""
    return output.get("error") is None


def _has_rows(output: dict[str, Any]) -> bool:
    return output.get("error") is None and len(output.get("result", [])) > 0


def _rows_count(output: dict[str, Any]) -> int:
    return len(output.get("result", []))


def _sql_contains(output: dict[str, Any], *parts: str) -> bool:
    sql = (output.get("sql") or "").upper()
    return all(part.upper() in sql for part in parts)


_QUESTION_VALIDATORS: dict[str, Callable[[dict[str, Any]], bool]] = {
    # Core set
    "show all students": lambda o: _has_rows(o) and _sql_contains(o, "SELECT"),
    "list all courses": lambda o: _has_rows(o) and _sql_contains(o, "SELECT"),
    "top scoring student": lambda o: o.get("error") is None and _rows_count(o) == 1,
    "show student name with course and marks": lambda o: _has_rows(o) and _sql_contains(o, "JOIN"),
    "list students and their courses": lambda o: _has_rows(o) and _sql_contains(o, "JOIN"),
    "average marks per student": lambda o: _has_rows(o) and _sql_contains(o, "AVG", "GROUP BY"),
    "top 3 students by marks": lambda o: o.get("error") is None and _rows_count(o) == 3 and _sql_contains(o, "ORDER BY"),
    "student_name instead of name": _has_rows,
    "student_scores instead of scores": _has_rows,
    # Hard set
    "show best student": lambda o: o.get("error") is None and _rows_count(o) == 1,
    "top performer": lambda o: o.get("error") is None and _rows_count(o) == 1,
    "high scoring students": lambda o: _has_rows(o) and _sql_contains(o, "WHERE"),
    "list student emails with course names and marks above average": (
        lambda o: _has_rows(o) and _sql_contains(o, "JOIN", "AVG")
    ),
    "students who performed better than average in each course": (
        lambda o: _has_rows(o) and _sql_contains(o, "AVG")
    ),
    "find students who scored above average in at least 2 courses": (
        lambda o: _has_rows(o) and _sql_contains(o, "HAVING")
    ),
    "top department based on average marks": (
        lambda o: o.get("error") is None and _rows_count(o) >= 1 and _sql_contains(o, "GROUP BY", "AVG")
    ),
    "student_name list": _has_rows,
    "course score data": lambda o: _has_rows(o) and _sql_contains(o, "JOIN"),
    "list students whose average marks are above the overall average": (
        lambda o: _has_rows(o) and _sql_contains(o, "AVG")
    ),
    "show course-wise toppers with student names": (
        lambda o: _has_rows(o) and _sql_contains(o, "MAX", "JOIN")
    ),
    "count students scoring above 90 in each course": (
        lambda o: _has_rows(o) and _sql_contains(o, "COUNT", "GROUP BY")
    ),
    "students who never enrolled in any course": (
        lambda o: _has_rows(o) and (_sql_contains(o, "LEFT JOIN") or _sql_contains(o, "NOT EXISTS"))
    ),
    "courses where average marks are above overall average": (
        lambda o: _has_rows(o) and _sql_contains(o, "AVG", "HAVING")
    ),
    "show top 3 students per course": (
        lambda o: _has_rows(o) and (_sql_contains(o, "ROW_NUMBER") or _sql_contains(o, "LIMIT"))
    ),
    "find students with highest marks in each department": (
        lambda o: _has_rows(o) and _sql_contains(o, "MAX")
    ),
    "list students whose marks improved over time": (
        lambda o: _has_rows(o) and _sql_contains(o, "EXAM_DATE")
    ),
    "show departments with more than 5 students scoring above 80": (
        lambda o: _has_rows(o) and _sql_contains(o, "GROUP BY", "HAVING")
    ),
    "courses taken by all computer science students": (
        lambda o: _has_rows(o) and (_sql_contains(o, "HAVING") or _sql_contains(o, "NOT EXISTS"))
    ),
    "students who scored in every course": (
        lambda o: _has_rows(o) and _sql_contains(o, "GROUP BY", "HAVING")
    ),
}

_PARTIAL_SQL_HINTS: dict[str, list[str]] = {
    "top scoring student": ["ORDER BY", "LIMIT"],
    "show student name with course and marks": ["JOIN", "MARKS"],
    "average marks per student": ["AVG", "GROUP BY"],
    "top 3 students by marks": ["ORDER BY", "LIMIT"],
    "show best student": ["ORDER BY", "LIMIT"],
    "top performer": ["ORDER BY", "LIMIT"],
    "high scoring students": ["WHERE", "MARKS"],
    "list student emails with course names and marks above average": ["JOIN", "AVG", "EMAIL"],
    "students who performed better than average in each course": ["AVG", "GROUP BY"],
    "find students who scored above average in at least 2 courses": ["HAVING", "COUNT"],
    "top department based on average marks": ["GROUP BY", "AVG", "ORDER BY"],
    "course score data": ["JOIN", "MARKS"],
    "list students whose average marks are above the overall average": ["AVG", "HAVING"],
    "show course-wise toppers with student names": ["MAX", "JOIN"],
    "count students scoring above 90 in each course": ["COUNT", "GROUP BY"],
    "students who never enrolled in any course": ["LEFT JOIN", "NOT EXISTS"],
    "courses where average marks are above overall average": ["AVG", "HAVING"],
    "show top 3 students per course": ["ROW_NUMBER", "PARTITION BY", "LIMIT"],
    "find students with highest marks in each department": ["MAX", "GROUP BY"],
    "list students whose marks improved over time": ["EXAM_DATE", "ORDER BY"],
    "show departments with more than 5 students scoring above 80": ["GROUP BY", "HAVING"],
    "courses taken by all computer science students": ["HAVING", "COUNT"],
    "students who scored in every course": ["GROUP BY", "HAVING", "COUNT"],
}


def _pick_winner(
    baseline_correct: bool,
    system_correct: bool,
    baseline_exec_success: bool,
    system_exec_success: bool,
) -> str:
    """Decide winner between baseline and system."""
    if system_correct and not baseline_correct:
        return "system"
    if baseline_correct and not system_correct:
        return "baseline"
    if baseline_correct and system_correct:
        return "tie"
    if not baseline_exec_success and system_exec_success:
        return "system"
    if baseline_exec_success and not system_exec_success:
        return "baseline"
    return "tie"

