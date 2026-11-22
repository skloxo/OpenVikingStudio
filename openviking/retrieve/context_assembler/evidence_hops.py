# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Evidence-driven bounded multi-hop bridge retrieval for context assembly."""

from __future__ import annotations

import asyncio
import math
import re
from collections import Counter
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from openviking.retrieve.context_assembler.params import MAX_EVIDENCE_HOPS
from openviking.storage.bm25_tokenizer import STOPWORDS
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

_ASCII_ENTITY_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_.\-]{1,40}\b")
_QUOTED_CJK_RE = re.compile(r"[「『“《【]([\u4e00-\u9fffA-Za-z0-9_]{2,16})[」』”》】]")
_CJK_SPAN_RE = re.compile(r"[\u4e00-\u9fff]{2,16}")
_CJK_PARTICLE_SPLIT_RE = re.compile(
    r"[的了在和与及为向由被把将从到对给是有等中上下内外并且或着过]"
)
_SENTENCE_SPLIT_RE = re.compile(r"[。！？\n.!?;；]+")
_GENERIC_BRIDGE_STOPWORDS = STOPWORDS | frozenset(
    {
        "项目",
        "系统",
        "平台",
        "文档",
        "记录",
        "问题",
        "方案",
        "相关",
        "主要",
        "通过",
        "进行",
        "使用",
        "以及",
        "目前",
        "已经",
        "负责",
    }
)


def _extract_true_boundary_terms(text: str) -> List[Tuple[str, float]]:
    """Extract candidate bridge terms with true word/particle boundaries and entity boost."""
    if not text:
        return []
    found: List[Tuple[str, float]] = []

    for m in _QUOTED_CJK_RE.findall(text):
        term = m.strip()
        if len(term) >= 2 and term not in _GENERIC_BRIDGE_STOPWORDS:
            found.append((term, 1.35))

    for m in _ASCII_ENTITY_RE.findall(text):
        low = m.lower()
        if low in _GENERIC_BRIDGE_STOPWORDS or len(m) < 2:
            continue
        boost = 1.3 if any(ch.isupper() or ch in "_.-" for ch in m) else 1.0
        found.append((m, boost))

    for span in _CJK_SPAN_RE.findall(text):
        for piece in _CJK_PARTICLE_SPLIT_RE.split(span):
            phrase = piece.strip()
            if 2 <= len(phrase) <= 6 and phrase not in _GENERIC_BRIDGE_STOPWORDS:
                found.append((phrase, 1.0))

    return found


def extract_bridge_terms(
    query: str,
    evidence_texts: Sequence[str],
    *,
    df_lookup: Optional[Callable[[Sequence[str]], Mapping[str, int]]] = None,
    total_docs: int = 0,
    max_terms: int = 4,
) -> List[str]:
    """Select top IDF + co-occurrence weighted bridge terms absent from the original query."""
    if not evidence_texts or max_terms <= 0:
        return []

    query_lower = query.lower()
    query_terms = {t.lower() for t, _ in _extract_true_boundary_terms(query)}
    scores: Counter[str] = Counter()
    canonical: Dict[str, str] = {}

    for doc in evidence_texts:
        if not doc:
            continue
        for sentence in _SENTENCE_SPLIT_RE.split(doc):
            if not sentence.strip():
                continue
            sent_lower = sentence.lower()
            has_query_cooccur = any(qt in sent_lower for qt in query_terms if len(qt) >= 2)
            cooccur_boost = 1.5 if has_query_cooccur else 1.0

            seen_in_sent: set[str] = set()
            for term, entity_boost in _extract_true_boundary_terms(sentence):
                low = term.lower()
                if low in query_terms or low in query_lower or low in seen_in_sent:
                    continue
                seen_in_sent.add(low)
                canonical.setdefault(low, term)
                scores[low] += entity_boost * cooccur_boost

    if not scores:
        return []

    df_map: Mapping[str, int] = {}
    if df_lookup is not None:
        try:
            df_map = df_lookup([canonical[k] for k in scores])
        except Exception as exc:
            logger.debug("Bridge DF lookup skipped: %s", exc)

    n_docs = max(1, total_docs)
    weighted: List[Tuple[float, str]] = []
    for low, base_score in scores.items():
        term = canonical[low]
        df = int(df_map.get(term, 0) or 0)
        idf = math.log((n_docs + 1.0) / (df + 1.0)) + 1.0 if total_docs > 0 else 1.0
        weighted.append((base_score * idf, term))

    weighted.sort(key=lambda pair: (-pair[0], pair[1]))
    return [term for _, term in weighted[:max_terms]]


