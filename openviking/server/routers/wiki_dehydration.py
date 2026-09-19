# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""REST Endpoints for Microsoft LLMLingua-2 Wiki Dehydration Engine.

(Card-LLMLingua-01 / v1.5.46)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.wiki_dehydration_engine import (
    DehydrationRequest,
    DehydrationResult,
    DehydrationStats,
    WikiDehydrationEngine,
)
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/wiki/dehydrate", tags=["wiki-dehydrate"])


class BatchDehydrationRequest(BaseModel):
    documents: Optional[List[str]] = Field(None, description="List of markdown or wiki documents")
    items: Optional[List[str]] = Field(None, description="Alternative key for document chunks")
    target_rate: Optional[float] = Field(None, description="Target compression rate")
    rate: Optional[float] = Field(None, description="Alternative target compression rate")

    @property
    def doc_list(self) -> List[str]:
        if self.documents is not None:
            return self.documents
        if self.items is not None:
            return self.items
        return []

    @property
    def effective_rate(self) -> float:
        if self.target_rate is not None:
            return self.target_rate
        if self.rate is not None:
            return self.rate
        return 0.50


class BatchDehydrationResponse(BaseModel):
    batch_count: int
    results: List[DehydrationResult]
    total_tokens_saved: int
    avg_latency_ms: float


@router.post("", response_model=DehydrationResult)
async def dehydrate_document(
    req: DehydrationRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> DehydrationResult:
    """Execute LLMLingua-2 structural dehydration on a wiki or markdown document."""
    engine = WikiDehydrationEngine.get_instance()
    result = engine.dehydrate(req)
    logger.info(
        f"WikiDehydration processed {result.original_chars} -> {result.compressed_chars} chars "
        f"({result.compression_ratio:.1f}%), saved {result.tokens_saved} tokens "
        f"via {result.engine_used} in {result.latency_ms}ms"
    )
    return result


@router.post("/batch", response_model=BatchDehydrationResponse)
async def batch_dehydrate_documents(
    req: BatchDehydrationRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> BatchDehydrationResponse:
    """Batch dehydrate multiple markdown chunks or wiki sections."""
    engine = WikiDehydrationEngine.get_instance()
    results: List[DehydrationResult] = []
    total_saved = 0
    total_lat = 0.0

    docs = req.doc_list
    for doc in docs:
        r = engine.dehydrate(DehydrationRequest(content=doc, rate=req.effective_rate))
        results.append(r)
        total_saved += r.tokens_saved
        total_lat += r.latency_ms

    avg_lat = round(total_lat / len(docs), 2) if docs else 0.0
    return BatchDehydrationResponse(
        batch_count=len(docs),
        results=results,
        total_tokens_saved=total_saved,
        avg_latency_ms=avg_lat,
    )


@router.get("/stats", response_model=DehydrationStats)
async def get_dehydration_stats(
    ctx: RequestContext = Depends(get_request_context),
) -> DehydrationStats:
    """Retrieve runtime observability metrics and active engine state."""
    engine = WikiDehydrationEngine.get_instance()
    return engine.get_stats()
