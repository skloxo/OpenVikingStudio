# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-207: REST API integration tests for Knowledge Deficit Capture & Remediation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.knowledge_deficits import router as deficits_router
from openviking.service.knowledge_deficit import BlindspotLedger
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def isolated_client(tmp_path: Path):
    ledger = BlindspotLedger(
        db_path=tmp_path / "api_deficits.db",
        deliverables_dir=tmp_path / "api_wiki",
        miss_threshold=3,
    )
    app = FastAPI()
    app.include_router(deficits_router)
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier("default", "api_tester"),
        role=Role.ADMIN,
    )
    with patch("openviking.server.routers.knowledge_deficits.BlindspotLedger.get_instance", return_value=ledger):
        yield TestClient(app), ledger


def test_knowledge_deficits_api_full_lifecycle(isolated_client):
    client, ledger = isolated_client

    # 1. Two misses stay observing
    for _ in range(2):
        r = client.post("/api/v1/knowledge-deficits/record-miss", json={"query": "OAuth PKCE 流程"})
        assert r.status_code == 200
        assert r.json()["result"]["status"] == "observing"

    # 2. Force-cast scaffold on observing item
    obs_id = ledger.list_deficits(status="observing")[0]["deficit_id"]
    cast = client.post(f"/api/v1/knowledge-deficits/{obs_id}/scaffold")
    assert cast.status_code == 200
    assert cast.json()["result"]["status"] == "pending_fulfillment"
    assert cast.json()["result"]["suggested_route"] == "autonomous_researcher"

    # 3. Fulfill via Stage-2 researcher track and confirm summary state-flip
    ful = client.post(
        f"/api/v1/knowledge-deficits/{obs_id}/fulfill",
        json={"content": "RFC 7636 S256 code_challenge 规范已补齐。", "track": "autonomous_researcher"},
    )
    assert ful.status_code == 200
    assert ful.json()["result"]["status"] == "fulfilled"

    summary = client.get("/api/v1/knowledge-deficits/summary").json()["result"]
    assert summary["pending_fulfillment_count"] == 0
    assert summary["fulfilled_count"] == 1

    # 4. Separate entry dismiss test
    r_noise = client.post("/api/v1/knowledge-deficits/record-miss", json={"query": "临时调试噪音词汇"})
    noise_id = r_noise.json()["result"]["deficit_id"]
    dis = client.post(f"/api/v1/knowledge-deficits/{noise_id}/dismiss", json={"reason": "false_positive"})
    assert dis.status_code == 200
    assert dis.json()["result"]["status"] == "dismissed"
