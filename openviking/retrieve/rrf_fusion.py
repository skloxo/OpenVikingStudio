# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Reciprocal Rank Fusion (RRF) Engine for Hybrid Dense-Sparse Retrieval.

Key Principles:
1. Non-Parametric Rank Fusion: Combines dense vector similarity and sparse BM25 scores.
2. Standard Constant k=60: Industry consensus (Cormack et al.) preventing top ranks from dominating.
3. Provenance Tracking: Accurately labels each candidate as 'hybrid', 'dense_only', or 'sparse_only'.
4. Linear Complexity: O(N log N) rank merge with zero extra dependencies.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FusedCandidate(BaseModel):
    """Hybrid candidate fused from dense and sparse rankings."""
    uri: str
    title: str = ""
    level: int = 2
    context_type: str = "resource"
    snippet: str = ""
    origin: str = "dense_only"  # "hybrid" | "dense_only" | "sparse_only"
    dense_rank: Optional[int] = None
    sparse_rank: Optional[int] = None
    dense_score: float = 0.0
    bm25_score: float = 0.0
    rrf_score: float = 0.0
    fused_rank: int = 0
    extra_metadata: Dict[str, Any] = Field(default_factory=dict)


def rrf_fuse(
    dense_results: List[Dict[str, Any]],
    sparse_results: List[Dict[str, Any]],
    k: int = 60,
    top_k: int = 10,
    dense_weight: float = 1.0,
    sparse_weight: float = 1.0,
) -> List[FusedCandidate]:
    """
    Perform Reciprocal Rank Fusion on dense and sparse results.

    Args:
        dense_results: Ordered list of dicts with 'uri', 'score' (higher is better)
        sparse_results: Ordered list of dicts with 'uri', 'score'/'bm25_score'
        k: Smoothing constant (standard k=60)
        top_k: Maximum number of fused items to return
        dense_weight: Weight multiplier for dense stream
        sparse_weight: Weight multiplier for sparse BM25 stream

    Returns:
        Sorted list of FusedCandidate ordered by descending rrf_score.
    """
    candidates_by_uri: Dict[str, FusedCandidate] = {}

    # 1. Ingest Dense Stream
    for rank, item in enumerate(dense_results, start=1):
        uri = item.get("uri") or item.get("id")
        if not uri:
            continue

        dense_score = float(item.get("score") or item.get("similarity") or 0.0)
        rrf_contrib = dense_weight / (k + rank)

        candidates_by_uri[uri] = FusedCandidate(
            uri=uri,
            title=item.get("title") or item.get("name") or "",
            level=int(item.get("level", 2)),
            context_type=item.get("context_type", "resource"),
            snippet=item.get("snippet") or item.get("abstract") or item.get("text") or "",
            origin="dense_only",
            dense_rank=rank,
            dense_score=dense_score,
            rrf_score=rrf_contrib,
            extra_metadata={
                k_meta: v_meta
                for k_meta, v_meta in item.items()
                if k_meta not in ("uri", "title", "level", "context_type", "snippet", "score")
            },
        )

    # 2. Ingest Sparse BM25 Stream
    for rank, item in enumerate(sparse_results, start=1):
        uri = item.get("uri") or item.get("id")
        if not uri:
            continue

        sparse_score = float(item.get("bm25_score") or item.get("score") or 0.0)
        rrf_contrib = sparse_weight / (k + rank)

        if uri in candidates_by_uri:
            cand = candidates_by_uri[uri]
            cand.origin = "hybrid"
            cand.sparse_rank = rank
            cand.bm25_score = sparse_score
            cand.rrf_score += rrf_contrib
            if not cand.snippet and (item.get("snippet") or item.get("text")):
                cand.snippet = item.get("snippet") or item.get("text") or ""
        else:
            candidates_by_uri[uri] = FusedCandidate(
                uri=uri,
                title=item.get("title") or item.get("name") or "",
                level=int(item.get("level", 2)),
                context_type=item.get("context_type", "resource"),
                snippet=item.get("snippet") or item.get("text") or "",
                origin="sparse_only",
                sparse_rank=rank,
                bm25_score=sparse_score,
                rrf_score=rrf_contrib,
                extra_metadata={
                    k_meta: v_meta
                    for k_meta, v_meta in item.items()
                    if k_meta not in ("uri", "title", "level", "context_type", "snippet", "bm25_score", "score")
                },
            )

    # 3. Sort by rrf_score descending
    sorted_candidates = sorted(
        candidates_by_uri.values(),
        key=lambda c: c.rrf_score,
        reverse=True,
    )

    # 4. Assign fused ranks
    for final_rank, cand in enumerate(sorted_candidates[:top_k], start=1):
        cand.fused_rank = final_rank
        cand.rrf_score = round(cand.rrf_score, 6)

    return sorted_candidates[:top_k]
