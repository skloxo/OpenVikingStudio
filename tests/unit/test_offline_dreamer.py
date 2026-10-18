# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Offline Dream Consolidation Pipeline (ov_dream).
(Card-37 / v1.6.1)
"""

import time
import pytest
from unittest.mock import MagicMock, patch
from openviking.service.offline_dreamer import (
    OfflineDreamer,
    MasterKnowledgeCard,
    DreamCycleResult,
)
from openviking.service.memory_lifecycle_fsm import (
    MemoryLifecycleStore,
    MemoryStatus,
)
from openviking.service.memory_conflict_resolver import MemoryConflictResolver


@pytest.fixture(autouse=True)
def reset_singletons(tmp_path):
    """Ensure clean isolated SQLite and singleton state for each test."""
    db_file = tmp_path / "memory_lifecycle.db"
    store = MemoryLifecycleStore(db_path=str(db_file))
    MemoryLifecycleStore._instance = store
    MemoryConflictResolver.reset_for_testing()
    OfflineDreamer.reset_for_testing()
    yield
    MemoryConflictResolver.reset_for_testing()
    OfflineDreamer.reset_for_testing()
    MemoryLifecycleStore._instance = None


def test_offline_dreamer_singleton():
    """Verify OfflineDreamer adheres to strict double-checked singleton."""
    d1 = OfflineDreamer.get_instance()
    d2 = OfflineDreamer.get_instance()
    assert d1 is d2
    stats = d1.get_stats()
    assert "total_dreams" in stats
    assert stats["total_dreams"] == 0


def test_offline_dreamer_clustering_and_consolidation(tmp_path):
    """Verify fragments of the same theme are clustered, synthesized into Master Card,
    and atomically superseded in memory_lifecycle.db and relations DAG.
    """
    dreamer = OfflineDreamer.get_instance(crystals_dir=tmp_path / "crystals")
    store = MemoryLifecycleStore.get_instance()

    # Create 3 raw fragmented experiences under the same topic
    frag_1 = {
        "uri": "viking://resources/master_memory/evolution_lessons/lesson_01.md",
        "topic": "systemd_service",
        "content": "Always verify restart policy when daemonizing openviking service.",
        "created_at": time.time() - 50000,
    }
    frag_2 = {
        "uri": "viking://resources/master_memory/evolution_lessons/lesson_02.md",
        "topic": "systemd_service",
        "content": "Check journalctl logs to diagnose socket binding conflicts on 1933.",
        "created_at": time.time() - 40000,
    }
    frag_3 = {
        "uri": "viking://resources/master_memory/evolution_lessons/lesson_03.md",
        "topic": "systemd_service",
        "content": "Ensure environment variables are loaded in systemd user service unit.",
        "created_at": time.time() - 30000,
    }

    # Execute dream cycle
    result: DreamCycleResult = dreamer.run_dream_cycle(
        candidate_fragments=[frag_1, frag_2, frag_3],
        theme="systemd_service",
        min_cluster_size=2,
    )

    assert result.status == "ok"
    assert result.fragments_scanned == 3
    assert result.fragments_consolidated == 3
    assert result.master_cards_created == 1
    assert result.net_entropy_reduced == 2  # 3 fragments reduced to 1 master card = net 2 reduction
    assert len(result.master_card_uris) == 1
    master_uri = result.master_card_uris[0]

    # Verify that source fragments are superseded in MemoryLifecycleStore
    for f in [frag_1, frag_2, frag_3]:
        rec = store.get_record(f["uri"])
        assert rec is not None
        assert rec.status == MemoryStatus.SUPERSEDED
        assert rec.superseded_by == master_uri

    # Verify conflict resolver records the lineage transition
    resolver = MemoryConflictResolver.get_instance()
    chain = resolver.get_lineage_chain(frag_1["uri"])
    assert chain["is_superseded"] is True
    assert chain["current_active_ssot"] == master_uri

    # Verify stats
    stats = dreamer.get_stats()
    assert stats["total_dreams"] == 1
    assert stats["fragments_consolidated"] == 3
    assert stats["master_cards_created"] == 1
    assert stats["net_entropy_reduced"] == 2


def test_offline_dreamer_skips_insufficient_cluster(tmp_path):
    """Verify clusters below min_cluster_size are safely skipped without mutation."""
    dreamer = OfflineDreamer.get_instance(crystals_dir=tmp_path / "crystals")

    single_frag = {
        "uri": "viking://resources/master_memory/evolution_lessons/lone_lesson.md",
        "topic": "rare_topic",
        "content": "An isolated one-off observation.",
        "created_at": time.time(),
    }

    result = dreamer.run_dream_cycle(
        candidate_fragments=[single_frag],
        min_cluster_size=3,
    )

    assert result.status == "no_qualifying_clusters"
    assert result.fragments_consolidated == 0
    assert result.master_cards_created == 0
