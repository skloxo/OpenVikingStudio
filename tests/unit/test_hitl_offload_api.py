# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for HITL and Read-Side Offload Telemetry & API (v1.5.12).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.core.hitl_gate import HITLGate, DangerousActionPolicy
from openviking.core.hitl_offload_telemetry import HITLOffloadTelemetry
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.hitl_offload import router as hitl_offload_router
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture(autouse=True)
def reset_telemetry():
    telemetry = HITLOffloadTelemetry()
    telemetry.reset_for_tests()
    gate = HITLGate()
    telemetry.set_hitl_gate(gate)
    yield
    telemetry.reset_for_tests()


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(hitl_offload_router)
    mock_ctx = RequestContext(
        user=UserIdentifier(account_id="test", user_id="test_admin"),
        role=Role(Role.ADMIN),
    )
    app.dependency_overrides[get_request_context] = lambda: mock_ctx
    return TestClient(app)


def test_hitl_offload_telemetry_singleton():
    t1 = HITLOffloadTelemetry()
    t2 = HITLOffloadTelemetry()
    assert t1 is t2


def test_read_offload_recording():
    telemetry = HITLOffloadTelemetry()
    record = telemetry.record_read_offload(
        target_path="openviking/pipeline/orchestrator.py",
        total_lines=1500,
        total_bytes=56000,
        content_hash="abc1234567890",
    )
    assert record.ref_id.startswith("ref_")
    assert record.total_lines == 1500
    assert record.tokens_saved > 0
    assert record.estimated_raw_tokens == 14000
    assert record.estimated_offloaded_tokens == 350

    snapshot = telemetry.get_metrics_snapshot()
    assert snapshot["summary"]["active_refs_count"] >= 1
    assert snapshot["summary"]["total_tokens_saved"] > 0
    assert snapshot["summary"]["reduction_ratio_pct"] > 50.0


def test_hitl_dangerous_intercept_and_resolve():
    telemetry = HITLOffloadTelemetry()
    gate = HITLGate()
    telemetry.set_hitl_gate(gate)

    # 1. Record intercept
    item = telemetry.record_dangerous_intercept(
        tool_name="deploy_production",
        args_summary="env='prod', force=True",
        danger_reason="工具属于受限工具",
        phase="spec_review",
    )
    assert item.status == "pending"
    assert item.action_id in [p["action_id"] for p in telemetry.get_metrics_snapshot()["hitl_queue"]["pending"]]

    # 2. Approve
    approved = telemetry.resolve_action(
        action_id=item.action_id,
        decision="approve",
        resolved_by="admin@test",
        comment="测试核准",
    )
    assert approved is not None
    assert approved.status == "approved"
    assert approved.resolved_by == "admin@test"
    # Verify token is granted to gate
    assert approved.approval_token in gate.policy.valid_approval_tokens

    # 3. Record another and reject
    item2 = telemetry.record_dangerous_intercept(
        tool_name="rm_rf",
        args_summary="path='/var/log'",
        danger_reason="命令破坏性",
        phase="testing",
    )
    rejected = telemetry.resolve_action(
        action_id=item2.action_id,
        decision="reject",
        resolved_by="security@test",
        comment="拒绝删除生产日志",
    )
    assert rejected is not None
    assert rejected.status == "rejected"
    assert rejected.approval_token not in gate.policy.valid_approval_tokens


def test_api_hitl_offload_metrics(client: TestClient):
    resp = client.get("/api/v1/system/hitl_offload_metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "read_offload" in data
    assert "hitl_queue" in data
    assert data["summary"]["total_tokens_saved"] >= 0
    assert data["summary"]["danger_interception_rate_pct"] == 100.0


def test_api_hitl_resolve(client: TestClient):
    # First create a pending action via probe
    resp_probe = client.post(
        "/api/v1/hitl/probe",
        json={
            "probe_type": "simulate_hitl_intercept",
            "tool_name": "delete_all",
            "command": "rm -rf /",
        },
    )
    assert resp_probe.status_code == 200
    target_id = resp_probe.json()["action"]["action_id"]

    # Resolve with approve
    resp_resolve = client.post(
        "/api/v1/hitl/resolve",
        json={"action_id": target_id, "decision": "approve", "comment": "API测试批准"},
    )
    assert resp_resolve.status_code == 200
    res = resp_resolve.json()
    assert res["status"] == "ok"
    assert res["action"]["status"] == "approved"

    # Verify action moved to history
    resp_after = client.get("/api/v1/system/hitl_offload_metrics")
    data_after = resp_after.json()
    history_ids = [h["action_id"] for h in data_after["hitl_queue"]["history"]]
    assert target_id in history_ids


def test_api_hitl_probes(client: TestClient):
    # 1. Simulate read offload probe
    resp1 = client.post(
        "/api/v1/hitl/probe",
        json={
            "probe_type": "simulate_read_offload",
            "target_path": "openviking/probe_file.py",
            "line_count": 2200,
        },
    )
    assert resp1.status_code == 200
    res1 = resp1.json()
    assert res1["status"] == "ok"
    assert res1["record"]["total_lines"] == 2200
    assert res1["record"]["tokens_saved"] > 0

    # 2. Simulate HITL dangerous intercept probe
    resp2 = client.post(
        "/api/v1/hitl/probe",
        json={
            "probe_type": "simulate_hitl_intercept",
            "tool_name": "run_command",
            "command": "rm -rf /tmp/scratch/*",
        },
    )
    assert resp2.status_code == 200
    res2 = resp2.json()
    assert res2["status"] == "ok"
    assert res2["action"]["status"] == "pending"
    action_id = res2["action"]["action_id"]

    # 3. Reject simulated action
    resp3 = client.post(
        "/api/v1/hitl/resolve",
        json={"action_id": action_id, "decision": "reject"},
    )
    assert resp3.status_code == 200
    assert resp3.json()["action"]["status"] == "rejected"
