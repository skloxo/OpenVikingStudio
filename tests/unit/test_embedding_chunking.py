# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

import pytest
from openviking.utils.embedding_input import (
    estimate_embedding_input_tokens,
    split_embedding_chunks,
)


def test_split_embedding_chunks_small_text():
    text = "这是一段非常简短的记忆文本，完全不需要切片。"
    chunks = split_embedding_chunks(text, max_chunk_tokens=500)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_split_embedding_chunks_long_chinese_markdown():
    # Construct a ~3000 token markdown document with sections
    sections = []
    for i in range(1, 15):
        sections.append(
            f"## 第 {i} 章节：技术调研与系统架构设计\n\n"
            f"在第 {i} 阶段的工程实现中，我们重点对体外大脑记忆中枢进行了深度优化。"
            f"系统需要支持高并发下的向量化入库，同时保证跨会话检索的一致性与低延迟。"
            f"每个模块都应该遵循高内聚低耦合的原则，切除一切冗余包装与伪状态。\n\n"
            f"- 模块 A: 向量存储与索引引擎\n"
            f"- 模块 B: 语义分块与滑动窗口中间件\n"
            f"- 模块 C: 跨会话上下文检索聚合器\n"
        )
    full_text = "\n\n".join(sections)
    total_tokens = estimate_embedding_input_tokens(full_text)
    assert total_tokens > 2000

    max_chunk = 800
    chunks = split_embedding_chunks(full_text, max_chunk_tokens=max_chunk, overlap_tokens=100)
    assert len(chunks) >= 3

    # Verify every chunk is strictly bounded within token limit
    for idx, chunk in enumerate(chunks):
        chunk_tokens = estimate_embedding_input_tokens(chunk)
        assert chunk_tokens <= max_chunk + 100, f"Chunk {idx} token count {chunk_tokens} exceeded {max_chunk}"
        assert len(chunk.strip()) > 0


def test_split_embedding_chunks_single_huge_paragraph():
    # Long unbroken string
    huge_paragraph = "这是一句很长很长的句子，包含很多核心业务逻辑和详细技术细节。" * 200
    tokens = estimate_embedding_input_tokens(huge_paragraph)
    assert tokens > 2000

    chunks = split_embedding_chunks(huge_paragraph, max_chunk_tokens=600, overlap_tokens=50)
    assert len(chunks) >= 3
    for chunk in chunks:
        assert estimate_embedding_input_tokens(chunk) <= 700


def test_split_embedding_chunks_empty_or_zero():
    assert split_embedding_chunks("") == []
    assert split_embedding_chunks("hello", max_chunk_tokens=0) == ["hello"]


@pytest.mark.asyncio
async def test_collection_schemas_dequeue_auto_slicing():
    import json
    from unittest.mock import AsyncMock, MagicMock
    from openviking.models.embedder.base import EmbedResult
    from openviking.storage.collection_schemas import TextEmbeddingHandler
    from openviking.storage.queuefs.embedding_msg import EmbeddingMsg

    mock_vikingdb = MagicMock()
    mock_vikingdb.is_closing = False
    mock_vikingdb.upsert = AsyncMock(return_value="mock_id_123")

    schemas = TextEmbeddingHandler(vikingdb=mock_vikingdb)

    mock_embedder = MagicMock()
    # embed_compat works with async embed or synchronous embed
    mock_embedder.embed_async = AsyncMock(return_value=EmbedResult(dense_vector=[0.1] * 1024))
    mock_embedder.embed = MagicMock(return_value=EmbedResult(dense_vector=[0.1] * 1024))
    schemas._embedder = mock_embedder
    schemas._vector_dim = 1024

    # Construct a large text message > 1500 tokens
    large_text = (
        "## Section Title\n\n"
        "这是一段非常详细的系统架构分析与向量检索调优记录，包含核心业务逻辑与技术方案。"
        "我们需要验证在长文本输入时，分块切片算子能够正确将文本切解为多个小于1500 Tokens的语义块。\n\n"
    ) * 30

    msg = EmbeddingMsg(
        message=large_text,
        context_data={
            "uri": "viking://user/default/memories/events/2026/06/18/test_event.md",
            "account_id": "default",
            "level": 2,
            "context_type": "memory",
        },
        telemetry_id="test_tel_001",
    )

    data = {"data": json.dumps(msg.to_dict())}
    result = await schemas.on_dequeue(data)
    assert result is not None
    assert result.get("uri") == "viking://user/default/memories/events/2026/06/18/test_event.md"

    # Verify upsert was called multiple times (one for each chunk)
    assert mock_vikingdb.upsert.call_count >= 2

    # Check that each call had a chunk_index and distinct id
    ids = set()
    for call in mock_vikingdb.upsert.call_args_list:
        chunk_data = call[0][0]
        assert "chunk_index" in chunk_data
        assert "chunk_count" in chunk_data
        assert chunk_data["uri"] == "viking://user/default/memories/events/2026/06/18/test_event.md"
        ids.add(chunk_data["id"])

    assert len(ids) == mock_vikingdb.upsert.call_count

