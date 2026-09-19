# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for AHE (Automated Harness Evolution) REST API router.

测试所有 8 个端点:
  - POST /api/v1/ahe/manifest
  - GET  /api/v1/ahe/manifest
  - GET  /api/v1/ahe/manifest/{manifest_id}
  - POST /api/v1/ahe/manifest/{manifest_id}/verify
  - POST /api/v1/ahe/manifest/{manifest_id}/violate
  - GET  /api/v1/ahe/manifest/{manifest_id}/drift
  - GET  /api/v1/ahe/clusters
  - GET  /api/v1/ahe/summary
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
from openviking.server.routers.ahe import router as ahe_router
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(ahe_router)
    mock_ctx = RequestContext(
        user=UserIdentifier(account_id="test", user_id="test_admin"),
        role=Role(Role.ADMIN),
    )
    app.dependency_overrides[get_request_context] = lambda: mock_ctx
    return TestClient(app)


def test_ahe_api_full_lifecycle(client):
    """测试 AHE REST API 完整生命周期闭环。"""
    # 1. 创建 Manifest
    create_payload = {
        "skill_name": "api-test-skill",
        "assumptions": [
            {
                "description": "True assumption",
                "validation_command": "python3 -c 'exit(0)'",
            }
        ],
        "snapshot_paths": [],
    }
    resp = client.post("/api/v1/ahe/manifest", json=create_payload)
    assert resp.status_code == 200
    manifest = resp.json()
    manifest_id = manifest["manifest_id"]
    assert manifest_id.startswith("ahe-")
    assert manifest["skill_name"] == "api-test-skill"

    # 2. 单个获取
    resp = client.get(f"/api/v1/ahe/manifest/{manifest_id}")
    assert resp.status_code == 200
    assert resp.json()["manifest_id"] == manifest_id

    # 3. 列表获取 (GET /api/v1/ahe/manifest)
    resp = client.get("/api/v1/ahe/manifest")
    assert resp.status_code == 200
    manifests = resp.json()
    assert any(m["manifest_id"] == manifest_id for m in manifests)

    # 4. Polar 判官验证 (POST /api/v1/ahe/manifest/{manifest_id}/verify)
    resp = client.post(f"/api/v1/ahe/manifest/{manifest_id}/verify")
    assert resp.status_code == 200
    verify_data = resp.json()
    assert verify_data["status"] == "verified"
    assert verify_data["results"][0]["verdict"] == "pass"

    # 5. 快照漂移检测 (GET /api/v1/ahe/manifest/{manifest_id}/drift)
    resp = client.get(f"/api/v1/ahe/manifest/{manifest_id}/drift")
    assert resp.status_code == 200
    drift_data = resp.json()
    assert drift_data["snapshot_clean"] is True

    # 6. 违规归因聚类 (POST /api/v1/ahe/manifest/{manifest_id}/violate)
    violation_payload = {
        "mechanism": "tool_interface",
        "description": "API signature mismatch in test",
    }
    resp = client.post(f"/api/v1/ahe/manifest/{manifest_id}/violate", json=violation_payload)
    assert resp.status_code == 200
    violation_data = resp.json()
    assert violation_data["mechanism"] == "tool_interface"

    # 7. 聚类目录列表 (GET /api/v1/ahe/clusters)
    resp = client.get("/api/v1/ahe/clusters")
    assert resp.status_code == 200
    data = resp.json()
    assert "clusters" in data
    assert "summary" in data
    assert len(data["clusters"]) >= 1

    # 8. 全局汇总 (GET /api/v1/ahe/summary)
    resp = client.get("/api/v1/ahe/summary")
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["manifests"]["total"] >= 1
    assert summary["clusters"]["total_clusters"] >= 1
