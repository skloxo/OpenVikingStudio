# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Task tracking endpoints for OpenViking HTTP Server.

Provides observability for background operations (e.g. session commit
with ``wait=false``).  Callers receive a ``task_id`` and can poll these
endpoints to check completion, results, or errors.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

logger = logging.getLogger("openviking.server.routers.tasks")

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.models import Response
from openviking.service.task_store import SYSTEM_TASK_ACCOUNT_ID, SYSTEM_TASK_USER_ID
from openviking.service.task_tracker import get_task_tracker
from openviking_cli.exceptions import (
    FailedPreconditionError,
    OpenVikingError,
    PermissionDeniedError,
)

router = APIRouter(prefix="/api/v1", tags=["tasks"])


@router.get("/tasks/valet/ticket/{ticket_id}")
async def get_valet_ticket(ticket_id: str, _ctx: RequestContext = Depends(get_request_context)):
    """Retrieve ticket status from the Valet Ingestion Engine."""
    from openviking.service.valet_ingestion import ValetIngestionEngine

    engine = ValetIngestionEngine.get_instance()
    ticket = engine.get_ticket(ticket_id)
    if not ticket:
        raise OpenVikingError(
            f"Valet ticket not found: {ticket_id}",
            code="NOT_FOUND",
            details={"ticket_id": ticket_id},
        )
    return Response(status="ok", result=ticket.to_dict())


