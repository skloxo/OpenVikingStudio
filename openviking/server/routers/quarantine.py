# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Quarantine audit and restoration probe endpoints (Card-Observability-MemoryQuarantine-Dashboard / v1.5.10)."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from openviking.core.quarantine_manager import QuarantineManager
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext

router = APIRouter(tags=["quarantine"])


class RestoreDryRunRequest(BaseModel):
    batch_id: str
    item_name: str


@router.get("/api/v1/memory/quarantine_manifest")
@router.get("/api/v1/memory/quarantine/manifest")
async def get_quarantine_manifest(
    search: Optional[str] = Query(None, description="Keyword search in item name or source"),
    category: Optional[str] = Query(None, description="Filter by category (zombie_sessions, cold_staging_sessions)"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=500, description="Page limit"),
    force_refresh: bool = Query(False, description="Force disk rescan"),
    _ctx: RequestContext = Depends(get_request_context),
):
    """
    Get aggregate net entropy reduction metrics and paginated quarantine manifest.
    Provides verifiable proof that quarantined items are safely cold-archived.
    """
    manager = QuarantineManager.get_instance()
    snapshot = manager.get_snapshot(
        search=search,
        category=category,
        offset=offset,
        limit=limit,
        force_refresh=force_refresh,
    )
    return JSONResponse(status_code=200, content=snapshot.model_dump())


@router.post("/api/v1/memory/quarantine_restore_dry_run")
@router.post("/api/v1/memory/quarantine/restore_dry_run")
async def restore_dry_run_probe(
    req: RestoreDryRunRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """
    Execute read-only dry-run restoration validation probe.
    Verifies destination archive integrity and target restore path without modifying live data.
    """
    manager = QuarantineManager.get_instance()
    result = manager.dry_run_restore(batch_id=req.batch_id, item_name=req.item_name)
    return JSONResponse(status_code=200, content=result.model_dump())
