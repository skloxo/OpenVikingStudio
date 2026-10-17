# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Contract and behavioral tests for Skill Evolution Pipeline REST API and FastMCP Tool (Card-86)."""

import json
import pytest
from starlette.testclient import TestClient

from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role, UserIdentifier
import openviking.server.mcp_endpoint as mcp_endpoint


@pytest.fixture
def api_client():
    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    return TestClient(app)


def test_rest_api_clusters_discovery(api_client):
    """验证 GET /api/v1/skills/evolution/pipeline/clusters 正确发现同质候选簇。"""
    resp = api_client.get("/api/v1/skills/evolution/pipeline/clusters?min_cluster_size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "total_clusters" in data
    assert "clusters" in data
    assert isinstance(data["clusters"], list)


def test_rest_api_pipeline_run_dry_run(api_client):
    """验证 POST /api/v1/skills/evolution/pipeline/run 执行仿真干跑。"""
    resp = api_client.post(
        "/api/v1/skills/evolution/pipeline/run",
        json={"dry_run": True, "max_clusters": 2},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["dry_run"] is True
    assert "report" in data
    report = data["report"]
    assert "processed_clusters" in report
    assert "total_crystallized" in report
    assert "overall_attempt_pass_rate" in report


def test_rest_api_status_objective_metrics(api_client):
    """验证 GET /api/v1/skills/evolution/pipeline/status 返回 4 大前端客观指标锚定。"""
    resp = api_client.get("/api/v1/skills/evolution/pipeline/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    metrics = data["metrics"]
    assert "intent_collisions" in metrics
    assert "average_health_score" in metrics
    assert "s_grade_ratio" in metrics
    assert "attempt_pass_rate" in metrics
    assert metrics["average_health_score"] >= 0.0


def test_rest_api_rollback_endpoint(api_client):
    """验证 POST /api/v1/skills/evolution/pipeline/rollback 安全回滚端点。"""
    resp = api_client.post(
        "/api/v1/skills/evolution/pipeline/rollback",
        json={"quarantine_timestamp": None},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "noop")
    assert "restored_skills" in data


@pytest.mark.asyncio
async def test_fastmcp_skill_evolution_tool_preview():
    """验证 FastMCP 原生工具 openviking_skill_evolution_pipeline 的 preview 动作。"""
    raw_res = await mcp_endpoint.openviking_skill_evolution_pipeline(
        action="preview",
        max_clusters=2,
    )
    res = json.loads(raw_res)
    assert res["status"] == "ok"
    assert res["dry_run"] is True
    assert "report" in res


@pytest.mark.asyncio
async def test_fastmcp_skill_evolution_tool_status_and_rollback():
    """验证 FastMCP 原生工具 status 与 rollback 动作。"""
    status_raw = await mcp_endpoint.openviking_skill_evolution_pipeline(action="status")
    status_res = json.loads(status_raw)
    assert status_res["status"] == "ok"
    assert "metrics" in status_res
    assert "intent_collisions" in status_res["metrics"]

    rollback_raw = await mcp_endpoint.openviking_skill_evolution_pipeline(action="rollback")
    rollback_res = json.loads(rollback_raw)
    assert rollback_res["status"] in ("ok", "noop")


@pytest.mark.asyncio
async def test_fastmcp_skill_evolution_tool_invalid_action():
    """验证 FastMCP 原生工具对非法 action 的防御与提示。"""
    err_raw = await mcp_endpoint.openviking_skill_evolution_pipeline(action="destroy_everything")
    err_res = json.loads(err_raw)
    assert "error" in err_res
    assert "Unknown action" in err_res["error"]
