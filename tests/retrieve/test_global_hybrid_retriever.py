# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

"""Tests for GlobalHybridRetriever: single-stage hybrid recall, anti-starvation, and score fidelity."""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from openviking.core.context import ContextLevel
from openviking.retrieve.global_hybrid_retriever import (
    GlobalHybridRetriever,
    RetrieverMode,
)
from openviking.retrieve.hierarchical_retriever import HierarchicalRetriever
from openviking.server.identity import RequestContext, Role
from openviking_cli.retrieve.types import ContextType, MatchedContext, QueryResult, TypedQuery
from openviking_cli.session.user_id import UserIdentifier


def _make_result(uri, score=0.85, level=2, abstract=None, **extra):
    res = {
        "uri": uri,
        "abstract": abstract if abstract is not None else uri.rsplit("/", 1)[-1],
        "_score": score,
        "level": level,
        "context_type": "resource",
    }
    res.update(extra)
    return res


class DummyEmbedResult:
    def __init__(self) -> None:
        self.dense_vector = [0.1] * 128
        self.sparse_vector = {"test": 1.0}


class DummyEmbedder:
    def prepare_embedding_input(self, text: str) -> str:
        return text

    def embed(self, _query: str, is_query: bool = False) -> DummyEmbedResult:
        return DummyEmbedResult()

    async def embed_async(self, text: str, is_query: bool = False) -> DummyEmbedResult:
        return self.embed(text, is_query=is_query)


class DummyVectorStorage:
    collection_name = "context"

    def __init__(self, results=None):
        self.results = list(results or [])
        self.search_calls = []

    async def get_account_backend(self, account_id):
        assert account_id
        return self

    async def collection_exists(self):
        return True

    async def search_in_tenant(self, ctx=None, **kwargs):
        self.search_calls.append({"ctx": ctx, **kwargs})
        level = kwargs.get("level")
        results = [
            dict(result)
            for result in self.results
            if level is None or result.get("level", 2) in level
        ]
        results.sort(key=lambda result: result["_score"], reverse=True)
        limit = kwargs.get("limit")
        return results[:limit] if limit else results


def _req_ctx():
    return RequestContext(
        user=UserIdentifier(account_id="acc_default", user_id="usr_001"),
        role=Role.ADMIN,
    )


@pytest.mark.asyncio
async def test_deep_nested_file_recall_anti_starvation():
    """Verify that deep nested files (e.g. at depth 4) are recalled without hierarchical pruning."""
    deep_uri = "viking://resources/deep/level1/level2/level3/target_doc.md"
    storage = DummyVectorStorage(
        results=[
            _make_result(deep_uri, score=0.92, level=2, abstract="Critical core specification"),
            _make_result("viking://resources/shallow/root.md", score=0.45, level=0),
        ]
    )
    retriever = GlobalHybridRetriever(storage=storage, embedder=DummyEmbedder())

    query = TypedQuery(query="critical specification", intent="", context_type=ContextType.RESOURCE)
    res = await retriever.retrieve(query, ctx=_req_ctx(), limit=5)

    assert isinstance(res, QueryResult)
    matched_uris = [c.uri for c in res.matched_contexts]
    # Deep file must be Top-1, not starved by low-scoring shallow ancestors
    assert matched_uris[0] == deep_uri
    assert res.matched_contexts[0].score >= 0.85


@pytest.mark.asyncio
async def test_physical_score_fidelity_and_threshold_filtering():
    """Ensure scores remain in continuous physical [0, 1] scale so score_threshold=0.5 works as expected."""
    storage = DummyVectorStorage(
        results=[
            _make_result("viking://resources/high.md", score=0.88),
            _make_result("viking://resources/mid.md", score=0.62),
            _make_result("viking://resources/low.md", score=0.25),
        ]
    )
    retriever = GlobalHybridRetriever(storage=storage, embedder=DummyEmbedder())

    query = TypedQuery(query="score test", intent="", context_type=ContextType.RESOURCE)
    # Threshold 0.5 must filter out low.md (0.25) but keep high.md and mid.md
    res = await retriever.retrieve(query, ctx=_req_ctx(), limit=5, score_threshold=0.5)

    matched_uris = [c.uri for c in res.matched_contexts]
    assert "viking://resources/high.md" in matched_uris
    assert "viking://resources/mid.md" in matched_uris
    assert "viking://resources/low.md" not in matched_uris

    # Check scores: not collapsed to 0.01~0.03
    for c in res.matched_contexts:
        assert 0.5 <= c.score <= 1.0


@pytest.mark.asyncio
async def test_fail_open_when_bm25_fails():
    """Verify Fail-Open degradation to pure vector search if BM25 throws an error."""
    storage = DummyVectorStorage(results=[_make_result("viking://resources/safe.md", score=0.80)])
    retriever = GlobalHybridRetriever(storage=storage, embedder=DummyEmbedder())

    # Simulate broken BM25 index
    with patch.object(retriever, "_search_bm25", side_effect=RuntimeError("SQLite FTS5 locked")):
        query = TypedQuery(query="fail open test", intent="", context_type=ContextType.RESOURCE)
        res = await retriever.retrieve(query, ctx=_req_ctx(), limit=5)

        assert len(res.matched_contexts) == 1
        assert res.matched_contexts[0].uri == "viking://resources/safe.md"
        # Telemetry / metadata must record bm25 failure honestly
        assert res.matched_contexts[0].extra_metadata.get("is_bm25_ready") is False


@pytest.mark.asyncio
async def test_facade_hierarchical_retriever_compatibility():
    """Verify that HierarchicalRetriever preserves 100% backward compatibility as a facade."""
    storage = DummyVectorStorage(results=[_make_result("viking://resources/legacy.md", score=0.85)])
    facade = HierarchicalRetriever(storage=storage, embedder=DummyEmbedder())

    query = TypedQuery(query="legacy compatibility", intent="", context_type=ContextType.RESOURCE)
    res = await facade.retrieve(query, ctx=_req_ctx(), limit=5)

    assert isinstance(res, QueryResult)
    assert len(res.matched_contexts) == 1
    assert res.matched_contexts[0].uri == "viking://resources/legacy.md"


@pytest.mark.asyncio
async def test_asymmetric_time_decay_integration():
    """Verify that recent event memories are protected while old records undergo smooth decay."""
    now = datetime.now(timezone.utc)
    fresh_time = (now - timedelta(days=1)).isoformat()
    stale_time = (now - timedelta(days=30)).isoformat()

    storage = DummyVectorStorage(
        results=[
            _make_result(
                "viking://memories/fresh_event.md",
                score=0.85,
                context_type="memory",
                updated_ts=fresh_time,
                memory_type="event",
            ),
            _make_result(
                "viking://memories/stale_event.md",
                score=0.85,
                context_type="memory",
                updated_ts=stale_time,
                memory_type="event",
            ),
        ]
    )
    retriever = GlobalHybridRetriever(storage=storage, embedder=DummyEmbedder())

    query = TypedQuery(query="event update", intent="", context_type=ContextType.MEMORY)
    res = await retriever.retrieve(query, ctx=_req_ctx(), limit=5, request_now=now)

    fresh_match = next(c for c in res.matched_contexts if "fresh_event" in c.uri)
    stale_match = next(c for c in res.matched_contexts if "stale_event" in c.uri)

    # Fresh event should have decay_factor 1.0 (3-day protection)
    # Stale event should have decayed score
    assert fresh_match.score > stale_match.score
