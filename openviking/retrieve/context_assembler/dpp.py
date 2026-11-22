# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Pure-Python TF-IDF Determinantal Point Process (DPP) diversity re-ranking."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Sequence, TypeVar

from openviking.storage.bm25_tokenizer import STOPWORDS, extract_cjk_tokens

T = TypeVar("T")

_ASCII_WORD_RE = re.compile(r"[A-Za-z0-9_]{2,}")


def _tokenize_for_dpp(text: str) -> List[str]:
    if not text:
        return []
    tokens: List[str] = []
    for word in _ASCII_WORD_RE.findall(text):
        low = word.lower()
        if low not in STOPWORDS:
            tokens.append(low)
    for cjk in extract_cjk_tokens(text):
        if cjk not in STOPWORDS:
            tokens.append(cjk)
    return tokens


def _candidate_text(candidate: object) -> str:
    abstract = str(getattr(candidate, "abstract", "") or "")
    base_uri = str(getattr(candidate, "base_uri", "") or getattr(candidate, "uri", "") or "")
    if abstract.strip():
        return abstract
    return base_uri


def _candidate_score(candidate: object) -> float:
    for attr in ("ranked_score", "score"):
        val = getattr(candidate, attr, None)
        if val is not None:
            try:
                f = float(val)
                if math.isfinite(f):
                    return f
            except (TypeError, ValueError):
                pass
    return 0.0


def _build_tfidf_vectors(texts: Sequence[str]) -> List[Dict[str, float]]:
    n_docs = len(texts)
    tokenized = [_tokenize_for_dpp(t) for t in texts]
    df: Counter[str] = Counter()
    for toks in tokenized:
        df.update(set(toks))

    vectors: List[Dict[str, float]] = []
    for toks in tokenized:
        if not toks:
            vectors.append({})
            continue
        tf = Counter(toks)
        total = float(len(toks))
        vec: Dict[str, float] = {}
        norm_sq = 0.0
        for term, cnt in tf.items():
            idf = math.log((n_docs + 1.0) / (df[term] + 1.0)) + 1.0
            weight = (cnt / total) * idf
            vec[term] = weight
            norm_sq += weight * weight
        norm = math.sqrt(norm_sq)
        if norm > 0.0:
            for term in vec:
                vec[term] /= norm
        vectors.append(vec)
    return vectors


def _dot(a: Dict[str, float], b: Dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(val * b[k] for k, val in a.items() if k in b)


def dpp_rerank_candidates(
    candidates: Sequence[T],
    *,
    top_n: int = 10,
    alpha: float = 0.5,
) -> List[T]:
    """Diversify the top-N candidates via greedy MAP DPP over TF-IDF cosine kernels."""
    items = list(candidates)
    if len(items) <= 2 or top_n <= 1:
        return items

    k = min(top_n, len(items))
    pool = items[: max(k * 2, k)]
    tail = items[len(pool) :]

    vectors = _build_tfidf_vectors([_candidate_text(c) for c in pool])
    raw_scores = [_candidate_score(c) for c in pool]
    max_s = max(raw_scores)
    min_s = min(raw_scores)
    span = (max_s - min_s) if max_s > min_s else 1.0

    # Relevance multiplier q_i: balances relevance with orthogonal diversity residual.
    quality = [
        math.exp(alpha * ((s - min_s) / span))
        for s in raw_scores
    ]

    n = len(pool)
    di2 = [1.0] * n
    ortho_vecs: List[List[float]] = []
    selected: List[int] = []
    selected_set: set[int] = set()

    for _ in range(k):
        best_idx = -1
        best_gain = -1.0
        for i in range(n):
            if i in selected_set:
                continue
            gain = quality[i] * max(0.0, di2[i])
            if gain > best_gain:
                best_gain = gain
                best_idx = i
        if best_idx < 0:
            break
        selected.append(best_idx)
        selected_set.add(best_idx)

        if len(selected) >= k or di2[best_idx] <= 1e-9:
            continue

        denom = math.sqrt(di2[best_idx])
        c_new = [0.0] * n
        prev_vecs = ortho_vecs
        sel_vec = vectors[best_idx]
        for i in range(n):
            if i in selected_set:
                continue
            sim = _dot(sel_vec, vectors[i])
            proj = sum(v[best_idx] * v[i] for v in prev_vecs)
            e_i = (sim - proj) / denom
            c_new[i] = e_i
            di2[i] = max(0.0, di2[i] - e_i * e_i)
        ortho_vecs.append(c_new)

    ordered = [pool[idx] for idx in selected]
    ordered.extend(pool[idx] for idx in range(n) if idx not in selected_set)
    ordered.extend(tail)
    return ordered
