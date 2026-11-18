# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Zero-embedding BM25 fast-path helpers for GlobalHybridRetriever."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional, Tuple

from openviking.storage.bm25_fts_index import BM25FTSIndex, BM25Match
from openviking.storage.vikingdb_manager import VikingDBManager
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

BM25_FAST_MODES = frozenset({"bm25_fast", "zero_embedding"})


def is_bm25_fast_mode(mode: Any, image_query: Any = None) -> bool:
    """Return True when retrieval mode requests zero-embedding BM25 fast search."""
    if image_query:
        return False
    return str(mode or "").strip().lower() in BM25_FAST_MODES


async def search_bm25_candidates(
    bm25_index: Optional[BM25FTSIndex],
    vector_store: Any,
    query: str,
    limit: int,
    ctx_type: Optional[str],
    target_dirs: Optional[List[str]],
    level: Optional[List[int]] = None,
    allow_unbounded_singleton: bool = False,
) -> Tuple[List[Dict[str, Any]], bool, Optional[BM25FTSIndex]]:
    """Run FTS5 BM25 recall without requiring a vector store in bm25_fast mode."""
    resolved = bm25_index
    if resolved is None:
        in_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        if allow_unbounded_singleton:
            if in_pytest and BM25FTSIndex._instance is None:
                return [], False, None
        elif not isinstance(vector_store, VikingDBManager) or in_pytest:
            return [], False, None
        try:
            resolved = BM25FTSIndex.get_instance()
        except Exception:
            return [], False, None

    try:
        matches: List[BM25Match] = await asyncio.to_thread(
            resolved.search,
            query=query,
            limit=limit,
            context_type=ctx_type,
            target_directories=target_dirs,
        )
        candidates = [
            {
                "uri": m.uri,
                "title": m.title,
                "level": m.level,
                "context_type": m.context_type,
                "bm25_score": m.bm25_score,
                "snippet": m.snippet,
                "abstract": m.snippet or m.title,
            }
            for m in matches
            if level is None or m.level in level
        ]
        return candidates, True, resolved
    except Exception as exc:
        logger.warning(f"[GlobalHybridRetriever] BM25 FTS5 search fail-open degraded: {exc}")
        return [], False, resolved


def format_bm25_fast_results(
    sparse_candidates: List[Dict[str, Any]],
    limit: int,
    is_bm25_ready: bool,
) -> List[Dict[str, Any]]:
    """Normalize BM25 candidates for downstream decay and MatchedContext conversion."""
    ordered = sorted(
        sparse_candidates,
        key=lambda item: float(item.get("bm25_score", 0.0) or 0.0),
        reverse=True,
    )
    results: List[Dict[str, Any]] = []
    for item in ordered[: max(1, limit)]:
        score = float(item.get("bm25_score", 0.0) or 0.0)
        results.append(
            {
                **item,
                "_score": score,
                "extra_metadata": {
                    "origin": "bm25_fast",
                    "bm25_score": score,
                    "is_bm25_ready": is_bm25_ready,
                },
            }
        )
    return results
