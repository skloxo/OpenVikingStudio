# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from mcp.types import CallToolResult, TextContent

from openviking.observability.events import _GLOBAL_EVENT_BUS
from openviking.server import mcp_endpoint
from openviking.server.identity import RequestContext, Role
from openviking.server.mcp_write_telemetry import (
    context_write_operation_for_mcp_tool,
    install_mcp_write_telemetry,
    is_mcp_tool_result_success,
)
from openviking_cli.session.user_id import UserIdentifier


def test_mcp_tool_operation_mapping():
    assert context_write_operation_for_mcp_tool("write") == "add_resource"
    assert context_write_operation_for_mcp_tool("openviking_write") == "add_resource"
    assert context_write_operation_for_mcp_tool("edit") == "add_resource"
    assert context_write_operation_for_mcp_tool("openviking_valet_handover") == "add_resource"
    assert context_write_operation_for_mcp_tool("remember") == "session.commit"
    assert context_write_operation_for_mcp_tool("store") == "session.commit"
    assert context_write_operation_for_mcp_tool("openviking_record_evolution_lesson") == "session.commit"
    assert context_write_operation_for_mcp_tool("openviking_file_task_card") == "session.commit"
    assert context_write_operation_for_mcp_tool("openviking_resolve_task_card") == "session.commit"
    assert context_write_operation_for_mcp_tool("openviking_auto_onboard_skills") == "add_skill"
    assert context_write_operation_for_mcp_tool("openviking_fix_skill") == "add_skill"
    assert context_write_operation_for_mcp_tool("openviking_skills", {"action": "add"}) == "add_skill"
    assert context_write_operation_for_mcp_tool("openviking_skills", {"action": "list"}) is None
    assert context_write_operation_for_mcp_tool("find") is None
    assert context_write_operation_for_mcp_tool("read") is None


def test_is_mcp_tool_result_success():
    assert is_mcp_tool_result_success("Wrote 42 bytes") is True
    assert is_mcp_tool_result_success('{"status": "ok"}') is True
    assert is_mcp_tool_result_success("Error: failed") is False
    assert is_mcp_tool_result_success('{"status": "error", "error": "bad"}') is False
    assert is_mcp_tool_result_success(
        CallToolResult(content=[TextContent(type="text", text="ok")], isError=True)
    ) is False


@pytest.mark.asyncio
async def test_install_mcp_write_telemetry_emits_only_on_successful_writes():
    captured = []
    _GLOBAL_EVENT_BUS.register("test_mcp_write", captured.append)
    ctx = RequestContext(
        user=UserIdentifier(account_id="acct-mcp", user_id="agent-1"),
        role=Role.USER,
    )

    class FakeToolManager:
        async def call_tool(self, name, arguments, context=None, convert_result=False):
            if name == "write" and arguments.get("fail"):
                raise RuntimeError("boom")
            if name == "openviking_fix_skill" and arguments.get("err_json"):
                return '{"status": "error", "error": "nope"}'
            return f"ok:{name}"

    tm = FakeToolManager()
    install_mcp_write_telemetry(tm, get_ctx=lambda: ctx)
    install_mcp_write_telemetry(tm, get_ctx=lambda: ctx)  # idempotent

    try:
        await tm.call_tool("write", {"uri": "viking://resources/a.md"})
        await tm.call_tool("store", {"content": "hello"})
        await tm.call_tool("openviking_skills", {"action": "add", "name": "s1"})
        await tm.call_tool("openviking_skills", {"action": "list"})
        await tm.call_tool("find", {"query": "x"})
        await tm.call_tool("openviking_fix_skill", {"err_json": True})
        with pytest.raises(RuntimeError):
            await tm.call_tool("write", {"fail": True})
    finally:
        _GLOBAL_EVENT_BUS.unregister("test_mcp_write")

    events = [e for e in captured if e.event_name == "context.write"]
    assert [(e.payload["operation"], e.payload["tool_name"], e.account_id, e.user_id) for e in events] == [
        ("add_resource", "write", "acct-mcp", "agent-1"),
        ("session.commit", "store", "acct-mcp", "agent-1"),
        ("add_skill", "openviking_skills", "acct-mcp", "agent-1"),
    ]


@pytest.mark.asyncio
async def test_live_mcp_endpoint_tool_manager_emits_context_write_event():
    captured = []
    _GLOBAL_EVENT_BUS.register("test_live_mcp_write", captured.append)
    ctx = RequestContext(
        user=UserIdentifier(account_id="acct-live", user_id="tester"),
        role=Role.ADMIN,
    )
    fake_service = SimpleNamespace(
        fs=SimpleNamespace(
            write=pytest.importorskip("unittest.mock").AsyncMock(
                return_value={"written_bytes": 12, "uri": "viking://resources/demo.md", "mode": "replace"}
            )
        )
    )

    token = mcp_endpoint._mcp_ctx.set(ctx)
    try:
        with (
            patch.object(mcp_endpoint, "get_service", return_value=fake_service),
            patch(
                "openviking.service.entropy_gatekeeper.EntropyGatekeeper.get_instance"
            ) as mock_gk,
        ):
            gk_inst = mock_gk.return_value
            gk_inst.evaluate_and_intercept = pytest.importorskip("unittest.mock").AsyncMock(
                return_value=SimpleNamespace(action="allow", saved_bytes=0)
            )
            await mcp_endpoint.mcp._tool_manager.call_tool(
                "write",
                {"uri": "viking://resources/demo.md", "content": "hello world!"},
            )
    finally:
        mcp_endpoint._mcp_ctx.reset(token)
        _GLOBAL_EVENT_BUS.unregister("test_live_mcp_write")

    writes = [e for e in captured if e.event_name == "context.write"]
    assert len(writes) == 1
    assert writes[0].payload["operation"] == "add_resource"
    assert writes[0].payload["tool_name"] == "write"
    assert writes[0].account_id == "acct-live"
    assert writes[0].user_id == "tester"
