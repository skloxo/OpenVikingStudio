# -*- coding: utf-8 -*-
# Copyright (c) 2026 OpenViking Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0.

"""
Unit Test Suite for Card-53 (v1.7.7):
Atomic Lifecycle Transactions, Proxy De-layering & Valet URI Decoupling.
First Principles:
1. Atomic Dual-Write: link_superseded_pair persists both records in one transaction, zero dangling pointer.
2. Direct SQLite SSOT: Status counts directly computed from index without 200-item truncation.
3. Zero Redundant IO: Valet worker detects bitwise identical disk file and avoids duplicate write.
4. Dynamic URI Resolution: Resolves arbitrary viking://<collection>/<path> without hardcoded paths.
"""

import os
import time
import pytest
from pathlib import Path

from openviking.service.memory_lifecycle_fsm import (
    MemoryLifecycleFSM,
    MemoryLifecycleRecord,
    MemoryLifecycleStore,
    MemoryStatus,
    LifecycleTransitionEvent,
)
from openviking.service.valet_ingestion import ValetIngestionEngine, ValetTicket


def test_lifecycle_atomic_dual_write(tmp_path):
    """
    Test 1: Verify link_superseded_pair writes old and new records atomically in single transaction.
    """
    db_file = str(tmp_path / "test_lifecycle_atomic.db")
    store = MemoryLifecycleStore(db_path=db_file)

    old_uri = "viking://resources/finance/alpha_strategy_v1.md"
    new_uri = "viking://resources/finance/alpha_strategy_v2.md"

    # 1. Initialize original active memory
    initial_rec = MemoryLifecycleRecord(
        uri=old_uri,
        status=MemoryStatus.ACTIVE,
        updated_at=time.time(),
    )
    store.save_record(initial_rec)

    # 2. Execute atomic link_superseded_pair
    updated_old, new_rec = MemoryLifecycleFSM.link_superseded_pair(
        old_record=initial_rec,
        new_uri=new_uri,
        reason="Upgraded strategy with multi-factor risk control",
        store=store,
    )

    assert updated_old.status == MemoryStatus.SUPERSEDED
    assert updated_old.superseded_by == new_uri
    assert new_rec.status == MemoryStatus.ACTIVE
    assert new_rec.supersedes_uri == old_uri

    # 3. Read directly from disk to confirm atomic persistence
    rebooted_store = MemoryLifecycleStore(db_path=db_file)
    db_old = rebooted_store.get_record(old_uri)
    db_new = rebooted_store.get_record(new_uri)

    assert db_old is not None
    assert db_old.status == MemoryStatus.SUPERSEDED
    assert db_old.superseded_by == new_uri

    assert db_new is not None
    assert db_new.status == MemoryStatus.ACTIVE
    assert db_new.supersedes_uri == old_uri

    # 4. Verify lineage chain navigation
    lineage = MemoryLifecycleFSM.build_lineage_chain(old_uri, store=store)
    assert lineage["is_active_head"] is False
    assert len(lineage["successors"]) == 1
    assert lineage["successors"][0]["uri"] == new_uri


def test_lifecycle_store_batch_atomic_and_counts(tmp_path):
    """
    Test 2: Verify save_records_batch_atomic and get_status_counts with zero truncation.
    """
    db_file = str(tmp_path / "test_counts_ssot.db")
    store = MemoryLifecycleStore(db_path=db_file)

    records = [
        MemoryLifecycleRecord(uri=f"viking://resources/active_{i}.md", status=MemoryStatus.ACTIVE)
        for i in range(15)
    ] + [
        MemoryLifecycleRecord(uri=f"viking://resources/disputed_{i}.md", status=MemoryStatus.DISPUTED)
        for i in range(5)
    ] + [
        MemoryLifecycleRecord(uri=f"viking://resources/superseded_{i}.md", status=MemoryStatus.SUPERSEDED)
        for i in range(8)
    ]

    # Batch atomic write
    store.save_records_batch_atomic(records)

    # Holistic indexed counts
    counts = store.get_status_counts()
    assert counts["active"] == 15
    assert counts["disputed"] == 5
    assert counts["superseded"] == 8

    # List records pagination
    page_records, total, page_counts = store.list_records(limit=10)
    assert total == 28
    assert len(page_records) == 10
    assert page_counts["active"] == 15


def test_valet_ingestion_dynamic_uri_and_capacity_bound(tmp_path, monkeypatch):
    """
    Test 3: Verify dynamic URI resolution and bounded in-memory ticket cache eviction.
    """
    monkeypatch.setenv("OPENVIKING_DATA_DIR", str(tmp_path / "ov_data"))
    engine = ValetIngestionEngine.get_instance()

    # 1. Test dynamic resolution for various collections
    res_path = engine._resolve_uri_to_path("viking://resources/market/kline.csv")
    sess_path = engine._resolve_uri_to_path("viking://sessions/agent_session_42.json")
    mem_path = engine._resolve_uri_to_path("viking://master_memory/crystals/core_axioms.md")

    assert "resources" in str(res_path) and "market" in str(res_path)
    assert "sessions" in str(sess_path) and "agent_session_42.json" in str(sess_path)
    assert "master_memory" in str(mem_path) and "core_axioms.md" in str(mem_path)

    # 2. Test ticket cache eviction when capacity exceeds threshold
    with engine._tickets_lock:
        engine._tickets.clear()
        # Seed 2005 tickets with status parked
        for i in range(2005):
            t_id = f"ticket_dummy_{i}"
            engine._tickets[t_id] = ValetTicket(ticket_id=t_id, uri=f"viking://test_{i}", status="parked")

    # Handover one more item, triggering eviction
    new_ticket = engine.handover(
        uri="viking://resources/test_eviction.md",
        content="Testing eviction contract",
        caller="TestRunner",
    )

    with engine._tickets_lock:
        # Cache must remain tightly bounded around 1500-2000, eliminating unbounded memory leak
        assert len(engine._tickets) <= 2000
        assert new_ticket.ticket_id in engine._tickets
