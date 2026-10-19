# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
TDD Retina Tests for Card-189:
1. Multimodal hybrid retrieval input support (list of image URLs, client normalization).
2. CompositeHybridEmbedder multimodal routing: dense handles images, sparse skips images and avoids failure.
3. Explicit scope & target protection in Hierarchical/Global retrieval for image queries.
4. SearchService image_url list resolution.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openviking.core.retrieval_types import SearchType
from openviking.models.embedder.base import (
    CompositeHybridEmbedder,
    DenseEmbedderBase,
    EmbedResult,
    EmbedderBase,
    SparseEmbedderBase,
)
from openviking.retrieve.global_hybrid_retriever import (
    GlobalHybridRetriever,
    _has_context_type_filter,
)
from openviking.server.identity import RequestContext, Role
from openviking_cli.session.user_id import UserIdentifier
from openviking.service.search_service import SearchService, _ensure_non_empty_query
from openviking.utils.image_search import (
    build_multimodal_embedding_input,
    normalize_client_image_input,
)
from openviking_cli.retrieve.types import ContextType, TypedQuery


# ---------------------------------------------------------------------------
# 1. Multimodal input helper tests
# ---------------------------------------------------------------------------


def test_build_multimodal_embedding_input_accepts_list_of_images():
    """Verify build_multimodal_embedding_input handles str, list[str], and None."""
    # Single image
    single = build_multimodal_embedding_input("cat photo", "data:image/png;base64,YQ==")
    assert single == [
        {"type": "text", "text": "cat photo"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,YQ=="}},
    ]

    # Multiple images
    multi = build_multimodal_embedding_input(
        "two cats",
        ["data:image/png;base64,YQ==", "viking://resources/photos/cat2.png"],
    )
    assert multi == [
        {"type": "text", "text": "two cats"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,YQ=="}},
        {"type": "image_url", "image_url": {"url": "viking://resources/photos/cat2.png"}},
    ]

    # None or empty
    text_only = build_multimodal_embedding_input("only text", None)
    assert text_only == [{"type": "text", "text": "only text"}]


def test_normalize_client_image_input_accepts_list():
    """Verify normalize_client_image_input recursively normalizes a list of images."""
    inputs = [
        "viking://resources/1.png",
        "data:image/png;base64,YQ==",
    ]
    normalized = normalize_client_image_input(inputs)
    assert isinstance(normalized, list)
    assert normalized == ["viking://resources/1.png", "data:image/png;base64,YQ=="]


# ---------------------------------------------------------------------------
# 2. CompositeHybridEmbedder multimodal routing
# ---------------------------------------------------------------------------


class MockDenseEmbedder(DenseEmbedderBase):
    def __init__(self, supports_multi: bool = True):
        super().__init__(model_name="mock-dense")
        self.dimension = 4
        self._supports_multi = supports_multi
        self.dense_calls = 0

    @property
    def supports_multimodal(self) -> bool:
        return self._supports_multi

    def embed(self, content: Any, is_query: bool = False) -> EmbedResult:
        self.dense_calls += 1
        return EmbedResult(dense_vector=[0.1, 0.2, 0.3, 0.4])

    async def embed_async(self, content: Any, is_query: bool = False) -> EmbedResult:
        self.dense_calls += 1
        return EmbedResult(dense_vector=[0.1, 0.2, 0.3, 0.4])

    def get_dimension(self) -> int:
        return 4


class MockSparseEmbedder(SparseEmbedderBase):
    def __init__(self):
        super().__init__(model_name="mock-sparse")
        self.sparse_calls = 0

    @property
    def supports_multimodal(self) -> bool:
        return False

    def embed(self, content: Any, is_query: bool = False) -> EmbedResult:
        if isinstance(content, list) or (isinstance(content, str) and not content.strip()):
            raise ValueError("Sparse embedder cannot accept images or empty text!")
        self.sparse_calls += 1
        return EmbedResult(sparse_vector={"term1": 1.0})

    async def embed_async(self, content: Any, is_query: bool = False) -> EmbedResult:
        if isinstance(content, list) or (isinstance(content, str) and not content.strip()):
            raise ValueError("Sparse embedder cannot accept images or empty text!")
        self.sparse_calls += 1
        return EmbedResult(sparse_vector={"term1": 1.0})


@pytest.mark.asyncio
async def test_composite_hybrid_embedder_multimodal_routing():
    """Dense channel accepts images while sparse channel skips image-only input."""
    dense = MockDenseEmbedder(supports_multi=True)
    sparse = MockSparseEmbedder()
    composite = CompositeHybridEmbedder(dense, sparse)

    assert composite.supports_multimodal is True

    # 1. Mixed query: text + image -> dense gets mixed, sparse gets text
    mixed_content = [
        {"type": "text", "text": "cat photo"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,YQ=="}},
    ]
    res_mixed = await composite.embed_async(mixed_content, is_query=True)
    assert res_mixed.dense_vector == [0.1, 0.2, 0.3, 0.4]
    assert res_mixed.sparse_vector == {"term1": 1.0}
    assert dense.dense_calls == 1
    assert sparse.sparse_calls == 1

    # 2. Image-only query: no text -> dense called, sparse SKIPPED, sparse_vector is None
    image_only = [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,YQ=="}},
    ]
    res_image = await composite.embed_async(image_only, is_query=True)
    assert res_image.dense_vector == [0.1, 0.2, 0.3, 0.4]
    assert res_image.sparse_vector is None
    assert dense.dense_calls == 2
    assert sparse.sparse_calls == 1  # not incremented!


# ---------------------------------------------------------------------------
# 3. SearchService image_url resolution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_service_resolves_image_url_list():
    """SearchService._resolve_image_url handles list of URLs."""
    vfs = MagicMock()
    vfs.read_file_bytes = AsyncMock(return_value=b"fake-image-bytes")
    service = SearchService(vfs)
    ctx = RequestContext(user=UserIdentifier.the_default_user("test_user"), role=Role.USER)

    # Mixed list of viking:// and http://
    urls = ["viking://resources/test.png", "https://example.com/photo.jpg"]
    resolved = await service._resolve_image_url(urls, ctx)
    assert isinstance(resolved, list)
    assert resolved[0].startswith("data:image/png;base64,")
    assert resolved[1] == "https://example.com/photo.jpg"


# ---------------------------------------------------------------------------
# 4. Scope and explicit target protection
# ---------------------------------------------------------------------------


def test_has_context_type_filter_detection():
    """Verify _has_context_type_filter recognizes AST and dict forms."""
    assert _has_context_type_filter({"field": "context_type", "operator": "==", "value": "memory"}) is True
    assert _has_context_type_filter({"field": "tag", "value": "blue"}) is False
    assert _has_context_type_filter([{"field": "context_type", "value": "resource"}]) is True
    assert _has_context_type_filter({"and": [{"field": "context_type", "value": "skill"}]}) is True


@pytest.mark.asyncio
async def test_hierarchical_retriever_explicit_scope_and_target_protection():
    """Ensure image search respects explicit scope_dsl and has_explicit_target."""
    storage = MagicMock()
    proxy = MagicMock()
    proxy.collection_exists_bound = AsyncMock(return_value=False)

    retriever = GlobalHybridRetriever(
        storage=storage,
        embedder=MockDenseEmbedder(),
    )
    retriever._create_vector_proxy = MagicMock(return_value=proxy)
    ctx = RequestContext(user=UserIdentifier.the_default_user("user1"), role=Role.USER)

    # Case A: Default image search (no explicit target, no filter) -> context_type defaults to RESOURCE
    # We inspect the context_type logic directly
    typed_query = TypedQuery(
        query="",
        context_type=None,
        intent="",
        target_directories=["viking://user/memories", "viking://resources"],  # default expanded
        image_query=True,
    )
    retriever._search_dense = AsyncMock(return_value=[])
    proxy.collection_exists_bound = AsyncMock(return_value=True)

    # Case A: Default image search (no explicit target, no filter) -> context_type defaults to RESOURCE
    await retriever.retrieve(
        typed_query,
        ctx=ctx,
        has_explicit_target=False,
        scope_dsl=None,
    )
    assert retriever._search_dense.call_args[0][4] == ContextType.RESOURCE.value

    # Case B: Image search with has_explicit_target=True -> context_type stays None (not forced to RESOURCE)
    typed_query_target = TypedQuery(
        query="",
        context_type=None,
        intent="",
        target_directories=["viking://user/memories/preferences"],
        image_query=True,
    )
    await retriever.retrieve(
        typed_query_target,
        ctx=ctx,
        has_explicit_target=True,
        scope_dsl=None,
    )
    assert retriever._search_dense.call_args[0][4] is None

    # Case C: Image search with explicit context_type in scope_dsl -> context_type stays None (not forced to RESOURCE)
    await retriever.retrieve(
        typed_query,
        ctx=ctx,
        has_explicit_target=False,
        scope_dsl={"field": "context_type", "value": "memory"},
    )
    assert retriever._search_dense.call_args[0][4] is None
 
 
@pytest.mark.asyncio
async def test_viking_fs_find_and_search_passes_has_explicit_target():
    """Verify VikingFS.find passes has_explicit_target accurately based on retrieval_targets."""
    from openviking.storage.viking_fs import VikingFS

    vfs = VikingFS(agfs=MagicMock())
    mock_retriever = MagicMock()
    mock_retriever.retrieve = AsyncMock(return_value=SimpleNamespace(matched_contexts=[]))

    vfs._get_vector_store = MagicMock(return_value=MagicMock())
    vfs._get_embedder = MagicMock(return_value=MockDenseEmbedder())
    vfs._ensure_retrieval_scope = AsyncMock()

    with patch("openviking.retrieve.hierarchical_retriever.HierarchicalRetriever", return_value=mock_retriever):
        ctx = RequestContext(user=UserIdentifier.the_default_user("test_user"), role=Role.USER)

        # 1. No target_uri -> has_explicit_target must be False
        await vfs.find(
            query="test",
            image_url="data:image/png;base64,YQ==",
            ctx=ctx,
        )
        assert "has_explicit_target" in mock_retriever.retrieve.call_args.kwargs
        assert mock_retriever.retrieve.call_args.kwargs["has_explicit_target"] is False

        # 2. Explicit target_uri -> has_explicit_target must be True
        await vfs.find(
            query="test",
            image_url="data:image/png;base64,YQ==",
            target_uri="viking://resources/docs",
            ctx=ctx,
        )
        assert "has_explicit_target" in mock_retriever.retrieve.call_args.kwargs
        assert mock_retriever.retrieve.call_args.kwargs["has_explicit_target"] is True


def test_blank_and_dirty_multimodal_input_sanitization():
    """Verify blank, None, or dirty string items are sanitized across all input paths."""
    # 1. build_multimodal_embedding_input filters dirty blank strings
    res = build_multimodal_embedding_input("   ", ["   ", ""])
    assert res == []

    res2 = build_multimodal_embedding_input(
        " valid text ", ["   ", "viking://valid.png", None]
    )
    assert res2 == [
        {"type": "text", "text": "valid text"},
        {"type": "image_url", "image_url": {"url": "viking://valid.png"}},
    ]

    # 2. normalize_client_image_input cleans blank and None items
    assert normalize_client_image_input("   ") is None
    assert normalize_client_image_input("") is None
    assert normalize_client_image_input(["   ", "", None]) is None
    assert normalize_client_image_input(["  viking://a.png  ", "", None]) == [
        "viking://a.png"
    ]


@pytest.mark.asyncio
async def test_search_service_concurrent_image_resolution_and_blank_filtration():
    """Verify SearchService resolves image URLs concurrently and filters empty elements."""
    service = SearchService()
    mock_vfs = MagicMock()
    mock_vfs.read_file_bytes = AsyncMock(return_value=b"fake-bytes")
    service._viking_fs = mock_vfs
    ctx = RequestContext(user=UserIdentifier.the_default_user("test_user"), role=Role.USER)

    # 1. Blank inputs return None
    assert await service._resolve_image_url("", ctx) is None
    assert await service._resolve_image_url("   ", ctx) is None
    assert await service._resolve_image_url(["", "   ", None], ctx) is None

    # 2. Mixed inputs: empty items stripped, viking:// resolved concurrently
    input_urls = [
        "viking://resources/img1.png",
        "   ",
        "viking://resources/img2.png",
        "data:image/png;base64,YQ==",
        None,
    ]
    resolved = await service._resolve_image_url(input_urls, ctx)
    assert isinstance(resolved, list)
    assert len(resolved) == 3
    assert resolved[0].startswith("data:image/png;base64,")
    assert resolved[1].startswith("data:image/png;base64,")
    assert resolved[2] == "data:image/png;base64,YQ=="
    assert mock_vfs.read_file_bytes.call_count == 2


@pytest.mark.asyncio
async def test_composite_hybrid_embedder_sparse_blank_string_bypass():
    """Verify CompositeHybridEmbedder bypasses sparse embedder on blank string input."""
    dense = MockDenseEmbedder()
    sparse = MockSparseEmbedder()
    hybrid = CompositeHybridEmbedder(dense_embedder=dense, sparse_embedder=sparse)

    # Blank string input
    res = await hybrid.embed_async("    ", is_query=True)
    assert res.dense_vector == [0.1, 0.2, 0.3, 0.4]
    assert res.sparse_vector is None
    assert sparse.sparse_calls == 0

    # Sync path
    sync_res = hybrid.embed("   ", is_query=True)
    assert sync_res.sparse_vector is None
    assert sparse.sparse_calls == 0


def test_search_router_image_url_resolution_cleaner():
    """Verify router-level _resolve_image_url filters blanks and strips strings."""
    from openviking.server.routers.search import _resolve_image_url

    ctx = RequestContext(user=UserIdentifier.the_default_user("test_user"), role=Role.USER)
    assert _resolve_image_url(None, ctx) is None
    assert _resolve_image_url("   ", ctx) is None
    assert _resolve_image_url(["   ", "", None], ctx) is None

    res = _resolve_image_url(["  https://example.com/pic.png  ", ""], ctx)
    assert res == ["https://example.com/pic.png"]



