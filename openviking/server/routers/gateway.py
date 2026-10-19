# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Gateway and Prompt Cache monitoring endpoints for OpenViking Server."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request

from openviking.server.identity import RequestContext, Role
from openviking.server.models import Response
from openviking_cli.session.user_id import UserIdentifier
from openviking_gateway.overview import cache_alerts, overview_summary

router = APIRouter(prefix="/api/v1/gateway", tags=["gateway"])

# In-memory buffer of recent gateway request events for real-time overview aggregation
_GATEWAY_EVENT_BUFFER: List[Dict[str, Any]] = []
_MAX_BUFFER_SIZE = 10_000


def record_gateway_request_event(event: Dict[str, Any]) -> None:
    """Record a gateway request log event into the real-time buffer."""
    _GATEWAY_EVENT_BUFFER.append(event)
    if len(_GATEWAY_EVENT_BUFFER) > _MAX_BUFFER_SIZE:
        del _GATEWAY_EVENT_BUFFER[: len(_GATEWAY_EVENT_BUFFER) - _MAX_BUFFER_SIZE]


def get_gateway_events() -> List[Dict[str, Any]]:
    """Return a shallow copy of recorded events."""
    return list(_GATEWAY_EVENT_BUFFER)


def clear_gateway_events() -> None:
    """Clear buffer for testing."""
    _GATEWAY_EVENT_BUFFER.clear()


async def _resolve_ctx(request: Request) -> RequestContext:
    plugin = getattr(request.app.state, "auth_plugin", None)
    if plugin is not None:
        try:
            from openviking.server.auth import resolve_identity
            return await resolve_identity(request)
        except Exception:
            pass
    return RequestContext(user=UserIdentifier.the_default_user("default"), role=Role.USER)


@router.get("/overview")
async def get_gateway_overview(
    request: Request,
) -> Response:
    """Get Gateway 2.0 real-time overview, Prompt Cache metrics, and miss streak alerts."""
    _ctx = await _resolve_ctx(request)
    now = time.time()
    events = get_gateway_events()
    summary = overview_summary(events, now=now)
    return Response(status="ok", result=summary)


@router.get("/cache-alerts")
async def get_gateway_cache_alerts(
    request: Request,
) -> Response:
    """Get prompt cache miss alerts for long conversations and silent upstreams."""
    _ctx = await _resolve_ctx(request)
    now = time.time()
    events = get_gateway_events()
    alerts = cache_alerts(events, now=now)
    return Response(status="ok", result=alerts)


