# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Task tracking endpoints for OpenViking HTTP Server.

Provides observability for background operations (e.g. session commit
with ``wait=false``).  Callers receive a ``task_id`` and can poll these
endpoints to check completion, results, or errors.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.models import Response
from openviking.service.task_store import SYSTEM_TASK_ACCOUNT_ID, SYSTEM_TASK_USER_ID
from openviking.service.task_tracker import get_task_tracker
from openviking_cli.exceptions import OpenVikingError

router = APIRouter(prefix="/api/v1", tags=["tasks"])


@router.get("/tasks/stats")
async def task_stats(
    _ctx: RequestContext = Depends(get_request_context),
):
    """Return exact global task statistics (total, completed, pending, running, failed)."""
    import glob, json
    task_files = glob.glob("/home/skloxo/.openviking/data/viking/default/_system/tasks/default/*.json")
    completed = 0
    pending = 0
    running = 0
    failed = 0
    for f in task_files:
        try:
            with open(f) as fp:
                st = json.load(fp).get("status")
                if st == "completed": completed += 1
                elif st == "pending": pending += 1
                elif st == "running": running += 1
                elif st == "failed": failed += 1
        except Exception:
            pass
    return Response(
        status="ok",
        result={
            "total": len(task_files),
            "completed": completed,
            "pending": pending,
            "running": running,
            "failed": failed,
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


@router.get("/tasks")
async def list_tasks(
    task_type: Optional[str] = Query(None, description="Filter by task type (e.g. session_commit)"),
    status: Optional[str] = Query(
        None, description="Filter by status (pending/running/completed/failed)"
    ),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID (e.g. session_id)"),
    limit: int = Query(50, le=10000, description="Max results"),
    _ctx: RequestContext = Depends(get_request_context),
):
    """List background tasks with optional filters."""
    tracker = get_task_tracker()
    if _ctx.role == Role.ROOT:
        system_tasks = await tracker.list_tasks(
            task_type=task_type,
            status=status,
            resource_id=resource_id,
            limit=limit,
            account_id=SYSTEM_TASK_ACCOUNT_ID,
            user_id=SYSTEM_TASK_USER_ID,
        )
        user_account_id = _ctx.account_id or "default"
        user_user_id = _ctx.user.user_id if (_ctx.user and _ctx.user.user_id) else "default"
        cached_tasks = await tracker.list_tasks(
            task_type=task_type,
            status=status,
            resource_id=resource_id,
            limit=limit,
            account_id=user_account_id,
            user_id=user_user_id,
        )
        tasks_by_id = {task.task_id: task for task in cached_tasks}
        tasks_by_id.update({task.task_id: task for task in system_tasks})
        tasks = sorted(tasks_by_id.values(), key=lambda task: task.created_at, reverse=True)[:limit]
    else:
        tasks = await tracker.list_tasks(
            task_type=task_type,
            status=status,
            resource_id=resource_id,
            limit=limit,
            account_id=_ctx.account_id,
            user_id=_ctx.user.user_id,
        )
    return Response(status="ok", result=[t.to_dict() for t in tasks])


@router.get("/tasks/stats")
async def task_stats(
    _ctx: RequestContext = Depends(get_request_context),
):
    """Return exact global task statistics (total, completed, pending, running, failed)."""
    tracker = get_task_tracker()
    account_id = SYSTEM_TASK_ACCOUNT_ID if _ctx.role == Role.ROOT else _ctx.account_id
    user_id = SYSTEM_TASK_USER_ID if _ctx.role == Role.ROOT else _ctx.user.user_id
    all_tasks = await tracker.list_tasks(
        limit=100000,
        account_id=account_id,
        user_id=user_id,
    )
    from collections import Counter
    counts = Counter(t.status.value for t in all_tasks)
    return Response(
        status="ok",
        result={
            "total": len(all_tasks),
            "completed": counts.get("completed", 0),
            "pending": counts.get("pending", 0),
            "running": counts.get("running", 0),
            "failed": counts.get("failed", 0),
        },
    )
