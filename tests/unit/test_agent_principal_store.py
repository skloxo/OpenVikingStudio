# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for AgentPrincipalStore (Card-111 / v1.7.65).
"""

import pytest
from pathlib import Path
from openviking.storage.agent_principal_store import AgentPrincipalStore, AgentPrincipal


@pytest.fixture
def store(tmp_path: Path):
    AgentPrincipalStore.reset_instance()
    db_file = tmp_path / "test_agents.db"
    store_inst = AgentPrincipalStore.get_instance(db_path=db_file)
    yield store_inst
    AgentPrincipalStore.reset_instance()


def test_register_and_get_agent(store: AgentPrincipalStore):
    agent = store.register_agent(
        agent_id="antigravity@2080ti",
        user_id="default",
        role_desc="2080Ti 主控 IDE",
        icon="brain",
        connection_mode="realtimeApi",
        total_messages=1100,
    )
    assert agent.agent_id == "antigravity@2080ti"
    assert agent.user_id == "default"
    assert agent.total_messages == 1100
    assert agent.status == "active"

    fetched = store.get_agent("antigravity@2080ti")
    assert fetched is not None
    assert fetched.role_desc == "2080Ti 主控 IDE"


def test_list_agents_filtering(store: AgentPrincipalStore):
    store.register_agent("agent-1@2080ti", user_id="default", role_desc="Agent 1", total_messages=10)
    store.register_agent("agent-2@3070", user_id="default", role_desc="Agent 2", total_messages=50)
    store.register_agent("agent-3@laptop", user_id="other_user", role_desc="Agent 3", total_messages=5)

    default_agents = store.list_agents(user_id="default")
    assert len(default_agents) == 2
    # Ordered by total_messages descending
    assert default_agents[0].agent_id == "agent-2@3070"
    assert default_agents[1].agent_id == "agent-1@2080ti"

    other_agents = store.list_agents(user_id="other_user")
    assert len(other_agents) == 1
    assert other_agents[0].agent_id == "agent-3@laptop"


def test_record_activity_increment(store: AgentPrincipalStore):
    store.register_agent("dsh@2080ti", user_id="default", role_desc="DSH", total_messages=0)
    store.record_activity("dsh@2080ti", increment=5)
    
    agent = store.get_agent("dsh@2080ti")
    assert agent is not None
    assert agent.total_messages == 5
    assert agent.last_seen > 0

    # Auto-provisioning when record_activity receives an unseen agent
    store.record_activity("new_comer@remote", user_id="default", increment=1)
    new_agent = store.get_agent("new_comer@remote")
    assert new_agent is not None
    assert new_agent.total_messages == 1


def test_revoke_and_delete_agent(store: AgentPrincipalStore):
    store.register_agent("workbuddy@rtx3070", user_id="default", role_desc="WorkBuddy")
    assert len(store.list_agents(user_id="default", status="active")) == 1

    # Revoke
    revoked = store.revoke_agent("workbuddy@rtx3070")
    assert revoked is True
    assert len(store.list_agents(user_id="default", status="active")) == 0
    assert len(store.list_agents(user_id="default", status="revoked")) == 1

    # Delete
    deleted = store.delete_agent("workbuddy@rtx3070")
    assert deleted is True
    assert store.get_agent("workbuddy@rtx3070") is None
