# Licensed under the Apache License, Version 2.0 (the "License");
"""
Semantic (fuzzy) test deduplication without LLMs.

Always-on reducer to collapse exact and near-duplicate test cases using
pure Python heuristics:
- Normalized exact/substring check
- Token Jaccard similarity
- Sequence similarity (difflib)

Environment variables (optional):
- TEST_SEMANTIC_DEDUP_ENABLED=true|false (default: true)
- TEST_SEMANTIC_DEDUP_SEQ=0.92  (SequenceMatcher threshold)
- TEST_SEMANTIC_DEDUP_JACCARD=0.88 (Token Jaccard threshold)
- TEST_SEMANTIC_DEDUP_LENRATIO=0.90 (Short/long length ratio for substring near-dupes)
"""

from __future__ import annotations

import os
import re
import unicodedata
from difflib import SequenceMatcher
from typing import List, Tuple

from .logging_config import get_logger

logger = get_logger(__name__)


_STOPWORDS_EN = {
    # articles, prepositions, conjunctions, auxiliaries
    "the", "a", "an", "of", "for", "to", "in", "on", "at", "by", "with", "from", "into",
    "and", "or", "but", "not", "no", "is", "are", "was", "were", "be", "been", "being",
    "this", "that", "these", "those", "as", "it", "its", "their", "there", "then",
    "must", "should", "shall", "can", "could", "would", "may", "might",
    "return", "show", "display", "list", "retrieve",  # common verb noise in tests
}

_STOPWORDS_IT = {
    # articoli, preposizioni, congiunzioni, ausiliari
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "del", "della", "dei", "degli", "delle",
    "a", "da", "in", "su", "con", "per", "tra", "fra", "e", "o", "ma", "non", "che", "come",
    "è", "sono", "era", "erano", "essere", "stato", "stati",
    "deve", "devono", "dovrebbe", "mostra", "visualizza", "elenca", "restituisci"
}

_TAG_PATTERN = re.compile(r"\[(?:EVIDENCE-CRITICAL|CRITICAL|MANDATORY)\]")
_PUNCT_PATTERN = re.compile(r"[\t\n\r\f\v]+|[\.,;:!\?\(\)\[\]\{\}\-_/\\]+")
_SPACE_PATTERN = re.compile(r"\s+")


def _bool_env(name: str, default: bool) -> bool:
    v = os.getenv(name, str(default)).strip().lower()
    return v in ("1", "true", "yes", "on")


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _remove_diacritics(text: str) -> str:
    # NFKD normalize and strip combining chars
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _normalize_for_compare(text: str) -> Tuple[str, bool]:
    """Normalize text for robust comparison.

    Returns a tuple of (normalized_text, has_evidence_critical_tag).
    """
    if not isinstance(text, str):
        text = str(text)

    has_tag = bool(_TAG_PATTERN.search(text))

    # Strip tags for semantic comparison but remember presence
    t = _TAG_PATTERN.sub("", text)

    # Lowercase + diacritics removal for cross-language robustness
    t = _remove_diacritics(t.casefold())

    # Collapse punctuation to spaces and normalize whitespace
    t = _PUNCT_PATTERN.sub(" ", t)
    t = _SPACE_PATTERN.sub(" ", t).strip()

    return t, has_tag


def _tokenize(text: str) -> List[str]:
    # Words and numbers only (keeps digits intact)
    tokens = re.findall(r"[a-zA-Z0-9]+", text)
    if not tokens:
        return []
    # Drop short 1-char tokens that are often noise
    tokens = [tok for tok in tokens if len(tok) > 1 or tok.isdigit()]

    # Remove lightweight stopwords to focus on semantics
    stop = _STOPWORDS_EN | _STOPWORDS_IT
    return [t for t in tokens if t not in stop]


def _jaccard(a_tokens: List[str], b_tokens: List[str]) -> float:
    if not a_tokens and not b_tokens:
        return 1.0
    if not a_tokens or not b_tokens:
        return 0.0
    a_set, b_set = set(a_tokens), set(b_tokens)
    inter = len(a_set & b_set)
    union = len(a_set | b_set)
    if union == 0:
        return 0.0
    return inter / union


def _sequence_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _is_near_duplicate(
    a_norm: str,
    b_norm: str,
    jaccard_threshold: float,
    seq_threshold: float,
    len_ratio_threshold: float,
) -> bool:
    # Exact equality or near-substring with high length overlap
    if a_norm == b_norm:
        return True
    short, long = (a_norm, b_norm) if len(a_norm) <= len(b_norm) else (b_norm, a_norm)
    if short and short in long:
        if len(short) / max(1, len(long)) >= len_ratio_threshold:
            return True

    # Token Jaccard and sequence similarity
    j = _jaccard(_tokenize(a_norm), _tokenize(b_norm))
    s = _sequence_ratio(a_norm, b_norm)

    # Accept if either is very high or a strong combination
    if j >= jaccard_threshold or s >= seq_threshold:
        return True
    if j >= (jaccard_threshold - 0.05) and s >= (seq_threshold - 0.03):
        return True

    return False


def reduce_tests_semantic(tests: List[str]) -> List[str]:
    """
    Reduce exact and near-duplicate tests deterministically, preserving order.

    - Prefers keeping the first occurrence.
    - If a duplicate later has an evidence-critical tag and the kept one does not,
      upgrades the kept text to the tagged version.

    Returns the reduced list.
    """
    if not tests:
        return []

    if not _bool_env("TEST_SEMANTIC_DEDUP_ENABLED", True):
        return [t for t in tests if t and t != "GENERATION FAILED"]

    seq_thr = _float_env("TEST_SEMANTIC_DEDUP_SEQ", 0.92)
    jac_thr = _float_env("TEST_SEMANTIC_DEDUP_JACCARD", 0.88)
    len_thr = _float_env("TEST_SEMANTIC_DEDUP_LENRATIO", 0.90)

    kept: List[str] = []
    kept_norm: List[str] = []
    kept_has_tag: List[bool] = []

    for raw in tests:
        if not raw or raw == "GENERATION FAILED":
            continue
        norm, has_tag = _normalize_for_compare(raw)
        if not norm:
            continue

        dup_index = -1
        for i, existing_norm in enumerate(kept_norm):
            if _is_near_duplicate(norm, existing_norm, jac_thr, seq_thr, len_thr):
                dup_index = i
                break

        if dup_index >= 0:
            # Prefer preserving evidence-critical if present in the new variant
            if has_tag and not kept_has_tag[dup_index]:
                kept[dup_index] = raw  # upgrade to tagged version
                kept_has_tag[dup_index] = True
            else:
                # Optionally prefer the more informative (longer) variant
                if len(raw) > len(kept[dup_index]) * 1.15:
                    kept[dup_index] = raw
            continue

        kept.append(raw)
        kept_norm.append(norm)
        kept_has_tag.append(has_tag)

    before, after = len(tests), len(kept)
    if after < before:
        logger.info(f"Semantic test reducer: {before} -> {after} (removed {before - after})")

    return kept

