# Licensed under the Apache License, Version 2.0 (the "License");
"""
RelevanceGuard: classify evidence-derived tests as STRICT, WEAK, or IRRELEVANT
using pure-Python lexical and structural heuristics (no LLMs).

Inputs:
- question: user question string
- sql: generated SQL string (used to extract tables/columns actually used)
- tests: list[str] evidence-critical tests (strings)

Outputs:
- dict with keys: strict, weak, irrelevant, details
  where details is a per-test list with computed features and label.

Env/Config knobs (all optional, with safe defaults):
- RELEVANCE_STRICT_MIN_SCORE (float) default 0.75
- RELEVANCE_WEAK_MIN_SCORE (float)   default 0.45
- RELEVANCE_DROP_BELOW (float)       default 0.30
- RELEVANCE_W_BM25 (float)           default 0.6
- RELEVANCE_W_STRUCT (float)         default 0.4
- RELEVANCE_USE_RRF (bool)           default false (not used; kept for parity)
- RELEVANCE_LOG_JSONL (bool)         default true (write jsonl diagnostics)

Notes:
- BM25 is computed over the tests corpus with the question as the query.
- Structural features are derived by matching SQL tables/columns against test text.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

from helpers.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class GuardConfig:
    strict_min: float = 0.75
    weak_min: float = 0.45
    drop_below: float = 0.30
    w_bm25: float = 0.6
    w_struct: float = 0.4
    use_rrf: bool = False
    log_jsonl: bool = True


def _to_bool(val: str | None, default: bool) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


def load_config_from_env() -> GuardConfig:
    try:
        return GuardConfig(
            strict_min=float(os.getenv("RELEVANCE_STRICT_MIN_SCORE", 0.75)),
            weak_min=float(os.getenv("RELEVANCE_WEAK_MIN_SCORE", 0.45)),
            drop_below=float(os.getenv("RELEVANCE_DROP_BELOW", 0.30)),
            w_bm25=float(os.getenv("RELEVANCE_W_BM25", 0.6)),
            w_struct=float(os.getenv("RELEVANCE_W_STRUCT", 0.4)),
            use_rrf=_to_bool(os.getenv("RELEVANCE_USE_RRF"), False),
            log_jsonl=_to_bool(os.getenv("RELEVANCE_LOG_JSONL", "true"), True),
        )
    except Exception as e:
        logger.warning(f"Failed to load relevance guard config from env, using defaults: {e}")
        return GuardConfig()


# ------------------------ Tokenization & BM25 ------------------------

_STOPWORDS = {
    # Italian + English minimal set
    'the', 'and', 'or', 'of', 'in', 'to', 'for', 'on', 'by', 'with', 'a', 'an',
    'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'una', 'uno', 'di', 'da', 'per', 'con', 'su', 'tra', 'fra',
}


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    # keep alphanumerics and underscores, split on non-word
    tokens = re.split(r"\W+", text.lower())
    return [t for t in tokens if t and t not in _STOPWORDS]


def _bm25_scores(query: List[str], docs: List[List[str]]) -> List[float]:
    """Compute BM25 scores for a query against a small corpus of documents.
    Returns scores in [0,1] after min-max normalization (safe for empty cases).
    """
    if not docs:
        return []
    # Build term frequencies
    N = len(docs)
    df: Dict[str, int] = {}
    for d in docs:
        seen = set(d)
        for t in seen:
            df[t] = df.get(t, 0) + 1
    # IDF
    idf = {t: math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5)) for t in set(query)}
    # Average doc length
    avgdl = sum(len(d) for d in docs) / max(N, 1)
    k1, b = 1.5, 0.75
    raw_scores: List[float] = []
    for d in docs:
        tf: Dict[str, int] = {}
        for t in d:
            tf[t] = tf.get(t, 0) + 1
        score = 0.0
        for t in query:
            if t not in idf:
                continue
            f = tf.get(t, 0)
            if f == 0:
                continue
            denom = f + k1 * (1 - b + b * (len(d) / max(avgdl, 1e-9)))
            score += idf[t] * (f * (k1 + 1)) / denom
        raw_scores.append(score)
    # Normalize to [0,1]
    if not raw_scores:
        return [0.0 for _ in docs]
    mn, mx = min(raw_scores), max(raw_scores)
    if mx <= mn:
        return [0.0 for _ in docs]
    return [(s - mn) / (mx - mn) for s in raw_scores]


# ------------------------ SQL entity extraction ------------------------

def _extract_sql_entities(sql: str) -> Dict[str, List[str]]:
    """Extract table and column identifiers from a SQL string using sqlglot if possible,
    with regex fallbacks.
    Returns { 'tables': [..], 'columns': [..] } (lowercased).
    """
    tables: List[str] = []
    columns: List[str] = []
    try:
        import sqlglot
        from sqlglot import expressions as exp
        tree = sqlglot.parse_one(sql, read=None)  # autodetect
        if tree is not None:
            # Tables
            for t in tree.find_all(exp.Table):
                if t and t.name:
                    tables.append(str(t.name).lower())
            # Columns
            for c in tree.find_all(exp.Column):
                if c and c.name:
                    columns.append(str(c.name).lower())
    except Exception:
        # Fallback regex heuristics
        # Capture tokens after FROM/JOIN and bare qualified names like schema.table
        tbl_matches = re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w\.]*)(?:\s+as\s+[\w]+)?", sql, re.IGNORECASE)
        for m in tbl_matches:
            tables.append(m.split(".")[-1].lower())
        col_matches = re.findall(r"\b([a-zA-Z_][\w]*)\s*\.\s*([a-zA-Z_][\w]*)\b", sql)
        for t, c in col_matches:
            columns.append(c.lower())

    # Dedup while preserving order
    def _dedup(seq: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in seq:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    return {"tables": _dedup(tables), "columns": _dedup(columns)}


def _struct_hits(test_text: str, tables: List[str], columns: List[str]) -> tuple[int, int]:
    t = test_text.lower()
    table_hits = sum(1 for tb in tables if re.search(rf"\b{re.escape(tb)}\b", t))
    column_hits = sum(1 for col in columns if re.search(rf"\b{re.escape(col)}\b", t))
    return table_hits, column_hits


def _struct_score(table_hits: int, column_hits: int) -> float:
    # weighted: at least one table hit is a strong signal
    # cap contributions to 1.0
    table_component = 1.0 if table_hits >= 1 else 0.0
    col_component = min(1.0, column_hits / 2.0)
    return 0.6 * table_component + 0.4 * col_component


def _combine_scores(bm25: float, struct: float, w_bm25: float, w_struct: float) -> float:
    # Normalize weights
    total = max(1e-9, w_bm25 + w_struct)
    wb = w_bm25 / total
    ws = w_struct / total
    score = wb * bm25 + ws * struct
    return max(0.0, min(1.0, score))


def classify_tests(question: str, sql: str, tests: List[str], cfg: GuardConfig | None = None) -> Dict[str, Any]:
    """
    Classify each test as STRICT/WEAK/IRRELEVANT.

    Returns dict with keys:
    - strict: list[str]
    - weak: list[str]
    - irrelevant: list[str]
    - details: list[dict] per test with features and label
    """
    cfg = cfg or load_config_from_env()

    question_tokens = _tokenize(question)
    docs_tokens = [_tokenize(t or '') for t in tests]
    bm25_list = _bm25_scores(question_tokens, docs_tokens) if tests else []

    entities = _extract_sql_entities(sql or "")
    tables = entities.get("tables", [])
    columns = entities.get("columns", [])

    strict: List[str] = []
    weak: List[str] = []
    irrelevant: List[str] = []
    details: List[Dict[str, Any]] = []

    for i, t in enumerate(tests):
        bm25 = bm25_list[i] if i < len(bm25_list) else 0.0
        th, ch = _struct_hits(t or '', tables, columns)
        sstruct = _struct_score(th, ch)
        score = _combine_scores(bm25, sstruct, cfg.w_bm25, cfg.w_struct)

        if score < cfg.drop_below:
            label = "IRRELEVANT"
            irrelevant.append(t)
        elif score >= cfg.strict_min and (th >= 1 or ch >= 1):
            label = "STRICT"
            strict.append(t)
        elif score >= cfg.weak_min:
            label = "WEAK"
            weak.append(t)
        else:
            # Low score and no structure → irrelevant
            label = "IRRELEVANT"
            irrelevant.append(t)

        details.append({
            "test": t,
            "bm25": round(bm25, 4),
            "table_hits": th,
            "column_hits": ch,
            "struct": round(sstruct, 4),
            "score": round(score, 4),
            "label": label,
            "sql_tables": tables,
            "sql_columns": columns,
        })

    _log_classification(question, tables, columns, strict, weak, irrelevant, details, cfg)

    return {
        "strict": strict,
        "weak": weak,
        "irrelevant": irrelevant,
        "details": details,
    }


def _log_classification(
    question: str,
    tables: List[str],
    columns: List[str],
    strict: List[str],
    weak: List[str],
    irrelevant: List[str],
    details: List[Dict[str, Any]],
    cfg: GuardConfig,
):
    # Human-readable INFO logs
    logger.info(
        f"RelevanceGuard → strict={len(strict)}, weak={len(weak)}, irrelevant={len(irrelevant)}; "
        f"tables={tables}, columns={columns}"
    )

    # Optional JSONL diagnostic
    if cfg.log_jsonl:
        try:
            is_docker = os.getenv('DOCKER_CONTAINER', 'false').lower() == 'true'
            log_dir = Path('/app/logs') if is_docker else Path('frontend/sql_generator/logs')
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / 'relevance.jsonl'
            record = {
                "event": "relevance_guard_classification",
                "question": question,
                "sql_tables": tables,
                "sql_columns": columns,
                "counts": {
                    "strict": len(strict),
                    "weak": len(weak),
                    "irrelevant": len(irrelevant),
                },
                "details": details,
            }
            with log_file.open('a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write relevance.jsonl: {e}")

