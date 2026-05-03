"""CLI runner for the same-prompt fair experiment."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from queryshield.evaluation.comparator_same_prompt import QUERY_SETS, compare
from queryshield.evaluation.metrics import calculate_metrics

EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_RESULTS_PATH = EVAL_DIR / "results" / "groq_hard_results_saved_copy.json"
RUNTIME_LOGS_DIR = EVAL_DIR / "runtime_logs"
FAILURE_LOG_PATH = RUNTIME_LOGS_DIR / "failure_log_same_prompt.jsonl"
API_ERROR_LOG_PATH = RUNTIME_LOGS_DIR / "api_error_log_same_prompt.jsonl"
RETRY_LOG_PATH = RUNTIME_LOGS_DIR / "retry_log_same_prompt.jsonl"


def run_evaluation(
    queries: list[str],
    output_path: Path = DEFAULT_RESULTS_PATH,
) -> dict[str, Any]:
    """Run same-prompt benchmark comparison and return full payload."""
    _reset_log_files()
    rows: list[dict[str, Any]] = []

    for question in queries:
        compared = compare(question)
        row = _build_row(compared)
        rows.append(row)
        _log_row(row)

    metrics = calculate_metrics(rows)
    payload = {
        "experiment": "same_prompt_fair",
        "results": rows,
        "metrics": metrics,
        "queries_used": queries,
    }
    _save_results(payload, output_path)
    _print_table(rows)
    _print_final_summary(metrics)
    return payload


def _build_row(compared: dict[str, Any]) -> dict[str, Any]:
    baseline = compared["baseline"]
    system = compared["system"]
    return {
        "question": compared["question"],
        "baseline_sql": baseline.get("sql", ""),
        "system_sql": system.get("sql", ""),
        "baseline_success": baseline.get("success", False),
        "system_success": system.get("success", False),
        "baseline_correct": baseline.get("correct", False),
        "system_correct": system.get("correct", False),
        "baseline_partial_correct": baseline.get("partial_correct", False),
        "system_partial_correct": system.get("partial_correct", False),
        "baseline_classification": baseline.get("classification", "success"),
        "system_classification": system.get("classification", "success"),
        "baseline_failure_type": baseline.get("failure_type", "success"),
        "system_failure_type": system.get("failure_type", "success"),
        "baseline_api_failures": baseline.get("api_failures", 0),
        "system_api_failures": system.get("api_failures", 0),
        "baseline_retries_used": baseline.get("retries_used", 0),
        "system_retries_used": system.get("retries_used", 0),
        "baseline_retry_success": baseline.get("retry_success", False),
        "system_retry_success": system.get("retry_success", False),
        "attempts_used": system.get("attempts_used", 0),
        "winner": compared["winner"],
        "baseline_error": baseline.get("error"),
        "system_error": system.get("error"),
        "notes": _build_notes(compared),
    }


def _save_results(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _print_table(rows: list[dict[str, Any]]) -> None:
    print(
        "| Query | Baseline SQL | System SQL | Baseline Correct | "
        "System Correct | Winner |"
    )
    print("|---|---|---|---|---|---|")
    for row in rows:
        print(
            f"| {row['question']} | "
            f"`{_shorten(row['baseline_sql'])}` | "
            f"`{_shorten(row['system_sql'])}` | "
            f"{'Yes' if row['baseline_correct'] else 'No'} | "
            f"{'Yes' if row['system_correct'] else 'No'} | "
            f"{row['winner']} |"
        )


def _print_final_summary(metrics: dict[str, Any]) -> None:
    print("\nFinal Summary")
    print(
        f"- baseline_accuracy (excluding API failures): {metrics['baseline_accuracy']}"
    )
    print(f"- system_accuracy: {metrics['system_accuracy']}")
    print(f"- improvement %: {metrics['improvement_percent']}")
    print(f"- api_failures: {metrics['api_failures']}")
    print(f"- retry_success_rate: {metrics['retry_success_rate']}")
    print("- failure_breakdown:")
    print(
        f"  baseline -> incorrect_sql={metrics['baseline_incorrect_sql']}, "
        f"wrong_results={metrics['baseline_wrong_results']}, "
        f"partial_correct={metrics['baseline_partial_correct']}"
    )
    print(
        f"  system   -> incorrect_sql={metrics['system_incorrect_sql']}, "
        f"wrong_results={metrics['system_wrong_results']}, "
        f"partial_correct={metrics['system_partial_correct']}"
    )


def _shorten(text: str, max_len: int = 120) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 3] + "..."


def _build_notes(compared: dict[str, Any]) -> str:
    winner = compared.get("winner", "tie")
    baseline_error = compared.get("baseline", {}).get("error")
    system_error = compared.get("system", {}).get("error")
    baseline_correct = bool(compared.get("baseline", {}).get("correct"))
    system_correct = bool(compared.get("system", {}).get("correct"))

    if winner == "system":
        if baseline_error and not system_error:
            return f"System recovered baseline failure: {baseline_error}"
        if system_correct and not baseline_correct:
            return "System produced more correct result."
        return "System outperformed baseline."

    if winner == "baseline":
        if system_error and not baseline_error:
            return f"Baseline recovered system failure: {system_error}"
        if baseline_correct and not system_correct:
            return "Baseline produced more correct result."
        return "Baseline outperformed system."

    if baseline_error and system_error:
        return f"Both failed (baseline: {baseline_error}; system: {system_error})"
    return "Both produced similar outcome."


def _reset_log_files() -> None:
    for path in (FAILURE_LOG_PATH, API_ERROR_LOG_PATH, RETRY_LOG_PATH):
        if path.exists():
            path.unlink()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def _log_row(row: dict[str, Any]) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    for side in ("baseline", "system"):
        classification = str(row.get(f"{side}_classification") or "success")
        retries_used = int(row.get(f"{side}_retries_used") or 0)
        retry_success = bool(row.get(f"{side}_retry_success"))
        error = row.get(f"{side}_error")
        sql = row.get(f"{side}_sql")

        retry_entry = {
            "timestamp_utc": ts,
            "question": row["question"],
            "side": side,
            "retries_used": retries_used,
            "retry_success": retry_success,
            "classification": classification,
        }
        _append_jsonl(RETRY_LOG_PATH, retry_entry)

        if classification != "success":
            failure_entry = {
                "timestamp_utc": ts,
                "question": row["question"],
                "side": side,
                "classification": classification,
                "error": error,
                "retries_used": retries_used,
                "sql": sql,
            }
            _append_jsonl(FAILURE_LOG_PATH, failure_entry)

        if classification == "api_error":
            api_entry = {
                "timestamp_utc": ts,
                "question": row["question"],
                "side": side,
                "error": error,
                "retries_used": retries_used,
            }
            _append_jsonl(API_ERROR_LOG_PATH, api_entry)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run same-prompt fair baseline-vs-system evaluation."
    )
    parser.add_argument(
        "--query-set",
        choices=sorted(QUERY_SETS.keys()),
        default="hard",
        help="Which query set to run.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_RESULTS_PATH),
        help="Where to save JSON results.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    selected_queries = QUERY_SETS[args.query_set]
    run_evaluation(queries=selected_queries, output_path=Path(args.output))


if __name__ == "__main__":
    main()
