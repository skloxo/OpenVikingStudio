# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
zg (zvec-grep) Code Semantic Search REST Router.
Exposes POST /api/v1/search/zg, GET /api/v1/search/zg/stats, and POST /api/v1/search/zg/reindex.
(Card-Retrieval-LocalFirst-zgSemanticSearch / v1.5.30)
"""

import asyncio
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from openviking.search.tiered_fetch import TieredFetchSummary, TierLevel
from openviking.search.zg_engine import ZGSearchEngine, ZGStats
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/search/zg", tags=["zg-search"])

# Global in-memory query and token savings telemetry for the cockpit widget
_TELEMETRY_LOCK = asyncio.Lock()
_TOTAL_ZG_QUERIES = 0
_TOTAL_TOKENS_SAVED = 0
_DEPTH_DISTRIBUTION = {0: 0, 1: 0, 2: 0}


class ZGSearchRequest(BaseModel):
    """Payload for zg code semantic search."""
    query: str = Field(..., min_length=1, description="Code symbol or semantic query")
    depth: int = Field(1, ge=0, le=3, description="TieredLazyFetch depth: 0=Meta, 1=Fingerprint (default), 2=Full block")
    limit: int = Field(10, ge=1, le=50, description="Max symbols to return")
    path_filter: Optional[str] = Field(None, description="Optional path substring filter")


class ZGStatsResponse(BaseModel):
    """Aggregate statistics for the zg engine and token shield."""
    total_symbols: int
    total_files: int
    total_lines: int
    avg_lines_per_symbol: float
    is_ready: bool
    last_indexed_ts: float
    total_queries: int
    total_tokens_saved: int
    depth_distribution: Dict[int, int]
    avg_savings_ratio: float


@router.post("", response_model=Dict[str, Any])
async def search_zg(
    req: ZGSearchRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Execute local-first AST code semantic search with TieredLazyFetch depth formatting."""
    global _TOTAL_ZG_QUERIES, _TOTAL_TOKENS_SAVED, _DEPTH_DISTRIBUTION

    engine = ZGSearchEngine.get_instance()
    summary: TieredFetchSummary = await asyncio.to_thread(
        engine.search,
        query=req.query,
        depth=req.depth,
        limit=req.limit,
        path_filter=req.path_filter,
    )

    # Accumulate telemetry for frontend cockpit
    async with _TELEMETRY_LOCK:
        _TOTAL_ZG_QUERIES += 1
        _TOTAL_TOKENS_SAVED += summary.total_tokens_saved
        effective_depth = min(2, max(0, req.depth))
        _DEPTH_DISTRIBUTION[effective_depth] = _DEPTH_DISTRIBUTION.get(effective_depth, 0) + 1

    return {
        "status": "ok",
        "result": summary.model_dump(),
        "error": None,
    }


@router.get("/stats", response_model=Dict[str, Any])
async def get_zg_stats(
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Return zg code index statistics and cumulative token shield telemetry."""
    engine = ZGSearchEngine.get_instance()
    stats: ZGStats = engine.get_stats()

    async with _TELEMETRY_LOCK:
        tot_queries = _TOTAL_ZG_QUERIES
        tot_saved = _TOTAL_TOKENS_SAVED
        depth_dist = dict(_DEPTH_DISTRIBUTION)

    # Estimate average token savings ratio based on depth distribution
    # depth=0: ~95% savings, depth=1: ~80% savings, depth=2: 0% savings
    if tot_queries > 0:
        weighted_savings = (depth_dist.get(0, 0) * 0.95 + depth_dist.get(1, 0) * 0.80) / max(1, tot_queries)
    else:
        weighted_savings = 0.82  # Baseline theoretical ~82% savings for depth=1

    stats_dict = ZGStatsResponse(
        total_symbols=stats.total_symbols,
        total_files=stats.total_files,
        total_lines=stats.total_lines,
        avg_lines_per_symbol=stats.avg_lines_per_symbol,
        is_ready=stats.is_ready,
        last_indexed_ts=stats.last_indexed_ts,
        total_queries=tot_queries,
        total_tokens_saved=tot_saved,
        depth_distribution=depth_dist,
        avg_savings_ratio=round(weighted_savings, 3),
    ).model_dump()

    return {
        "status": "ok",
        "result": stats_dict,
        "error": None,
    }


@router.post("/reindex", response_model=Dict[str, Any])
async def trigger_zg_reindex(
    max_files: int = Query(500, ge=10, le=2000),
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Trigger background AST scanning and index refresh."""
    engine = ZGSearchEngine.get_instance()
    indexed_count = await asyncio.to_thread(engine.index_directory, max_files=max_files)
    stats = engine.get_stats()

    return {
        "status": "ok",
        "result": {
            "indexed_symbols": indexed_count,
            "total_symbols": stats.total_symbols,
            "total_files": stats.total_files,
            "is_ready": stats.is_ready,
        },
        "error": None,
    }
