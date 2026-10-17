# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Memory Cold Archive Service & Temporal Decay Audit (Card-92 / v1.7.46).
"""

import time
import pytest
from fastapi.testclient import TestClient

from openviking.service.memory_cold_archive_service import (
    ColdArchiveRecord,
    MemoryColdArchiveService,
)
from openviking.service.memory_lifecycle_fsm import (
    MemoryLifecycleRecord,
    MemoryLifecycleStore,
    MemoryStatus,
)
from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def temp_archive_service(tmp_path):
    """Provides a fresh isolated instance of MemoryColdArchiveService."""
    db_file = str(tmp_path / "test_cold_archive.db")
    service = MemoryColdArchiveService(db_path=db_file)
    return service


def test_cold_archive_lifecycle_audit(temp_archive_service, tmp_path):
    """Test auditing memory decay and identifying dormant candidates."""
    # Setup isolated lifecycle store
    store = MemoryLifecycleStore(db_path=str(tmp_path / "test_lifecycle.db"))
    
    # 1. Fresh active memory (immune to dormancy)
    temp_archive_service.lifecycle_store.save_record(MemoryLifecycleRecord(
        uri="viking://resources/memory/fresh.md",
        status=MemoryStatus.ACTIVE,
        updated_at=time.time(),
    ))

    # 2. Dormant aged memory (old timestamp, low usage, active but decayed)
    temp_archive_service.lifecycle_store.save_record(MemoryLifecycleRecord(
        uri="viking://resources/memory/dormant_old.md",
        status=MemoryStatus.ACTIVE,
        updated_at=time.time() - 86400 * 180,  # 180 days old ensures score < 0.35
    ))

    audit = temp_archive_service.audit_storage_lifecycle()

    assert audit["total_active_memories"] == 2
    assert audit["dormant_candidates_count"] >= 1
    assert "viking://resources/memory/dormant_old.md" in [c["uri"] for c in audit["candidates"]]
    assert audit["data_safety_guarantee"] == "100% Never Delete Non-Destructive"


def test_archive_to_cold_and_revival(temp_archive_service, tmp_path):
    """Test atomic archiving into cold storage and subsequent non-destructive revival."""
    store = temp_archive_service.lifecycle_store
    
    target_uri = "viking://resources/memory/to_archive.md"
    store.save_record(MemoryLifecycleRecord(
        uri=target_uri,
        status=MemoryStatus.SUPERSEDED,
        updated_at=time.time() - 86400 * 45,
    ))

    # 1. Archive to cold
    record = temp_archive_service.archive_to_cold(
        uri=target_uri,
        reason="Aged superseded memory archived to reduce vector noise",
        decay_score=0.15,
    )
    assert record.uri == target_uri
    assert record.decay_score == 0.15

    # Verify active store marked it superseded/archived
    active_rec = store.get_record(target_uri)
    assert active_rec.status == MemoryStatus.SUPERSEDED

    # Verify cold store has it
    cold_records, total_cold = temp_archive_service.list_cold_records()
    assert total_cold == 1
    assert cold_records[0].uri == target_uri

    # 2. Revive back to active
    revive_res = temp_archive_service.revive_from_cold(
        uri=target_uri,
    )
    assert revive_res["status"] == "ok"
    assert revive_res["uri"] == target_uri

    # Verify cold store is now empty
    cold_records_after, total_cold_after = temp_archive_service.list_cold_records()
    assert total_cold_after == 0

    # Verify active store restored it to ACTIVE status
    restored = store.get_record(target_uri)
    assert restored is not None
    assert restored.status == MemoryStatus.ACTIVE


def test_cold_archive_api_endpoints(monkeypatch, tmp_path):
    """Test the HTTP API routes under /api/v1/memory/cold/*."""
    app = create_app()

    # Override auth
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="test-user"),
        role=Role.ADMIN,
    )

    client = TestClient(app)

    # 1. Cold audit
    resp = client.get("/api/v1/memory/cold/audit")
    assert resp.status_code == 200
    data = resp.json()["result"]
    assert "total_active_memories" in data
    assert "data_safety_guarantee" in data

    # 2. Cold list
    resp_list = client.get("/api/v1/memory/cold/list")
    assert resp_list.status_code == 200
    assert "records" in resp_list.json()["result"]

    # 3. Archive URI
    resp_archive = client.post(
        "/api/v1/memory/cold/archive",
        json={"uri": "viking://non_existent.md", "decay_score": 0.1},
    )
    assert resp_archive.status_code == 200
    assert resp_archive.json()["result"]["uri"] == "viking://non_existent.md"

    # 4. Revive invalid URI (should return 404)
    resp_revive = client.post(
        "/api/v1/memory/cold/revive",
        json={"uri": "viking://non_existent_cold.md"},
    )
    assert resp_revive.status_code == 404
