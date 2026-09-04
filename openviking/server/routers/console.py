# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Console BFF endpoints for usage and audit data."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, Request

from openviking.server.auth import require_role
from openviking.server.identity import RequestContext, Role
from openviking.server.models import Response

router = APIRouter(prefix="/api/v1/console", tags=["console"])


def _split_multi(values: Optional[list[str]]) -> list[str]:
    if not values:
        return []
    result: list[str] = []
    for value in values:
        result.extend(part.strip() for part in str(value).split(",") if part.strip())
    return result


def _runtime_service(request: Request):
    runtime = getattr(request.app.state, "usage_audit_runtime", None)
    if runtime is None:
        return None
    return runtime.api_service


def _ok_response(result):
    return Response(status="ok", result=result).model_dump(exclude_none=True)


def _disabled_response():
    return _ok_response(
        {
            "enabled": False,
            "message": "Usage/Audit is disabled or not initialized.",
        }
    )


@router.get("/dashboard/summary")
async def dashboard_summary(
    request: Request,
    timezone: Optional[str] = Query(
        None,
        description="IANA viewer timezone (e.g. Asia/Shanghai). Defaults to server tz.",
    ),
    _ctx: RequestContext = require_role(Role.ROOT, Role.ADMIN, Role.USER),
):
    """Return Dashboard top-card data."""
    service = _runtime_service(request)
    if service is None:
        return _disabled_response()
    return _ok_response(await service.dashboard_summary(_ctx, timezone_name=timezone))


@router.get("/tokens")
async def token_series(
    request: Request,
    start_date: str = Query(..., description="Start date (viewer-local) in YYYY-MM-DD"),
    end_date: str = Query(..., description="End date (viewer-local) in YYYY-MM-DD"),
    bucket: str = Query("day", pattern="^(day)$"),
    timezone: Optional[str] = Query(
        None,
        description="IANA viewer timezone (e.g. Asia/Shanghai). Defaults to server tz.",
    ),
    _ctx: RequestContext = require_role(Role.ROOT, Role.ADMIN, Role.USER),
):
    """Return token usage trend for a date range."""
    service = _runtime_service(request)
    if service is None:
        return _disabled_response()
    result = await service.token_series(
        ctx=_ctx,
        start_date=start_date,
        end_date=end_date,
        bucket=bucket,
        timezone_name=timezone,
    )
    return _ok_response(result)


@router.get("/context-commits")
async def context_commits(
    request: Request,
    start_date: str = Query(..., description="Start date (viewer-local) in YYYY-MM-DD"),
    end_date: str = Query(..., description="End date (viewer-local) in YYYY-MM-DD"),
    bucket: str = Query("hour", pattern="^(hour|4h)$"),
    timezone: Optional[str] = Query(
        None,
        description="IANA viewer timezone (e.g. Asia/Shanghai). Defaults to server tz.",
    ),
    _ctx: RequestContext = require_role(Role.ROOT, Role.ADMIN, Role.USER),
):
    """Return context write heatmap rows for a date range."""
    service = _runtime_service(request)
    if service is None:
        return _disabled_response()
    result = await service.context_commits(
        ctx=_ctx,
        start_date=start_date,
        end_date=end_date,
        bucket=bucket,
        timezone_name=timezone,
    )
    return _ok_response(result)


@router.get("/audit")
async def audit_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    request_id: Optional[str] = Query(None),
    status: Optional[list[str]] = Query(None),
    api_type: Optional[list[str]] = Query(None),
    _ctx: RequestContext = require_role(Role.ROOT, Role.ADMIN, Role.USER),
):
    """Return filtered request audit logs."""
    service = _runtime_service(request)
    if service is None:
        return _disabled_response()
    result = await service.audit_logs(
        ctx=_ctx,
        request_id=request_id,
        statuses=_split_multi(status),
        api_types=_split_multi(api_type),
        page=page,
        page_size=page_size,
    )
    return _ok_response(result)


