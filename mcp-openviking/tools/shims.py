# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: tools.shims ───────────────────────────────────────────────────
"""
用途: 卫星模式向后兼容优雅垫片 (Graceful Deprecation Shim)
解决痛点: 外部 Agent 在历史上下文或意外调用被精简的管理工具时，避免抛出 JSON-RPC 异常造成崩溃
依赖: FastMCP
被调用: mcp_openviking_server.py
"""

# SECTION: Imports
import json
import logging
from typing import Any, Callable, Dict
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

logger = logging.getLogger("openviking-mcp")

# SECTION: Shim Interceptor Registration
def register_shims(mcp: FastMCP, mcp_mode: str) -> None:
    """在卫星模式下拦截被裁剪的运维特权工具调用，返回友好提示而非 JSON-RPC 崩溃"""
    if mcp_mode != "satellite":
        return

    orig_call_tool = mcp._tool_manager.call_tool

    async def graceful_call_tool(
        name: str,
        arguments: dict[str, Any],
        context: Any = None,
        convert_result: bool = False,
    ) -> Any:
        tool = mcp._tool_manager.get_tool(name)
        if not tool and name.startswith("openviking_"):
            logger.info(f"[Shim Intercepted] Satellite client invoked trimmed tool: {name}")
            resp_payload = {
                "status": "skipped",
                "tool": name,
                "message": (
                    f"[Satellite Mode] 工具 '{name}' 为本地核心运维特权接口，卫星客户端已安全解耦。"
                    "当前卫星客户端专注于数据面语义检索、代码大纲与记忆协作。"
                ),
                "suggestion": "请改用 openviking_find, openviking_search, openviking_read 或在本地服务端执行运维指令。",
            }
            msg = json.dumps(resp_payload, ensure_ascii=False, indent=2)
            if convert_result:
                return [TextContent(type="text", text=msg)]
            return msg

        return await orig_call_tool(name, arguments, context=context, convert_result=convert_result)

    mcp._tool_manager.call_tool = graceful_call_tool
    logger.debug("[Dual-Mode MCP] Graceful deprecation shim installed for Satellite mode.")
