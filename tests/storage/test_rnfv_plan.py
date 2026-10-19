# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""TDD Retina Tests for RNFV Pure Functional Planning Pipeline.

First Principles:
Zero Added Entity: Pure functional in-memory diffing pipeline.
RNFVSnapshot (R, N, F, V) -> ActionPlan (files, vectors, orphans).
"""

import time
import pytest
from openviking.storage.transaction.rnfv_plan import (
    RNFVSnapshot,
    RequestIntent,
    FileEntry,
    VectorEntry,
    ActionPlan,
    plan_rnfv_actions,
    build_dlq_payload_from_error,
)


class TestRNFVPlanningPipeline:
    """Test suite verifying pure functional RNFV transaction planning."""

    def test_clean_ingest_plan(self):
        """Phase 1: Pure ingest where Formal Tree and Vector Index are initially empty."""
        snapshot = RNFVSnapshot(
            intent=RequestIntent(
                action="write",
                target_uri="viking://resources/docs/guide.md",
                account_id="acc_default",
                user_id="usr_001",
            ),
            new_artifacts=[
                FileEntry(path="viking://resources/docs/guide.md", md5="hash_content_1", size=1024),
                FileEntry(path="viking://resources/docs/.abstract.md", md5="hash_abs_1", size=128),
            ],
            formal_tree=[],
            vector_records=[],
        )

        plan: ActionPlan = plan_rnfv_actions(snapshot)

        assert len(plan.files_to_write) == 2
        assert len(plan.files_to_delete) == 0
        assert len(plan.vectors_to_upsert) == 0
        assert len(plan.vectors_to_delete) == 0
        assert plan.orphans_detected == 0
        assert plan.intent_action == "write"

    def test_in_place_update_with_orphan_vector_purge(self):
        """Phase 2: Updating existing file with smaller chunks purges orphaned vectors."""
        formal_files = [
            FileEntry(path="viking://resources/docs/guide.md", md5="old_hash", size=2048)
        ]
        existing_vectors = [
            VectorEntry(id="vec_chunk_1", uri="viking://resources/docs/guide.md", md5="old_c1"),
            VectorEntry(id="vec_chunk_2", uri="viking://resources/docs/guide.md", md5="old_c2"),
            VectorEntry(id="vec_chunk_3", uri="viking://resources/docs/guide.md", md5="old_c3"),
        ]

        # New content only produces chunk_1 and chunk_2
        new_files = [
            FileEntry(path="viking://resources/docs/guide.md", md5="new_hash", size=1024)
        ]
        new_vectors = [
            VectorEntry(id="vec_chunk_1", uri="viking://resources/docs/guide.md", md5="new_c1"),
            VectorEntry(id="vec_chunk_2", uri="viking://resources/docs/guide.md", md5="new_c2"),
        ]

        snapshot = RNFVSnapshot(
            intent=RequestIntent(
                action="write",
                target_uri="viking://resources/docs/guide.md",
                account_id="acc_default",
            ),
            new_artifacts=new_files,
            formal_tree=formal_files,
            vector_records=existing_vectors,
            new_vectors=new_vectors,
        )

        plan: ActionPlan = plan_rnfv_actions(snapshot)

        assert len(plan.files_to_write) == 1
        assert plan.files_to_write[0].md5 == "new_hash"
        assert len(plan.vectors_to_upsert) == 2
        # chunk_3 is not in new_vectors, must be purged as an orphan!
        assert len(plan.vectors_to_delete) == 1
        assert plan.vectors_to_delete[0] == "vec_chunk_3"
        assert plan.orphans_detected == 1

    def test_delete_intent_cascades_formal_and_vectors(self):
        """Phase 3: DELETE intent calculates deletion of formal files and all associated vectors."""
        formal_files = [
            FileEntry(path="viking://resources/docs/guide.md", md5="hash_1", size=1024),
            FileEntry(path="viking://resources/docs/.abstract.md", md5="hash_2", size=128),
        ]
        existing_vectors = [
            VectorEntry(id="vec_1", uri="viking://resources/docs/guide.md", md5="hash_1"),
            VectorEntry(id="vec_2", uri="viking://resources/docs/guide.md", md5="hash_1"),
        ]

        snapshot = RNFVSnapshot(
            intent=RequestIntent(
                action="delete",
                target_uri="viking://resources/docs",
                account_id="acc_default",
            ),
            new_artifacts=[],
            formal_tree=formal_files,
            vector_records=existing_vectors,
        )

        plan: ActionPlan = plan_rnfv_actions(snapshot)

        assert len(plan.files_to_write) == 0
        assert len(plan.files_to_delete) == 2
        assert len(plan.vectors_to_upsert) == 0
        assert len(plan.vectors_to_delete) == 2
        assert set(plan.vectors_to_delete) == {"vec_1", "vec_2"}

    def test_pure_functional_idempotency_and_latency(self):
        """Phase 4: Assert 100% idempotency and < 5ms pure computation latency."""
        formal_files = [
            FileEntry(path=f"viking://resources/node_{i}.md", md5=f"hash_{i}", size=512)
            for i in range(100)
        ]
        existing_vectors = [
            VectorEntry(id=f"v_{i}_{c}", uri=f"viking://resources/node_{i}.md", md5=f"vhash_{i}_{c}")
            for i in range(100)
            for c in range(5)
        ]

        new_files = [
            FileEntry(path="viking://resources/node_0.md", md5="updated_hash", size=600)
        ]
        new_vectors = [
            VectorEntry(id="v_0_0", uri="viking://resources/node_0.md", md5="new_vhash_0"),
        ]

        snapshot = RNFVSnapshot(
            intent=RequestIntent(
                action="write",
                target_uri="viking://resources/node_0.md",
                account_id="acc_default",
            ),
            new_artifacts=new_files,
            formal_tree=formal_files,
            vector_records=existing_vectors,
            new_vectors=new_vectors,
        )

        start = time.perf_counter()
        plan_a = plan_rnfv_actions(snapshot)
        elapsed_ms = (time.perf_counter() - start) * 1000

        plan_b = plan_rnfv_actions(snapshot)

        # Idempotency check
        assert plan_a == plan_b
        # Latency check: Pure in-memory calculation must be < 10ms even with 500 vectors
        assert elapsed_ms < 10.0, f"RNFV planning took too long: {elapsed_ms:.2f}ms"
        # 4 out of 5 vectors for node_0 became orphans and must be deleted
        assert len(plan_a.vectors_to_delete) == 4

    def test_dlq_payload_generation_on_failure(self):
        """Phase 5: If an unrecoverable conflict occurs, generate DLQ-compatible payload."""
        intent = RequestIntent(
            action="write",
            target_uri="viking://resources/docs/corrupt.md",
            account_id="acc_test",
        )
        error = ValueError("Path traversal forbidden: ../../etc/passwd")

        dlq_record = build_dlq_payload_from_error(
            intent=intent,
            error=error,
            queue_name="resource_transaction_dlq",
        )

        assert dlq_record["queue_name"] == "resource_transaction_dlq"
        assert dlq_record["uri"] == "viking://resources/docs/corrupt.md"
        assert dlq_record["account_id"] == "acc_test"
        assert dlq_record["error_type"] == "ValueError"
        assert "Path traversal forbidden" in dlq_record["error_message"]
