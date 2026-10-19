# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Gateway overview aggregation and Prompt Cache alerts."""

from __future__ import annotations

import time
import pytest

from openviking_gateway.overview import (
    CACHE_TTL,
    LONG_CONTEXT,
    MISS_STREAK,
    cache_alerts,
    miss_streak,
    overview_summary,
)


def _make_call(
    input_tokens: int,
    cached_tokens: int = 0,
    time_offset: float = 0.0,
    duration_s: float = 1.0,
    model: str = "claude-3-5-sonnet",
    upstream_id: str = "up-1",
    session: str = "sess-1",
    kind: str = "user",
    status: int = 200,
    credential_id: str = "cred-1",
    protocol: str = "anthropic",
) -> dict:
    now = 1_000_000.0
    finish_time = now - time_offset
    return {
        "time": finish_time,
        "duration_ms": int(duration_s * 1000),
        "input_tokens": input_tokens,
        "cached_tokens": cached_tokens,
        "first_upstream_input_tokens": input_tokens,
        "first_upstream_cached_tokens": cached_tokens,
        "model": model,
        "upstream_id": upstream_id,
        "session": session,
        "kind": kind,
        "status": status,
        "credential_id": credential_id,
        "protocol": protocol,
    }


def test_miss_streak_detects_consecutive_long_misses():
    # 3 consecutive calls > 32k with 0 cache hits within TTL
    c1 = _make_call(35_000, 0, time_offset=120)
    c2 = _make_call(36_000, 0, time_offset=60)
    c3 = _make_call(37_000, 0, time_offset=10)

    streak = miss_streak([c1, c2, c3])
    assert len(streak) == 3

    # If oldest was < 32k tokens, streak stops
    c0 = _make_call(10_000, 0, time_offset=200)
    streak_short = miss_streak([c0, c1, c2, c3])
    assert len(streak_short) == 3

    # If middle call hit cache, streak stops
    c_hit = _make_call(36_000, 30_000, time_offset=60)
    streak_hit = miss_streak([c1, c_hit, c3])
    assert len(streak_hit) == 1  # only newest c3


def test_cache_alerts_reports_misses_and_unreported_upstreams():
    now = 1_000_000.0
    # Conversation 1: 3 consecutive misses on up-1
    sess1_calls = [
        _make_call(35_000, 0, time_offset=120, upstream_id="up-1", session="s1"),
        _make_call(36_000, 0, time_offset=60, upstream_id="up-1", session="s1"),
        _make_call(37_000, 0, time_offset=10, upstream_id="up-1", session="s1"),
    ]
    # Another call from up-1 that did hit cache in the past 24h
    hit_call = _make_call(10_000, 8_000, time_offset=500, upstream_id="up-1", session="s_other")

    alerts = cache_alerts(sess1_calls + [hit_call], now=now)
    assert alerts is not None
    assert alerts["misses"] is not None
    assert alerts["misses"]["conversations"] == 1
    assert alerts["misses"]["streak"] == 3
    assert alerts["unreported"] == []

    # If up-1 never reported any cache hit anywhere, it should be in unreported
    alerts_unreported = cache_alerts(sess1_calls, now=now)
    assert alerts_unreported is not None
    assert "up-1" in alerts_unreported["unreported"]


def test_overview_summary_aggregates_first_call_and_continuation():
    now = 1_000_000.0
    logs = [
        # First call: 1000 input, 200 cached
        _make_call(1000, 200, kind="user"),
        # Continuation: 2000 input, 1500 cached
        _make_call(2000, 1500, kind="continuation"),
    ]
    summary = overview_summary(logs, now=now)
    assert summary["requests"] == 2
    assert summary["cache"]["first_call"]["input_tokens"] == 1000
    assert summary["cache"]["first_call"]["cached_tokens"] == 200
    assert summary["cache"]["first_call"]["cache_hit_ratio"] == 0.2

    assert summary["cache"]["continuation"]["input_tokens"] == 2000
    assert summary["cache"]["continuation"]["cached_tokens"] == 1500
    assert summary["cache"]["continuation"]["cache_hit_ratio"] == 0.75


@pytest.mark.asyncio
async def test_gateway_router_overview_and_alerts_endpoints():
    """Verify FastAPI router returns structured overview and cache alerts."""
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from openviking.server.routers.gateway import (
        clear_gateway_events,
        record_gateway_request_event,
        router,
    )

    app = FastAPI()
    app.include_router(router)
    clear_gateway_events()

    # Record two events
    record_gateway_request_event(_make_call(1000, 200, kind="user"))
    record_gateway_request_event(_make_call(2000, 1500, kind="continuation"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Overview
        resp = await client.get("/api/v1/gateway/overview")
        assert resp.status_code == 200
        data = resp.json()["result"]
        assert data["requests"] == 2
        assert data["cache"]["first_call"]["cached_tokens"] == 200

        # 2. Cache alerts
        resp_alerts = await client.get("/api/v1/gateway/cache-alerts")
        assert resp_alerts.status_code == 200
        alerts = resp_alerts.json()["result"]
        # No streak > 32k, so None
        assert alerts is None

    clear_gateway_events()

