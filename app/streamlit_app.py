"""QueryShield Streamlit UI — Interactive Text-to-SQL Demo.

Three-tab interface:
  Tab 1: Query Playground — live NL→SQL with side-by-side comparison
  Tab 2: Benchmark Results — charts from existing evaluation JSONs
  Tab 3: Architecture — pipeline diagram for recruiters/visitors

This module exposes ``render_app()`` which is called from the root ``app.py``
for HuggingFace Spaces deployment.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Paths — resolved relative to this file so imports work from any CWD
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SPIDER_DIR = DATA_DIR / "spider2" / "local_sqlite_dbs"
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"

# ---------------------------------------------------------------------------
# Pre-loaded example queries per database (clickable in the UI)
# ---------------------------------------------------------------------------
EXAMPLE_QUERIES: dict[str, list[str]] = {
    "IPL": [
        "Which team won the most matches in 2019?",
        "List top 5 batsmen by total runs across all seasons",
        "Find all matches where the margin was over 100 runs",
    ],
    "Db-IMDB": [
        "Find all movies directed by Christopher Nolan with rating above 8",
        "Which actor appeared in the most movies after 2010?",
        "List the top 10 highest-rated movies released in 2020",
    ],
    "E_commerce": [
        "What are the top 5 product categories by total revenue?",
        "How many orders were delivered late compared to estimated delivery date?",
        "Find customers who made more than 3 orders",
    ],
    "sqlite-sakila": [
        "Which customer has rented the most films?",
        "List the top 5 most-rented film categories",
        "Find the average rental duration per film category",
    ],
    "f1": [
        "Which driver has the most wins in a single season?",
        "List all constructors that have won a championship",
        "What is the average number of pit stops per race in 2021?",
    ],
}

# ---------------------------------------------------------------------------
# Lazy imports (avoid loading heavy model at startup on tab 2/3)
# ---------------------------------------------------------------------------


@st.cache_resource
def _load_llm_client(provider: str, model: str, timeout: int = 120):
    """Cache an LLMClient singleton per provider+model combo."""
    import os
    os.environ["LLM_PROVIDER"] = provider
    if provider == "groq":
        os.environ["GROQ_MODEL"] = model
    else:
        os.environ["OLLAMA_MODEL"] = model
    from queryshield.core.llm import LLMClient
    return LLMClient(provider=provider, model=model, timeout_seconds=timeout)


@st.cache_resource
def _load_schema_pruner():
    from queryshield.retrieval.schema_pruner import SchemaPruner
    return SchemaPruner(top_k=5)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def discover_databases() -> list[str]:
    """Find all .sqlite files in the Spider2 data directory."""
    if not SPIDER_DIR.exists():
        return []
    return sorted(p.stem for p in SPIDER_DIR.glob("*.sqlite"))


def get_db_path(db_id: str) -> Path:
    return SPIDER_DIR / f"{db_id}.sqlite"


def run_sql(db_path: Path, sql: str) -> tuple[list[dict], str | None]:
    """Execute SQL and return (rows_as_dicts, error_or_none)."""
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()[:100]]
            return rows, None
    except Exception as exc:
        return [], str(exc)


@st.cache_data(ttl=600)
def get_schema_text(db_path_str: str) -> str:
    from queryshield.evaluation.spider_schema import build_rich_schema_context
    return build_rich_schema_context(Path(db_path_str))


@st.cache_data(ttl=600)
def get_schema_dict(db_path_str: str) -> dict:
    from queryshield.evaluation.spider_schema import build_schema_dict
    return build_schema_dict(Path(db_path_str))


def generate_sql_pipeline(
    question: str,
    db_id: str,
    provider: str,
    model: str,
) -> dict[str, Any]:
    """Run the full QueryShield pipeline on a single question."""
    from queryshield.evaluation.planner import build_planner_prompt, parse_plan_response
    from queryshield.evaluation.sql_generator import build_sql_from_plan_prompt
    from queryshield.evaluation.spider_prompts import build_common_prompt
    from queryshield.evaluation.model_profiles import get_model_profile, strip_thinking_blocks
    from queryshield.retrieval.schema_pruner import build_pruned_schema_context, SchemaPruner

    db_path = get_db_path(db_id)
    db_path_str = str(db_path)
    full_schema_text = get_schema_text(db_path_str)
    schema_dict = get_schema_dict(db_path_str)

    # Prune schema
    pruned_schema = build_pruned_schema_context(
        nl_query=question,
        full_schema=schema_dict,
        full_schema_text=full_schema_text,
        top_k=5,
    )

    llm = _load_llm_client(provider, model)
    profile = get_model_profile(model)

    pruner = _load_schema_pruner()
    result: dict[str, Any] = {
        "question": question,
        "db_id": db_id,
        "model": model,
        "pruned_tables": list(
            pruner.prune(question, schema_dict).keys()
        ) if len(schema_dict) > 5 else list(schema_dict.keys()),
    }

    # --- Baseline (direct prompt) ---
    t0 = time.time()
    try:
        baseline_prompt = build_common_prompt(schema=full_schema_text, question=question)
        baseline_sql = llm.generate_sql(baseline_prompt)
    except Exception as exc:
        baseline_sql = f"-- ERROR: {exc}"
    result["baseline_sql"] = baseline_sql
    result["baseline_time_sec"] = round(time.time() - t0, 2)

    # --- System (plan-based with pruned schema) ---
    t1 = time.time()
    try:
        planner_prompt = build_planner_prompt(schema=pruned_schema, question=question)
        plan_raw = llm.generate_text(planner_prompt)
        if profile.get("strip_thinking"):
            plan_raw = strip_thinking_blocks(plan_raw)
        plan, parse_error = parse_plan_response(plan_raw)
        result["plan"] = plan
        result["plan_error"] = parse_error

        sql_prompt = build_sql_from_plan_prompt(plan=plan, schema=pruned_schema)
        system_sql = llm.generate_sql(sql_prompt)
    except Exception as exc:
        system_sql = f"-- ERROR: {exc}"
        result["plan"] = {}
        result["plan_error"] = str(exc)

    result["system_sql"] = system_sql
    result["system_time_sec"] = round(time.time() - t1, 2)

    # --- Execute both ---
    baseline_rows, baseline_err = run_sql(db_path, baseline_sql)
    system_rows, system_err = run_sql(db_path, system_sql)

    result["baseline_rows"] = baseline_rows
    result["baseline_error"] = baseline_err
    result["system_rows"] = system_rows
    result["system_error"] = system_err
    result["baseline_success"] = baseline_err is None
    result["system_success"] = system_err is None

    if system_err is None and baseline_err is not None:
        result["winner"] = "🏆 QueryShield"
    elif baseline_err is None and system_err is not None:
        result["winner"] = "📊 Baseline"
    elif system_rows == baseline_rows:
        result["winner"] = "🤝 Tie"
    else:
        result["winner"] = "🔍 Different Results"

    return result


def load_benchmark_results() -> list[dict[str, Any]]:
    """Load all benchmark JSON files from the results directory."""
    results = []
    if not RESULTS_DIR.exists():
        return results
    for path in sorted(RESULTS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("status") == "completed" and "metrics" in data:
                data["_filename"] = path.name
                results.append(data)
        except Exception:
            continue
    # Also load the Mistral fair-comparison file (different schema)
    for path in sorted(RESULTS_DIR.glob("results_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if "metrics" in data and "_filename" not in data:
                data["_filename"] = path.name
                data["status"] = "completed"
                results.append(data)
        except Exception:
            continue
    return results


# ---------------------------------------------------------------------------
# Main render function (called from root app.py)
# ---------------------------------------------------------------------------

def render_app() -> None:
    """Render the full Streamlit application."""

    st.set_page_config(
        page_title="QueryShield — Text-to-SQL Intelligence",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ---- Custom CSS ----
    st.markdown("""
    <style>
        .stMetric {
            background: rgba(20, 20, 40, 0.6);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(100, 120, 255, 0.15);
            border-radius: 16px;
            padding: 16px;
        }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            background: rgba(30, 30, 60, 0.5);
            border-radius: 12px 12px 0 0;
            padding: 10px 24px;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
        }
        div[data-testid="stExpander"] {
            background: rgba(20, 20, 40, 0.4);
            border: 1px solid rgba(100, 120, 255, 0.1);
            border-radius: 12px;
        }
        .winner-badge {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: 700;
            display: inline-block;
            font-size: 16px;
        }
        h1 {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
        }
    </style>
    """, unsafe_allow_html=True)

    # ---- Sidebar ----
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/database.png", width=64)
        st.title("QueryShield")
        st.caption("Text-to-SQL Intelligence Layer")
        st.divider()
        st.markdown("**Model Configuration**")

        provider = st.selectbox(
            "LLM Provider",
            ["groq", "ollama"],
            index=0,
            help="Groq = cloud (fast, free tier), Ollama = local",
        )

        if provider == "groq":
            model_options = [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "llama3-70b-8192",
                "mixtral-8x7b-32768",
                "mistral-saba-24b",
            ]
        else:
            model_options = [
                "gemma4:e4b",
                "gemma4:31b-cloud",
                "qwen2.5:3b",
                "deepseek-r1:8b",
            ]

        model = st.selectbox("Model", model_options, index=0)
        st.divider()
        st.markdown(
            "Built with ❤️ for Spider 2.0\n\n"
            "[GitHub](https://github.com) · [Paper](https://arxiv.org)"
        )

    # ---- Main area ----
    st.title("🛡️ QueryShield")
    st.caption("Plan-based Text-to-SQL with schema pruning, model-adaptive validation, and execution verification")

    tab1, tab2, tab3 = st.tabs(["🎮 Query Playground", "📊 Benchmark Results", "🏗️ Architecture"])

    # ===========================================================================
    # TAB 1: Query Playground
    # ===========================================================================
    with tab1:
        databases = discover_databases()
        if not databases:
            st.warning(
                "No Spider2 databases found. Place .sqlite files in "
                "`queryshield/data/spider2/local_sqlite_dbs/`"
            )
        else:
            col1, col2 = st.columns([2, 1])
            with col1:
                db_id = st.selectbox(
                    "📁 Database",
                    databases,
                    index=databases.index("IPL") if "IPL" in databases else 0,
                )
            with col2:
                st.metric("Tables", len(get_schema_dict(str(get_db_path(db_id)))))

            with st.expander("📋 Database Schema", expanded=False):
                st.code(get_schema_text(str(get_db_path(db_id))), language="text")

            # --- Example queries ---
            examples = EXAMPLE_QUERIES.get(db_id, [])
            if examples:
                st.markdown("**💡 Try an example:**")
                example_cols = st.columns(len(examples))
                selected_example = None
                for i, (col, ex) in enumerate(zip(example_cols, examples)):
                    with col:
                        if st.button(ex[:50] + ("…" if len(ex) > 50 else ""), key=f"ex_{db_id}_{i}"):
                            selected_example = ex

                if selected_example:
                    st.session_state["_example_query"] = selected_example

            default_q = st.session_state.pop("_example_query", "")
            question = st.text_area(
                "💬 Ask a question in natural language",
                value=default_q,
                placeholder="e.g., Find the top 5 batsmen with the highest strike rate who played more than 10 matches",
                height=80,
            )

            run_btn = st.button("🚀 Generate & Compare SQL", type="primary", use_container_width=True)

            if run_btn and question.strip():
                with st.spinner("🔄 Running QueryShield pipeline..."):
                    result = generate_sql_pipeline(
                        question=question.strip(),
                        db_id=db_id,
                        provider=provider,
                        model=model,
                    )

                st.markdown(f'<div class="winner-badge">{result["winner"]}</div>', unsafe_allow_html=True)
                st.write("")

                col_b, col_s = st.columns(2)
                with col_b:
                    st.subheader("📊 Baseline SQL")
                    st.code(result["baseline_sql"], language="sql")
                    if result.get("baseline_error"):
                        st.error(f"❌ {result['baseline_error']}")
                    elif result.get("baseline_rows"):
                        st.success(f"✅ {len(result['baseline_rows'])} rows returned")
                        st.dataframe(pd.DataFrame(result["baseline_rows"]), use_container_width=True, height=250)
                    st.caption(f"⏱ {result.get('baseline_time_sec', '?')}s")

                with col_s:
                    st.subheader("🛡️ QueryShield SQL")
                    st.code(result["system_sql"], language="sql")
                    if result.get("system_error"):
                        st.error(f"❌ {result['system_error']}")
                    elif result.get("system_rows"):
                        st.success(f"✅ {len(result['system_rows'])} rows returned")
                        st.dataframe(pd.DataFrame(result["system_rows"]), use_container_width=True, height=250)
                    st.caption(f"⏱ {result.get('system_time_sec', '?')}s")

                with st.expander("📋 Generated Plan (JSON)", expanded=False):
                    st.json(result.get("plan", {}))
                    if result.get("plan_error"):
                        st.warning(f"Parse note: {result['plan_error']}")

                with st.expander("🔍 Schema Pruning Result", expanded=False):
                    pruned = result.get("pruned_tables", [])
                    all_tables = list(get_schema_dict(str(get_db_path(db_id))).keys())
                    st.markdown(f"**Selected {len(pruned)}/{len(all_tables)} tables:**")
                    for t in pruned:
                        st.markdown(f"- ✅ `{t}`")
                    removed = set(all_tables) - set(pruned)
                    if removed:
                        st.markdown(f"**Pruned ({len(removed)} tables):**")
                        for t in sorted(removed):
                            st.markdown(f"- ❌ `{t}`")

    # ===========================================================================
    # TAB 2: Benchmark Results
    # ===========================================================================
    with tab2:
        benchmarks = load_benchmark_results()

        if not benchmarks:
            st.info("No completed benchmark results found in evaluation/results/")
        else:
            st.subheader("📈 Benchmark Comparison Across Runs")
            summary_rows = []
            for b in benchmarks:
                m = b.get("metrics", {})
                rc = b.get("runtime_config", {})
                adj = b.get("adjusted_metrics", {})
                summary_rows.append({
                    "Run": b["_filename"].replace(".json", ""),
                    "Queries": m.get("total_queries", 0),
                    "Baseline Acc": f"{m.get('baseline_accuracy', 0):.1%}",
                    "System Acc": f"{m.get('system_accuracy', 0):.1%}",
                    "Improvement": f"{m.get('improvement_percent', m.get('improvement', 0)*100):+.1f}%",
                    "Exec Success (B)": f"{m.get('baseline_execution_success_rate', 0):.1%}",
                    "Exec Success (S)": f"{m.get('system_execution_success_rate', 0):.1%}",
                    "Pipeline": rc.get("pipeline_mode", "n/a"),
                    "Adjusted Acc": f"{adj.get('adjusted_accuracy', 0):.1f}%" if adj else "n/a",
                })

            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, height=300)

            st.subheader("🎯 Accuracy: Baseline vs QueryShield System")
            chart_data = []
            for b in benchmarks:
                m = b.get("metrics", {})
                name = b["_filename"].replace(".json", "").replace("spider2_", "").replace("results_", "").replace("_", " ").title()
                chart_data.append({"Run": name, "Baseline": m.get("baseline_accuracy", 0), "System": m.get("system_accuracy", 0)})
            if chart_data:
                st.bar_chart(pd.DataFrame(chart_data).set_index("Run"), height=350)

            st.subheader("⚡ Execution Success Rate")
            exec_data = []
            for b in benchmarks:
                m = b.get("metrics", {})
                name = b["_filename"].replace(".json", "").replace("spider2_", "").replace("results_", "").replace("_", " ").title()
                exec_data.append({
                    "Run": name,
                    "Baseline": m.get("baseline_execution_success_rate", 0),
                    "System": m.get("system_execution_success_rate", 0),
                })
            if exec_data:
                st.bar_chart(pd.DataFrame(exec_data).set_index("Run"), height=300)

            st.subheader("🔎 Per-Query Breakdown")
            selected_run = st.selectbox("Select benchmark run", [b["_filename"] for b in benchmarks])
            selected_benchmark = next(b for b in benchmarks if b["_filename"] == selected_run)
            query_rows = []
            for r in selected_benchmark.get("results", []):
                query_rows.append({
                    "DB": r.get("db_id", "?"),
                    "Question": r.get("question", "?")[:80],
                    "Baseline ✓": "✅" if r.get("baseline_correct") else "❌",
                    "System ✓": "✅" if r.get("system_correct") else "❌",
                    "Winner": r.get("winner", "?"),
                    "Plan Quality": r.get("system_plan_quality", "?"),
                    "Time (s)": r.get("query_runtime_sec", "?"),
                })
            if query_rows:
                st.dataframe(pd.DataFrame(query_rows), use_container_width=True, height=400)

    # ===========================================================================
    # TAB 3: Architecture
    # ===========================================================================
    with tab3:
        st.subheader("🏗️ QueryShield Architecture")
        st.markdown("""
