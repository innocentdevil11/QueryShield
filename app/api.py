"""FastAPI service for QueryShield — standalone (no Streamlit dependency).

Includes endpoints for the React UI: database listing, benchmarks,
full pipeline query execution with side-by-side baseline vs system comparison,
SSE streaming for real-time pipeline status, and BYOD file upload.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import shutil
import sqlite3
import time
import traceback
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SPIDER_DIR = DATA_DIR / "spider2" / "local_sqlite_dbs"
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"
UPLOAD_DIR = DATA_DIR / "uploads"  # BYOD uploaded databases
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="QueryShield", version="3.0.0")

# Allow Vite dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Cached LLM clients (no Streamlit dependency)
# ---------------------------------------------------------------------------
_llm_cache: dict[str, Any] = {}


def _get_llm(provider: str, model: str):
    """Return a cached LLMClient instance per provider+model combo."""
    key = f"{provider}:{model}"
    if key not in _llm_cache:
        os.environ["LLM_PROVIDER"] = provider
        if provider == "groq":
            os.environ["GROQ_MODEL"] = model
        else:
            os.environ["OLLAMA_MODEL"] = model
        from queryshield.core.llm import LLMClient
        # Ollama needs longer timeout for cold-start model loading into VRAM
        timeout = 300 if provider == "ollama" else 60
        _llm_cache[key] = LLMClient(provider=provider, model=model, timeout_seconds=timeout)
    return _llm_cache[key]


# ---------------------------------------------------------------------------
# Helpers (extracted from streamlit_app.py, no @st decorators)
# ---------------------------------------------------------------------------

def discover_databases() -> list[str]:
    dbs = set()
    if SPIDER_DIR.exists():
        dbs.update(p.stem for p in SPIDER_DIR.glob("*.sqlite"))
    if UPLOAD_DIR.exists():
        dbs.update(p.stem for p in UPLOAD_DIR.glob("*.sqlite"))
    return sorted(dbs)


def get_db_path(db_id: str) -> Path:
    # Check uploads first, then spider datasets
    upload_path = UPLOAD_DIR / f"{db_id}.sqlite"
    if upload_path.exists():
        return upload_path
    return SPIDER_DIR / f"{db_id}.sqlite"


def run_sql(db_path: Path, sql: str) -> tuple[list[dict], str | None]:
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()[:100]]
            return rows, None
    except Exception as exc:
        return [], str(exc)


_schema_cache: dict[str, str] = {}


def get_schema_text(db_path: Path) -> str:
    key = str(db_path)
    if key not in _schema_cache:
        from queryshield.evaluation.spider_schema import build_rich_schema_context
        _schema_cache[key] = build_rich_schema_context(db_path)
    return _schema_cache[key]


_schema_dict_cache: dict[str, dict] = {}


def get_schema_dict(db_path: Path) -> dict:
    key = str(db_path)
    if key not in _schema_dict_cache:
        from queryshield.evaluation.spider_schema import build_schema_dict
        _schema_dict_cache[key] = build_schema_dict(db_path)
    return _schema_dict_cache[key]


# ---------------------------------------------------------------------------
# SSE Streaming Pipeline
# ---------------------------------------------------------------------------

def _sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def generate_sql_pipeline_streaming(
    question: str,
    db_id: str,
    provider: str,
    model: str,
):
    """Generator that yields SSE events as the pipeline progresses."""
    from queryshield.evaluation.spider_prompts import build_common_prompt, build_correction_prompt

    db_path = get_db_path(db_id)
    full_schema_text = get_schema_text(db_path)
    llm = _get_llm(provider, model)

    result: dict[str, Any] = {
        "question": question,
        "db_id": db_id,
        "model": model,
    }

    # --- Step 1: Baseline (direct prompt) ---
    yield _sse_event("step", {"step": "generating", "message": "Generating Baseline SQL (direct prompt)..."})

    t0 = time.time()
    try:
        baseline_prompt = build_common_prompt(schema=full_schema_text, question=question)
        baseline_sql = llm.generate_sql(baseline_prompt)
    except Exception as exc:
        baseline_sql = f"-- ERROR: {exc}"
    result["baseline_sql"] = baseline_sql
    result["baseline_time_sec"] = round(time.time() - t0, 2)

    yield _sse_event("step", {"step": "generating", "message": f"✓ Baseline SQL generated in {result['baseline_time_sec']}s"})

    # --- Step 2: Schema Pruning ---
    yield _sse_event("step", {"step": "schema_check", "message": "Pruning schema — semantic selection + FK graph expansion..."})

    t1 = time.time()
    pruned_schema_text = full_schema_text  # Fallback in case pruning fails
    try:
        from queryshield.evaluation.planner import build_planner_prompt, parse_plan_response
        from queryshield.evaluation.sql_generator import build_sql_from_plan_prompt
        from queryshield.retrieval.schema_pruner import build_pruned_schema_context

        schema_dict = get_schema_dict(db_path)
        pruned_schema_text = build_pruned_schema_context(
            nl_query=question,
            full_schema=schema_dict,
            full_schema_text=full_schema_text,
            top_k=5,
        )

        # Count how many tables survived pruning
        pruned_count = pruned_schema_text.count("Table: ")
        total_count = full_schema_text.count("Table: ")
        yield _sse_event("step", {"step": "schema_check", "message": f"✓ Schema pruned: {pruned_count}/{total_count} tables selected"})

        # --- Step 3: Cognitive Planner ---
        yield _sse_event("step", {"step": "deterministic_fix", "message": "Running Cognitive Planner — building structured JSON plan..."})

        planner_prompt = build_planner_prompt(schema=pruned_schema_text, question=question)
        plan_raw = llm.generate_text(planner_prompt)

        plan_dict, parse_err = parse_plan_response(plan_raw)
        if parse_err:
            plan_dict = {"raw_fallback": plan_raw, "parse_error": parse_err}
            yield _sse_event("step", {"step": "deterministic_fix", "message": f"⚠ Plan parse warning: {parse_err[:80]}..."})
        else:
            tables_in_plan = plan_dict.get("tables", [])
            yield _sse_event("step", {"step": "deterministic_fix", "message": f"✓ Plan generated — tables: {tables_in_plan}"})

        # --- Step 4: SQL Generation from Plan ---
        yield _sse_event("step", {"step": "deterministic_fix", "message": "Compiling SQL from plan..."})

        sql_prompt = build_sql_from_plan_prompt(plan=plan_dict, schema=pruned_schema_text)
        system_sql = llm.generate_sql(sql_prompt)

        yield _sse_event("step", {"step": "deterministic_fix", "message": "✓ QueryShield SQL generated from plan"})
    except Exception as exc:
        system_sql = f"-- ERROR: {exc}"
        yield _sse_event("step", {"step": "deterministic_fix", "message": f"✗ System generation failed: {exc}"})

    # --- Step 5: Semantic Correction Loop ---
    yield _sse_event("step", {"step": "semantic_loop", "message": "Executing QueryShield SQL against database..."})

    max_retries = 2
    system_rows = []
    system_err = None

    for attempt in range(max_retries + 1):
        try:
            system_rows, system_err = run_sql(db_path, system_sql)

            if system_err is None:
                if len(system_rows) == 0:
                    if attempt < max_retries:
                        system_err = "The query executed successfully but returned 0 rows. This is likely a logical error in the JOIN conditions or WHERE clauses. Please rethink the logic and try again."
                        yield _sse_event("step", {
                            "step": "semantic_loop",
                            "message": f"⚠ 0 rows returned — auto-correcting (attempt {attempt + 1}/{max_retries})..."
                        })
                    else:
                        yield _sse_event("step", {"step": "semantic_loop", "message": "⚠ 0 rows after all retries — accepting result"})
                        break
                else:
                    yield _sse_event("step", {"step": "semantic_loop", "message": f"✓ Query returned {len(system_rows)} rows"})
                    break
            else:
                if attempt < max_retries:
                    yield _sse_event("step", {
                        "step": "semantic_loop",
                        "message": f"✗ Execution error: {system_err[:60]}... Auto-correcting (attempt {attempt + 1}/{max_retries})..."
                    })

            # Auto-correct
            if attempt < max_retries:
                correction_prompt = build_correction_prompt(
                    schema=pruned_schema_text,
                    question=question,
                    failed_sql=system_sql,
                    error=system_err,
                )
                try:
                    system_sql = llm.generate_sql(correction_prompt)
                    yield _sse_event("step", {"step": "semantic_loop", "message": f"✓ Correction generated — re-executing..."})
                except Exception as e:
                    system_err = f"Correction failed: {e}"
                    yield _sse_event("step", {"step": "semantic_loop", "message": f"✗ Correction LLM call failed: {e}"})
                    break
        except Exception as big_e:
            traceback.print_exc()
            system_err = f"API Loop Exception: {big_e}"
            yield _sse_event("step", {"step": "semantic_loop", "message": f"✗ Critical error: {big_e}"})
            break

    result["system_sql"] = system_sql
    result["system_time_sec"] = round(time.time() - t1, 2)

    # --- Execute Baseline ---
    baseline_rows, baseline_err = run_sql(db_path, baseline_sql)

    result["baseline_rows"] = baseline_rows
    result["baseline_error"] = baseline_err
    result["system_rows"] = system_rows
    result["system_error"] = system_err

    if system_err is None and baseline_err is not None:
        result["winner"] = "🏆 QueryShield"
    elif baseline_err is None and system_err is not None:
        result["winner"] = "📊 Baseline"
    elif system_rows == baseline_rows:
        result["winner"] = "🤝 Tie"
    else:
        result["winner"] = "🔍 Different Results"

    # --- Final: Done ---
    yield _sse_event("step", {"step": "done", "message": f"Pipeline complete — Winner: {result['winner']}"})
    yield _sse_event("result", result)


# ---------------------------------------------------------------------------
# BYOD: CSV to SQLite converter
# ---------------------------------------------------------------------------

def csv_to_sqlite(csv_bytes: bytes, db_name: str) -> Path:
    """Convert an uploaded CSV file to a SQLite database."""
    db_path = UPLOAD_DIR / f"{db_name}.sqlite"
    reader = csv.reader(io.StringIO(csv_bytes.decode("utf-8-sig")))
    headers = [h.strip().replace(" ", "_").replace("-", "_") for h in next(reader)]

    with sqlite3.connect(str(db_path)) as conn:
        cols = ", ".join(f'"{h}" TEXT' for h in headers)
        conn.execute(f'CREATE TABLE IF NOT EXISTS "{db_name}" ({cols})')
        placeholders = ", ".join("?" for _ in headers)
        for row in reader:
            if len(row) == len(headers):
                conn.execute(f'INSERT INTO "{db_name}" VALUES ({placeholders})', row)
        conn.commit()
    return db_path


def load_benchmark_results() -> list[dict[str, Any]]:
    results = []
    if not RESULTS_DIR.exists():
        return results
    for path in sorted(RESULTS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if "metrics" in data:
                data["_filename"] = path.name
                results.append(data)
        except Exception:
            continue
    return results


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class FullQueryRequest(BaseModel):
    question: str
    db_id: str
    provider: str = "groq"
    model: str = "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/databases")
def get_databases():
    return {"databases": discover_databases()}


@app.get("/api/benchmarks")
def get_benchmarks():
    return {"benchmarks": load_benchmark_results()}


@app.post("/api/query")
async def run_full_query(req: FullQueryRequest):
    """SSE streaming endpoint — returns real-time pipeline events."""
    def event_stream():
        yield from generate_sql_pipeline_streaming(
            question=req.question,
            db_id=req.db_id,
            provider=req.provider,
            model=req.model,
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/upload")
async def upload_database(file: UploadFile = File(...)):
    """Upload a .sqlite or .csv file as a BYOD database."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    name = Path(file.filename).stem
    suffix = Path(file.filename).suffix.lower()
    content = await file.read()

    if suffix == ".sqlite":
        dest = UPLOAD_DIR / f"{name}.sqlite"
        dest.write_bytes(content)
    elif suffix == ".csv":
        csv_to_sqlite(content, name)
    else:
        raise HTTPException(status_code=400, detail="Only .sqlite and .csv files are supported")

    # Clear schema caches for this new db
    db_path = UPLOAD_DIR / f"{name}.sqlite"
    key = str(db_path)
    _schema_cache.pop(key, None)
    _schema_dict_cache.pop(key, None)

    return {"status": "ok", "db_id": name, "message": f"Database '{name}' uploaded successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("queryshield.app.api:app", host="127.0.0.1", port=8000, reload=True)
