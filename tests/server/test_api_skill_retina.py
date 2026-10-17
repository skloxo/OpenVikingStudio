# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Test skill retina audit and self-healing HTTP endpoints."""

import sys
import types
import pytest
from starlette.responses import PlainTextResponse


@pytest.fixture(autouse=True)
def _stub_mcp_endpoint(monkeypatch):
    module = types.ModuleType("openviking.server.mcp_endpoint")

    def create_mcp_app():
        async def _endpoint(_request):
            return PlainTextResponse("mcp stub")

        return _endpoint

    module.create_mcp_app = create_mcp_app
    monkeypatch.setitem(sys.modules, "openviking.server.mcp_endpoint", module)


@pytest.mark.asyncio
async def test_skill_retina_status_endpoint(client):
    """Test GET /api/v1/skills/retina/status returns physical audit report."""
    resp = await client.get("/api/v1/skills/retina/status")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ok"
    assert "user" in data["result"]
    assert "agent" in data["result"]
    assert "is_identical" in data["result"]


@pytest.mark.asyncio
async def test_skill_retina_audit_and_heal_endpoints(client):
    """Test POST /api/v1/skills/retina/audit and /heal."""
    # 1. Audit endpoint
    audit_resp = await client.post("/api/v1/skills/retina/audit")
    assert audit_resp.status_code == 200, audit_resp.text
    audit_data = audit_resp.json()
    assert audit_data["status"] == "ok"
    assert "is_identical" in audit_data["result"]

    # 2. Heal endpoint
    heal_resp = await client.post("/api/v1/skills/retina/heal")
    assert heal_resp.status_code == 200, heal_resp.text
    heal_data = heal_resp.json()
    assert heal_data["status"] == "ok"
    assert "total_healed" in heal_data["result"]
