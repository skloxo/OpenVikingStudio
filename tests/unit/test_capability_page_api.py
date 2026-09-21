"""
Unit tests for Capability Pages & Negative Boundary Router REST API.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.capability_page import router as capability_page_router
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(capability_page_router)

    async def _mock_ctx() -> RequestContext:
        return RequestContext(
            user_id=UserIdentifier("test-user"),
            role=Role.ADMIN,
            auth_mode="dev",
        )

    app.dependency_overrides[get_request_context] = _mock_ctx
    return TestClient(app)


def test_list_capability_pages(client: TestClient) -> None:
    res = client.get("/api/v1/capability-pages")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert any(p["skill_id"] == "docker_inspect_logs" for p in data)


def test_create_and_get_capability_page(client: TestClient) -> None:
    payload = {
        "skill_id": "api_test_skill",
        "skill_name": "API 测试技能",
        "cluster_id": "test_cluster",
        "positive_triggers": ["执行测试", "运行 pytest"],
        "negative_boundaries": ["DO NOT use for '构建生产包'"],
        "summary": "自动运行测试套件并收集覆盖率指标。",
        "prerequisites": ["pytest installed"],
        "inputs": {"test_path": "string"},
        "outputs": {"passed": "boolean"},
    }
    create_res = client.post("/api/v1/capability-pages", json=payload)
    assert create_res.status_code == 200
    created = create_res.json()
    assert created["skill_id"] == "api_test_skill"

    get_res = client.get("/api/v1/capability-pages/api_test_skill")
    assert get_res.status_code == 200
    assert get_res.json()["skill_name"] == "API 测试技能"


def test_contrast_neighbors_api(client: TestClient) -> None:
    res = client.post(
        "/api/v1/capability-pages/contrast-neighbors",
        json={"target_skill_id": "docker_inspect_logs"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["target_skill_id"] == "docker_inspect_logs"
    assert data["cluster_id"] == "container_ops"
    assert "docker_restart_service" in data["neighbor_skill_ids"]
    assert len(data["suggested_negative_boundaries"]) > 0


def test_route_api(client: TestClient) -> None:
    # 1. Clear query route
    res = client.post(
        "/api/v1/capability-pages/route",
        json={"query": "查看 Docker 容器运行日志", "cluster_id": "container_ops"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["selected_skill_id"] == "docker_inspect_logs"
    assert len(data["candidates"]) >= 1

    # 2. Conflicting query route (restart container)
    restart_res = client.post(
        "/api/v1/capability-pages/route",
        json={"query": "重启容器", "cluster_id": "container_ops"},
    )
    assert restart_res.status_code == 200
    restart_data = restart_res.json()
    assert restart_data["selected_skill_id"] == "docker_restart_service"

    # 3. Metrics summary
    metrics_res = client.get("/api/v1/capability-pages/metrics/summary")
    assert metrics_res.status_code == 200
    m_data = metrics_res.json()
    assert m_data["total_routes"] >= 2
    assert "top1_discrimination_gain_pct" in m_data
