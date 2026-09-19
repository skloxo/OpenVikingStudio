# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for RSI REST API router.

测试端点:
  - GET  /api/v1/rsi/status
  - POST /api/v1/rsi/phase/switch
  - POST /api/v1/rsi/trajectory/record
  - POST /api/v1/rsi/credit/evaluate
  - POST /api/v1/rsi/surface/inspect
  - POST /api/v1/rsi/surface/update
  - POST /api/v1/rsi/gate/verify_split
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
from openviking.server.routers.rsi import router as rsi_router
from openviking_cli.session.user_id import UserIdentifier

SAMPLE_SKILL = """---
name: rsi-skill
---
# Static Header
# EVOLVE-BLOCK-START
rule_v1 = True
# EVOLVE-BLOCK-END
# Static Footer
"""


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(rsi_router)
    mock_ctx = RequestContext(
        user=UserIdentifier(account_id="test", user_id="test_admin"),
        role=Role(Role.ADMIN),
    )
    app.dependency_overrides[get_request_context] = lambda: mock_ctx
    return TestClient(app)


def test_rsi_api_lifecycle(client):
    """测试 RSI REST API 完整生命周期。"""
    # 1. 状态查询
    resp = client.get("/api/v1/rsi/status")
    assert resp.status_code == 200
    assert "current_phase" in resp.json()

    # 2. 昼夜模式切换
    resp = client.post("/api/v1/rsi/phase/switch", json={"target_phase": "nighttime_dreaming"})
    assert resp.status_code == 200
    assert resp.json()["current_phase"] == "nighttime_dreaming"

    # 3. 收集轨迹回合
    rec_payload = {
        "session_id": "rsi-api-sess",
        "turn_data": {"turn_id": 0, "student_log_prob": -2.0, "teacher_log_prob": -0.1},
    }
    resp = client.post("/api/v1/rsi/trajectory/record", json=rec_payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "recorded"

    # 4. 局部信用分配
    eval_payload = {"session_id": "rsi-api-sess"}
    resp = client.post("/api/v1/rsi/credit/evaluate", json=eval_payload)
    assert resp.status_code == 200
    assert resp.json()["total_turns"] == 1

    # 5. Surface 审查
    resp = client.post("/api/v1/rsi/surface/inspect", json={"raw_text": SAMPLE_SKILL})
    assert resp.status_code == 200
    insp = resp.json()
    assert insp["has_evolve_blocks"] is True
    assert insp["block_count"] == 1

    # 6. Surface 有界更新
    update_payload = {
        "raw_text": SAMPLE_SKILL,
        "block_index": 0,
        "new_content": "rule_v2 = True\n",
    }
    resp = client.post("/api/v1/rsi/surface/update", json=update_payload)
    assert resp.status_code == 200
    assert "rule_v2 = True" in resp.json()["updated_text"]

    # 7. 双 Split 门禁
    gate_payload = {
        "train_results": [True, True, True],
        "holdout_results": [True, True, True, True],
        "baseline_holdout_pass_rate": 0.8,
    }
    resp = client.post("/api/v1/rsi/gate/verify_split", json=gate_payload)
    assert resp.status_code == 200
    assert resp.json()["passed"] is True
