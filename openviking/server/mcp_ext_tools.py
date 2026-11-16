# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Additional #182 MCP tools (mounted MCP search/invoke and Rule search)."""

from __future__ import annotations

import json
from typing import Annotated, Any, Callable, Dict, Optional

from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

from openviking.server.dependencies import get_service
from openviking.server.identity import RequestContext
from openviking.service.rule_service import RuleSearchRequest
from openviking_cli.exceptions import OpenVikingError


def register_ext_tools(
    mcp: Any,
    *,
    get_ctx: Callable[[], RequestContext],
    read_annotations: ToolAnnotations,
    open_world_destructive_annotations: ToolAnnotations,
) -> None:
    """Register #182 MCP mount and Rule search tools onto the shared FastMCP server."""

    @mcp.tool(annotations=read_annotations, structured_output=False)
    async def find_mcp_tools(query: str, limit: int = 10) -> CallToolResult | str:
        """Semantically retrieve candidate MCP tools for the user's intent.

        Returns ranked tools with routing URI, score, and complete MCP definitions.
        Choose a tool, fill arguments according to its inputSchema, then call
        invoke_mcp_tool with the returned uri as tool_uri.
        """
        service = get_service()
        ctx = get_ctx()
        try:
            result = await service.mcps.find(query, limit, ctx, include_definition=True)
        except OpenVikingError as exc:
            return f"Error: {exc}"
        tools = [
            {key: hit[key] for key in ("uri", "score", "tool") if key in hit}
            for hit in result.get("tools", [])
        ]
        payload = {"tools": tools, "total": len(tools)}
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))],
            structuredContent=payload,
        )

    @mcp.tool(annotations=open_world_destructive_annotations, structured_output=False)
    async def invoke_mcp_tool(
        tool_uri: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> CallToolResult | str:
        """Execute a tool selected from find_mcp_tools.

        Pass its returned uri as tool_uri and fill arguments according to tool.inputSchema.
        OpenViking resolves the server and credentials internally.
        """
        service = get_service()
        ctx = get_ctx()
        try:
            result = await service.mcps.invoke(tool_uri, arguments or {}, ctx)
        except OpenVikingError as exc:
            return f"Error: {exc}"
        return CallToolResult.model_validate(result)

    @mcp.tool(annotations=read_annotations)
    async def rule_search(
        task_context: Annotated[str, Field(min_length=1, max_length=64_000)],
        rule_probability_threshold: Annotated[float, Field(ge=0.0, le=1.0)] = 0.65,
    ) -> str:
        """Retrieve active OpenViking Rules applicable to a concrete task context."""
        try:
            result = await get_service().rules.search_rules(
                RuleSearchRequest(
                    task_context=task_context,
                    rule_probability_threshold=rule_probability_threshold,
                ),
                ctx=get_ctx(),
            )
        except OpenVikingError as exc:
            return f"Error: {exc}"
        rendered = result.get("rendered") if isinstance(result, dict) else None
        if isinstance(rendered, str) and rendered.strip():
            return rendered
        return json.dumps(result, ensure_ascii=False)
