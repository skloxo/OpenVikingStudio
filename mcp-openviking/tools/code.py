# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: tools.code ────────────────────────────────────────────────────
"""
用途: 代码语义检索、类与函数结构大纲提纯、符号展开与全局正则行匹配
依赖: _core.config
被调用: mcp_openviking_server.py
"""

# SECTION: Imports
import logging
from typing import Callable, Dict
from pydantic import Field
from mcp.server.fastmcp import FastMCP
from _core.config import (
    _validate_uri,
    _validate_limit,
    _make_error,
    _run_cli,
    http_client,
    _api_then_cli,
)

logger = logging.getLogger("openviking-mcp")

# SECTION: Tool Registration
def register_code_tools(mcp: FastMCP, mcp_tool: Callable) -> Dict[str, Callable]:
    registered: Dict[str, Callable] = {}

    @mcp_tool()
    def openviking_code_outline(
        target_uri: str = Field(description="代码文件 Viking URI"),
    ) -> str:
        """显示文件符号结构（函数、类等结构大纲）"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)

        def _api():
            return http_client.get("/api/v1/content/overview", {"uri": target_uri})

        return _api_then_cli(_api, ["overview", target_uri])
    registered["openviking_code_outline"] = openviking_code_outline

    @mcp_tool()
    def openviking_code_search(
        query: str = Field(description="符号名搜索"),
        target_uri: str = Field(default="viking://", description="搜索范围"),
    ) -> str:
        """搜索代码符号名（函数、类、变量等）"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)

        def _api():
            body = {"query": query}
            if target_uri and target_uri != "viking://":
                body["target_uri"] = target_uri
            return http_client.post("/api/v1/search/find", body)

        def _cli():
            args = ["find", query]
            if target_uri and target_uri != "viking://":
                args.extend(["--uri", target_uri])
            return _run_cli(args)

        return _api_then_cli(_api, ["find", query] + (["--uri", target_uri] if target_uri and target_uri != "viking://" else []))
    registered["openviking_code_search"] = openviking_code_search

    @mcp_tool()
    def openviking_code_expand(
        target_uri: str = Field(description="符号所在文件 Viking URI"),
        symbol: str = Field(default="", description="符号名"),
    ) -> str:
        """返回符号完整源码切片"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)

        def _api():
            return http_client.get("/api/v1/content/read", {"uri": target_uri})

        return _api_then_cli(_api, ["read", target_uri], timeout=60)
    registered["openviking_code_expand"] = openviking_code_expand

    @mcp_tool()
    def openviking_grep(
        pattern: str = Field(description="正则表达式"),
        target_uri: str = Field(default="viking://", description="搜索范围 URI"),
        limit: int = Field(default=50, description="最大返回数"),
    ) -> str:
        """正则表达式搜索文件行内容"""
        for err in [_validate_uri(target_uri), _validate_limit(limit)]:
            if err:
                return _make_error(err)

        def _api():
            return http_client.post("/api/v1/search/grep", {"pattern": pattern, "uri": target_uri, "limit": limit})

        return _api_then_cli(_api, ["grep", pattern, "--uri", target_uri, "--limit", str(limit)])
    registered["openviking_grep"] = openviking_grep

    @mcp_tool()
    def openviking_glob(
        pattern: str = Field(description="glob 模式（如 **/*.py）"),
        target_uri: str = Field(default="viking://", description="搜索范围 URI"),
    ) -> str:
        """按 glob 模式匹配文件列表"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)

        def _api():
            return http_client.post("/api/v1/search/glob", {"pattern": pattern, "uri": target_uri})

        return _api_then_cli(_api, ["glob", pattern, "--uri", target_uri])
    registered["openviking_glob"] = openviking_glob

    return registered