def _select_gated_evidence(
    candidates: Sequence[Any],
    *,
    min_score: float,
    max_evidence: int = 5,
) -> List[Any]:
    gated = [
        c
        for c in candidates
        if float(getattr(c, "score", 0.0) or 0.0) >= min_score
        and str(getattr(c, "abstract", "") or "").strip()
    ]
    if not gated:
        gated = [c for c in candidates if str(getattr(c, "abstract", "") or "").strip()]
    return list(gated[:max_evidence])


async def run_evidence_hops(
    *,
    query: str,
    initial_candidates: Sequence[Any],
    evidence_hops: int,
    gather_hop_fn: Callable[[str, Set[str]], Awaitable[Sequence[Any]]],
    rank_key: Callable[[Any], Tuple[float, int]],
    excluded: Set[str],
    min_evidence_score: float = 0.0,
    df_lookup: Optional[Callable[[Sequence[str]], Mapping[str, int]]] = None,
    total_docs: int = 0,
    timeout_s: float = 5.0,
) -> Tuple[List[Any], Dict[str, Any]]:
    """Iteratively expand candidates using extracted bridge terms with fail-closed timeout."""
    hops = max(0, min(MAX_EVIDENCE_HOPS, int(evidence_hops or 0)))
    merged: Dict[str, Any] = {}
    for cand in initial_candidates:
        uri = str(getattr(cand, "uri", "") or "")
        if uri:
            merged[uri] = cand

    if hops == 0 or not query.strip() or not merged:
        return list(initial_candidates), {
            "hops_requested": hops,
            "hops_executed": 0,
            "bridge_queries": [],
            "added": 0,
            "status": "off",
        }

    seen_uris: Set[str] = set(excluded) | set(merged.keys())
    used_bridge_terms: Set[str] = set()
    bridge_queries: List[str] = []
    hops_executed = 0
    added_count = 0
    status = "used"

    async def _execute_hops() -> None:
        nonlocal hops_executed, added_count
        frontier = list(merged.values())
        for _ in range(hops):
            evidence = _select_gated_evidence(frontier, min_score=min_evidence_score)
            if not evidence:
                break
            terms = extract_bridge_terms(
                query,
                [str(getattr(c, "abstract", "") or "") for c in evidence],
                df_lookup=df_lookup,
                total_docs=total_docs,
                max_terms=4,
            )
            fresh_terms = [t for t in terms if t.lower() not in used_bridge_terms]
            if not fresh_terms:
                break
            used_bridge_terms.update(t.lower() for t in fresh_terms)
            hop_query = " ".join(fresh_terms)
            bridge_queries.append(hop_query)
            hops_executed += 1

            hop_hits = await gather_hop_fn(hop_query, set(seen_uris))
            new_frontier: List[Any] = []
            for cand in hop_hits:
                uri = str(getattr(cand, "uri", "") or "")
                if not uri or uri in seen_uris:
                    continue
                seen_uris.add(uri)
                merged[uri] = cand
                new_frontier.append(cand)
                added_count += 1
            if not new_frontier:
                break
            frontier = sorted(new_frontier, key=rank_key, reverse=True)

    try:
        await asyncio.wait_for(_execute_hops(), timeout=max(0.1, float(timeout_s)))
    except asyncio.TimeoutError:
        logger.warning("Evidence-hop retrieval timed out after %.2fs; returning gathered hits", timeout_s)
        status = "timeout"
    except Exception as exc:
        logger.warning("Evidence-hop retrieval failed (%s); returning gathered hits", exc)
        status = "failed"

    ordered = sorted(merged.values(), key=rank_key, reverse=True)
    return ordered, {
        "hops_requested": hops,
        "hops_executed": hops_executed,
        "bridge_queries": bridge_queries,
        "added": added_count,
        "status": status,
    }
