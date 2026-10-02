# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Agent Autonomous Issue Filing & Task Card Lifecycle.

Validates the Charlie Munger Inversion & Occam's Razor System:
1. Agent can file a high-fidelity task card for system bugs (504, silent drop, etc.).
2. Deduplication & Anti-Card-Storm: Repeated errors with the same fingerprint atomically
   increment occurrence_count and merge affected_agents, never flooding the inbox.
3. Blame-Shift Guard: 4xx client errors (bad args) are rejected from system bug filing.
4. Master Agent Discovery: Pending cards can be retrieved by priority for triage.
5. Lifecycle Resolution: Resolving a card updates status, records resolution Git tag/hash.
"""

import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def clean_inbox(tmp_path, monkeypatch):
    """Isolate inbox directory during tests."""
    from openviking.service.task_card_manager import TaskCardManager

    mgr = TaskCardManager.get_instance()
    mgr._inbox_dir = tmp_path / "task_cards" / "inbox"
    mgr._inbox_dir.mkdir(parents=True, exist_ok=True)
    mgr._resolved_dir = tmp_path / "task_cards" / "resolved"
    mgr._resolved_dir.mkdir(parents=True, exist_ok=True)
    yield


@pytest.mark.asyncio
async def test_file_first_system_bug_card():
    """Verify first-time bug report creates a structured task card with unique fingerprint."""
    from openviking.service.task_card_manager import TaskCardManager

    mgr = TaskCardManager.get_instance()
    res = await mgr.file_issue_card(
        title="Card-Issue-Valet-HighSim-Overwrite-Silent-Drop",
        priority="P0",
        module="storage/gatekeeper",
        symptom="Updating 20KB document returned parked but disk kept old version. Sim was 0.985.",
        initiator="workbuddy@rtx3070",
        root_cause_hypothesis="Entropy gatekeeper misclassified Sim>=0.95 as NOOP.",
        reproduce_steps="Call valet ingestion with Sim>=0.95 on existing URI.",
        suggested_action="Add Overwrite Immunity check.",
    )

    assert res["status"] == "created"
    assert res["action"] == "new_card"
    assert res["occurrence_count"] == 1
    assert "workbuddy@rtx3070" in res["affected_agents"]
    card_id = res["card_id"]
    assert card_id.startswith("Card-Issue-")

    # Physical verification: JSON file must exist in inbox
    card_path = mgr._inbox_dir / f"{card_id}.json"
    assert card_path.exists()


@pytest.mark.asyncio
async def test_card_flooding_dedup_and_aggregation():
    """Verify multiple occurrences of the same bug increment occurrence_count rather than creating duplicate cards."""
    from openviking.service.task_card_manager import TaskCardManager

    mgr = TaskCardManager.get_instance()

    # Occurrence 1 from WorkBuddy
    res1 = await mgr.file_issue_card(
        title="Gateway 504 Timeout on Embedding Generation",
        priority="P1",
        module="server/router/content",
        symptom="HTTP 504 Gateway Timeout during probe_nearest_vector.",
        initiator="workbuddy@rtx3070",
    )
    assert res1["status"] == "created"
    assert res1["occurrence_count"] == 1
    first_card_id = res1["card_id"]

    # Occurrence 2 from XiaomiMo (same module and symptom pattern)
    res2 = await mgr.file_issue_card(
        title="Gateway 504 Timeout on Embedding Generation",
        priority="P1",
        module="server/router/content",
        symptom="HTTP 504 Gateway Timeout during probe_nearest_vector.",
        initiator="xiaomimo@rtx3070",
    )

    # Must be aggregated, NOT duplicated!
    assert res2["status"] == "aggregated"
    assert res2["card_id"] == first_card_id
    assert res2["occurrence_count"] == 2
    assert "workbuddy@rtx3070" in res2["affected_agents"]
    assert "xiaomimo@rtx3070" in res2["affected_agents"]

    # Only 1 card file must exist in inbox
    json_files = list(mgr._inbox_dir.glob("*.json"))
    assert len(json_files) == 1


@pytest.mark.asyncio
async def test_client_bad_request_rejected():
    """Verify 4xx client errors (bad parameters) are rejected to prevent blaming server for client bugs."""
    from openviking.service.task_card_manager import TaskCardManager

    mgr = TaskCardManager.get_instance()

    with pytest.raises(ValueError) as exc_info:
        await mgr.file_issue_card(
            title="My Script Crashed",
            priority="P0",
            module="client/caller",
            symptom="HTTP 400 Bad Request: Missing required query parameter 'uri'.",
            initiator="test_subagent",
        )

    assert "400" in str(exc_info.value) or "客户端" in str(exc_info.value) or "Bad Request" in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_pending_cards_for_master_triage():
    """Verify Antigravity can list all pending cards sorted by priority for proactive triage."""
    from openviking.service.task_card_manager import TaskCardManager

    mgr = TaskCardManager.get_instance()

    await mgr.file_issue_card(
        title="Low Priority UI Glitch",
        priority="P2",
        module="ui/cockpit",
        symptom="Badge color slightly offset on dark mode.",
        initiator="designer@2080ti",
    )
    await mgr.file_issue_card(
        title="Critical Data Corruption in WAL",
        priority="P0",
        module="storage/viking_fs",
        symptom="Crash during snapshot commit.",
        initiator="tester@3070",
    )

    pending = await mgr.list_pending_cards()
    assert len(pending) == 2
    # P0 must precede P2
    assert pending[0]["priority"] == "P0"
    assert pending[1]["priority"] == "P2"


@pytest.mark.asyncio
async def test_resolve_card_lifecycle():
    """Verify resolving a card archives it and records delivery metadata."""
    from openviking.service.task_card_manager import TaskCardManager

    mgr = TaskCardManager.get_instance()

    res = await mgr.file_issue_card(
        title="Memory Leak in WebSocket Stream",
        priority="P1",
        module="server/stream",
        symptom="RSS increased by 500MB over 24h.",
        initiator="operator@macstudio",
    )
    card_id = res["card_id"]

    # Master Agent resolves the card
    resolve_res = await mgr.resolve_card(
        card_id=card_id,
        resolution_tag="v1.6.4",
        commit_hash="abc12345",
        summary="Fixed unclosed generator in stream handler.",
    )

    assert resolve_res["status"] == "resolved"
    assert resolve_res["resolution_tag"] == "v1.6.4"

    # Must no longer be in pending
    pending = await mgr.list_pending_cards()
    assert len(pending) == 0

    # Must be moved to resolved directory
    assert (mgr._resolved_dir / f"{card_id}.json").exists()
    assert not (mgr._inbox_dir / f"{card_id}.json").exists()


def test_task_cards_http_api_endpoints():
    """Verify FastAPI endpoints for filing and listing task cards via TestClient."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from openviking.server.auth import get_request_context
    from openviking.server.identity import RequestContext, UserIdentifier, Role
    from openviking.server.routers.task_cards import router as task_cards_router

    app = FastAPI()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test_acc", user_id="test_user"),
        role=Role.ROOT,
    )
    app.include_router(task_cards_router)
    client = TestClient(app)

    # 1. File via HTTP POST
    resp = client.post(
        "/api/v1/task-cards/file",
        json={
            "title": "API Gateway 504 on High Concurrency",
            "priority": "P1",
            "module": "server/gateway",
            "symptom": "Upstream timeout after 30s under load.",
            "hypothesis": "Connection pool exhausted.",
            "reproduce_steps": "Run 50 parallel requests.",
            "agent_id": "tester@3070",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["result"]["status"] == "created"
    card_id = data["result"]["card_id"]

    # 2. List pending via HTTP GET
    list_resp = client.get("/api/v1/task-cards/pending")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["status"] == "ok"
    pending_list = list_data["result"]["cards"]
    assert any(c["card_id"] == card_id for c in pending_list)
