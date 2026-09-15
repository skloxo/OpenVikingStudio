# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
REST Endpoints for zg (zvec-grep) Code Semantic Search & TieredLazyFetch.
(Card-Retrieval-LocalFirst-zgSemanticSearch / v1.5.17)
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.search.zg_engine import ZGSearchEngine
from openviking.search.tiered_fetch import TierLevel

router = APIRouter(tags=["zg_search"])


class ZGSearchRequest(BaseModel):
    query: str
    depth: int = Field(default=1, ge=0, le=3)
    limit: int = Field(default=10, ge=1, le=50)
    path_filter: Optional[str] = None


class ZGFetchRequest(BaseModel):
    fingerprint: str
    depth: int = Field(default=2, ge=0, le=3)


@router.get("/api/v1/search/zg/stats")
async def get_zg_stats(_ctx: RequestContext = Depends(get_request_context)):
    """Get zg engine index and line coverage statistics."""
    engine = ZGSearchEngine.get_instance()
    stats = engine.get_stats()
    return JSONResponse(status_code=200, content=stats.model_dump())


@router.post("/api/v1/search/zg/search")
async def search_zg_symbols(
    req: ZGSearchRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """
    Search codebase symbols with quartet ranking and TieredLazyFetch output.
    Enforces depth=0/1/2 token hygiene.
    """
    engine = ZGSearchEngine.get_instance()
    summary = engine.search(
        query=req.query,
        depth=req.depth,
        limit=req.limit,
        path_filter=req.path_filter,
    )
    return JSONResponse(status_code=200, content=summary.model_dump())


@router.post("/api/v1/search/zg/fetch")
async def fetch_zg_symbol(
    req: ZGFetchRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Fetch exact symbol by anchor fingerprint at desired depth (0/1/2)."""
    engine = ZGSearchEngine.get_instance()
    result = engine.fetch_by_fingerprint(
        fingerprint=req.fingerprint,
        depth=req.depth,
    )
    if not result:
        return JSONResponse(
            status_code=404,
            content={"error": "Symbol fingerprint not found", "fingerprint": req.fingerprint},
        )
    return JSONResponse(status_code=200, content=result)


@router.post("/api/v1/search/zg/reindex")
async def reindex_zg_codebase(
    _ctx: RequestContext = Depends(get_request_context),
):
    """Trigger AST rescan of codebase and update FTS5 index."""
    engine = ZGSearchEngine.get_instance()
    count = engine.index_directory(max_files=300)
    stats = engine.get_stats()
    return JSONResponse(
        status_code=200,
        content={"indexed_symbols": count, "stats": stats.model_dump()},
    )
