# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""TokenShift AST-Aware Code Compression REST API Router.

Endpoints:
  POST /api/v1/tokenshift/compress     <- Compress source code preserving AST syntax
  POST /api/v1/tokenshift/protect      <- Extract AST nodes and frozen signatures
  GET  /api/v1/tokenshift/stats        <- Query telemetry metrics (tokens saved, pass rate)
  POST /api/v1/tokenshift/reset-stats  <- Reset telemetry metrics
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.tokenshift_engine import TokenShiftEngine, TokenShiftTelemetry
from openviking.service.tokenshift_types import (
    TokenShiftLanguage,
    TokenShiftProtectResult,
    TokenShiftRequest,
    TokenShiftResult,
    TokenShiftStats,
)

router = APIRouter(prefix="/api/v1/tokenshift", tags=["tokenshift"])


class ProtectCodeRequest(BaseModel):
    model_config = ConfigDict(strict=False)
    code: str = Field(..., description="Source code to analyze")
    language: TokenShiftLanguage = Field(default=TokenShiftLanguage.AUTO, description="Language hint")


@router.post("/compress", response_model=TokenShiftResult)
async def compress_code(
    req: TokenShiftRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> TokenShiftResult:
    """Execute PointFive AST-aware code compression with syntax validation gate."""
    return TokenShiftEngine.compress(req)


@router.post("/protect", response_model=TokenShiftProtectResult)
async def protect_code(
    req: ProtectCodeRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> TokenShiftProtectResult:
    """Extract and analyze protected AST symbols and signatures."""
    return TokenShiftEngine.protect(req.code, req.language)


@router.get("/stats", response_model=TokenShiftStats)
async def get_tokenshift_stats(
    ctx: RequestContext = Depends(get_request_context),
) -> TokenShiftStats:
    """Query cumulative compression metrics and token savings."""
    return TokenShiftTelemetry.get_instance().get_stats()


@router.post("/reset-stats")
async def reset_tokenshift_stats(
    ctx: RequestContext = Depends(get_request_context),
) -> dict:
    """Reset telemetry statistics."""
    TokenShiftTelemetry.get_instance().reset()
    return {"status": "ok", "message": "TokenShift stats reset successfully"}
