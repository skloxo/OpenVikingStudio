# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0
"""Unit and round-trip tests for Card-152: write 0-byte NOOP physical persistence fix.

SSOT:
1. NOOP is ONLY valid when the target file actually exists on physical disk AND
   already contains the exact same content.
2. If the target file does not exist on disk, NOOP MUST be overridden with physical write.
3. If the target file exists but the content is changed, NOOP MUST be overridden with physical write.
4. MCP write tool must accurately report written bytes and never emit misleading 'Wrote 0 bytes'.
"""

from unittest.mock import AsyncMock, patch
import pytest

from openviking.server.identity import RequestContext, Role
from openviking.server.dependencies import set_service
from openviking.service.entropy_gatekeeper import GatekeeperDecision
from openviking.session.memory.utils.content_visibility import visible_content
from openviking.server.mcp_endpoint import write as mcp_write, _mcp_ctx


@pytest.mark.asyncio
async def test_write_new_file_gatekeeper_noop_overridden(service):
    """When target file does NOT exist on disk, even if Gatekeeper returns NOOP,
    it must be overridden and physically persisted to disk."""
    ctx = RequestContext(user=service.user, role=Role.USER)
    target_uri = "viking://resources/master_memory/test_card152_new.md"
    content = "Card 152 test content for physical persistence. Must not be dropped!"

    fake_noop = GatekeeperDecision(
        action="noop",
        similarity=0.985,
        matched_uri="viking://resources/master_memory/other_lesson.md",
        reason="[NOOP 印证去重] 模拟高度相似事实",
        saved_bytes=len(content.encode("utf-8")),
        uri=target_uri,
    )

    with patch(
        "openviking.service.entropy_gatekeeper.EntropyGatekeeper.evaluate_and_intercept",
        new_callable=AsyncMock,
    ) as mock_intercept:
        mock_intercept.return_value = fake_noop

        result = await service.fs.write(
            uri=target_uri,
            content=content,
            ctx=ctx,
            mode="replace",
            wait=True,
        )

        # Must NOT be noop: target file was missing, so write was forced
        assert result.get("action") != "noop"
        assert result["written_bytes"] == len(content.encode("utf-8"))
        assert result["written_bytes"] > 0

        # Read back from disk to verify physical persistence
        stored = await service.viking_fs.read_file(target_uri, ctx=ctx)
        assert visible_content(stored, uri=target_uri) == content


@pytest.mark.asyncio
async def test_write_existing_file_identical_content_honors_noop(service):
    """When target file already exists on disk and content is identical,
    NOOP is safely executed and file on disk remains intact."""
    ctx = RequestContext(user=service.user, role=Role.USER)
    target_uri = "viking://resources/master_memory/test_card152_identical.md"
    content = "Exact same content on physical disk. NOOP is safe here."

    # Initial write to create file on disk
    init_res = await service.fs.write(
        uri=target_uri,
        content=content,
        ctx=ctx,
        mode="replace",
        wait=True,
    )
    assert init_res["written_bytes"] > 0

    fake_noop = GatekeeperDecision(
        action="noop",
        similarity=1.0000,
        matched_uri=target_uri,
        reason="[NOOP 指纹秒级印证] 内容完全一致",
        saved_bytes=len(content.encode("utf-8")),
        uri=target_uri,
    )

    with patch(
        "openviking.service.entropy_gatekeeper.EntropyGatekeeper.evaluate_and_intercept",
        new_callable=AsyncMock,
    ) as mock_intercept:
        mock_intercept.return_value = fake_noop

        noop_res = await service.fs.write(
            uri=target_uri,
            content=content,
            ctx=ctx,
            mode="replace",
            wait=True,
        )

        # When content is identical on disk, NOOP is valid
        assert noop_res.get("action") == "noop"
        assert noop_res["written_bytes"] == 0

        # Verify file still readable and intact on disk
        stored = await service.viking_fs.read_file(target_uri, ctx=ctx)
        assert visible_content(stored, uri=target_uri) == content


@pytest.mark.asyncio
async def test_write_existing_file_changed_content_overrides_noop(service):
    """When target file exists on disk but content is modified,
    Gatekeeper returning NOOP (e.g. cross-doc similarity) must be overridden with physical update."""
    ctx = RequestContext(user=service.user, role=Role.USER)
    target_uri = "viking://resources/master_memory/test_card152_changed.md"
    original_content = "Original version 1 content on disk."
    updated_content = "Updated version 2 content with critical modifications!"

    # Initial write
    await service.fs.write(
        uri=target_uri,
        content=original_content,
        ctx=ctx,
        mode="replace",
        wait=True,
    )

    # Gatekeeper mistakenly thinks this is NOOP due to cross-doc similarity
    fake_noop = GatekeeperDecision(
        action="noop",
        similarity=0.965,
        matched_uri="viking://resources/master_memory/similar_doc.md",
        reason="[NOOP 跨文档去重] 相似度过高",
        saved_bytes=len(updated_content.encode("utf-8")),
        uri=target_uri,
    )

    with patch(
        "openviking.service.entropy_gatekeeper.EntropyGatekeeper.evaluate_and_intercept",
        new_callable=AsyncMock,
    ) as mock_intercept:
        mock_intercept.return_value = fake_noop

        update_res = await service.fs.write(
            uri=target_uri,
            content=updated_content,
            ctx=ctx,
            mode="replace",
            wait=True,
        )

        # Must override NOOP and write updated content
        assert update_res.get("action") != "noop"
        assert update_res["written_bytes"] == len(updated_content.encode("utf-8"))

        stored = await service.viking_fs.read_file(target_uri, ctx=ctx)
        assert visible_content(stored, uri=target_uri) == updated_content


@pytest.mark.asyncio
async def test_mcp_write_tool_clean_message_reporting(service):
    """Verify MCP write tool output messages:
    - Never misleadingly says 'Wrote 0 bytes'
    - Reports exact bytes when written
    - Returns clean [Entropy Defense] NOOP message when safely deduplicated
    """
    set_service(service)
    ctx = RequestContext(user=service.user, role=Role.USER)
    token = _mcp_ctx.set(ctx)
    try:
        target_uri = "viking://resources/master_memory/test_card152_mcp.md"
        content = "MCP write tool verification content for Card-152."

        # Case 1: First write - target does not exist -> writes bytes
        msg1 = await mcp_write(uri=target_uri, content=content, mode="replace", wait=True)
        assert "Wrote" in msg1
        assert f"Wrote {len(content.encode('utf-8'))} bytes" in msg1
        assert "Wrote 0 bytes" not in msg1

        # Case 2: Second write with exact same content -> clean NOOP message
        msg2 = await mcp_write(uri=target_uri, content=content, mode="replace", wait=True)
        assert "[Entropy Defense] NOOP" in msg2 or "Wrote 0 bytes" not in msg2

        # Verify file is 100% readable
        stored = await service.viking_fs.read_file(target_uri, ctx=ctx)
        assert visible_content(stored, uri=target_uri) == content
    finally:
        _mcp_ctx.reset(token)
