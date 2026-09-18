# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Tests for queue endpoints (/api/v1/queue/*)."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_queue_status_api(client: httpx.AsyncClient):
    """GET /api/v1/queue/status should return structured queue statuses."""
    resp = await client.get("/api/v1/queue/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    result = body["result"]
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_queue_dlq_api(client: httpx.AsyncClient):
    """GET /api/v1/queue/dlq should return DLQ entries list."""
    resp = await client.get("/api/v1/queue/dlq")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    result = body["result"]
    assert "total" in result
    assert "entries" in result
    assert isinstance(result["entries"], list)


@pytest.mark.asyncio
async def test_queue_retry_failed_api(client: httpx.AsyncClient):
    """POST /api/v1/queue/retry_failed should trigger self-healing replay."""
    resp = await client.post("/api/v1/queue/retry_failed", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    result = body["result"]
    assert result["success"] is True
    assert "retried_count" in result
    assert "remaining_dlq_count" in result


@pytest.mark.asyncio
async def test_queue_clear_dlq_api(client: httpx.AsyncClient):
    """POST /api/v1/queue/clear_dlq should clear DLQ and return cleared count."""
    resp = await client.post("/api/v1/queue/clear_dlq", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    result = body["result"]
    assert "cleared_count" in result
