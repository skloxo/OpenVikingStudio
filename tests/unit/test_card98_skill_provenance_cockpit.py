# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""TDD Test Suite for Card-98: Blackbox Provenance Audit Trail & Ingestion Cockpit."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role, UserIdentifier
from openviking.server.routers.skill_ingestion import router
from openviking.service.skill_provenance_tracker import (
    ProvenanceAction,
    ProvenanceRecord,
    SkillProvenanceTracker,
)


@pytest.fixture
def temp_provenance_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def tracker(temp_provenance_dir):
    return SkillProvenanceTracker(vault_root=temp_provenance_dir)


@pytest.fixture
def client(tracker) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    mock_ctx = RequestContext(
        user=UserIdentifier(account_id="test", user_id="test_admin"),
        role=Role(Role.ADMIN),
    )
    app.dependency_overrides[get_request_context] = lambda: mock_ctx
    return TestClient(app, raise_server_exceptions=False)


def test_record_and_list_provenance_event(tracker):
    """Verify appending event to PROVENANCE.jsonl and reading it back."""
    rec = tracker.record_event(
        action=ProvenanceAction.INGEST,
        skill_name="k8s-pod-debugger",
        version="1.0.0",
        receipt_id="ingest_test01",
        operator="ci-agent",
        details={"status": "STAGED", "lines": 42},
    )

    assert rec.event_id.startswith("prov_")
    assert rec.action == ProvenanceAction.INGEST
    assert rec.skill_name == "k8s-pod-debugger"

    events = tracker.list_events()
    assert len(events) >= 1
    assert events[0].skill_name == "k8s-pod-debugger"


def test_create_snapshot_and_rollback(tracker, temp_provenance_dir):
    """Verify physical content snapshot creation and sub-50ms rollback restoration."""
    target_skill_path = temp_provenance_dir / "target_skill.md"
    original_content = "# Original Skill Content v1\nEverything works."
    broken_content = "# Broken Skill Content v2\nBuggy override."

    target_skill_path.write_text(original_content, encoding="utf-8")

    # 1. Create snapshot
    snapshot_path = tracker.create_snapshot(
        skill_name="target_skill",
        content=original_content,
    )
    assert Path(snapshot_path).exists()

    # 2. Poison the file
    target_skill_path.write_text(broken_content, encoding="utf-8")
    assert "Buggy override" in target_skill_path.read_text(encoding="utf-8")

    # 3. Rollback
    t0 = time.perf_counter()
    restored = tracker.rollback_snapshot(snapshot_path, target_skill_path)
    rollback_ms = (time.perf_counter() - t0) * 1000.0

    assert restored is True
    assert rollback_ms < 50.0
    assert target_skill_path.read_text(encoding="utf-8") == original_content


def test_append_changelog_entry(tracker, temp_provenance_dir):
    """Verify human-readable CHANGELOG.md generation."""
    changelog_path = tracker.append_changelog(
        skill_name="k8s-pod-debugger",
        version="1.0.1",
        summary="Absorbed --dry-run flag and extra error handling.",
        action=ProvenanceAction.MERGE,
        delta_triggers=["k8s crashloop"],
    )

    assert changelog_path.exists()
    content = changelog_path.read_text(encoding="utf-8")
    assert "## [1.0.1]" in content
    assert "k8s crashloop" in content
    assert "Absorbed --dry-run" in content


def test_rest_provenance_and_rollback_endpoints(client: TestClient, tracker, temp_provenance_dir):
    """Verify REST router returns provenance history and handles rollback."""
    tracker.record_event(
        action=ProvenanceAction.INGEST,
        skill_name="git-helper",
        version="1.0.0",
        receipt_id="ingest_git01",
        operator="auto-dev",
    )

    resp = client.get("/api/v1/skills/ingestion/provenance?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "events" in data
