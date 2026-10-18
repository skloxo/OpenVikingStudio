# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test for Dynamic Agent Peer Registry & Living Discovery Engine."""

import pytest
from pathlib import Path
from openviking.service.agent_peer_registry import AgentPeerRegistry, PeerMetadata


@pytest.fixture
def temp_registry(tmp_path: Path):
    reg_file = tmp_path / "test_peers_registry.json"
    registry = AgentPeerRegistry(registry_file=reg_file)
    registry.staging_base = tmp_path / "staging"
    registry.harness_file = tmp_path / "test_harness_metrics.json"
    return registry


def test_auto_inference_and_registration(temp_registry: AgentPeerRegistry):
    # 1. Register deepseek-harness@2080ti
    meta = temp_registry.record_peer_activity("deepseek-harness@2080ti", calls=5)
    assert meta.id == "deepseek-harness@2080ti"
    assert meta.node == "2080Ti"
    assert meta.connection_mode == "realtimeApi"
    assert "DeepSeek Harness" in meta.role
    assert meta.icon == "brain"
    assert meta.call_count == 5

    # 2. Register workbuddy@rtx3070
    wb_meta = temp_registry.record_peer_activity("workbuddy@rtx3070", calls=12)
    assert wb_meta.node == "RTX3070"
    assert wb_meta.connection_mode == "apiClient"
    assert "WorkBuddy" in wb_meta.role
    assert wb_meta.icon == "wrench"


def test_deregister_peer(temp_registry: AgentPeerRegistry):
    temp_registry.record_peer_activity("openclaw@2080ti", calls=2)
    assert "openclaw@2080ti" in temp_registry._peers

    # Purge/deregister
    removed = temp_registry.deregister_peer("openclaw@2080ti")
    assert removed is True
    assert "openclaw@2080ti" not in temp_registry._peers


def test_dynamic_active_peers_filtering(temp_registry: AgentPeerRegistry):
    # Register active peer with calls
    temp_registry.record_peer_activity("deepseek-harness@2080ti", calls=10)
    temp_registry.record_peer_activity("antigravity@2080ti", calls=100)

    # Inactive/ghost peer with 0 calls
    ghost_meta = PeerMetadata(
        id="xiaomimo@2080ti",
        name_key="xiaomimo@2080ti",
        client="xiaomimo",
        node="2080Ti",
        role="XiaomiMo 客户端",
        icon="zap",
        connection_mode="realtimeApi",
        last_seen=0.0,
        call_count=0,
        is_active=True,
    )
    temp_registry._peers["xiaomimo@2080ti"] = ghost_meta

    peers = temp_registry.get_active_peers(account_id="default")
    peer_ids = [p["id"] for p in peers]

    # Active peers MUST be present
    assert "antigravity@2080ti" in peer_ids
    assert "deepseek-harness@2080ti" in peer_ids

    # 0-call standby ghost MUST be filtered out!
    assert "xiaomimo@2080ti" not in peer_ids
