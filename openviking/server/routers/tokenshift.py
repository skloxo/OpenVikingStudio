# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""TokenShift AST-Aware Code Compression REST API Router.

Endpoints:
  POST /api/v1/tokenshift/compress     <- Compress source code preserving AST syntax
  POST /api/v1/tokenshift/protect      <- Extract AST nodes and frozen signatures
  GET  /api/v1/tokenshift/stats        <- Query telemetry metrics (tokens saved, pass rate)
  POST /api/v1/tokenshift/reset-stats  <- Reset telemetry metrics
  GET  /api/v1/tokenshift/files        <- Scan real codebase files for picker
  GET  /api/v1/tokenshift/file         <- Read real source file content
  POST /api/v1/tokenshift/apply        <- Persist compressed code with snapshot
"""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.tokenshift_apply import (
    ApplyTokenShiftRequest,
    ApplyTokenShiftResult,
    CodeFileItem,
    TokenShiftApplyService,
)
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


@router.get("/files", response_model=List[CodeFileItem])
async def list_code_files(
    search: Optional[str] = Query(default=None, description="Search keyword in filename or path"),
    language: Optional[str] = Query(default=None, description="Language filter (python, typescript, etc.)"),
    limit: int = Query(default=50, ge=1, le=200, description="Max items to return"),
    ctx: RequestContext = Depends(get_request_context),
) -> List[CodeFileItem]:
    """Scan and list real codebase files across openviking, src, tests, scripts."""
    service = TokenShiftApplyService()
    return service.list_code_files(search=search, language=language, limit=limit)


@router.get("/file")
async def read_code_file(
    path: str = Query(..., description="Project-relative path of the code file"),
    ctx: RequestContext = Depends(get_request_context),
) -> dict:
    """Read source code file content safely."""
    service = TokenShiftApplyService()
    try:
        return service.read_code_file(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read code file: {exc}")


@router.post("/apply", response_model=ApplyTokenShiftResult)
async def apply_compressed_code(
    req: ApplyTokenShiftRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> ApplyTokenShiftResult:
    """Persist compressed code to disk with AST syntax gate and quarantine snapshotting."""
    service = TokenShiftApplyService()
    try:
        return service.apply_compression(req)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist compressed code: {exc}")