@router.get("/tasks/dual_track")
async def get_dual_track_tasks(
    limit: int = Query(50, le=200, description="Max tasks per track"),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Retrieve tasks categorized into Human-Friendly Business Jobs and System Maintenance Ops."""
    from openviking.service.entropy_gatekeeper import EntropyGatekeeper

    tracker = get_task_tracker()
    raw_tasks = await tracker.list_tasks(limit=limit * 2)

    business_jobs = []
    system_ops = []
    completed_deliverables = 0

    # 1. First collect business jobs from active and recent Valet Ingestion tickets
    try:
        from pathlib import Path
        from openviking.service.valet_ingestion import ValetIngestionEngine

        valet_engine = ValetIngestionEngine.get_instance()
        valet_tickets = valet_engine.list_tickets(limit=limit)
        seen_tickets = set()
        for vt in valet_tickets:
            seen_tickets.add(vt.ticket_id)
            is_done = vt.status == "parked"
            is_parking = vt.status in ("accepted", "parking")
            progress = {
                "completed": 1 if is_done else 0,
                "total": 1,
                "unit": "个节点",
            }
            deliverable = None
            if vt.deliverable_uri:
                deliverable = {
                    "uri": vt.deliverable_uri,
                    "label": "成果物直达",
                    "action_type": "view_memory",
                }
            name = Path(vt.uri).name
            if name.endswith(".md"):
                name = name[:-3]
            title = f"📥 轻量增量入库：{name}"

            business_jobs.append({
                "task_id": vt.ticket_id,
                "task_type": "valet_parking",
                "status": "completed" if is_done else ("running" if is_parking else "failed"),
                "human_title": title,
                "initiator": "Agent",
                "created_at": vt.created_at,
                "updated_at": vt.created_at,
                "deliverable": deliverable,
                "progress": progress,
                "message": vt.message,
            })
            if is_done and deliverable:
                completed_deliverables += 1
    except Exception as e:
        logger.debug("Failed to list valet tickets: %s", e)
        seen_tickets = set()

    for t in raw_tasks:
        if t.task_id in seen_tickets:
            continue
        td = t.to_dict()
        meta = td.get("meta") or {}
        res = td.get("result") or {}
        task_type = t.task_type

        # Check if it's a first-class business job
        is_business = meta.get("is_business") or task_type in {
            "valet_parking",
            "batch_digest",
            "official_digest",
            "node_rebuild",
            "session_distill",
        }

        # Deliverable link closure
        deliverable = res.get("deliverable") or meta.get("deliverable")
        if deliverable and t.status.value == "completed":
            completed_deliverables += 1

        if is_business:
            human_title = meta.get("human_title")
            if not human_title:
                human_title = f"业务作业：{task_type.replace('_', ' ').title()}"
            td["human_title"] = human_title
            td["initiator"] = meta.get("initiator", "Agent")
            td["deliverable"] = deliverable
            td["progress"] = res.get("progress") or meta.get("progress") or {
                "completed": 1 if t.status.value == "completed" else 0,
                "total": 1,
                "unit": "个节点",
            }
            business_jobs.append(td)
        else:
            # Humanize machine codes for system ops
            short_id = t.task_id.split("-")[-1] if "-" in t.task_id else t.task_id[-6:]
            type_label = {
                "admin_reindex": "后台增量向量重排",
                "quality_gate": "系统周期质检守护",
                "memory_dream": "长周期记忆反思整理",
                "memory_compaction": "存储空间压缩收敛",
                "fact_mutation": "知识状态机变异校验",
                "entity_summarization": "实体全局拓扑归纳",
                "four_tier_governance": "四层信息退火巡检",
            }.get(task_type, f"系统运维工序 ({task_type})")
            td["human_title"] = f"{type_label} #{short_id}"
            system_ops.append(td)

    # Compute KPI metrics
    gatekeeper = EntropyGatekeeper.get_instance()
    kpi = {
        "active_business_jobs": sum(1 for j in business_jobs if j.get("status") in ("pending", "running")),
        "completed_deliverables_today": completed_deliverables,
        "saved_bytes": gatekeeper._stats.get("saved_bytes", 0),
        "total_probes": gatekeeper._stats.get("total_probes", 0),
    }

    return Response(
        status="ok",
        result={
            "business_jobs": business_jobs[:limit],
            "system_ops": system_ops[:limit],
            "kpi": kpi,
        },
    )


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Get the status of a single background task."""
    tracker = get_task_tracker()
    if _ctx.role == Role.ROOT:
        task = await tracker.get(task_id)
        if task is None:
            task = await tracker.get(
                task_id,
                account_id=SYSTEM_TASK_ACCOUNT_ID,
                user_id=SYSTEM_TASK_USER_ID,
            )
    else:
        task = await tracker.get(
            task_id,
            account_id=_ctx.account_id,
            user_id=_ctx.user.user_id,
        )
    if not task:
        raise OpenVikingError(
            "Task not found or expired",
            code="NOT_FOUND",
            details={"resource": task_id, "type": "task"},
        )
    return Response(status="ok", result=task.to_dict())


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Request cooperative cancellation of a background task."""
    if _ctx.role == Role.ROOT:
        raise PermissionDeniedError("ROOT may not cancel tasks")
    tracker = get_task_tracker()
    try:
        task = await tracker.cancel(
            task_id,
            account_id=_ctx.account_id,
            user_id=_ctx.user.user_id,
        )
    except ValueError as exc:
        raise FailedPreconditionError(str(exc)) from exc
    if task is None:
        raise OpenVikingError(
            "Task not found or expired",
            code="NOT_FOUND",
            details={"resource": task_id, "type": "task"},
        )
    return Response(status="ok", result=task.to_dict())


@router.get("/tasks")
async def list_tasks(
    task_type: Optional[str] = Query(None, description="Filter by task type (e.g. session_commit)"),
    status: Optional[str] = Query(
        None,
        description="Filter by status (pending/running/cancelling/completed/failed/cancelled)",
    ),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID (e.g. session_id)"),
    limit: int = Query(50, le=200, description="Max results"),
    _ctx: RequestContext = Depends(get_request_context),
):
    """List background tasks with optional filters."""
    tracker = get_task_tracker()
    tasks_by_id = {}
    if _ctx.role == Role.ROOT:
        all_store_tasks = []
        if hasattr(tracker._store, "list_all"):
            try:
                for payload in await tracker._store.list_all():
                    all_store_tasks.append(tracker._record_from_payload(payload))
                tracker._merge_loaded_tasks(all_store_tasks)
            except Exception:
                pass
        system_tasks = await tracker.list_tasks(
            task_type=task_type,
            status=status,
            resource_id=resource_id,
            limit=limit,
            account_id=SYSTEM_TASK_ACCOUNT_ID,
            user_id=SYSTEM_TASK_USER_ID,
        )
        default_tasks = await tracker.list_tasks(
            task_type=task_type,
            status=status,
            resource_id=resource_id,
            limit=limit,
            account_id="default",
            user_id=None,
        )
        cached_tasks = await tracker.list_tasks(
            task_type=task_type,
            status=status,
            resource_id=resource_id,
            limit=limit,
        )
        for task in cached_tasks:
            tasks_by_id[task.task_id] = task
        for task in default_tasks:
            tasks_by_id[task.task_id] = task
        for task in system_tasks:
            tasks_by_id[task.task_id] = task
    else:
        user_tasks = await tracker.list_tasks(
            task_type=task_type,
            status=status,
            resource_id=resource_id,
            limit=limit,
            account_id=_ctx.account_id,
            user_id=_ctx.user.user_id,
        )
        system_tasks = await tracker.list_tasks(
            task_type=task_type,
            status=status,
            resource_id=resource_id,
            limit=limit,
            account_id=SYSTEM_TASK_ACCOUNT_ID,
            user_id=SYSTEM_TASK_USER_ID,
        )
        for task in user_tasks:
            tasks_by_id[task.task_id] = task
        for task in system_tasks:
            tasks_by_id.setdefault(task.task_id, task)

    tasks = sorted(tasks_by_id.values(), key=lambda task: task.created_at, reverse=True)[:limit]
    return Response(status="ok", result=[t.to_dict() for t in tasks])


@router.delete("/tasks/{task_id}")
async def delete_task_endpoint(
    task_id: str,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Delete a single terminal (completed/failed/cancelled) task record."""
    tracker = get_task_tracker()
    account_id = None if _ctx.role == Role.ROOT else _ctx.account_id
    user_id = None if _ctx.role == Role.ROOT else _ctx.user.user_id
    try:
        deleted = await tracker.delete_task(
            task_id,
            account_id=account_id,
            user_id=user_id,
        )
    except RuntimeError as exc:
        raise FailedPreconditionError(str(exc)) from exc
    if not deleted:
        raise OpenVikingError(
            "Task not found or active",
            code="NOT_FOUND",
            details={"resource": task_id, "type": "task"},
        )
    return Response(status="ok", result={"task_id": task_id, "deleted": True})


@router.post("/tasks/clear-failed")
async def clear_failed_tasks(
    _ctx: RequestContext = Depends(get_request_context),
):
    """Batch delete all failed and cancelled task records."""
    tracker = get_task_tracker()
    account_id = None if _ctx.role == Role.ROOT else _ctx.account_id
    user_id = None if _ctx.role == Role.ROOT else _ctx.user.user_id
    deleted_count = await tracker.clear_terminal_tasks(
        account_id=account_id,
        user_id=user_id,
    )
    return Response(status="ok", result={"deleted_count": deleted_count})


@router.post("/tasks/trigger-quality-gate")
async def trigger_quality_gate(
    reason: str = Query("manual_api_trigger", description="Reason for triggering"),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Trigger an immediate automated Quality Gate and Remediation cycle."""
    from openviking.service.entropy_watchdog import get_entropy_watchdog

    watchdog = get_entropy_watchdog()
    res = await watchdog.trigger_cycle(reason=reason)
    return Response(status="ok", result=res)


@router.post("/tasks/dispatch-anti-entropy")
async def dispatch_anti_entropy_task(
    task_type: str = Query(..., description="memory_dream | memory_compaction | fact_mutation | entity_summarization | four_tier_governance"),
    target: Optional[str] = Query(None, description="Optional target parameter (theme/URI/statement/entity/domain)"),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Dispatch an anti-entropy task (memory_dream, memory_compaction, fact_mutation, entity_summarization, four_tier_governance)."""
    from openviking.service.entropy_watchdog import get_entropy_watchdog

    watchdog = get_entropy_watchdog()
    account_id = "default" if _ctx.role == Role.ROOT else _ctx.account_id

    if task_type == "memory_dream":
        tid = await watchdog.dispatch_memory_dream(theme=target or "general_reflection", account_id=account_id)
    elif task_type == "memory_compaction":
        tid = await watchdog.dispatch_memory_compaction(account_id=account_id)
    elif task_type == "fact_mutation":
        tid = await watchdog.dispatch_fact_mutation(source_doc=target or "session_stream", account_id=account_id)
    elif task_type == "entity_summarization":
        tid = await watchdog.dispatch_entity_summarization(entity=target or "OpenViking", account_id=account_id)
    elif task_type == "four_tier_governance":
        tid = await watchdog.dispatch_four_tier_governance(topic=target or "vector_entropy", account_id=account_id)
    else:
        raise OpenVikingError(f"Unsupported anti-entropy task type: {task_type}", code="INVALID_ARGUMENT")

    return Response(status="ok", result={"task_id": tid, "task_type": task_type})



