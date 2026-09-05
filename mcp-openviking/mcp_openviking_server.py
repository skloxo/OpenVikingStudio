#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: mcp_openviking_server ─────────────────────────────────────────
"""
OpenViking MCP Server — AI Agent 可调用的 OpenViking 语义记忆管理工具集 (v1.4.33)

封装 OpenViking CLI 命令和 HTTP API，提供结构化的 MCP 工具接口。
支持：资源管理、语义搜索、分层读取、会话管理、系统监控。
优先 HTTP API，失败回退 CLI。
"""

# SECTION: Imports
import logging
import os
import sys
import urllib.request
from urllib.request import urlopen
from mcp.server.fastmcp import FastMCP

from _core.config import (
    DEFAULT_API,
    DEFAULT_CLI,
    DEFAULT_ROOT_API_KEY,
    CLI_ONLY_MODE,
    SATELLITE_ALLOWED_TOOLS,
    resolve_mcp_mode,
    _get_config,
    _run_cli,
    OpenVikingHTTPClient,
    http_client,
    _format_result,
    _api_then_cli,
    _has_error,
    _make_error,
    _handle_http_error,
    _handle_cli_error,
    _handle_timeout,
    _validate_uri,
    _normalize_level,
    _validate_level,
    _validate_limit,
    _validate_score_threshold,
    _get_skill_base_sources,
    _infer_skill_source,
    _parse_skill_description,
)
from _core.decorators import create_mcp_tool_decorator
from tools import (
    register_memory_tools,
    register_code_tools,
    register_filesystem_tools,
    register_skills_tools,
    register_sessions_tools,
    register_system_tools,
    register_observability_tools,
    register_shims,
)
from tools.observability import (
    HARNESS_METRICS,
    _load_harness_metrics,
    _save_harness_metrics,
    _record_harness_call,
    _harness_pre_execution_guard,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openviking-mcp")

# SECTION: Mode Resolution & FastMCP Initialization
MCP_MODE = resolve_mcp_mode()
logger.info(f"[Dual-Mode MCP] Active mode: [{MCP_MODE.upper()}]")

mcp = FastMCP(
    name="openviking",
    instructions=(
        "OpenViking 语义记忆管理工具集 — 资源管理、语义搜索、分层读取、"
        "会话管理、系统监控。优先 HTTP API，CLI 回退。"
    ),
)

# SECTION: Tool Registration via Decorator Factory
mcp_tool = create_mcp_tool_decorator(mcp, MCP_MODE)

_all_tools = {}
_all_tools.update(register_memory_tools(mcp, mcp_tool))
_all_tools.update(register_code_tools(mcp, mcp_tool))
_all_tools.update(register_filesystem_tools(mcp, mcp_tool))
_all_tools.update(register_skills_tools(mcp, mcp_tool))
_all_tools.update(register_sessions_tools(mcp, mcp_tool))
_all_tools.update(register_system_tools(mcp, mcp_tool))
_all_tools.update(register_observability_tools(mcp, mcp_tool))
register_shims(mcp, MCP_MODE)

# 将所有工具函数暴露在模块顶层，保证单测与动态调用 100% 兼容
globals().update(_all_tools)

# SECTION: CLI Runner Entry Point
if __name__ == "__main__":
    for arg in sys.argv[1:]:
        if arg.startswith("--mode="):
            MCP_MODE = arg.split("=", 1)[1].strip().lower()
        elif arg == "--mode" and sys.argv.index(arg) + 1 < len(sys.argv):
            MCP_MODE = sys.argv[sys.argv.index(arg) + 1].strip().lower()

    logger.info(f"🚀 OpenViking MCP Server starting in [{MCP_MODE.upper()}] mode...")
    if any(arg.isdigit() for arg in sys.argv[1:]):
        port = next(int(arg) for arg in sys.argv[1:] if arg.isdigit())
        mcp.run(transport="sse", port=port)
    else:
        mcp.run(transport="stdio")
