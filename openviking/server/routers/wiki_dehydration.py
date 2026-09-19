# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""REST Endpoints for Wiki Dehydration & LLMLingua-2 Adapter.

(Card-LLMLingua-01 / v1.5.46)
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.wiki_dehydration_engine import (
    DehydrationRequest,
    DehydrationResult,
    DehydrationTelemetry,
    WikiDehydrationEngine,
)
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/wiki/dehydrate", tags=["wiki-dehydration"])


class BatchDehydrateRequest(BaseModel):
    """Batch request containing multiple wiki documents or sections."""
    documents: List[str] = Field(..., description="List of document contents to dehydrate")
    target_rate: float = Field(default=0.50, ge=0.10, le=0.90)


class BatchDehydrateResponse(BaseModel):
    """Batch response payload."""
    results: List[DehydrationResult]
    total_tokens_saved: int
    batch_count: int


@router.post("", response_model=DehydrationResult)
async def dehydrate_document(
    req: DehydrationRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> DehydrationResult:
    """Execute LLMLingua-2 / rule-based dehydration on a single Wiki markdown document."""
    engine = WikiDehydrationEngine.get_instance()
    res = engine.dehydrate(req)
    logger.info(
        f"Wiki dehydration completed: {res.original_tokens} -> {res.dehydrated_tokens} tokens "
        f"({res.compression_ratio:.1%}, saved={res.tokens_saved}, engine={res.engine_used})"
    )
    return res


@router.post("/batch", response_model=BatchDehydrateResponse)
async def batch_dehydrate(
    req: BatchDehydrateRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> BatchDehydrateResponse:
    """Execute batch dehydration on multiple wiki sections or documents."""
    engine = WikiDehydrationEngine.get_instance()
    results: List[DehydrationResult] = []
    total_saved = 0

    for doc in req.documents:
        r = engine.dehydrate(DehydrationRequest(content=doc, target_rate=req.target_rate))
        results.append(r)
        total_saved += r.tokens_saved

    return BatchDehydrateResponse(
        results=results,
        total_tokens_saved=total_saved,
        batch_count=len(results),
    )


@router.get("/stats", response_model=DehydrationTelemetry)
async def get_dehydration_stats(
    ctx: RequestContext = Depends(get_request_context),
) -> DehydrationTelemetry:
    """Retrieve cumulative telemetry metrics for wiki dehydration engine."""
    engine = WikiDehydrationEngine.get_instance()
    return engine.get_telemetry()
