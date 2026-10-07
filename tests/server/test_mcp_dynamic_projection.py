# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit and integration tests for MCP Dynamic Capability Projection & Tool ACL Gate (TASK-GATE-05).
"""

import json
from pathlib import Path
import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from openviking.server.mcp_endpoint import (
    _filter_obj_tools,
    _filter_tools_list_payload,
)
from openviking.storage.agent_principal_store import (
    AgentPrincipal,
    AgentPrincipalStore,
)


def test_filter_obj_tools_filters_correctly():
    """Verify JSON object filtering retains only authorized tools."""
    obj = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {"name": "openviking_find", "description": "find things"},
                {"name": "openviking_write", "description": "write things"},
                {"name": "keepass_get", "description": "get password"},
            ]
        },
    }
    allowed = {"openviking_find", "keepass_get"}
    _filter_obj_tools(obj, allowed)
    tools = obj["result"]["tools"]
    assert len(tools) == 2
    tool_names = [t["name"] for t in tools]
    assert "openviking_find" in tool_names
    assert "keepass_get" in tool_names
    assert "openviking_write" not in tool_names


def test_filter_obj_tools_wildcard_keeps_all():
    """Verify wildcard '*' retains all tools without alteration."""
    obj = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {"name": "tool_1"},
                {"name": "tool_2"},
            ]
        },
    }
    allowed = {"*"}
    _filter_obj_tools(obj, allowed)
    assert len(obj["result"]["tools"]) == 2


def test_filter_tools_list_payload_json():
    """Verify raw JSON bytes are properly decoded, filtered, and re-encoded."""
    raw_payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 10,
        "result": {
            "tools": [
                {"name": "openviking_find"},
                {"name": "forbidden_tool"},
            ]
        }
    }).encode("utf-8")

    filtered = _filter_tools_list_payload(raw_payload, {"openviking_find"})
    data = json.loads(filtered.decode("utf-8"))
    tools = data["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "openviking_find"


def test_filter_tools_list_payload_sse():
    """Verify SSE (text/event-stream) data: lines are properly filtered."""
    sse_text = (
        "event: message\n"
        'data: {"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"openviking_find"},{"name":"secret_tool"}]}}\n\n'
    ).encode("utf-8")

    filtered = _filter_tools_list_payload(sse_text, {"openviking_find"})
    decoded = filtered.decode("utf-8")
    assert "openviking_find" in decoded
    assert "secret_tool" not in decoded


def test_dynamic_tool_acl_hot_reload_store(tmp_path: Path):
    """Verify store update enables instant tool authorization without restarting."""
    db_file = tmp_path / "test_hot_reload.db"
    store = AgentPrincipalStore(db_path=db_file)

    agent = store.register_agent(
        agent_id="ag_hot_reload_01",
        allowed_tools=["openviking_find"],
    )
    assert agent.allowed_tools == ["openviking_find"]

    # Verify initial permission
    fetched = store.get_agent("ag_hot_reload_01")
    assert fetched is not None
    assert "openviking_write" not in fetched.allowed_tools

    # Instant hot reload via update_agent
    store.update_agent(
        agent_id="ag_hot_reload_01",
        allowed_tools=["openviking_find", "openviking_write"],
    )
    reloaded = store.get_agent("ag_hot_reload_01")
    assert reloaded is not None
    assert "openviking_write" in reloaded.allowed_tools
