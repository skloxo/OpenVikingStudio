# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Harness Cockpit API endpoints.
(Card-Observability-HarnessCockpit - v1.5.08)
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.system import router as system_router
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(system_router)
    mock_ctx = RequestContext(
        user=UserIdentifier(account_id="test", user_id="test_admin"),
        role=Role(Role.ADMIN),
    )
    app.dependency_overrides[get_request_context] = lambda: mock_ctx
    return TestClient(app)


def test_harness_metrics_contains_fsm_and_gates(client):
    """Assert /api/v1/system/harness_metrics returns FSM topology and gate invariants."""
    response = client.get("/api/v1/system/harness_metrics")
    assert response.status_code == 200
    data = response.json()

    # 1. FSM Topology assertions
    assert "fsm" in data
    fsm = data["fsm"]
    assert "states" in fsm
    assert "IDLE" in fsm["states"]
    assert "SPEC_INGEST" in fsm["states"]
    assert "VERIFY" in fsm["states"]
    assert "COMPLETED" in fsm["states"]
    assert len(fsm["states"]) >= 12
    assert len(fsm["pipeline"]) >= 8

    # 2. Gate Invariant assertions
    assert "gates" in data
    gates = data["gates"]
    assert "physical_diff" in gates
    assert "test_retina" in gates
    assert "anti_lazy" in gates
    assert "role_separation" in gates
    assert gates["physical_diff"]["status"] == "active"
    assert gates["anti_lazy"]["status"] == "active"


def test_anti_lazy_guard_detects_omissions(client):
    """Assert /api/v1/harness/test_guard blocks pass, TODO, and ellipsis stubs."""
    # 1. Block pass
    resp = client.post("/api/v1/harness/test_guard", json={"code": "def process():\n    pass"})
    assert resp.status_code == 200
    res = resp.json()
    assert res["blocked"] is True
    assert res["passed"] is False
    assert "pass" in res["matched_pattern"]

    # 2. Block TODO
    resp_todo = client.post("/api/v1/harness/test_guard", json={"code": "def fetch_data():\n    # TODO: implement later"})
    assert resp_todo.status_code == 200
    assert resp_todo.json()["blocked"] is True

    # 3. Block ellipsis
    resp_dots = client.post("/api/v1/harness/test_guard", json={"code": "class Evaluator:\n    ..."})
    assert resp_dots.status_code == 200
    assert resp_dots.json()["blocked"] is True

    # 4. Allow clean code
    clean_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    resp_clean = client.post("/api/v1/harness/test_guard", json={"code": clean_code})
    assert resp_clean.status_code == 200
    assert resp_clean.json()["blocked"] is False
    assert resp_clean.json()["passed"] is True


def test_verify_probe_diff_validation(client):
    """Assert /api/v1/harness/verify_probe accurately verifies physical diff text."""
    # 1. Pure comment diff should be rejected
    comment_diff = (
        "--- a/file.py\n"
        "+++ b/file.py\n"
        "@@ -1,1 +1,2 @@\n"
        " # Existing header\n"
        "+# Just a comment added\n"
    )
    resp = client.post("/api/v1/harness/verify_probe", json={"diff_text": comment_diff})
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is False
    assert data["diff_result"]["comments_only"] is True

    # 2. Genuine code diff should pass diff gate
    real_diff = (
        "--- a/file.py\n"
        "+++ b/file.py\n"
        "@@ -1,1 +1,3 @@\n"
        " def old():\n"
        "+    x = 10\n"
        "+    return x * 2\n"
    )
    resp2 = client.post("/api/v1/harness/verify_probe", json={"diff_text": real_diff})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["diff_result"]["is_valid"] is True
    assert data2["diff_result"]["effective_diff_lines"] == 2
