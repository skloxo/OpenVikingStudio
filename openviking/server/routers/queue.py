# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Queue management and Dead Letter Queue (DLQ) endpoints."""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.server.models import Response
from openviking.storage.queuefs import get_queue_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/queue", tags=["queue"])


class RetryFailedPayload(BaseModel):
    queue_name: Optional[str] = None
    entry_ids: Optional[List[str]] = None
    max_items: Optional[int] = Field(default=100, ge=1, le=1000)


class ClearDLQPayload(BaseModel):
    queue_name: Optional[str] = None


@router.get("/dlq")
async def get_dlq(
    queue_name: Optional[str] = Query(None, description="Filter by queue name"),
    include_retried: bool = Query(False, description="Include already retried items"),
    limit: int = Query(100, ge=1, le=1000, description="Max entries to return"),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Audit dead-letter queue (DLQ) failed items."""
    qm = get_queue_manager()
    entries = await qm.get_dlq(queue_name=queue_name, include_retried=include_retried, limit=limit)
    return Response(
        status="ok",
        result={
            "total": len(entries),
            "queue_name": queue_name,
            "entries": entries,
        },
    )


@router.post("/retry_failed")
async def retry_failed(
    payload: RetryFailedPayload = RetryFailedPayload(),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Re-enqueue failed items from DLQ for self-healing."""
    qm = get_queue_manager()
    result = await qm.retry_failed(
        queue_name=payload.queue_name,
        entry_ids=payload.entry_ids,
        max_items=payload.max_items,
    )
    return Response(status="ok", result=result)


@router.post("/clear_dlq")
async def clear_dlq(
    payload: ClearDLQPayload = ClearDLQPayload(),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Clear DLQ entries and reset error counts."""
    qm = get_queue_manager()
    cleared = qm.clear_dlq(queue_name=payload.queue_name)
    return Response(status="ok", result={"cleared_count": cleared})


@router.get("/status")
async def get_queue_status(
    queue_name: Optional[str] = Query(None, description="Queue name"),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Get status of queues."""
    qm = get_queue_manager()
    statuses = await qm.check_status(queue_name=queue_name)
    result = {
        name: {
            "pending": s.pending,
            "in_progress": s.in_progress,
            "processed": s.processed,
            "requeue_count": s.requeue_count,
            "error_count": s.error_count,
            "recent_error_rate": s.recent_error_rate,
            "is_complete": s.is_complete,
            "is_healthy": s.is_healthy,
            "has_errors": s.has_errors,
        }
        for name, s in statuses.items()
    }
    return Response(status="ok", result=result)
