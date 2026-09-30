# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for HybridRetriever superseded filtering and decay demotion.
Card-36: Memory-Anti-Entropy-Lineage-DAG-And-Conflict-Resolution (v1.6.0)
"""

import pytest
import os
import shutil
import tempfile
from openviking.storage.bm25_fts_index import BM25FTSIndex
from openviking.retrieve.hybrid_retriever import HybridRetriever
from openviking.service.memory_lifecycle_fsm import (
    MemoryLifecycleFSM,
    MemoryLifecycleStore,
    LifecycleTransitionEvent,
)


@pytest.fixture
def test_setup():
    temp_dir = tempfile.mkdtemp()
    db_bm25 = os.path.join(temp_dir, "bm25.db")
    db_fsm = os.path.join(temp_dir, "lifecycle.db")

    bm25 = BM25FTSIndex(db_path=db_bm25)
    fsm_store = MemoryLifecycleStore(db_path=db_fsm)

    # Monkeypatch singleton
    orig_store = MemoryLifecycleStore._instance
    MemoryLifecycleStore._instance = fsm_store

    retriever = HybridRetriever(bm25_index=bm25)

    yield {
        "retriever": retriever,
        "bm25": bm25,
        "fsm_store": fsm_store,
        "temp_dir": temp_dir,
    }

    MemoryLifecycleStore._instance = orig_store
    from openviking.service.memory_conflict_resolver import MemoryConflictResolver
    MemoryConflictResolver.reset_for_testing()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_superseded_filtering_and_demotion(test_setup):
    retriever = test_setup["retriever"]
    fsm_store = test_setup["fsm_store"]

    uri_old = "viking://resources/master_memory/config_v1.md"
    uri_new = "viking://resources/master_memory/config_v2.md"

    # Register in FSM: old is superseded by new
    from openviking.service.memory_conflict_resolver import MemoryConflictResolver
    resolver = MemoryConflictResolver(store=fsm_store)
    resolver.resolve_and_link(old_uri=uri_old, new_uri=uri_new, reason="Upgrade to v2")

    dense_candidates = [
        {
            "uri": uri_old,
            "title": "Config V1 (Legacy)",
            "level": 1,
            "context_type": "memory",
            "dense_score": 0.95,
            "extra_metadata": {"status": "active"},  # Stale metadata should be overridden by physical FSM
        },
        {
            "uri": uri_new,
            "title": "Config V2 (Latest SSOT)",
            "level": 1,
            "context_type": "memory",
            "dense_score": 0.90,
            "extra_metadata": {"status": "active"},
        },
    ]

    # Case 1: When exclude_superseded is False, both are returned, but old is demoted
    results_with_superseded = await retriever.retrieve(
        query="config",
        dense_candidates=dense_candidates,
        limit=5,
        exclude_superseded=False,
    )

    uris = [r.uri for r in results_with_superseded]
    assert uri_old in uris
    assert uri_new in uris

    old_cand = next(r for r in results_with_superseded if r.uri == uri_old)
    assert old_cand.extra_metadata["status"] == "superseded"
    assert old_cand.extra_metadata["superseded_by"] == uri_new
    assert old_cand.extra_metadata["decay_factor"] <= 0.20

    # New should rank higher despite lower raw score due to decay demotion
    assert results_with_superseded[0].uri == uri_new

    # Case 2: When exclude_superseded is True, old is physically filtered out
    results_pure = await retriever.retrieve(
        query="config",
        dense_candidates=dense_candidates,
        limit=5,
        exclude_superseded=True,
    )

    pure_uris = [r.uri for r in results_pure]
    assert uri_old not in pure_uris
    assert uri_new in pure_uris
    assert len(results_pure) == 1
