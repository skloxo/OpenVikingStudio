# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Console BFF endpoints for usage and audit data."""

from __future__ import annotations

from typing import Any, Optional


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
        result.extend(part.strip() for part in value.split(",") if part.strip())
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


def _extract_registered_routes(app: Any) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for r in getattr(app, "routes", []):
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", None)
        if path:
            routes.append(
                {
                    "path": path,
                    "methods": sorted(list(methods)) if methods else ["GET"],
                }
            )
    return routes


@router.get("/audit/frequency")
async def endpoint_frequency(
    request: Request,
    window: str = Query("all", pattern="^(24h|7d|30d|all)$"),
    _ctx: RequestContext = require_role(Role.ROOT, Role.ADMIN, Role.USER),
):
    """Return endpoint invocation frequency stats, hot rankings, and dormant diagnostics."""
    service = _runtime_service(request)
    if service is None:
        return _disabled_response()
    registered_routes = _extract_registered_routes(request.app)
    result = await service.endpoint_frequency(
        ctx=_ctx,
        window=window,
        registered_routes=registered_routes,
    )
    return _ok_response(result)


@router.get("/peers")
async def peer_agents(
    request: Request,
    _ctx: RequestContext = require_role(Role.ROOT, Role.ADMIN, Role.USER),
):
    """Return dynamically perceived agent peers connected to Viking memory exocortex with client@node identity."""
    from openviking.service.agent_peer_registry import AgentPeerRegistry

    account_id = getattr(_ctx, "account_id", "default") or "default"
    registry = AgentPeerRegistry.get_instance()
    peers = registry.get_active_peers(account_id=account_id)
    return _ok_response(peers)


@router.post("/peers/heartbeat")
async def peer_heartbeat(
    request: Request,
    payload: dict,
    _ctx: RequestContext = require_role(Role.ROOT, Role.ADMIN, Role.USER),
):
    """Dynamically register or bump heartbeat for an agent peer."""
    from openviking.service.agent_peer_registry import AgentPeerRegistry

    peer_id = payload.get("peer_id", "").strip()
    if not peer_id:
        return _ok_response({"success": False, "message": "peer_id is required"})

    calls = int(payload.get("calls", 1))
    staging_dir = payload.get("staging_dir")
    meta = AgentPeerRegistry.get_instance().record_peer_activity(
        peer_id=peer_id, calls=calls, staging_dir=staging_dir
    )
    return _ok_response({"success": True, "peer": meta.model_dump()})


@router.post("/peers/deregister")
async def peer_deregister(
    request: Request,
    payload: dict,
    _ctx: RequestContext = require_role(Role.ROOT, Role.ADMIN, Role.USER),
):
    """Explicitly deregister a dead or purged agent peer."""
    from openviking.service.agent_peer_registry import AgentPeerRegistry

    peer_id = payload.get("peer_id", "").strip()
    if not peer_id:
        return _ok_response({"success": False, "message": "peer_id is required"})

    removed = AgentPeerRegistry.get_instance().deregister_peer(peer_id)
    return _ok_response({"success": removed, "peer_id": peer_id})