QueryShield is a **plan-based Text-to-SQL system** that adds an intelligent
reasoning layer between the natural language question and the final SQL query.
Instead of asking an LLM to generate SQL directly, QueryShield breaks the
problem into structured steps — making the process more transparent,
debuggable, and accurate.
        """)

        st.markdown("### Pipeline Flow")
        st.markdown("""
```
NL Question
    │
    ▼
┌────────────────────────┐
│   Schema Pruner        │  all-MiniLM-L6-v2 embeddings
│   (top-K tables)       │  ~80% token reduction
└──────────┬─────────────┘
           ▼
┌────────────────────────┐
│   Planner              │  NL → structured JSON plan
│   (2-shot guided)      │  tables, joins, filters, aggs
└──────────┬─────────────┘
           ▼
┌────────────────────────┐
│   SQL Generator        │  plan → executable SQL
│   (SQLite rules)       │  no YEAR(), no QUALIFY
└──────────┬─────────────┘
           ▼
┌────────────────────────┐
│   Plan Validator       │◄── Model Profiles
│   (≥0.65 confidence)   │    (per-LLM strictness)
└──────────┬─────────────┘
           ▼
┌────────────────────────┐
│   Error Router         │  deterministic fixes
│   + Schema Validator   │  YEAR→strftime, col fuzzy
└──────────┬─────────────┘
           ▼
┌────────────────────────┐
│   Execution + Verify   │  semantic correction loop
└────────────────────────┘
```
        """)

        st.markdown("### Key Components")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
**🔍 Schema Pruner**
SentenceTransformer embeddings select the top-K relevant tables.
Keyword fallback when model is unavailable.

**📋 Planner**
Structured JSON execution plan: tables, joins, filters,
aggregations, grouping, ordering. 2-shot examples.

**⚙️ SQL Generator**
Compiles plan into SQL with SQLite-specific rules.
            """)

        with col2:
            st.markdown("""
**✅ Plan Validator**
Confidence-gated (≥0.65 + CRITICAL severity).
Model-specific strictness via profiles.

**🔧 Error Router**
Deterministic fixes without LLM calls:
YEAR→strftime, UNION ORDER BY, column fuzzy matching.

**🧠 Model Profiles**
Per-model config: validator leniency, timeout
multipliers, thinking-block stripping.
            """)

        st.markdown("### Benchmark Protocol")
        st.markdown("""
- **Dataset**: Spider 2.0 local subset (16 databases, 24 complex queries)
- **Fair comparison**: Same prompt, same schema, same model for both baseline and system
- **Baseline**: Direct NL→SQL with single LLM call
- **System**: Full pipeline with plan, validation, correction, semantic loop
- **Headline result**: Mistral fair comparison: **38.5% → 65.4%** (+26.9%)
        """)

        st.markdown("### Tech Stack")
        tech_cols = st.columns(4)
        with tech_cols[0]:
            st.markdown("**Core**\n- Python 3.12\n- SQLite\n- FastAPI")
        with tech_cols[1]:
            st.markdown("**LLM**\n- Groq API\n- Ollama (local)\n- Multi-model")
        with tech_cols[2]:
            st.markdown("**ML**\n- SentenceTransformers\n- sqlglot\n- numpy")
        with tech_cols[3]:
            st.markdown("**UI**\n- Streamlit\n- Pandas\n- Plotly")


# ---------------------------------------------------------------------------
# Direct execution (local dev: `streamlit run queryshield/app/streamlit_app.py`)
# ---------------------------------------------------------------------------
if __name__ == "__main__" or st.runtime.exists():
    render_app()
