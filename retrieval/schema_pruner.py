"""Schema pruning helpers for QueryShield.

Primary strategy:
- Use SentenceTransformer embeddings to rank table relevance to an NL query.
- After semantic selection, expand the selected set by traversing Foreign Key
  relationships (graph BFS) to pull in any "bridge" tables needed to connect
  the semantically selected seeds. This ensures multi-table JOIN queries are
  never missing an intermediate link table.

Fallback strategy:
- If embedding model cannot be loaded (offline/proxy/no cache), use
  deterministic keyword overlap scoring so the pipeline never crashes.
"""

from __future__ import annotations

import logging
import os
import re
from collections import deque
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_PRUNER_MODEL = None
_PRUNER_LOAD_FAILED = False


def _get_model():
    """Lazy-load the embedding model; return None if unavailable.

    Download behaviour:
    - On HuggingFace Spaces (SPACE_ID is set): always allow download.
    - Locally: honour QUERYSHIELD_PRUNER_ALLOW_DOWNLOAD (default "0").
      Set to "1" to force download, otherwise local_files_only is used.
    """
    global _PRUNER_MODEL
    global _PRUNER_LOAD_FAILED
    if _PRUNER_MODEL is None and not _PRUNER_LOAD_FAILED:
        try:
            from sentence_transformers import SentenceTransformer

            on_hf_spaces = bool(os.getenv("SPACE_ID"))
            allow_download = (
                on_hf_spaces
                or os.getenv("QUERYSHIELD_PRUNER_ALLOW_DOWNLOAD", "0") == "1"
            )
            if allow_download:
                _PRUNER_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info(
                    "Loaded SentenceTransformer: all-MiniLM-L6-v2 (download=%s, spaces=%s)",
                    allow_download, on_hf_spaces,
                )
            else:
                _PRUNER_MODEL = SentenceTransformer(
                    "all-MiniLM-L6-v2",
                    local_files_only=True,
                )
                logger.info("Loaded SentenceTransformer: all-MiniLM-L6-v2 (local cache)")
        except Exception as exc:  # noqa: BLE001
            _PRUNER_LOAD_FAILED = True
            _PRUNER_MODEL = None
            logger.warning(
                "SchemaPruner model unavailable, falling back to keyword pruning: %s",
                exc,
            )
    return _PRUNER_MODEL


# ---------------------------------------------------------------------------
# Foreign Key Graph Utilities
# ---------------------------------------------------------------------------

def _build_fk_graph(full_schema: dict[str, Any]) -> dict[str, set[str]]:
    """Build an undirected adjacency graph of tables connected by foreign keys.

    Returns a dict mapping each table name to the set of tables it is
    directly connected to via a foreign key (in either direction).
    """
    graph: dict[str, set[str]] = {t: set() for t in full_schema}

    for table_name, table_info in full_schema.items():
        if not isinstance(table_info, dict):
            continue
        fks = table_info.get("foreign_keys", [])
        for fk in fks:
            if not isinstance(fk, dict):
                continue
            # Support both naming conventions used in the codebase
            ref_table = fk.get("referenced_table") or fk.get("to_table") or fk.get("table", "")
            if ref_table and ref_table in full_schema:
                graph.setdefault(table_name, set()).add(ref_table)
                graph.setdefault(ref_table, set()).add(table_name)

    return graph


def _bfs_shortest_path(
    graph: dict[str, set[str]], start: str, end: str
) -> list[str] | None:
    """Return the shortest path (list of table names) between two tables using BFS.

    Returns None if no path exists.
    """
    if start == end:
        return [start]
    if start not in graph or end not in graph:
        return None

    visited: set[str] = {start}
    queue: deque[list[str]] = deque([[start]])

    while queue:
        path = queue.popleft()
        current = path[-1]

        for neighbor in graph.get(current, set()):
            if neighbor in visited:
                continue
            new_path = path + [neighbor]
            if neighbor == end:
                return new_path
            visited.add(neighbor)
            queue.append(new_path)

    return None


def _expand_with_fk_graph(
    seed_tables: list[str],
    full_schema: dict[str, Any],
    max_total: int = 10,
) -> list[str]:
    """Expand the seed table set by finding shortest FK paths between all seed pairs.

    This ensures that if answering a query requires joining Table A to Table C
    through an intermediate Table B, Table B is automatically included even if
    it wasn't semantically relevant to the user's question.

    Args:
        seed_tables: The semantically selected table names.
        full_schema: The complete database schema dict.
        max_total: Hard ceiling to prevent runaway expansion on huge schemas.

    Returns:
        An expanded list of table names (seed tables + bridge tables).
    """
    if len(seed_tables) <= 1:
        return seed_tables

    graph = _build_fk_graph(full_schema)
    expanded: set[str] = set(seed_tables)

    # For every pair of seed tables, find the shortest FK path and include
    # all intermediate "bridge" tables.
    for i, t1 in enumerate(seed_tables):
        for t2 in seed_tables[i + 1:]:
            path = _bfs_shortest_path(graph, t1, t2)
            if path:
                for table in path:
                    if len(expanded) >= max_total:
                        break
                    expanded.add(table)

    added = expanded - set(seed_tables)
    if added:
        logger.info(
            "FK Graph Expansion: added %d bridge tables: %s",
            len(added),
            sorted(added),
        )

    return list(expanded)


