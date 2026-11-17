# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""REST API tests for 5-Layer Memory Governance & Dream Snapshot Rollback (Card-168)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.memory_lifecycle import router
from openviking.service.entropy_gatekeeper import EntropyGatekeeper
from openviking.service.memory_conflict_resolver import MemoryConflictResolver
from openviking.service.memory_lifecycle_fsm import MemoryLifecycleStore, MemoryStatus
from openviking.service.memory_purity import MemoryPurityBenchmark
from openviking.service.offline_dreamer import OfflineDreamer
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def client(tmp_path: Path):
    db_file = tmp_path / "memory_lifecycle.db"
    MemoryLifecycleStore._instance = MemoryLifecycleStore(db_path=str(db_file))
    MemoryConflictResolver.reset_for_testing()
    OfflineDreamer.reset_for_testing()
    MemoryPurityBenchmark._instance = None
    EntropyGatekeeper._instance = None

    # Seed isolated fragments folder so /dream/run triggers real snapshot capture without touching user home
    src_dir = tmp_path / "master_memory" / "net_ops"
    src_dir.mkdir(parents=True)
    (src_dir / "tip1.md").write_text("---\ntopic: net_ops\n---\n# Tip 1\nAlways pass -TimeoutSec 5 to HTTP probes.\n", encoding="utf-8")
    (src_dir / "tip2.md").write_text("---\ntopic: net_ops\n---\n# Tip 2\nUse -m 3 on curl calls inside automation scripts.\n", encoding="utf-8")

    OfflineDreamer.get_instance(
        crystals_dir=tmp_path / "master_memory" / "crystals",
        ledger_path=tmp_path / "entropy_gatekeeper.jsonl",
        source_dir=tmp_path / "master_memory",
    )

    app = FastAPI()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="default", user_id="admin"),
        role=Role.ADMIN,
    )
    app.include_router(router)
    yield TestClient(app), tmp_path
    MemoryConflictResolver.reset_for_testing()
    OfflineDreamer.reset_for_testing()
    MemoryPurityBenchmark._instance = None
    EntropyGatekeeper._instance = None
    MemoryLifecycleStore._instance = None


def test_five_layer_governance_overview_and_dream_snapshot_rollback_endpoints(client):
    tc, _ = client

    # 1. Inspect 5-layer overview before dreaming
    ov1 = tc.get("/api/v1/memory/governance/layers")
    assert ov1.status_code == 200
    body1 = ov1.json()["result"]
    for key in (
        "layer1_ingestion_dedup",
        "layer2_conflict_dag",
        "layer3_temporal_decay",
        "layer4_offline_dreaming",
        "layer5_snapshot_and_purity",
    ):
        assert key in body1

    # 2. Run dream cycle -> creates real snapshot
    run_res = tc.post("/api/v1/memory/dream/run", json={"min_cluster_size": 2, "dry_run": False})
    assert run_res.status_code == 200
    snap_id = run_res.json()["result"]["snapshot_commit"]
    assert snap_id
    assert run_res.json()["result"]["master_cards_created"] == 1

    # 3. List recoverable snapshots
    snaps = tc.get("/api/v1/memory/dream/snapshots")
    assert snaps.status_code == 200
    assert snaps.json()["result"]["total"] == 1
    assert snaps.json()["result"]["items"][0]["snapshot_id"] == snap_id
    assert snaps.json()["result"]["items"][0]["rolled_back"] is False

    # 4. Execute rollback via API
    rb = tc.post("/api/v1/memory/dream/rollback", json={"snapshot_id": snap_id})
    assert rb.status_code == 200
    assert rb.json()["result"]["status"] == "rolled_back"
    assert rb.json()["result"]["removed_crystals"] == 1

    # Verify fragments are active again
    store = MemoryLifecycleStore.get_instance()
    assert store.get_record("viking://resources/master_memory/net_ops/tip1.md").status == MemoryStatus.ACTIVE

    # 5. Missing snapshot returns 404
    missing = tc.post("/api/v1/memory/dream/rollback", json={"snapshot_id": "snap_missing"})
    assert missing.status_code == 404
