# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for EntropyCrystallizer Autonomous Idle Daemon & Midnight Closure.
(Card-Memory-EntropyCrystallizer-IdleDaemon-Closure / v1.5.80)
"""

import os
import shutil
import tempfile
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from openviking.core.dreaming_gate import DreamingDefectMiner
from openviking.core.failure_taxonomy_telemetry import FailureCategory, FailureTaxonomyTelemetry
from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking_cli.session.user_id import UserIdentifier
from openviking.service.entropy_crystallizer import (
    EntropyCrystallizer,
    MemoryFragment,
)
from openviking.service.entropy_watchdog import EntropyWatchdog
from openviking.service.memory_lifecycle_fsm import (
    MemoryLifecycleFSM,
    MemoryLifecycleRecord,
    MemoryLifecycleStore,
    MemoryStatus,
)


@pytest.fixture
def temp_workspace():
    """Create isolated temporary directory for memory lessons and crystals."""
    tmpdir = tempfile.mkdtemp(prefix="test_entropy_daemon_")
    lessons_dir = Path(tmpdir) / "evolution_lessons"
    crystals_dir = Path(tmpdir) / "crystals"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    crystals_dir.mkdir(parents=True, exist_ok=True)
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_crystallizer_state():
    """Ensure crystallizer singleton is reset before and after each test."""
    crystallizer = EntropyCrystallizer.get_instance()
    crystallizer.reset_rule()
    crystallizer._crystals.clear()
    crystallizer._total_evaluated = 0
    crystallizer._total_blocked = 0
    crystallizer._total_net_reduced = 0
    yield
    crystallizer.reset_rule()
    crystallizer._crystals.clear()


def test_load_candidate_fragments_respects_lifecycle(temp_workspace):
    """Test loading fragments from storage filters out already superseded records."""
    lessons_dir = temp_workspace / "evolution_lessons"
    now = time.time()
    created_at = now - (30.0 * 3600.0)  # 30 hours ago (passes 24h cooling)

    # Create 3 lesson files
    for i in range(1, 4):
        p = lessons_dir / f"20260901_00000{i}_test_lesson_{i}.md"
        p.write_text(f"Lesson content {i} on topic network_resilience", encoding="utf-8")
        os.utime(p, (created_at, created_at))

    # Mark lesson 2 as SUPERSEDED in MemoryLifecycleStore
    store = MemoryLifecycleStore.get_instance()
    rec2 = MemoryLifecycleRecord(
        uri=f"viking://resources/master_memory/evolution_lessons/{lessons_dir.name}/20260901_000002_test_lesson_2.md",
        status=MemoryStatus.SUPERSEDED,
    )
    store.save_record(rec2)

    crystallizer = EntropyCrystallizer.get_instance()
    # Should load candidate fragments and filter out the superseded one
    frags = crystallizer.load_candidate_fragments(base_dir=lessons_dir)
    assert len(frags) >= 2
    loaded_uris = [f.uri for f in frags]
    assert not any("test_lesson_2" in u for u in loaded_uris)


def test_run_crystallization_cycle_tri_gate_success(temp_workspace):
    """Test full cycle: tri-gate qualification distills crystal, supersedes sources, and writes to disk."""
    lessons_dir = temp_workspace / "evolution_lessons"
    crystals_dir = temp_workspace / "crystals"
    now = time.time()
    created_at = now - (36.0 * 3600.0)  # 36 hours ago

    # Create 5 lessons on same topic with similar content (passes cluster size >= 5, cooling >= 24h)
    frags = []
    for i in range(5):
        emb = [0.85, 0.85, 0.85, 0.85]
        frags.append(
            MemoryFragment(
                uri=f"viking://resources/master_memory/evolution_lessons/resilience_{i}.md",
                content=f"Systemic resilience check against network timeout event {i}.",
                created_at=created_at,
                embedding=emb,
                metadata={"topic": "network_resilience"},
            )
        )

    crystallizer = EntropyCrystallizer.get_instance()
    result = crystallizer.run_crystallization_cycle(
        candidate_fragments=frags,
        crystals_dir=crystals_dir,
        reason="unit_test_idle_run",
    )

    assert result["status"] == "ok"
    assert result["crystals_distilled"] == 1
    assert result["net_entropy_reduced"] == 4  # 5 fragments consolidated into 1
    assert len(crystallizer.list_crystals()) == 1

    # Verify physical file written to crystals directory
    crystal_files = list(crystals_dir.glob("*.md"))
    assert len(crystal_files) == 1
    content = crystal_files[0].read_text(encoding="utf-8")
    assert "network_resilience" in content
    assert "Immutable SSOT Axiom" in content or "FactCrystal" in content


def test_run_crystallization_cycle_with_failure_telemetry():
    """Test failure taxonomy telemetry events feed into DreamingDefectMiner during cycle."""
    telemetry = FailureTaxonomyTelemetry.get_instance()
    # Record 3 deterministic failures with same tool
    for _ in range(3):
        telemetry.record_evaluation(
            category=FailureCategory.DETERMINISTIC,
            tool_name="git_push_tool",
            reason="Unauthenticated push error",
            blocked=True,
        )

    miner = DreamingDefectMiner.get_instance()
    crystallizer = EntropyCrystallizer.get_instance()

    res = crystallizer.run_crystallization_cycle(reason="test_telemetry_harvest")
    assert res["status"] == "ok"
    # Dreaming cycle executed and defect clusters mined
    assert res["defects_mined"] >= 1
    assert any("git_push_tool" in d.cluster_topic or "DETERMINISTIC" in d.cluster_topic.upper() for d in miner.defects.values())


def test_entropy_watchdog_idle_trigger():
    """Test EntropyWatchdog trigger_crystallization_cycle executes successfully."""
    watchdog = EntropyWatchdog.get_instance()
    res = watchdog.trigger_crystallization_cycle(reason="watchdog_idle_test")
    assert res["status"] == "ok"
    assert "crystals_distilled" in res
    assert "defects_mined" in res


def test_crystallizer_telemetry_stats_api():
    """Test that /api/v1/memory/crystallize/stats includes daemon operational metrics."""
    crystallizer = EntropyCrystallizer.get_instance()
    crystallizer.run_crystallization_cycle(reason="api_stats_verification")

    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    client = TestClient(app)
    resp = client.get("/api/v1/memory/crystallize/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    result = data["result"]
    assert "idle_daemon_active" in result
    assert result["idle_daemon_active"] is True
    assert "total_idle_runs" in result
    assert result["total_idle_runs"] >= 1
    assert "last_idle_run_timestamp" in result
    assert result["last_idle_run_timestamp"] > 0
