# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Memory Purity Benchmark and Automated Watchdog Enforcement.
(Card-38 / v1.6.2)
"""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch

from openviking.service.memory_purity import (
    MemoryPurityBenchmark,
    MemoryPurityReport,
    GovernanceStreamEvent,
)
from openviking.service.memory_lifecycle_fsm import (
    MemoryLifecycleStore,
    MemoryStatus,
    _LIFECYCLE_REGISTRY,
    get_or_create_lifecycle_record,
)
from openviking.service.entropy_watchdog import EntropyWatchdog
from openviking.service.offline_dreamer import OfflineDreamer, DreamCycleResult
from openviking.service.memory_conflict_resolver import MemoryConflictResolver


@pytest.fixture(autouse=True)
def clean_benchmark_state(tmp_path):
    """Ensure clean isolated SQLite and singleton state for test execution."""
    db_file = tmp_path / "memory_lifecycle.db"
    store = MemoryLifecycleStore(db_path=str(db_file))
    MemoryLifecycleStore._instance = store
    MemoryConflictResolver.reset_for_testing()
    OfflineDreamer.reset_for_testing()
    MemoryPurityBenchmark._instance = None
    yield
    MemoryConflictResolver.reset_for_testing()
    OfflineDreamer.reset_for_testing()
    MemoryPurityBenchmark._instance = None
    MemoryLifecycleStore._instance = None


def test_purity_benchmark_empty_state(tmp_path):
    """Verify default purity report with an empty memory store."""
    bench = MemoryPurityBenchmark.get_instance(
        ledger_path=tmp_path / "ledger.jsonl",
        crystals_dir=tmp_path / "crystals",
    )
    report = bench.compute_purity_report()

    assert isinstance(report, MemoryPurityReport)
    assert report.total_memories == 0
    assert report.conflict_rate == 0.0
    assert report.freshness_retained == 1.0
    assert report.purity_score >= 0


def test_purity_benchmark_snr_and_conflict_calculation(tmp_path):
    """Verify SNR, conflict rate, and health score calculations with realistic records."""
    crystals_dir = tmp_path / "crystals"
    crystals_dir.mkdir(parents=True, exist_ok=True)
    (crystals_dir / "master_docker_01.md").write_text("Axiom 1", encoding="utf-8")
    (crystals_dir / "master_systemd_02.md").write_text("Axiom 2", encoding="utf-8")

    bench = MemoryPurityBenchmark.get_instance(
        ledger_path=tmp_path / "ledger.jsonl",
        crystals_dir=crystals_dir,
    )

    now = time.time()
    # Add 2 canonical active items
    rec_c1 = get_or_create_lifecycle_record("viking://resources/canonical/arch.md")
    rec_c1.updated_at = now - 1000

    rec_c2 = get_or_create_lifecycle_record("viking://resources/canonical/rule.md")
    rec_c2.updated_at = now - 2000

    # Add 3 raw active fragments
    rec_f1 = get_or_create_lifecycle_record("viking://resources/experience/raw_01.md")
    rec_f1.updated_at = now - 500

    rec_f2 = get_or_create_lifecycle_record("viking://resources/experience/raw_02.md")
    rec_f2.updated_at = now - (100 * 86400)  # stale > 90 days

    # Add 1 disputed record
    rec_d = get_or_create_lifecycle_record("viking://resources/disputed.md")
    rec_d.status = MemoryStatus.DISPUTED
    rec_d.updated_at = now

    # Add 2 superseded records
    rec_s1 = get_or_create_lifecycle_record("viking://resources/superseded_01.md")
    rec_s1.status = MemoryStatus.SUPERSEDED
    rec_s2 = get_or_create_lifecycle_record("viking://resources/superseded_02.md")
    rec_s2.status = MemoryStatus.SUPERSEDED

    report = bench.compute_purity_report()

    assert report.total_memories == 7
    assert report.master_cards_count == 2
    assert report.canonical_count == 2
    assert report.active_count == 4
    assert report.disputed_count == 1
    assert report.superseded_count == 2
    assert report.unconsolidated_fragments == 2
    assert report.conflict_rate == round(1.0 / 7.0, 4)
    assert 0 <= report.purity_score <= 100


def test_governance_stream_parsing(tmp_path):
    """Verify unified parsing of ingress admission and dream consolidation ledger entries."""
    ledger = tmp_path / "entropy_gatekeeper.jsonl"
    entries = [
        {"action": "add", "uri": "viking://resources/test1.md", "similarity": 0.45, "reason": "New proposition", "timestamp": 100.0},
        {"action": "noop", "uri": "viking://resources/test2.md", "similarity": 0.98, "reason": "Duplicate match", "timestamp": 200.0},
        {
            "event_id": "#dream_123",
            "type": "DREAM_CONSOLIDATION",
            "timestamp": 300.0,
            "theme": "docker_clean",
            "fragments_consolidated": 5,
            "master_card_uri": "viking://resources/master_memory/crystals/master_docker.md",
            "net_entropy_reduced": 4,
        },
    ]
    with open(ledger, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    bench = MemoryPurityBenchmark.get_instance(
        ledger_path=ledger,
        crystals_dir=tmp_path / "crystals",
    )
    events = bench.get_governance_stream(limit=10)

    assert len(events) == 3
    # Reverse chronological order
    assert events[0].type == "DREAM_CONSOLIDATION"
    assert events[0].event_id == "#dream_123"
    assert events[0].net_entropy_reduced == 4

    assert events[1].type == "INGRESS_ADMISSION"
    assert events[1].action == "noop"
    assert events[1].net_entropy_reduced == 1

    assert events[2].type == "INGRESS_ADMISSION"
    assert events[2].action == "add"


def test_watchdog_enforce_dream_triggers(tmp_path):
    """Verify check_and_enforce_dream_watchdog logic for force and watermark conditions."""
    watchdog = EntropyWatchdog.get_instance()
    bench = MemoryPurityBenchmark.get_instance(
        ledger_path=tmp_path / "ledger.jsonl",
        crystals_dir=tmp_path / "crystals",
    )

    with patch.object(OfflineDreamer, "run_dream_cycle") as mock_dream:
        mock_dream.return_value = DreamCycleResult(
            status="ok",
            dream_id="mock_dream_1",
            theme="watchdog_force_enforce",
            fragments_consolidated=3,
            master_cards_created=1,
            net_entropy_reduced=2,
            duration_ms=1.5,
        )

        # 1. Normal run without force or thresholds should not trigger
        res_normal = watchdog.check_and_enforce_dream_watchdog(dry_run=True, force=False)
        assert isinstance(res_normal, dict)
        assert res_normal["triggered"] is False

        # 2. Force enforcement should trigger immediately with mocked cycle
        res_forced = watchdog.check_and_enforce_dream_watchdog(dry_run=True, force=True)
        assert res_forced["triggered"] is True
        assert res_forced["reason"] == "force_enforce"
        assert "dream_cycle" in res_forced
        assert mock_dream.called
