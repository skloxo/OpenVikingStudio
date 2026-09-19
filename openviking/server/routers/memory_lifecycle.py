# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
REST Endpoints for Memory Lifecycle State Machine & Lineage Tracking.
(Card-Memory-LifecycleFSM / v1.5.32)

First Principles:
1. "Zero silent coexistence": Old memories superseded by newer insights are explicitly linked and demoted.
2. Fast and Deterministic: O(1) state transitions with lineage graph traversal.
3. Observability & Lineage: Exposes forward/backward pointers for UI cockpit visualization.
"""

import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.memory_lifecycle_fsm import (
    MemoryLifecycleFSM,
    MemoryLifecycleRecord,
    MemoryStatus,
    LifecycleTransitionEvent,
    InvalidLifecycleTransitionError,
    _LIFECYCLE_REGISTRY,
    get_or_create_lifecycle_record,
)
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/memory", tags=["memory-lifecycle"])

# Backward-compatible alias
_get_or_create_record = get_or_create_lifecycle_record


class TransitionStatusRequest(BaseModel):
    uri: str = Field(..., description="Target memory URI to transition")
    event: LifecycleTransitionEvent = Field(..., description="Transition event: dispute, resolve, supersede, revert")
    target_uri: Optional[str] = Field(None, description="Successor memory URI (required for supersede)")
    reason: Optional[str] = Field(None, description="Contextual reason or audit explanation")


class LinkPairRequest(BaseModel):
    old_uri: str = Field(..., description="Existing superseded memory URI")
    new_uri: str = Field(..., description="New authoritative successor memory URI")
    reason: Optional[str] = Field("Superseded by verified newer revision", description="Reason for superseding")


@router.post("/status")
async def transition_memory_status(
    req: TransitionStatusRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """
    Transition a memory item's lifecycle status (active/disputed/superseded).
    """
    current_record = _get_or_create_record(req.uri)
    try:
        updated = MemoryLifecycleFSM.transition(
            record=current_record,
            event=req.event,
            target_uri=req.target_uri,
            reason=req.reason,
        )
        _LIFECYCLE_REGISTRY[req.uri] = updated

        logger.info(
            f"Memory lifecycle transition successful: uri={req.uri}, "
            f"from={current_record.status.value} to={updated.status.value}, event={req.event.value}"
        )
        return {"status": "ok", "result": updated.to_dict()}
    except InvalidLifecycleTransitionError as e:
        logger.warning(f"Invalid memory lifecycle transition rejected: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to transition memory status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post("/link")
async def link_superseded_pair(
    req: LinkPairRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """
    Atomically link an old superseded memory to a new successor memory.
    """
    old_record = _get_or_create_record(req.old_uri)
    try:
        updated_old, new_rec = MemoryLifecycleFSM.link_superseded_pair(
            old_record=old_record,
            new_uri=req.new_uri,
            reason=req.reason or "Superseded by newer knowledge",
        )
        _LIFECYCLE_REGISTRY[req.old_uri] = updated_old
        _LIFECYCLE_REGISTRY[req.new_uri] = new_rec

        logger.info(f"Memory linked: {req.old_uri} -> superseded_by -> {req.new_uri}")
        return {
            "status": "ok",
            "result": {
                "old_record": updated_old.to_dict(),
                "new_record": new_rec.to_dict(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to link memory pair: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/lineage")
async def get_memory_lineage(
    uri: str = Query(..., description="Target memory URI to trace"),
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """
    Trace predecessor and successor lineage pointers for a specific memory URI.
    """
    clean_uri = uri.strip()
    _get_or_create_record(clean_uri)
    lineage = MemoryLifecycleFSM.build_lineage_chain(clean_uri, _LIFECYCLE_REGISTRY)
    return {"status": "ok", "result": lineage}


@router.get("/records")
async def list_lifecycle_records(
    status: Optional[str] = Query(None, description="Optional filter: active, disputed, superseded"),
    limit: int = Query(50, ge=1, le=200),
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """
    List registered memory lifecycle records with optional status filtering.
    """
    items = list(_LIFECYCLE_REGISTRY.values())
    if status:
        stat_lower = status.lower()
        items = [r for r in items if r.status.value == stat_lower]

    items.sort(key=lambda r: r.updated_at, reverse=True)
    results = [r.to_dict() for r in items[:limit]]

    return {
        "status": "ok",
        "result": {
            "total": len(items),
            "records": results,
            "status_counts": {
                "active": sum(1 for r in _LIFECYCLE_REGISTRY.values() if r.status == MemoryStatus.ACTIVE),
                "disputed": sum(1 for r in _LIFECYCLE_REGISTRY.values() if r.status == MemoryStatus.DISPUTED),
                "superseded": sum(1 for r in _LIFECYCLE_REGISTRY.values() if r.status == MemoryStatus.SUPERSEDED),
            },
        },
    }
