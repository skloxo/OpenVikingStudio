# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Context-write telemetry wrapper for FastMCP `tools/call` executions."""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

from openviking.observability.events import try_publish_event
from openviking.server.identity import RequestContext

_MCP_WRITE_TOOL_OPERATIONS: dict[str, str] = {
    "write": "add_resource",
    "edit": "add_resource",
    "add_resource": "add_resource",
    "valet_handover": "add_resource",
    "link": "add_resource",
    "unlink": "add_resource",
    "tag": "add_resource",
    "remember": "session.commit",
    "store": "session.commit",
    "record_evolution_lesson": "session.commit",
    "file_task_card": "session.commit",
    "resolve_task_card": "session.commit",
    "active_notes_update": "session.commit",
    "auto_onboard_skills": "add_skill",
    "fix_skill": "add_skill",
    "skill_publish": "add_skill",
    "skill_remediate": "add_skill",
}


def context_write_operation_for_mcp_tool(
    tool_name: str,
    arguments: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """Return the canonical context-write heatmap bucket for an MCP tool call."""
    raw = str(tool_name or "").strip()
    if not raw:
        return None
    canonical = raw[len("openviking_") :] if raw.startswith("openviking_") else raw
    if canonical == "skills":
        action = str((arguments or {}).get("action") or "").strip().lower()
        return "add_skill" if action == "add" else None
    return _MCP_WRITE_TOOL_OPERATIONS.get(canonical) or _MCP_WRITE_TOOL_OPERATIONS.get(raw)


def _text_indicates_error(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.startswith("Error:") or stripped.startswith("=== remember: No messages"):
        return True
    if stripped.startswith("{"):
        try:
            parsed = json.loads(stripped)
        except (TypeError, ValueError):
            return False
        if isinstance(parsed, dict) and str(parsed.get("status") or "").strip().lower() == "error":
            return True
    return False


def is_mcp_tool_result_success(result: Any) -> bool:
    """Return False when a FastMCP tool call result encodes an operational failure."""
    if getattr(result, "isError", False):
        return False
    if isinstance(result, str):
        return not _text_indicates_error(result)
    content = getattr(result, "content", None)
    if isinstance(content, (list, tuple)):
        for item in content:
            text = getattr(item, "text", None)
            if isinstance(text, str) and _text_indicates_error(text):
                return False
    if isinstance(result, (list, tuple)):
        for item in result:
            if isinstance(item, str) and _text_indicates_error(item):
                return False
            text = getattr(item, "text", None)
            if isinstance(text, str) and _text_indicates_error(text):
                return False
    return True


def install_mcp_write_telemetry(
    tool_manager: Any,
    *,
    get_ctx: Callable[[], Optional[RequestContext]],
) -> None:
    """Wrap `ToolManager.call_tool` to emit `context.write` events for successful MCP writes."""
    if getattr(tool_manager, "_write_telemetry_installed", False):
        return

    orig_call_tool = tool_manager.call_tool

    async def _telemetry_call_tool(
        name: str,
        arguments: dict[str, Any],
        context: Any = None,
        convert_result: bool = False,
    ) -> Any:
        result = await orig_call_tool(
            name,
            arguments,
            context=context,
            convert_result=convert_result,
        )
        operation = context_write_operation_for_mcp_tool(name, arguments)
        if operation and is_mcp_tool_result_success(result):
            payload: dict[str, Any] = {
                "operation": operation,
                "tool_name": name,
                "status": "success",
            }
            ctx = get_ctx()
            if ctx is not None:
                user_obj = getattr(ctx, "user", None)
                account_id = getattr(ctx, "account_id", None) or getattr(
                    user_obj, "account_id", None
                )
                user_id = getattr(user_obj, "user_id", None)
                if account_id:
                    payload["account_id"] = account_id
                if user_id:
                    payload["user_id"] = user_id
            try_publish_event("context.write", payload)
        return result

    tool_manager.call_tool = _telemetry_call_tool
    tool_manager._write_telemetry_installed = True
