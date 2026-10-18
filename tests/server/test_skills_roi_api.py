# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""API integration tests for Skill ROI and Telemetry endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from openviking.server.routers.skills import router as skills_router
from openviking.server.auth import get_request_context
from openviking.server.dependencies import set_service
from openviking.server.identity import RequestContext, Role
from openviking.service.skill_telemetry import SkillTelemetryStore
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
async def client():
    app = FastAPI()
    app.include_router(skills_router)

    # Mock service & auth context
    mock_service = MagicMock()
    mock_fs = AsyncMock()
    mock_fs.list_entries.return_value = []
    mock_service.fs = mock_fs
    set_service(mock_service)

    mock_ctx = RequestContext(user=UserIdentifier.the_default_user(), role=Role.ROOT)
    app.dependency_overrides[get_request_context] = lambda: mock_ctx

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    set_service(None)


class TestSkillRoiApi:
    """Test /api/v1/skills/telemetry endpoints."""

    @pytest.mark.asyncio
    async def test_roi_telemetry_get_and_record(self, client: AsyncClient):
        # 1. Post a telemetry record
        payload = {
            "skill_id": "test-quant-strategy",
            "bundle_name": "quant-trading",
            "event_type": "invoke",
            "success": True,
            "tokens_saved": 3500,
            "latency_ms": 32.5,
            "caller_agent": "test_agent",
        }
        res_post = await client.post("/api/v1/skills/telemetry/record", json=payload)
        assert res_post.status_code == 200
        data_post = res_post.json()
        assert data_post["status"] == "ok"
        assert data_post["result"]["event_id"] > 0

        # 2. Get ROI telemetry report
        res_get = await client.get("/api/v1/skills/telemetry/roi?days=30")
        assert res_get.status_code == 200
        data_get = res_get.json()
        assert data_get["status"] == "ok"
        res_body = data_get["result"]
        assert "summary" in res_body
        assert "top_roi_skills" in res_body
        assert "bundle_rankings" in res_body
        assert "dormant_warnings" in res_body
        assert res_body["summary"]["total_invocations"] >= 1

        # Check that test-quant-strategy is reflected
        top_ids = [item["skill_id"] for item in res_body["top_roi_skills"]]
        assert "test-quant-strategy" in top_ids

    @pytest.mark.asyncio
    async def test_list_skills_with_roi_sort(self, client: AsyncClient):
        res = await client.get("/api/v1/skills?sort_by=roi")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["result"]["sort_by"] == "roi"
        assert isinstance(data["result"]["skills"], list)
