# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Rerank pool capping and group rescoring helpers for context assembly."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from openviking.retrieve.context_assembler.params import RERANK_CANDIDATE_MULTIPLIER
from openviking.retrieve.rerank_scoring import Reranker, RerankScores
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)


def cap_rerank_pool(
    active: Sequence[Tuple[str, int]],
    buckets: Sequence[List[Any]],
    rank_key: Callable[[Any], Tuple[float, int]],
) -> Tuple[List[List[Any]], int]:
    """Bound rerank input to ``RERANK_CANDIDATE_MULTIPLIER`` x quota per bucket."""
    kept = [
        found[: quota * RERANK_CANDIDATE_MULTIPLIER]
        for (_, quota), found in zip(active, buckets, strict=True)
    ]
    rest = sorted(
        (
            (index, candidate)
            for index, found in enumerate(buckets)
            for candidate in found[len(kept[index]) :]
        ),
        key=lambda pair: rank_key(pair[1]),
        reverse=True,
    )
    room = sum(quota for _, quota in active) * RERANK_CANDIDATE_MULTIPLIER
    room = max(0, room - sum(len(found) for found in kept))
    for index, candidate in rest[:room]:
        kept[index].append(candidate)
    return kept, max(0, len(rest) - room)


async def rerank_groups(
    reranker: Reranker,
    query: str,
    groups: Sequence[List[Any]],
    score_threshold: Optional[float],
    rank_key: Callable[[Any], Tuple[float, int]],
) -> Tuple[List[List[Any]], Dict[str, Any]]:
    """Rescore every group with one rerank call over their distinct candidates."""
    pool: Dict[str, Any] = {}
    for group in groups:
        for candidate in group:
            pool.setdefault(candidate.uri, candidate)
    unique = list(pool.values())
    fallback = [candidate.score for candidate in unique]
    try:
        result = await reranker.score(query, [c.abstract for c in unique], fallback)
    except Exception as exc:
        logger.warning("Context rerank failed, keeping vector scores: %s", exc)
        result = RerankScores(fallback, [False] * len(unique))

    kept: Dict[str, Any] = {}
    for candidate, score, from_model in zip(unique, result.scores, result.reranked, strict=True):
        threshold = score_threshold
        if threshold is None:
            threshold = reranker.threshold if from_model else 0.0
        if score > threshold:
            penalty = candidate.score - candidate.ranked_score
            kept[candidate.uri] = replace(candidate, score=score, ranked_score=score - penalty)
    rescored = [
        sorted((kept[c.uri] for c in group if c.uri in kept), key=rank_key, reverse=True)
        for group in groups
    ]
    return rescored, {"used": result.model_used, "candidates": len(unique)}
