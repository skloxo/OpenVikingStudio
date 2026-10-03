# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Queue management, Dead Letter Queue (DLQ), and Vector Sync Health endpoints.

Unified SSOT:
Consolidates in-memory queue management, SQLite persistent DLQ auditing,
and vector synchronization invariants in a single cohesive router.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from openviking.server.models import Response
from openviking.storage.queuefs import get_queue_manager
from openviking.storage.queuefs.dlq_manager import DLQManager
from openviking.service.vector_sync_tracker import VectorSyncTracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/queue", tags=["queue"])


class RetryFailedPayload(BaseModel):
    queue_name: Optional[str] = None
    entry_ids: Optional[List[str]] = None
    max_items: Optional[int] = Field(default=100, ge=1, le=1000)


class ClearDLQPayload(BaseModel):
    queue_name: Optional[str] = None


class ResolveDeadLetterRequest(BaseModel):
    resolution_note: Optional[str] = None
    status: int = 1


@router.get("/dlq")
async def get_dlq(
    queue_name: Optional[str] = Query(None, description="Filter by queue name"),
    resolved: Optional[int] = Query(None, description="0 for pending, 1 for resolved, 2 for retried"),
    error_type: Optional[str] = Query(None, description="Filter by error type (e.g. INPUT_TOO_LARGE)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """Audit persistent Dead Letter Queue (DLQ) entries and active failure stats."""
    dlq = DLQManager.get_instance()
    items = dlq.list_dead_letters(
        queue_name=queue_name,
        resolved=resolved,
        error_type=error_type,
        limit=limit,
        offset=offset,
    )
    stats = dlq.get_stats()
    return {
        "status": "success",
        "total": stats.get("total_count", 0),
        "pending": stats.get("pending_count", 0),
        "resolved": stats.get("resolved_count", 0),
        "by_error_type": stats.get("by_error_type", {}),
        "items": items,
        "entries": items,  # legacy compatibility
    }


@router.get("/dlq/{dlq_id}")
async def get_dead_letter(dlq_id: int) -> Dict[str, Any]:
    """Retrieve details of a single dead letter message."""
    dlq = DLQManager.get_instance()
    item = dlq.get_dead_letter(dlq_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Dead letter #{dlq_id} not found")
    return {"status": "success", "item": item}


@router.post("/dlq/{dlq_id}/resolve")
async def resolve_dead_letter(dlq_id: int, req: ResolveDeadLetterRequest) -> Dict[str, Any]:
    """Mark a dead letter message as resolved."""
    dlq = DLQManager.get_instance()
    success = dlq.resolve_dead_letter(
        dlq_id=dlq_id,
        resolution_note=req.resolution_note,
        resolved_status=req.status,
    )
    if not success:
        raise HTTPException(status_code=404, detail=f"Dead letter #{dlq_id} not found")
    return {"status": "success", "resolved_id": dlq_id}


@router.post("/dlq/{dlq_id}/retry")
async def retry_dead_letter(dlq_id: int) -> Dict[str, Any]:
    """Retry a dead letter by re-enqueuing its original payload into NamedQueue."""
    dlq = DLQManager.get_instance()
    record = dlq.get_dead_letter(dlq_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Dead letter #{dlq_id} not found")

    try:
        from openviking.server.app import get_app_viking_service
        service = get_app_viking_service()
        if hasattr(service, "_vikingdb") and service._vikingdb and service._vikingdb.has_queue_manager:
            queue_name = record.get("queue_name") or "text_embedding"
            queue = await service._vikingdb._queue_manager.get_queue(queue_name)
            await queue.enqueue(record.get("payload", {}))
            dlq.increment_retry(dlq_id)
            dlq.resolve_dead_letter(dlq_id, resolution_note="Re-enqueued via DLQ retry endpoint", resolved_status=2)
            return {"status": "success", "re-enqueued": True, "dlq_id": dlq_id}
    except Exception as e:
        logger.error(f"[DLQ] Failed to retry dead letter #{dlq_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retry message: {e}")

    return {"status": "skipped", "message": "Queue manager not available", "dlq_id": dlq_id}


@router.get("/sync-metrics")
async def get_sync_metrics(account_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Retrieve vector index synchronization rate and health metrics."""
    tracker = VectorSyncTracker.get_instance()
    metrics = tracker.get_metrics(account_id=account_id)
    dlq_stats = DLQManager.get_instance().get_stats()
    return {
        "status": "success",
        "sync_rate_pct": metrics.get("sync_rate_pct", 100.0),
        "total_files": metrics.get("total_files", 0),
        "indexed_count": metrics.get("indexed_count", 0),
        "pending_count": metrics.get("pending_count", 0),
        "failed_count": metrics.get("failed_count", 0),
        "dlq_pending_count": dlq_stats.get("pending_count", 0),
        "dlq_total_count": dlq_stats.get("total_count", 0),
    }


@router.post("/sync-heal")
async def heal_unindexed_stragglers(
    account_id: Optional[str] = Query(None),
    max_age_seconds: float = Query(300.0, ge=10.0),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    """Find unindexed or failed files and initiate self-healing re-sync."""
    tracker = VectorSyncTracker.get_instance()
    unindexed = tracker.find_unindexed_or_failed(
        account_id=account_id,
        max_age_seconds=max_age_seconds,
        limit=limit,
    )
    healed_count = 0
    errors: List[str] = []

    for item in unindexed:
        uri = item.get("uri")
        try:
            tracker.mark_pending(uri, account_id=item.get("account_id", "default"))
            healed_count += 1
        except Exception as e:
            errors.append(f"{uri}: {e}")

    return {
        "status": "success",
        "candidate_count": len(unindexed),
        "healed_count": healed_count,
        "errors": errors,
    }


@router.post("/retry_failed")
async def retry_failed(
    payload: RetryFailedPayload = RetryFailedPayload(),
) -> Response:
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
) -> Response:
    """Clear DLQ entries and reset error counts."""
    qm = get_queue_manager()
    cleared = qm.clear_dlq(queue_name=payload.queue_name)
    return Response(status="ok", result={"cleared_count": cleared})


@router.get("/status")
async def get_queue_status(
    queue_name: Optional[str] = Query(None, description="Queue name"),
) -> Response:
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
