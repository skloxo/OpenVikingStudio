# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Memory Conflict Resolution and Lineage Superseding DAG.
Card-36: Memory-Anti-Entropy-Lineage-DAG-And-Conflict-Resolution (v1.6.0)
"""

import os
import shutil
import tempfile
import pytest

from openviking.service.memory_lifecycle_fsm import (
    MemoryLifecycleFSM,
    MemoryLifecycleStore,
    MemoryStatus,
    get_or_create_lifecycle_record,
)
from openviking.service.memory_conflict_resolver import (
    MemoryConflictResolver,
    ConflictResolutionResult,
)


@pytest.fixture
def temp_env():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_lifecycle.db")
    store = MemoryLifecycleStore(db_path=db_path)
    resolver = MemoryConflictResolver(store=store)
    yield {
        "temp_dir": temp_dir,
        "store": store,
        "resolver": resolver,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_resolve_and_link_basic(temp_env):
    resolver = temp_env["resolver"]
    store = temp_env["store"]

    old_uri = "viking://resources/master_memory/deploy_recipe_v1.md"
    new_uri = "viking://resources/master_memory/deploy_recipe_v2.md"

    # Pre-register old record as active
    old_rec = get_or_create_lifecycle_record(old_uri)
    store.save_record(old_rec)
    assert old_rec.status == MemoryStatus.ACTIVE

    # Execute resolution
    result = resolver.resolve_and_link(
        old_uri=old_uri,
        new_uri=new_uri,
        reason="Updated to support Docker Compose v2 syntax",
    )

    assert isinstance(result, ConflictResolutionResult)
    assert result.success is True
    assert result.old_uri == old_uri
    assert result.new_uri == new_uri
    assert result.old_status == "superseded"
    assert result.new_status == "active"

    # Verify persistent state in store
    saved_old = store.get_record(old_uri)
    saved_new = store.get_record(new_uri)

    assert saved_old is not None
    assert saved_old.status == MemoryStatus.SUPERSEDED
    assert saved_old.superseded_by == new_uri

    assert saved_new is not None
    assert saved_new.status == MemoryStatus.ACTIVE
    assert saved_new.supersedes_uri == old_uri


def test_idempotent_supersede_call(temp_env):
    resolver = temp_env["resolver"]
    store = temp_env["store"]

    old_uri = "viking://resources/master_memory/rule_a.md"
    new_uri = "viking://resources/master_memory/rule_b.md"

    # First call
    res1 = resolver.resolve_and_link(old_uri, new_uri, reason="First update")
    assert res1.success is True

    # Second call should be idempotent and not fail
    res2 = resolver.resolve_and_link(old_uri, new_uri, reason="Second redundant update")
    assert res2.success is True

    saved_old = store.get_record(old_uri)
    assert saved_old.status == MemoryStatus.SUPERSEDED
    assert saved_old.superseded_by == new_uri


def test_dag_traversal_multihop(temp_env):
    resolver = temp_env["resolver"]
    store = temp_env["store"]

    v1 = "viking://resources/mem/doc_v1.md"
    v2 = "viking://resources/mem/doc_v2.md"
    v3 = "viking://resources/mem/doc_v3.md"

    resolver.resolve_and_link(v1, v2, reason="Upgrade to v2")
    resolver.resolve_and_link(v2, v3, reason="Upgrade to v3")

    chain_v1 = resolver.get_lineage_chain(v1)
    assert chain_v1["root_uri"] == v1
    assert chain_v1["current_active_ssot"] == v3
    assert len(chain_v1["superseded_path"]) == 2
    assert chain_v1["superseded_path"] == [v1, v2]

    # Verify v2 perspective
    chain_v2 = resolver.get_lineage_chain(v2)
    assert chain_v2["current_active_ssot"] == v3
    assert chain_v2["predecessor"] == v1


def test_resolution_stats_and_history(temp_env):
    resolver = temp_env["resolver"]

    res_a = resolver.resolve_and_link("viking://a.md", "viking://b.md", reason="Fix bug A")
    res_b = resolver.resolve_and_link("viking://c.md", "viking://d.md", reason="Fix bug B")

    stats = resolver.get_conflict_stats()
    assert stats["total_resolutions"] >= 2
    assert stats["active_nodes"] >= 2
    assert stats["superseded_nodes"] >= 2

    history = resolver.get_resolution_history(limit=10)
    assert len(history) >= 2
    assert any(h["old_uri"] == "viking://a.md" and h["new_uri"] == "viking://b.md" for h in history)
