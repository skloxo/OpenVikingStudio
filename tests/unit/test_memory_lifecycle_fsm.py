# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Memory Lifecycle FSM, Automated Conflict Linking, and Demotion.
(Card-Memory-LifecycleFSM / v1.5.32)
"""

import time
import pytest
from fastapi.testclient import TestClient

from openviking.service.memory_lifecycle_fsm import (
    MemoryLifecycleFSM,
    MemoryLifecycleRecord,
    MemoryStatus,
    LifecycleTransitionEvent,
    InvalidLifecycleTransitionError,
)
from openviking.service.memory_dual_track import (
    DualTrackMemory,
    format_dual_track_markdown,
    extract_dual_track,
)
from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking_cli.session.user_id import UserIdentifier


def test_fsm_valid_and_invalid_transitions():
    """Verify canonical state machine paths and illegal transition guards."""
    record = MemoryLifecycleRecord(uri="viking://resources/memory/lesson_1.md", status=MemoryStatus.ACTIVE)

    # 1. Active -> Disputed
    disputed = MemoryLifecycleFSM.transition(
        record=record,
        event=LifecycleTransitionEvent.DISPUTE,
        reason="Observed contradictory execution outcome",
    )
    assert disputed.status == MemoryStatus.DISPUTED
    assert disputed.disputed_reason == "Observed contradictory execution outcome"

    # 2. Disputed -> Resolved (Active)
    resolved = MemoryLifecycleFSM.transition(
        record=disputed,
        event=LifecycleTransitionEvent.RESOLVE,
    )
    assert resolved.status == MemoryStatus.ACTIVE
    assert resolved.disputed_reason is None

    # 3. Active -> Superseded (requires target_uri)
    with pytest.raises(InvalidLifecycleTransitionError, match="requires a non-empty target_uri"):
        MemoryLifecycleFSM.transition(
            record=resolved,
            event=LifecycleTransitionEvent.SUPERSEDE,
            target_uri="",
        )

    superseded = MemoryLifecycleFSM.transition(
        record=resolved,
        event=LifecycleTransitionEvent.SUPERSEDE,
        target_uri="viking://resources/memory/lesson_2.md",
        reason="Overruled by verified v1.5.32 fix",
    )
    assert superseded.status == MemoryStatus.SUPERSEDED
    assert superseded.superseded_by == "viking://resources/memory/lesson_2.md"

    # 4. Illegal transition: Superseded cannot directly dispute without revert
    with pytest.raises(InvalidLifecycleTransitionError, match="Illegal memory lifecycle transition"):
        MemoryLifecycleFSM.transition(
            record=superseded,
            event=LifecycleTransitionEvent.DISPUTE,
        )

    # 5. Superseded -> Revert (Active)
    reverted = MemoryLifecycleFSM.transition(
        record=superseded,
        event=LifecycleTransitionEvent.REVERT,
    )
    assert reverted.status == MemoryStatus.ACTIVE
    assert reverted.superseded_by is None


def test_fsm_atomic_link_and_lineage_graph():
    """Verify atomic superseding link and forward/backward lineage tree traversal."""
    old_rec = MemoryLifecycleRecord(uri="viking://resources/rules/old_rule.md", status=MemoryStatus.ACTIVE)
    now_ts = time.time()

    # Link old to new
    updated_old, new_rec = MemoryLifecycleFSM.link_superseded_pair(
        old_record=old_rec,
        new_uri="viking://resources/rules/new_rule.md",
        reason="Refined with non-parametric fusion",
        now_ts=now_ts,
    )
    assert updated_old.status == MemoryStatus.SUPERSEDED
    assert updated_old.superseded_by == "viking://resources/rules/new_rule.md"
    assert new_rec.status == MemoryStatus.ACTIVE
    assert new_rec.supersedes_uri == "viking://resources/rules/old_rule.md"

    # Link new_rule to v3_rule
    updated_mid, v3_rec = MemoryLifecycleFSM.link_superseded_pair(
        old_record=new_rec,
        new_uri="viking://resources/rules/v3_rule.md",
        reason="Upgraded to v3",
        now_ts=now_ts + 10,
    )

    records = {
        updated_old.uri: updated_old,
        updated_mid.uri: updated_mid,
        v3_rec.uri: v3_rec,
    }

    # Trace lineage from mid
    mid_lineage = MemoryLifecycleFSM.build_lineage_chain(updated_mid.uri, records)
    assert mid_lineage["status"] == "superseded"
    assert len(mid_lineage["predecessors"]) == 1
    assert mid_lineage["predecessors"][0]["uri"] == "viking://resources/rules/old_rule.md"
    assert len(mid_lineage["successors"]) == 1
    assert mid_lineage["successors"][0]["uri"] == "viking://resources/rules/v3_rule.md"
    assert mid_lineage["is_active_head"] is False

    # Trace lineage from v3 (active head)
    v3_lineage = MemoryLifecycleFSM.build_lineage_chain(v3_rec.uri, records)
    assert v3_lineage["status"] == "active"
    assert len(v3_lineage["predecessors"]) == 2
    assert v3_lineage["is_active_head"] is True


def test_dual_track_markdown_lifecycle_persistence():
    """Verify dual-track markdown preserves status, superseded_by, and reason."""
    raw_md = format_dual_track_markdown(
        title="Superseded Logging Rule",
        semantic_anchor="Always write synchronous debug logs.",
        delta="def log(): pass",
        extra_metadata={
            "status": "superseded",
            "superseded_by": "viking://resources/rules/async_logger.md",
            "disputed_reason": "Causes async loop lag",
        },
    )

    dt: DualTrackMemory = extract_dual_track(raw_md)
    assert dt.status == "superseded"
    assert dt.superseded_by == "viking://resources/rules/async_logger.md"
    assert dt.disputed_reason == "Causes async loop lag"
    assert dt.is_dual_track is True


def test_memory_lifecycle_rest_api():
    """Verify FastAPI routes for status transitions, linking, and lineage inspection."""
    import uuid

    uid = uuid.uuid4().hex[:8]
    old_uri = f"viking://session/legacy_bug_{uid}.md"
    new_uri = f"viking://session/fixed_root_cause_{uid}.md"

    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="test-user"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    # 1. Link old to new via POST /api/v1/memory/link
    link_res = client.post(
        "/api/v1/memory/link",
        json={
            "old_uri": old_uri,
            "new_uri": new_uri,
            "reason": "Root cause identified in v1.5.32",
        },
    )
    assert link_res.status_code == 200
    link_data = link_res.json()["result"]
    assert link_data["old_record"]["status"] == "superseded"
    assert link_data["new_record"]["status"] == "active"

    # 2. GET /api/v1/memory/lineage
    lineage_res = client.get(f"/api/v1/memory/lineage?uri={old_uri}")
    assert lineage_res.status_code == 200
    lineage_data = lineage_res.json()["result"]
    assert lineage_data["status"] == "superseded"
    assert len(lineage_data["successors"]) >= 1

    # 3. Transition status via POST /api/v1/memory/status (Dispute new)
    trans_res = client.post(
        "/api/v1/memory/status",
        json={
            "uri": new_uri,
            "event": "dispute",
            "reason": "Regression detected on Edge browser",
        },
    )
    assert trans_res.status_code == 200
    trans_data = trans_res.json()["result"]
    assert trans_data["status"] == "disputed"

    # 4. GET /api/v1/memory/records
    rec_res = client.get("/api/v1/memory/records?status=disputed")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()["result"]
    assert rec_data["total"] >= 1
    assert any(r["uri"] == new_uri for r in rec_data["records"])


@pytest.mark.asyncio
async def test_hybrid_retriever_demotes_superseded_memory(tmp_path):
    """Verify hybrid retriever penalizes superseded memories by 0.20x in RRF fusion."""
    from openviking.storage.bm25_fts_index import BM25FTSIndex
    from openviking.retrieve.hybrid_retriever import HybridRetriever

    db_path = tmp_path / "test_lifecycle_bm25.db"
    index = BM25FTSIndex(db_path=db_path)
    retriever = HybridRetriever(bm25_index=index)

    now = time.time()
    # 1. Provide two candidates: one active, one superseded
    dense_candidates = [
        {
            "uri": "viking://resources/memory/superseded_approach.md",
            "score": 0.95,
            "title": "Deprecated Fast Approach",
            "extra_metadata": {"status": "superseded", "updated_ts": now},
        },
        {
            "uri": "viking://resources/memory/new_verified_approach.md",
            "score": 0.85,
            "title": "Verified Robust Approach",
            "extra_metadata": {"status": "active", "updated_ts": now},
        },
    ]

    results = await retriever.retrieve_hybrid(
        query="approach to async processing",
        dense_candidates=dense_candidates,
        limit=5,
    )

    assert len(results) >= 2
    # The active candidate must rank #1 despite having lower raw dense score (0.85 vs 0.95),
    # because the superseded candidate suffers 0.20x penalty!
    assert results[0].uri == "viking://resources/memory/new_verified_approach.md"
    assert results[1].uri == "viking://resources/memory/superseded_approach.md"
    assert results[1].extra_metadata["status"] == "superseded"
    assert results[1].extra_metadata["decay_factor"] == 0.20


def test_memory_lifecycle_sqlite_persistence_across_instances(tmp_path):
    """Verify memory lifecycle state survives instance re-creation (Zero Memory-Silo Bug)."""
    from openviking.service.memory_lifecycle_fsm import (
        MemoryLifecycleStore,
        MemoryLifecycleRecord,
        MemoryStatus,
        LifecycleTransitionEvent,
        MemoryLifecycleFSM,
    )

    db_path = str(tmp_path / "test_lifecycle_persist.db")
    store1 = MemoryLifecycleStore(db_path=db_path)

    rec1 = MemoryLifecycleRecord(uri="viking://test/rule_persist.md", status=MemoryStatus.ACTIVE)
    store1.save_record(rec1)

    # Transition to superseded
    MemoryLifecycleFSM.transition(
        record=rec1,
        event=LifecycleTransitionEvent.SUPERSEDE,
        target_uri="viking://test/new_rule.md",
        reason="Overruled in test",
        store=store1,
    )
    # Ensure saved in store1
    rec_updated = store1.get_record("viking://test/rule_persist.md")
    assert rec_updated.status == MemoryStatus.SUPERSEDED
    assert rec_updated.superseded_by == "viking://test/new_rule.md"

    # Simulate service restart: create fresh store2 pointing to same db_path
    store2 = MemoryLifecycleStore(db_path=db_path)
    rec_loaded = store2.get_record("viking://test/rule_persist.md")

    assert rec_loaded is not None
    assert rec_loaded.status == MemoryStatus.SUPERSEDED
    assert rec_loaded.superseded_by == "viking://test/new_rule.md"
    assert rec_loaded.disputed_reason == "Overruled in test"


