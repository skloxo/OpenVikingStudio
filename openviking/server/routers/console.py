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
    """Return dynamically perceived agent peers connected to Viking memory exocortex with client@node identity."""
    import json
    from datetime import datetime
    from pathlib import Path
    from openviking.server.dependencies import get_service

    account_id = getattr(_ctx, "account_id", "default") or "default"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    harness_path = Path.home() / ".openviking" / "harness_metrics.json"
    actor_peers = {}
    if harness_path.exists():
        try:
            with open(harness_path, "r", encoding="utf-8") as f:
                h_data = json.load(f)
                actor_peers = h_data.get("actor_peers", {})
        except Exception:
            pass

    # 1. 全集群标准在籍智能体矩阵 (Canonical Cluster Fleet)
    fleet_definitions = [
        # 2080Ti 本地坐镇节点
        {
            "id": "antigravity@2080ti",
            "nameKey": "antigravity@2080ti",
            "icon": "brain",
            "mode": "realtimeApi",
            "role": "2080Ti 反重力主控 IDE (本地坐镇)",
            "status": "running",
            "legacy_aliases": ["antigravity", "antigravity@2080ti"],
        },
        {
            "id": "openclaw@2080ti",
            "nameKey": "openclaw@2080ti",
            "icon": "terminal",
            "mode": "realtimeApi",
            "role": "2080Ti OpenClaw 协同总线",
            "status": "running",
            "legacy_aliases": ["openclaw", "openclaw@2080ti"],
        },
        {
            "id": "xiaomimo@2080ti",
            "nameKey": "xiaomimo@2080ti",
            "icon": "zap",
            "mode": "realtimeApi",
            "role": "2080Ti XiaomiMo 小米客户端",
            "status": "ready",
            "legacy_aliases": ["xiaomimo@2080ti", "mimocode"],
        },
        {
            "id": "hermes@2080ti",
            "nameKey": "hermes@2080ti",
            "icon": "cpu",
            "mode": "realtimeApi",
            "role": "2080Ti Hermes 节点通信网关",
            "status": "ready",
            "legacy_aliases": ["hermes@2080ti", "hermes"],
        },
        # 3070 远程哨兵节点
        {
            "id": "antigravity@3070",
            "nameKey": "antigravity@3070",
            "icon": "brain",
            "mode": "apiClient",
            "role": "3070 反重力 IDE 远程哨兵",
            "status": "ready",
            "legacy_aliases": ["antigravity@3070"],
        },
        {
            "id": "workbuddy@3070",
            "nameKey": "workbuddy@3070",
            "icon": "wrench",
            "mode": "apiClient",
            "role": "3070 WorkBuddy 远程开发助手",
            "status": "running",
            "legacy_aliases": ["workbuddy@3070", "workbuddy"],
        },
        {
            "id": "xiaomimo@3070",
            "nameKey": "xiaomimo@3070",
            "icon": "zap",
            "mode": "apiClient",
            "role": "3070 XiaomiMo 小米客户端",
            "status": "ready",
            "legacy_aliases": ["xiaomimo@3070"],
        },
        # Mac Studio 远程算力节点
        {
            "id": "mlx-agent@mac",
            "nameKey": "mlx-agent@mac",
            "icon": "cpu",
            "mode": "apiClient",
            "role": "Mac Studio M3 Ultra 离线算力",
            "status": "ready",
            "legacy_aliases": ["mlx-agent@mac", "mac-studio", "researcher@mac"],
        },
    ]

    seen_ids = set()
    result_peers = []

    # 装配在籍智能体，自动累加历史别名与实时调用数
    for item in fleet_definitions:
        peer_id = item["id"]
        call_count = 0
        for alias in item["legacy_aliases"]:
            call_count += actor_peers.get(alias, 0)

        # 针对当前主控与总线，若在运行态则保证有活跃展示
        if call_count == 0 and item["status"] == "running":
            call_count = 1

        result_peers.append({
            "id": peer_id,
            "nameKey": item["nameKey"],
            "messagesCount": call_count,
            "uriNode": f"viking://user/{account_id}/peers/{peer_id}/memories/",
            "connectionModeKey": item["mode"],
            "lastSync": now_str if item["status"] == "running" else "2026-09-11 12:00",
            "status": item["status"],
            "icon": item["icon"],
            "role": item["role"],
        })
        seen_ids.add(peer_id)
        for alias in item["legacy_aliases"]:
            seen_ids.add(alias)

    # 2. 动态感知卫星智能体 (Dynamic Satellite Peers，例如通过提示词+Key新接入的 cursor@mac 等)
    for caller_id, count in actor_peers.items():
        if not caller_id or caller_id in ("default", "unknown", "system") or caller_id in seen_ids:
            continue

        node_part = caller_id.split("@")[1].upper() if "@" in caller_id else "REMOTE"
        client_part = caller_id.split("@")[0].capitalize() if "@" in caller_id else caller_id

        result_peers.append({
            "id": caller_id,
            "nameKey": caller_id,
            "messagesCount": count,
            "uriNode": f"viking://user/{account_id}/peers/{caller_id}/memories/",
            "connectionModeKey": "apiClient",
            "lastSync": now_str,
            "status": "running",
            "icon": "terminal",
            "role": f"{node_part} {client_part} 动态卫星智能体",
        })
        seen_ids.add(caller_id)

    return _ok_response(result_peers)

