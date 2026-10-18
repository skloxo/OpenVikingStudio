# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-153 TDD Test Suite: Native Battlefield Tools & FastMCP Bidirectional Aliasing.

验证指标：
1. FastMCP 双向透明别名解析 (openviking_xxx 与 xxx 互通，store->remember 等同义词映射)；
2. 消除 30 秒自反向死锁，code_outline、code_expand、code_search、diff、skills、smart_read 毫秒级极速响应；
3. diff 工具纯 Python 实现 (difflib)，零 CLI 外部依赖；
4. link / get_relations / unlink 参数兼容双向契约 (from_uri/to_uris & source/target)。
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from openviking.server.mcp_endpoint import (
    mcp,
    openviking_code_outline,
    openviking_code_expand,
    openviking_code_search,
    openviking_diff,
    openviking_skills,
    openviking_smart_read,
    openviking_link,
    openviking_get_relations,
    openviking_unlink,
    openviking_tag,
    _install_aliased_tool_manager,
)


@pytest.mark.asyncio
async def test_fastmcp_bidirectional_aliasing():
    """验证 FastMCP 双向透明别名解析，彻底根除 Unknown Tool 报错。"""
    _install_aliased_tool_manager(mcp)
    tm = mcp._tool_manager

    # 1. 验证短名称 code_outline 能解析到 openviking_code_outline
    tool_outline = tm.get_tool("code_outline")
    assert tool_outline is not None, "code_outline 应当命中 openviking_code_outline"
    assert tool_outline.name in ("code_outline", "openviking_code_outline")

    # 2. 验证全名称 openviking_find 能解析到原生 find
    tool_find = tm.get_tool("openviking_find")
    assert tool_find is not None, "openviking_find 应当命中原生 find"

    # 3. 验证同义词别名 store 映射到 remember
    tool_store = tm.get_tool("store")
    assert tool_store is not None, "store 应当映射到 remember"

    tool_ov_store = tm.get_tool("openviking_store")
    assert tool_ov_store is not None, "openviking_store 应当映射到 remember"

    # 4. 验证同义词别名 ping 映射到 health
    tool_ping = tm.get_tool("ping")
    assert tool_ping is not None, "ping 应当映射到 health"

    # 5. 验证同义词别名 harness_stats 映射到 openviking_harness_probe
    tool_harness = tm.get_tool("harness_stats")
    assert tool_harness is not None, "harness_stats 应当映射到 openviking_harness_probe"

    # 6. 验证 skills 与 openviking_skills
    tool_skills = tm.get_tool("skills")
    assert tool_skills is not None, "skills 应当命中"


@pytest.mark.asyncio
async def test_native_code_outline_instant_execution():
    """验证 code_outline 纯原生异步执行，耗时 < 100ms，绝无 30s 阻塞。"""
    mock_service = MagicMock()
    mock_service.fs.overview = AsyncMock(return_value="=== Symbol Outline ===\n- class Foo\n  - def bar()")
    mock_ctx = MagicMock()

    with patch("openviking.server.mcp_endpoint.get_service", return_value=mock_service), \
         patch("openviking.server.mcp_endpoint._get_ctx", return_value=mock_ctx):
        
        t0 = asyncio.get_event_loop().time()
        result = await openviking_code_outline("viking://resources/test/file.py")
        t1 = asyncio.get_event_loop().time()

        elapsed_ms = (t1 - t0) * 1000
        assert elapsed_ms < 100, f"code_outline 应当在 100ms 内极速返回，实际耗时 {elapsed_ms:.2f}ms"
        assert "Symbol Outline" in result
        mock_service.fs.overview.assert_awaited_once()


@pytest.mark.asyncio
async def test_native_diff_pure_python():
    """验证 diff 工具使用纯 Python difflib，零 CLI 依赖且比对精准。"""
    mock_service = MagicMock()
    content_a = "line 1\nline 2 original\nline 3\n"
    content_b = "line 1\nline 2 modified\nline 3\nline 4 added\n"

    async def mock_read_visible(uri, ctx=None):
        if "a.py" in uri:
            return content_a
        return content_b

    mock_service.fs.read_visible = AsyncMock(side_effect=mock_read_visible)
    mock_ctx = MagicMock()

    with patch("openviking.server.mcp_endpoint.get_service", return_value=mock_service), \
         patch("openviking.server.mcp_endpoint._get_ctx", return_value=mock_ctx):
        
        diff_res = await openviking_diff("viking://resources/a.py", "viking://resources/b.py")
        assert "--- viking://resources/a.py" in diff_res
        assert "+++ viking://resources/b.py" in diff_res
        assert "-line 2 original" in diff_res
        assert "+line 2 modified" in diff_res
        assert "+line 4 added" in diff_res


@pytest.mark.asyncio
async def test_native_link_and_relations_contract_compatibility():
    """验证 link / unlink / get_relations 契约兼容 source/target 与 from_uri/to_uris。"""
    mock_service = MagicMock()
    mock_service.relations.link = AsyncMock()
    mock_service.relations.unlink = AsyncMock()
    mock_service.relations.relations = AsyncMock(return_value=[{"target": "viking://dest", "type": "related_to"}])
    mock_ctx = MagicMock()

    with patch("openviking.server.mcp_endpoint.get_service", return_value=mock_service), \
         patch("openviking.server.mcp_endpoint._get_ctx", return_value=mock_ctx):
        
        # 1. 使用 source / target 调用 link
        res_link = await openviking_link(source="viking://node1", target="viking://node2", reason="test")
        assert "Linked" in res_link
        mock_service.relations.link.assert_awaited_once()

        # 2. 查询关系
        res_rel = await openviking_get_relations("viking://node1")
        assert "viking://dest" in res_rel

        # 3. 使用 source / target 调用 unlink
        res_unlink = await openviking_unlink(source="viking://node1", target="viking://node2")
        assert "Unlinked" in res_unlink
        mock_service.relations.unlink.assert_awaited_once()


@pytest.mark.asyncio
async def test_native_skills_list_without_http_loopback():
    """验证 skills 列出在册技能走纯内部路由，无 HTTP 自身回环。"""
    mock_service = MagicMock()
    mock_ctx = MagicMock()
    mock_skills = [
        {"name": "diagnosing-bugs", "description": "排查系统报错"},
        {"name": "tdd", "description": "红绿测试循环"},
    ]

    with patch("openviking.server.mcp_endpoint.get_service", return_value=mock_service), \
         patch("openviking.server.mcp_endpoint._get_ctx", return_value=mock_ctx), \
         patch("openviking.server.routers.skills_helpers._list_skills_from_root", AsyncMock(return_value=mock_skills)):
        
        res = await openviking_skills(action="list")
        assert "diagnosing-bugs" in res
        assert "tdd" in res
