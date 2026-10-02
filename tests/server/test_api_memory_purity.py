# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Server API endpoint tests for Memory Purity Benchmark, Governance Stream, and Watchdog Enforcement.
(Card-38 / v1.6.2)
"""

import json
import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.memory_lifecycle import router
from openviking.service.memory_lifecycle_fsm import MemoryLifecycleStore
from openviking.service.offline_dreamer import OfflineDreamer, DreamCycleResult
from openviking.service.memory_purity import MemoryPurityBenchmark
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def client(tmp_path):
    """Setup test client with mock admin context and clean stores."""
    db_file = tmp_path / "memory_lifecycle.db"
    store = MemoryLifecycleStore(db_path=str(db_file))
    MemoryLifecycleStore._instance = store
    OfflineDreamer.reset_for_testing()
    MemoryPurityBenchmark._instance = None

    app = FastAPI()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="default", user_id="test_admin"),
        role=Role.ADMIN,
    )
    app.include_router(router)
    yield TestClient(app)
    OfflineDreamer.reset_for_testing()
    MemoryPurityBenchmark._instance = None
    MemoryLifecycleStore._instance = None


def test_api_purity_report(client):
    """Verify GET /api/v1/memory/purity/report returns valid purity telemetry."""
    resp = client.get("/api/v1/memory/purity/report")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    res = data["result"]
    assert "snr_ratio" in res
    assert "conflict_rate" in res
    assert "freshness_retained" in res
    assert "purity_score" in res
    assert 0 <= res["purity_score"] <= 100
    assert "watchdog_status" in res


def test_api_governance_stream(client, tmp_path):
    """Verify GET /api/v1/memory/governance/stream retrieves chronological audit events."""
    bench = MemoryPurityBenchmark.get_instance()
    ledger_path = tmp_path / "entropy_gatekeeper.jsonl"
    bench.ledger_path = ledger_path

    # Write dummy records
    events = [
        {"action": "add", "uri": "viking://resources/1.md", "reason": "Init", "timestamp": 100.0},
        {"type": "DREAM_CONSOLIDATION", "master_card_uri": "viking://crystals/m1.md", "theme": "arch", "fragments_consolidated": 3, "timestamp": 200.0},
    ]
    with open(ledger_path, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

    resp = client.get("/api/v1/memory/governance/stream?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    res = data["result"]
    assert len(res) == 2
    assert res[0]["type"] == "DREAM_CONSOLIDATION"
    assert res[1]["type"] == "INGRESS_ADMISSION"


def test_api_watchdog_enforce(client):
    """Verify POST /api/v1/memory/watchdog/enforce invokes watchdog evaluation."""
    with patch.object(OfflineDreamer, "run_dream_cycle") as mock_dream:
        mock_dream.return_value = DreamCycleResult(
            status="ok",
            dream_id="mock_api_dream",
            theme="watchdog_force_enforce",
            fragments_consolidated=4,
            master_cards_created=1,
            net_entropy_reduced=3,
            duration_ms=2.1,
        )

        resp = client.post(
            "/api/v1/memory/watchdog/enforce",
            json={"dry_run": True, "force": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        res = data["result"]
        assert res["triggered"] is True
        assert res["reason"] == "force_enforce"
        assert "dream_cycle" in res
