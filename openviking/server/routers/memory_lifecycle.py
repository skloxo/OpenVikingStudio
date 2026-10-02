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


class ResolveConflictRequest(BaseModel):
    old_uri: str = Field(..., description="Superseded older knowledge URI")
    new_uri: str = Field(..., description="Successor authoritative knowledge URI")
    reason: str = Field("Superseded by verified newer revision", description="Audit reason")


@router.get("/conflicts/stats")
async def get_conflict_stats(
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Retrieve aggregate conflict and lifecycle purity statistics."""
    from openviking.service.memory_conflict_resolver import MemoryConflictResolver
    stats = MemoryConflictResolver.get_instance().get_conflict_stats()
    return {"status": "ok", "result": stats}


@router.get("/conflicts/history")
async def get_conflict_history(
    limit: int = Query(50, ge=1, le=200),
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Retrieve recent conflict resolution and superseding events."""
    from openviking.service.memory_conflict_resolver import MemoryConflictResolver
    history = MemoryConflictResolver.get_instance().get_resolution_history(limit=limit)
    return {"status": "ok", "result": history}


@router.post("/conflicts/resolve")
async def resolve_memory_conflict(
    req: ResolveConflictRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Atomically resolve memory conflict and link superseding DAG."""
    from openviking.service.memory_conflict_resolver import MemoryConflictResolver
    res = MemoryConflictResolver.get_instance().resolve_and_link(
        old_uri=req.old_uri,
        new_uri=req.new_uri,
        reason=req.reason,
        ctx=ctx,
    )
    return {"status": "ok", "result": res.model_dump()}


@router.get("/lineage/dag")
async def get_memory_lineage_dag(
    uri: str = Query(..., description="Target memory URI to trace full DAG"),
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Traverse full superseding DAG chain for a memory URI."""
    from openviking.service.memory_conflict_resolver import MemoryConflictResolver
    chain = MemoryConflictResolver.get_instance().get_lineage_chain(uri)
    return {"status": "ok", "result": chain}


class SimulateDecayRequest(BaseModel):
    uri: str = Field("viking://resources/experience/sample.md", description="Candidate memory URI")
    raw_score: float = Field(0.80, ge=0.0, le=1.0, description="Semantic base score")
    delta_days: float = Field(30.0, ge=0.0, description="Days elapsed since last update/verification")
    active_count: int = Field(0, ge=0, description="Number of historical retrieval hits")
    memory_type: str = Field("experience", description="canonical, experience, event, task, session, general")
    status: str = Field("active", description="active, disputed, superseded")


@router.post("/decay/simulate")
async def simulate_temporal_decay(
    req: SimulateDecayRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Simulate temporal decay dynamics and hit boost for candidate parameters."""
    import time
    from openviking.retrieve.asymmetric_decay import AsymmetricDecayEngine
    engine = AsymmetricDecayEngine()
    now_ts = time.time()
    updated_ts = now_ts - (req.delta_days * 86400.0)
    assessment = engine.evaluate_candidate(
        uri=req.uri,
        raw_score=req.raw_score,
        updated_ts=updated_ts,
        status=req.status,
        now_ts=now_ts,
        active_count=req.active_count,
        memory_type=req.memory_type,
    )
    return {"status": "ok", "result": assessment.model_dump()}


class RunDreamRequest(BaseModel):
    theme: Optional[str] = Field(None, description="Topic or theme to cluster and distill")
    min_cluster_size: int = Field(2, ge=2, le=20, description="Minimum fragments required for cluster")
    dry_run: bool = Field(False, description="Preview without mutating physical files")


@router.post("/dream/run")
async def run_offline_dream(
    req: RunDreamRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Trigger offline dreaming knowledge consolidation cycle."""
    from openviking.service.offline_dreamer import OfflineDreamer
    dreamer = OfflineDreamer.get_instance()
    res = dreamer.run_dream_cycle(
        theme=req.theme,
        min_cluster_size=req.min_cluster_size,
        dry_run=req.dry_run,
        account_id=ctx.user.account_id,
    )
    return {"status": "ok", "result": res.model_dump()}


@router.get("/dream/stats")
async def get_offline_dream_stats(
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Get operational telemetry for offline dreaming knowledge consolidation."""
    from openviking.service.offline_dreamer import OfflineDreamer
    dreamer = OfflineDreamer.get_instance()
    return {"status": "ok", "result": dreamer.get_stats()}


@router.get("/purity/report")
async def get_memory_purity_report(
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Retrieve holistic memory purity benchmark report, SNR ratio, and health score."""
    from openviking.service.memory_purity import MemoryPurityBenchmark
    bench = MemoryPurityBenchmark.get_instance()
    report = bench.compute_purity_report()
    return {"status": "ok", "result": report.model_dump()}


@router.get("/governance/stream")
async def get_memory_governance_stream(
    limit: int = Query(50, ge=1, le=200),
    event_type: Optional[str] = Query(None, description="Filter: INGRESS_ADMISSION or DREAM_CONSOLIDATION"),
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Retrieve unified chronological audit stream of ingress decisions and dream consolidations."""
    from openviking.service.memory_purity import MemoryPurityBenchmark
    bench = MemoryPurityBenchmark.get_instance()
    events = bench.get_governance_stream(limit=limit, event_type=event_type)
    return {"status": "ok", "result": [e.model_dump() for e in events]}


class WatchdogEnforceRequest(BaseModel):
    dry_run: bool = Field(False, description="Preview without mutating physical files")
    force: bool = Field(False, description="Force trigger dream cycle regardless of watermark/window")


@router.post("/watchdog/enforce")
async def enforce_dream_watchdog(
    req: WatchdogEnforceRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Manually or autonomously evaluate and enforce dream watchdog rules."""
    from openviking.service.entropy_watchdog import EntropyWatchdog
    watchdog = EntropyWatchdog.get_instance()
    res = watchdog.check_and_enforce_dream_watchdog(dry_run=req.dry_run, force=req.force)
    return {"status": "ok", "result": res}