class SchemaPruner:
    """Select top-k relevant tables for a natural-language query.

    Pipeline:
    1. Semantic Scoring  — Rank all tables by cosine similarity to the query.
    2. FK Graph Expansion — BFS between selected seeds to pull in bridge tables.
    """

    def __init__(
        self,
        top_k: int = 5,
        min_score: float = 0.15,
        max_expansion: int = 10,
    ) -> None:
        self.top_k = max(1, int(top_k))
        self.min_score = float(min_score)
        self.max_expansion = max(self.top_k, int(max_expansion))

    def prune(
        self,
        nl_query: str,
        full_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a pruned schema dictionary containing only relevant tables."""
        if not full_schema or not nl_query.strip():
            return full_schema

        table_names = list(full_schema.keys())
        if len(table_names) <= self.top_k:
            return full_schema

        model = _get_model()
        if model is None:
            return self._keyword_prune(nl_query=nl_query, full_schema=full_schema)

        table_descriptions = []
        for tname in table_names:
            entry = full_schema[tname]
            cols = ', '.join(entry.get('columns', []))
            desc = f"{tname}: {cols}"
            # Enrich with foreign key relationships for better relational matching
            fks = entry.get('foreign_keys', [])
            if fks:
                linked_tables = list(set(
                    fk.get('referenced_table', fk.get('to_table', ''))
                    for fk in fks
                    if isinstance(fk, dict)
                ))
                linked_tables = [t for t in linked_tables if t]
                if linked_tables:
                    desc += f" | connects to: {', '.join(linked_tables)}"
            table_descriptions.append(desc)

        query_emb = model.encode([nl_query], normalize_embeddings=True)
        table_embs = model.encode(table_descriptions, normalize_embeddings=True)
        scores = np.dot(query_emb, table_embs.T)[0]

        ranked_indices = np.argsort(scores)[::-1]
        selected_indices: list[int] = []
        for idx in ranked_indices:
            if len(selected_indices) >= self.top_k:
                break
            if scores[idx] >= self.min_score or not selected_indices:
                selected_indices.append(int(idx))

        seed_tables = [table_names[i] for i in selected_indices]

        # --- FK Graph Expansion ---
        expanded_tables = _expand_with_fk_graph(
            seed_tables=seed_tables,
            full_schema=full_schema,
            max_total=self.max_expansion,
        )

        pruned = {t: full_schema[t] for t in expanded_tables if t in full_schema}
        logger.debug(
            "SchemaPruner: seeds=%d, expanded=%d/%d tables",
            len(seed_tables),
            len(pruned),
            len(table_names),
        )
        return pruned

    def _keyword_prune(
        self,
        nl_query: str,
        full_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Fallback pruning using token overlap (no external model required)."""
        query_tokens = set(re.findall(r"[a-zA-Z0-9_]+", nl_query.lower()))
        scored: list[tuple[int, str]] = []

        for table_name, table_info in full_schema.items():
            columns = table_info.get("columns", []) if isinstance(table_info, dict) else []
            table_tokens = set(re.findall(r"[a-zA-Z0-9_]+", table_name.lower()))
            for col in columns:
                table_tokens.update(re.findall(r"[a-zA-Z0-9_]+", str(col).lower()))
            overlap = len(query_tokens.intersection(table_tokens))
            scored.append((overlap, table_name))

        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        seed_names = [name for _, name in scored[: self.top_k]]
        if not seed_names and full_schema:
            seed_names = [next(iter(full_schema.keys()))]

        # --- FK Graph Expansion (also applies to keyword fallback) ---
        expanded_names = _expand_with_fk_graph(
            seed_tables=seed_names,
            full_schema=full_schema,
            max_total=self.max_expansion,
        )

        pruned = {name: full_schema[name] for name in expanded_names if name in full_schema}
        logger.debug(
            "SchemaPruner keyword fallback: seeds=%d, expanded=%d/%d tables",
            len(seed_names),
            len(pruned),
            len(full_schema),
        )
        return pruned


def build_pruned_schema_context(
    nl_query: str,
    full_schema: dict[str, Any],
    full_schema_text: str,
    top_k: int = 5,
) -> str:
    """Prune schema dict and return a reduced rich-schema text block."""
    if not full_schema or len(full_schema) <= top_k:
        return full_schema_text

    pruned = SchemaPruner(top_k=top_k).prune(nl_query=nl_query, full_schema=full_schema)
    pruned_tables = set(pruned.keys())

    lines = full_schema_text.split("\n")
    output: list[str] = []
    in_relevant_table = False
    in_fk_section = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("Foreign Keys:"):
            in_fk_section = True
            if output and output[-1].strip():
                output.append("")
            output.append(line)
            continue

        if in_fk_section:
            if stripped.startswith("- "):
                if any(table_name in line for table_name in pruned_tables):
                    output.append(line)
            elif stripped:
                output.append(line)
            continue

        if line.startswith("Table: "):
            table_name = line.split("Table: ", 1)[1].strip()
            in_relevant_table = table_name in pruned_tables
            if in_relevant_table:
                if output and output[-1].strip():
                    output.append("")
                output.append(line)
            continue

        if in_relevant_table:
            output.append(line)

    return "\n".join(output).strip()
