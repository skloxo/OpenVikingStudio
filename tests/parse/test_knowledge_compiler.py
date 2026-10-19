# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""TDD Retina Tests for Map-Shuffle-Reduce Knowledge Compiler Pipeline.

First Principles & Munger Inversion:
1. Map: fine-grained AST/token-bounded slicing.
2. Shuffle: domain clustering into discrete buckets with SHA256 fingerprints.
3. Reduce: hierarchical L1 module summaries + top-level L0 system ontology.
4. Incremental Caching: unmodified buckets skip LLM summarization completely.
"""

import pytest
from openviking.parse.compiler.pipeline import (
    SourceDocument,
    DocumentChunk,
    DomainBucket,
    CompilationResult,
    KnowledgeCompiler,
)


class TestKnowledgeCompilerPipeline:
    """Test suite verifying Map-Shuffle-Reduce knowledge compilation."""

    @pytest.fixture
    def sample_documents(self):
        return [
            SourceDocument(
                path="openviking/auth/jwt.py",
                content="def verify_token(token): return True\ndef decode_token(t): return {}",
                module="auth",
            ),
            SourceDocument(
                path="openviking/auth/models.py",
                content="class UserPrincipal: id: str; account: str",
                module="auth",
            ),
            SourceDocument(
                path="openviking/storage/viking_fs.py",
                content="class VikingFS: def read(p): pass; def write(p, d): pass",
                module="storage",
            ),
            SourceDocument(
                path="openviking/storage/viking_db.py",
                content="class VikingDB: def upsert(v): pass; def search(q): pass",
                module="storage",
            ),
            SourceDocument(
                path="openviking/server/app.py",
                content="app = FastAPI(); app.include_router(auth_router)",
                module="server",
            ),
        ]

    def test_full_map_shuffle_reduce_lifecycle(self, sample_documents):
        """Phase 1: Full pipeline transforms source documents into L0/L1 topology."""
        compiler = KnowledgeCompiler()
        result: CompilationResult = compiler.compile(sample_documents)

        # 1. Map assertions
        assert len(result.total_chunks) >= 5
        # 2. Shuffle assertions: exactly 3 buckets: auth, storage, server
        assert set(result.buckets.keys()) == {"auth", "storage", "server"}
        assert len(result.buckets["auth"].chunks) == 2
        assert len(result.buckets["storage"].chunks) == 2
        assert len(result.buckets["server"].chunks) == 1

        # 3. Reduce assertions: each bucket has L1 summary, plus top-level L0 overview
        assert len(result.l1_summaries) == 3
        assert "auth" in result.l1_summaries
        assert "storage" in result.l1_summaries
        assert result.l0_overview is not None
        assert "auth" in result.l0_overview.topology
        assert "storage" in result.l0_overview.topology
        assert result.status == "completed"

    def test_incremental_bucket_fingerprint_caching(self, sample_documents):
        """Phase 2: Munger Inversion Guard - unchanged buckets must hit cache and skip LLM."""
        summarizer_calls = []

        def mock_summarizer(bucket_name, chunks):
            summarizer_calls.append(bucket_name)
            return f"Summary for {bucket_name} with {len(chunks)} chunks"

        compiler = KnowledgeCompiler(summarizer_fn=mock_summarizer)

        # Run 1: Cold start, all 3 buckets must be reduced
        first_result = compiler.compile(sample_documents)
        assert len(summarizer_calls) == 3

        # Run 2: Update only server/app.py, auth and storage are untouched
        updated_documents = [
            doc if doc.path != "openviking/server/app.py"
            else SourceDocument(
                path="openviking/server/app.py",
                content="app = FastAPI(); # Modified app",
                module="server",
            )
            for doc in sample_documents
        ]

        summarizer_calls.clear()
        second_result = compiler.compile(
            updated_documents,
            previous_result=first_result,
        )

        # Assert incremental cache hit: only 'server' was re-reduced!
        assert summarizer_calls == ["server"]
        assert second_result.cache_hits == 2  # auth and storage were cached
        assert second_result.cache_misses == 1  # server was recomputed
        assert second_result.l1_summaries["auth"] == first_result.l1_summaries["auth"]
        assert second_result.l1_summaries["storage"] == first_result.l1_summaries["storage"]

    def test_resilient_fallback_on_summarizer_error(self, sample_documents):
        """Phase 3: Fail-safe fallback when reduction encounters an error."""
        def faulty_summarizer(bucket_name, chunks):
            if bucket_name == "storage":
                raise RuntimeError("LLM rate limit / timeout on storage")
            return f"Healthy summary for {bucket_name}"

        compiler = KnowledgeCompiler(summarizer_fn=faulty_summarizer)
        result = compiler.compile(sample_documents)

        # Storage should degrade gracefully to deterministic structural summary without crashing
        assert "storage" in result.l1_summaries
        assert "[Fallback Topology]" in result.l1_summaries["storage"]
        assert "auth" in result.l1_summaries
        assert result.status == "completed_with_fallbacks"
