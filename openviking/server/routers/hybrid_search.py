# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
REST Endpoints for Hybrid BM25-Dense Retrieval & Real-Time Diagnostics.
(Card-Retrieval-BM25Hybrid / v1.5.16)
"""

import logging
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.storage.bm25_fts_index import BM25FTSIndex, BM25Match
from openviking.retrieve.rrf_fusion import FusedCandidate, rrf_fuse
from openviking.retrieve.hybrid_retriever import HybridRetrievalTelemetry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["hybrid_search"])


class HybridSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=100)
    target_directories: Optional[List[str]] = None
    context_type: Optional[str] = None
    dense_candidates: Optional[List[Dict[str, Any]]] = None
    k: int = Field(default=60, ge=1, le=200)


class HybridProbeRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=20)


class IndexDocRequest(BaseModel):
    uri: str
    title: str = ""
    content: str
    level: int = 2
    context_type: str = "resource"


@router.get("/api/v1/search/hybrid_metrics")
@router.get("/api/v1/search/hybrid/metrics")
async def get_hybrid_metrics(_ctx: RequestContext = Depends(get_request_context)):
    """Get aggregate hybrid retrieval performance metrics."""
    bm25 = BM25FTSIndex.get_instance()
    telemetry = HybridRetrievalTelemetry.get_instance()
    stats = bm25.get_stats()
    snapshot = telemetry.get_snapshot(is_bm25_ready=stats.is_ready)

    return JSONResponse(
        status_code=200,
        content={
            "telemetry": snapshot.model_dump(),
            "index_stats": stats.model_dump(),
        },
    )


@router.post("/api/v1/search/hybrid_probe")
@router.post("/api/v1/search/hybrid/probe")
async def run_hybrid_probe(
    req: HybridProbeRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """
    Run comparative probe on a test query:
    Executes Sparse BM25, simulated Dense matches, and RRF Fusion to evaluate exact symbol recall.
    """
    t0 = time.monotonic()
    bm25 = BM25FTSIndex.get_instance()
    sparse_matches: List[BM25Match] = bm25.search(req.query, limit=req.limit)

    # Query real dense vector candidates via service search.find, or empty list
    dense_results: List[Dict[str, Any]] = []
    try:
        from openviking.server.dependencies import get_service

        service = get_service()
        if service and hasattr(service, "search"):
            find_res = await service.search.find(
                query=req.query,
                ctx=_ctx,
                limit=req.limit,
            )
            find_dict = (
                find_res.to_dict()
                if hasattr(find_res, "to_dict")
                else (find_res if isinstance(find_res, dict) else {})
            )
            all_hits = (
                find_dict.get("resources", [])
                + find_dict.get("memories", [])
                + find_dict.get("skills", [])
            )
            for hit in all_hits:
                dense_results.append({
                    "uri": hit.get("uri", ""),
                    "title": hit.get("title") or (hit.get("uri", "").split("/")[-1] if hit.get("uri") else ""),
                    "score": float(hit.get("score", 0.0)),
                    "snippet": hit.get("abstract") or (hit.get("content", "")[:120] if hit.get("content") else ""),
                    "level": int(hit.get("level", 1) or 1),
                })
    except Exception as e:
        logger.debug(f"Dense vector probe search bypassed: {e}")

    sparse_dicts = [
        {
            "uri": m.uri,
            "title": m.title,
            "level": m.level,
            "context_type": m.context_type,
            "bm25_score": m.bm25_score,
            "snippet": m.snippet,
        }
        for m in sparse_matches
    ]

    fused = rrf_fuse(dense_results=dense_results, sparse_results=sparse_dicts, top_k=req.limit)
    latency_ms = (time.monotonic() - t0) * 1000.0

    # Record probe in telemetry
    overlap_cnt = sum(1 for f in fused if f.origin == "hybrid")
    dense_only_cnt = sum(1 for f in fused if f.origin == "dense_only")
    sparse_only_cnt = sum(1 for f in fused if f.origin == "sparse_only")
    symbol_boost = any(f.origin == "sparse_only" and f.fused_rank <= 3 for f in fused)
    telemetry = HybridRetrievalTelemetry.get_instance()
    telemetry.record(
        dense_count=len(dense_results),
        sparse_count=len(sparse_matches),
        fused_count=len(fused),
        overlap_count=overlap_cnt,
        symbol_boost=symbol_boost,
        latency_ms=latency_ms,
        dense_only=dense_only_cnt,
        sparse_only=sparse_only_cnt,
    )

    return JSONResponse(
        status_code=200,
        content={
            "query": req.query,
            "sparse_bm25_count": len(sparse_matches),
            "dense_count": len(dense_results),
            "fused_count": len(fused),
            "latency_ms": round(latency_ms, 2),
            "sparse_results": [m.model_dump() for m in sparse_matches],
            "dense_results": dense_results,
            "fused_results": [f.model_dump() for f in fused],
        },
    )


@router.post("/api/v1/search/hybrid_index_doc")
@router.post("/api/v1/search/hybrid/index_doc")
async def index_document_for_hybrid(
    req: IndexDocRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Index a single document into the SQLite FTS5 BM25 engine."""
    bm25 = BM25FTSIndex.get_instance()
    ok = bm25.index_document(
        uri=req.uri,
        title=req.title,
        content=req.content,
        level=req.level,
        context_type=req.context_type,
    )
    return JSONResponse(status_code=200 if ok else 400, content={"success": ok, "uri": req.uri})