@router.get("/peers")
async def peer_agents(
    request: Request,
    _ctx: RequestContext = require_role(Role.ROOT, Role.ADMIN, Role.USER),
):
    """Return dynamically perceived agent peers connected to Viking memory exocortex."""
    import json
    from datetime import datetime
    from pathlib import Path
    from openviking.server.dependencies import get_service

    service = get_service()
    workspace = getattr(getattr(service, "_config", None), "storage", None)
    workspace_dir = Path(getattr(workspace, "workspace", "/home/skloxo/.openviking/data"))

    account_id = getattr(_ctx, "account_id", "default") or "default"
    peers_dir = workspace_dir / "viking" / "default" / "user" / account_id / "peers"

    harness_path = Path.home() / ".openviking" / "harness_metrics.json"
    actor_peers = {}
    if harness_path.exists():
        try:
            with open(harness_path, "r", encoding="utf-8") as f:
                h_data = json.load(f)
                actor_peers = h_data.get("actor_peers", {})
        except Exception:
            pass

    peer_metas = {
        "developer": {"icon": "code", "mode": "realtimeApi", "role": "代码与系统架构子代理"},
        "planner": {"icon": "network", "mode": "realtimeApi", "role": "项目规划与任务拆解代理"},
        "operator": {"icon": "wrench", "mode": "apiClient", "role": "自动化部署与运行看护代理"},
        "researcher": {"icon": "brain", "mode": "apiClient", "role": "深度调研与信息挖掘代理"},
        "designer": {"icon": "zap", "mode": "apiClient", "role": "UI/UX 设计与视觉契约代理"},
        "test": {"icon": "terminal", "mode": "apiClient", "role": "质量保障与自动化测试代理"},
        "tide-trading": {"icon": "database", "mode": "primaryEngine", "role": "量化投研与实盘信号主引擎"},
        "hermes": {"icon": "cpu", "mode": "apiClient", "role": "Hermes 跨节点通信子网"},
        "jarvis-feishu": {"icon": "network", "mode": "realtimeApi", "role": "飞书协作与自动化网关"},
        "main": {"icon": "brain", "mode": "primaryEngine", "role": "主指挥中枢 (Conductor)"},
        "antigravity": {"icon": "brain", "mode": "realtimeApi", "role": "反重力主控智能体 (IDE)"},
        "openclaw": {"icon": "terminal", "mode": "realtimeApi", "role": "OpenClaw 协同总线"},
    }

    seen_ids = set()
    result_peers = []

    for caller_id in ("antigravity", "openclaw"):
        if caller_id in actor_peers:
            meta = peer_metas.get(caller_id, {"icon": "terminal", "mode": "realtimeApi", "role": "活跃智能体"})
            call_count = actor_peers.get(caller_id, 0)
            result_peers.append({
                "id": caller_id,
                "nameKey": caller_id,
                "messagesCount": call_count,
                "uriNode": f"viking://user/{account_id}/peers/{caller_id}/memories/",
                "connectionModeKey": meta["mode"],
                "lastSync": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": "running",
                "icon": meta["icon"],
                "role": meta["role"],
            })
            seen_ids.add(caller_id)

    if peers_dir.exists():
        for item in sorted(peers_dir.iterdir()):
            if not item.is_dir() or item.name.startswith("."):
                continue
            peer_id = item.name
            if peer_id in seen_ids:
                continue

            memories_dir = item / "memories"
            msg_count = 0
            if memories_dir.exists():
                msg_count = len([x for x in memories_dir.iterdir() if not x.name.startswith(".")])

            mtime = datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            meta = peer_metas.get(peer_id, {"icon": "terminal", "mode": "apiClient", "role": f"{peer_id} 智能体"})

            status = "ready"
            if peer_id in ("developer", "planner", "main") or actor_peers.get(peer_id, 0) > 0:
                status = "running"

            result_peers.append({
                "id": peer_id,
                "nameKey": peer_id,
                "messagesCount": msg_count,
                "uriNode": f"viking://user/{account_id}/peers/{peer_id}/memories/",
                "connectionModeKey": meta["mode"],
                "lastSync": mtime,
                "status": status,
                "icon": meta["icon"],
                "role": meta["role"],
            })
            seen_ids.add(peer_id)

    return _ok_response(result_peers)

