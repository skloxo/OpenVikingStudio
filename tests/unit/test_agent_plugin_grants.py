# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Agent Principal Storage Engine with plugin_grants support (TASK-AGNT-04).
"""

from pathlib import Path
import tempfile
import pytest

from openviking.storage.agent_principal_store import (
    AgentPrincipal,
    AgentPrincipalStore,
    DEFAULT_ALLOWED_TOOLS,
)


@pytest.fixture
def temp_store(tmp_path: Path):
    """Fixture providing a fresh isolated AgentPrincipalStore per test."""
    db_file = tmp_path / "test_agents.db"
    store = AgentPrincipalStore(db_path=db_file)
    yield store


def test_agent_principal_model_plugin_grants_default():
    """Verify DTO defaults plugin_grants to empty dict."""
    agent = AgentPrincipal(
        agent_id="ag_test12345678",
        role_desc="Test Agent",
    )
    assert agent.plugin_grants == {}
    assert set(agent.allowed_tools) == set(DEFAULT_ALLOWED_TOOLS)


def test_register_agent_with_plugin_grants_derives_tools(temp_store: AgentPrincipalStore):
    """Verify register_agent automatically derives allowed_tools from plugin_grants."""
    grants = {
        "openviking-memory": ["openviking_find", "openviking_search"],
        "keepass-vault": ["keepass_get"],
    }
    agent = temp_store.register_agent(
        agent_id="ag_derived_01",
        agent_name="Derived Agent",
        role_desc="Derivation test",
        plugin_grants=grants,
    )
    assert agent.agent_id == "ag_derived_01"
    assert agent.plugin_grants == grants
    # Derived allowed_tools should contain unique tools across plugins
    assert set(agent.allowed_tools) == {"openviking_find", "openviking_search", "keepass_get"}


def test_update_agent_plugin_grants_updates_derived_tools(temp_store: AgentPrincipalStore):
    """Verify updating plugin_grants updates both plugin_grants and derived allowed_tools."""
    initial_grants = {
        "openviking-memory": ["openviking_read"],
    }
    agent = temp_store.register_agent(
        agent_id="ag_update_01",
        agent_name="Update Agent",
        plugin_grants=initial_grants,
    )
    assert agent.plugin_grants == initial_grants
    assert agent.allowed_tools == ["openviking_read"]

    # Now update plugin_grants
    new_grants = {
        "openviking-memory": ["openviking_read", "openviking_find"],
        "network-search": ["openviking_web_search"],
    }
    updated = temp_store.update_agent(
        agent_id="ag_update_01",
        plugin_grants=new_grants,
    )
    assert updated is not None
    assert updated.plugin_grants == new_grants
    assert set(updated.allowed_tools) == {"openviking_read", "openviking_find", "openviking_web_search"}


def test_backward_compatibility_legacy_records(temp_store: AgentPrincipalStore):
    """Verify legacy agent records without plugin_grants still load cleanly."""
    legacy_agent = temp_store.register_agent(
        agent_id="ag_legacy_01",
        agent_name="Legacy Agent",
        allowed_tools=["openviking_read", "openviking_write"],
    )
    assert legacy_agent.plugin_grants == {}
    assert legacy_agent.allowed_tools == ["openviking_read", "openviking_write"]

    fetched = temp_store.get_agent("ag_legacy_01")
    assert fetched is not None
    assert fetched.plugin_grants == {}
    assert fetched.allowed_tools == ["openviking_read", "openviking_write"]


def test_list_agents_deserializes_plugin_grants(temp_store: AgentPrincipalStore):
    """Verify list_agents properly deserializes plugin_grants for multiple agents."""
    temp_store.register_agent(
        agent_id="ag_list_01",
        plugin_grants={"plugin_a": ["tool_a1"]},
    )
    temp_store.register_agent(
        agent_id="ag_list_02",
        plugin_grants={"plugin_b": ["tool_b1", "tool_b2"]},
    )

    agents = temp_store.list_agents()
    grants_map = {a.agent_id: a.plugin_grants for a in agents}
    assert grants_map["ag_list_01"] == {"plugin_a": ["tool_a1"]}
    assert grants_map["ag_list_02"] == {"plugin_b": ["tool_b1", "tool_b2"]}
