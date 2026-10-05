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
        # New FastMCP tools added in Card-58 (v1.7.12)
        "openviking_context_route": (True, False, True, False),
        "openviking_agent_sensors": (True, False, True, False),
        # Context governance tools added in Card-59 (v1.7.13)
        "openviking_active_notes_get": (True, False, True, False),
        "openviking_active_notes_update": (False, True, True, False),
        "openviking_history_search": (True, False, True, False),
        # Privacy governance tools added in Card-62 (v1.7.16)
        "openviking_privacy_mask": (True, False, True, False),
        # Skill governance tools added in Card-63 (v1.7.17), Card-64 (v1.7.18), Card-65 (v1.7.19), Card-66 (v1.7.20), Card-67 (v1.7.21) & Card-68 (v1.7.22)
        "openviking_skill_validate": (True, False, True, False),
        "openviking_skill_intent_match": (True, False, True, False),
        "openviking_skill_publish": (False, True, True, False),
        "openviking_skill_judge": (True, False, True, False),
        "openviking_skill_remediate": (True, False, True, False),
        "openviking_skill_weight_tune": (False, True, True, False),
        # Privacy & Compliance Governance tools added in Card-69 (v1.7.23)
        "openviking_privacy_quarantine": (False, True, True, False),
        "openviking_privacy_audit": (True, False, True, False),
        # Harness & Engine Verification tools added in Card-75 (v1.7.29)
        "openviking_harness_probe": (True, False, True, False),
        # Skill Evolution Pipeline added in Card-86 (v1.7.40)
        "openviking_skill_evolution_pipeline": (False, True, True, False),
    }
    fields = ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint")

    observed = {}
    for name, tool in tools.items():
        assert tool.annotations is not None, f"Tool '{name}' missing annotations"
        annotations = tool.annotations.model_dump(by_alias=True, exclude_none=True)
        observed[name] = tuple(annotations[field] for field in fields)

    assert observed == expected
