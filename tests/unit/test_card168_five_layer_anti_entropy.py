# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Five-layer Anti-Entropy Memory Evolution & Layer 5 Rollback tests (Card-168)."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from openviking.retrieve.asymmetric_decay import AsymmetricDecayEngine
from openviking.service.entropy_gatekeeper import EntropyGatekeeper
from openviking.service.memory_conflict_resolver import MemoryConflictResolver
from openviking.service.memory_lifecycle_fsm import MemoryLifecycleStore, MemoryStatus
from openviking.service.offline_dreamer import OfflineDreamer


@pytest.fixture
def isolated_memory_env(tmp_path: Path):
    db_file = tmp_path / "memory_lifecycle.db"
    MemoryLifecycleStore._instance = MemoryLifecycleStore(db_path=str(db_file))
    MemoryConflictResolver.reset_for_testing()
    OfflineDreamer.reset_for_testing()
    EntropyGatekeeper._instance = None
    yield tmp_path
    MemoryConflictResolver.reset_for_testing()
    OfflineDreamer.reset_for_testing()
    EntropyGatekeeper._instance = None
    MemoryLifecycleStore._instance = None


@pytest.mark.asyncio
async def test_five_layer_anti_entropy_lifecycle_and_snapshot_rollback(isolated_memory_env: Path):
    tmp_path = isolated_memory_env
    store = MemoryLifecycleStore.get_instance()

    # Layer 1: Semantic Admission Dedup (0.88 Gold Band -> update, >= 0.95 -> noop)
    gk = EntropyGatekeeper.get_instance()
    gk._history_file = str(tmp_path / "gatekeeper.jsonl")
    with patch.object(gk, "_probe_nearest_vector", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = (0.91, "viking://resources/master_memory/old_rule.md", "existing rule")
        d_update = await gk.evaluate_and_intercept(
            "viking://resources/master_memory/new_rule.md",
            "Refined exception rule with 2026 edge case handling and telemetry",
        )
        assert d_update.action == "update"

        mock_probe.return_value = (0.97, "viking://resources/master_memory/old_rule.md", "same rule")
        d_noop = await gk.evaluate_and_intercept(
            "viking://resources/master_memory/dup_rule.md",
            "Duplicate invariant rule text already stored in knowledge vault",
        )
        assert d_noop.action == "noop"

    # Layer 2: Conflict Resolution & Superseded DAG
    resolver = MemoryConflictResolver.get_instance()
    link_res = resolver.resolve_and_link(
        "viking://resources/master_memory/old_rule.md",
        "viking://resources/master_memory/new_rule.md",
        reason="Superseded by 2026 refinement",
    )
    assert link_res.old_status == "superseded"
    assert store.get_record("viking://resources/master_memory/old_rule.md").superseded_by == (
        "viking://resources/master_memory/new_rule.md"
    )

    # Layer 3: Asymmetric Decay (Axiom immune = 1.0 vs session 14d fast decay)
    decay = AsymmetricDecayEngine()
    now_ts = time.time()
    axiom_eval = decay.evaluate_candidate(
        uri="viking://resources/master_memory/new_rule.md",
        raw_score=0.80,
        updated_ts=now_ts - 120 * 86400,
        now_ts=now_ts,
        memory_type="canonical",
    )
    session_eval = decay.evaluate_candidate(
        uri="viking://user/default/sessions/s1/note.md",
        raw_score=0.80,
        updated_ts=now_ts - 30 * 86400,
        now_ts=now_ts,
        memory_type="session",
    )
    assert axiom_eval.is_immune is True
    assert session_eval.adjusted_score < axiom_eval.adjusted_score

    # Layer 4 + Layer 5: Offline Dreaming captures physical snapshot before mutating
    crystals_dir = tmp_path / "crystals"
    ledger_path = tmp_path / "entropy_gatekeeper.jsonl"
    dreamer = OfflineDreamer.get_instance(
        crystals_dir=crystals_dir,
        ledger_path=ledger_path,
        snapshot_dir=tmp_path / "dream_snapshots",
    )
    frags = [
        {
            "uri": "viking://resources/master_memory/lessons/f1.md",
            "topic": "cache_ops",
            "content": "Bypass SW cache for locales directory to avoid stale UI strings.",
            "created_at": now_ts - 90000,
        },
        {
            "uri": "viking://resources/master_memory/lessons/f2.md",
            "topic": "cache_ops",
            "content": "Bump CACHE_VERSION when changing locale assets behind PWA worker.",
            "created_at": now_ts - 85000,
        },
    ]

    # Dry-run must NOT create snapshots or crystal files
    dry_res = dreamer.run_dream_cycle(candidate_fragments=frags, theme="cache_ops", dry_run=True)
    assert dry_res.master_cards_created == 1
    assert dreamer.list_snapshots() == []
    assert list(crystals_dir.glob("*.md")) == [] if crystals_dir.exists() else True

    # Real run creates crystal, supersedes fragments, and captures snapshot
    live_res = dreamer.run_dream_cycle(candidate_fragments=frags, theme="cache_ops", dry_run=False)
    assert live_res.status == "ok"
    snap_id = live_res.snapshot_commit
    assert snap_id
    assert len(list(crystals_dir.glob("*.md"))) == 1
    assert store.get_record(frags[0]["uri"]).status == MemoryStatus.SUPERSEDED
    assert store.get_record(frags[1]["uri"]).status == MemoryStatus.SUPERSEDED
    assert len(dreamer.list_snapshots()) == 1

    # Layer 5 Rollback ("后悔药"): deletes new crystal & restores source fragments to ACTIVE
    rb_res = dreamer.rollback_dream(snap_id)
    assert rb_res["status"] == "rolled_back"
    assert rb_res["restored_fragments"] == 2
    assert rb_res["removed_crystals"] == 1
    assert list(crystals_dir.glob("*.md")) == []
    for frag in frags:
        rec = store.get_record(frag["uri"])
        assert rec is not None
        assert rec.status == MemoryStatus.ACTIVE
        assert rec.superseded_by is None

    # Idempotent repeat rollback
    rb_repeat = dreamer.rollback_dream(snap_id)
    assert rb_repeat["status"] == "already_rolled_back"
