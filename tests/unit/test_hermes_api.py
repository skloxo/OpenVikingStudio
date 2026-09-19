# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Hermes REST API endpoints.

覆盖端点:
  - POST /api/v1/hermes/experience
  - GET  /api/v1/hermes/experience/search
  - GET  /api/v1/hermes/experience/session/{session_id}
  - POST /api/v1/hermes/nudge/trigger
  - GET  /api/v1/hermes/nudge/status
  - POST /api/v1/hermes/patch/propose
  - POST /api/v1/hermes/patch/{patch_id}/apply
  - POST /api/v1/hermes/patch/{patch_id}/revert
  - GET  /api/v1/hermes/patches
  - GET  /api/v1/hermes/summary
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.hermes import router as hermes_router
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(hermes_router)
    mock_ctx = RequestContext(
        user=UserIdentifier(account_id="test", user_id="test_admin"),
        role=Role(Role.ADMIN),
    )
    app.dependency_overrides[get_request_context] = lambda: mock_ctx
    return TestClient(app)


def test_hermes_api_lifecycle(client):
    """测试 Hermes API 完整生命周期。"""
    # 1. 记录经历
    exp_payload = {
        "session_id": "api-sess-1",
        "role": "user",
        "content": "Testing Hermes API with FTS5 search",
    }
    resp = client.post("/api/v1/hermes/experience", json=exp_payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "recorded"

    # 2. 会话经历获取
    resp = client.get("/api/v1/hermes/experience/session/api-sess-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert data["messages"][0]["content"] == "Testing Hermes API with FTS5 search"

    # 3. FTS5 检索
    resp = client.get("/api/v1/hermes/experience/search", params={"q": "Hermes"})
    assert resp.status_code == 200
    search_data = resp.json()
    assert search_data["total_matches"] >= 1

    # 4. 触发 Nudge
    resp = client.post("/api/v1/hermes/nudge/trigger", json={"session_id": "api-sess-1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"

    # 5. Nudge 状态
    resp = client.get("/api/v1/hermes/nudge/status")
    assert resp.status_code == 200
    assert "completed_reviews" in resp.json()

    # 6. 微补丁流程 (Propose -> Apply -> Revert)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("VAL = 10\n")
        temp_file = f.name

    try:
        patch_payload = {
            "skill_name": "config-skill",
            "file_path": temp_file,
            "target_content": "VAL = 10",
            "replacement_content": "VAL = 20",
            "reason": "Update config value",
        }
        resp = client.post("/api/v1/hermes/patch/propose", json=patch_payload)
        assert resp.status_code == 200
        patch = resp.json()
        patch_id = patch["patch_id"]

        # 应用补丁
        resp = client.post(f"/api/v1/hermes/patch/{patch_id}/apply")
        assert resp.status_code == 200
        assert resp.json()["status"] == "applied"
        assert "VAL = 20" in Path(temp_file).read_text(encoding="utf-8")

        # 回滚补丁
        resp = client.post(f"/api/v1/hermes/patch/{patch_id}/revert")
        assert resp.status_code == 200
        assert resp.json()["status"] == "reverted"
        assert "VAL = 10" in Path(temp_file).read_text(encoding="utf-8")

        # 补丁列表
        resp = client.get("/api/v1/hermes/patches")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

        # 全局汇总
        resp = client.get("/api/v1/hermes/summary")
        assert resp.status_code == 200
        summary = resp.json()
        assert "experience" in summary
        assert "nudge" in summary
        assert "patches" in summary
    finally:
        Path(temp_file).unlink(missing_ok=True)
