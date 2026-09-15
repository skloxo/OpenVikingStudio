# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Card-Observability-MemoryQuarantine-Dashboard (v1.5.10).
Validates quarantine manager, manifest aggregation, search filtering, and dry-run restore probe.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.core.quarantine_manager import QuarantineManager
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.quarantine import router as quarantine_router
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(quarantine_router)
    mock_ctx = RequestContext(
        user=UserIdentifier(account_id="test", user_id="test_admin"),
        role=Role(Role.ADMIN),
    )
    app.dependency_overrides[get_request_context] = lambda: mock_ctx
    return TestClient(app)


def test_quarantine_manager_snapshot_aggregation():
    """Verify that QuarantineManager correctly loads and aggregates cold archive manifests."""
    manager = QuarantineManager.get_instance()
    snapshot = manager.get_snapshot(limit=10, force_refresh=True)

    # 1,159 zombie sessions + 5 staging sessions = 1,164 total targets
    assert snapshot.total_quarantined_targets >= 1164
    assert snapshot.total_quarantined_files >= 4300
    assert snapshot.total_quarantined_mb > 4.0
    assert snapshot.total_batches >= 2
    assert len(snapshot.items) <= 10
    assert snapshot.filtered_count == snapshot.total_quarantined_targets


def test_quarantine_manager_search_and_category_filter():
    """Verify keyword search and category filtering across quarantine items."""
    manager = QuarantineManager.get_instance()

    # Search for staging session item
    snapshot_staging = manager.get_snapshot(category="cold_staging_sessions", limit=50)
    assert snapshot_staging.filtered_count >= 5
    assert all(it.category == "cold_staging_sessions" for it in snapshot_staging.items)

    # Keyword search for '2080ti'
    snapshot_search = manager.get_snapshot(search="2080ti", limit=20)
    assert snapshot_search.filtered_count >= 1
    assert any("2080ti" in it.name.lower() for it in snapshot_search.items)


def test_quarantine_dry_run_restore_probe():
    """Verify read-only dry run restoration validation probe."""
    manager = QuarantineManager.get_instance()
    snapshot = manager.get_snapshot(limit=1)
    assert len(snapshot.items) > 0
    first_item = snapshot.items[0]

    # Run probe on valid archived target
    res = manager.dry_run_restore(batch_id=first_item.batch_id, item_name=first_item.name)
    assert res.item_name == first_item.name
    assert res.destination_exists is True
    assert res.destination_files_count > 0
    assert res.safe_to_restore is True
    assert "Dry-run verified" in res.message

    # Run probe on nonexistent item
    res_fake = manager.dry_run_restore(batch_id=first_item.batch_id, item_name="nonexistent_item_99999")
    assert res_fake.success is False
    assert res_fake.safe_to_restore is False
    assert "not found" in res_fake.message


def test_quarantine_http_endpoints(client):
    """Verify HTTP API endpoints for manifest listing and dry-run probe."""
    # 1. GET /api/v1/memory/quarantine_manifest
    resp = client.get("/api/v1/memory/quarantine_manifest?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_quarantined_targets" in data
    assert data["total_quarantined_targets"] >= 1164
    assert len(data["items"]) <= 5
    assert len(data["batches"]) >= 2

    # 2. POST /api/v1/memory/quarantine_restore_dry_run
    first = data["items"][0]
    probe_resp = client.post(
        "/api/v1/memory/quarantine_restore_dry_run",
        json={"batch_id": first["batch_id"], "item_name": first["name"]},
    )
    assert probe_resp.status_code == 200
    probe_data = probe_resp.json()
    assert probe_data["item_name"] == first["name"]
    assert probe_data["safe_to_restore"] is True
    assert probe_data["destination_files_count"] > 0
