# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

"""Contract tests for MCP tool behavior annotations."""

import pytest

import openviking.server.mcp_endpoint as mcp_endpoint


@pytest.mark.asyncio
async def test_mcp_tools_advertise_behavior_annotations():
    tools = {tool.name: tool for tool in await mcp_endpoint.mcp.list_tools()}
    expected = {
        "find": (True, False, True, False),
        # Context mode can persist and prune the per-session recall ledger.
        "search": (False, True, False, False),
        "read": (True, False, True, False),
        "list": (True, False, True, False),
        "tree": (True, False, True, False),
        "remember": (False, True, False, False),
        "write": (False, True, False, False),
        "edit": (False, True, False, False),
        "add_resource": (False, True, False, True),
        "list_watches": (True, False, True, False),
        "cancel_watch": (False, True, True, False),
        "grep": (True, False, True, False),
        "glob": (True, False, True, False),
        "forget": (False, True, True, False),
        "health": (True, False, True, False),
        "zg_search": (True, False, True, False),
        # Task card & analytics tools added in v1.7.x
        "openviking_task_cards_summary": (True, False, True, False),
        "openviking_dlq_status": (True, False, True, False),
        "openviking_resolve_task_card": (False, True, True, False),
        "openviking_code_impact": (True, False, True, False),
        "openviking_vector_sync_metrics": (True, False, True, False),
        "openviking_generate_contract_test": (True, False, True, False),
        "openviking_list_pending_cards": (True, False, True, False),
        "openviking_file_task_card": (False, True, True, False),
        # Core FastMCP tools added in Card-56 (v1.8.0)
        "openviking_valet_handover": (False, True, True, False),
        "openviking_valet_ticket_status": (True, False, True, False),
        "openviking_dspy_compile": (True, False, True, False),
        "openviking_skill_zip": (True, False, True, False),
        "openviking_tokenshift_compress": (True, False, True, False),
        "openviking_memory_purity_report": (True, False, True, False),
        "openviking_retry_dead_letter": (False, True, True, False),
    }
    fields = ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint")

    observed = {}
    for name, tool in tools.items():
        assert tool.annotations is not None, f"Tool '{name}' missing annotations"
        annotations = tool.annotations.model_dump(by_alias=True, exclude_none=True)
        observed[name] = tuple(annotations[field] for field in fields)

    assert observed == expected
