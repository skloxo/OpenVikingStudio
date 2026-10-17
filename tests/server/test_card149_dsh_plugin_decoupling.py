# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Test Suite for Card-149: DSH Independent Plugins Decoupling and 34 Battlefield Tools / 3 Hooks Parity.
SSOT: Card-149 / docs/architecture/ATOMIC_TASK_CARDS_MATRIX.md
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.routers.client_caps import router as client_caps_router
from openviking.server.routers.client_caps_constants import (
    BATTLEFIELD_34_TOOLS,
    OPS_17_TOOLS,
    FLEET_2_TOOLS,
    MEMORY_3_HOOKS,
    OPS_2_HOOKS,
    FLEET_1_HOOKS,
)
from openviking.service.plugin_registry import PluginRegistry


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(client_caps_router)
    return TestClient(app)


def test_client_capabilities_memory_plugin_strict_alignment(client):
    """
    Card-149: 验证请求 openviking-memory 时严格仅返回 34 战地工具 + 3 Hook，
    彻底杜绝跨插件混杂 (0 搜索工具，0 KeePass 工具)。
    """
    resp = client.get("/api/v1/system/client-capabilities?plugin_id=openviking-memory")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "ok"
    assert data["authenticated"] is True
    assert data["plugin_id"] == "openviking-memory"

    # 验证插件列表单一性
    assert len(data["plugins"]) == 1
    plugin = data["plugins"][0]
    assert plugin["id"] == "openviking-memory"
    assert plugin["version"] == "2.0.13"

    # 验证 34 项战地工具真身
    tool_ids = [t["id"] for t in plugin["tools"]]
    assert len(tool_ids) == 34
    assert len(plugin["tools"]) == 34

    # 抽样验证核心记忆与代码工具
    expected_ids = {t["id"] for t in BATTLEFIELD_34_TOOLS}
    assert set(tool_ids) == expected_ids
    assert "openviking_find" in tool_ids
    assert "openviking_code_search" in tool_ids
    assert "openviking_skills" in tool_ids
    assert "openviking_file_task_card" in tool_ids
    tool_names = [t["name"] for t in plugin["tools"]]
    assert "find" in tool_names
    assert "code_search" in tool_names

    # 严格门禁：绝对禁止含有搜索插件与 KeePass 插件工具
    assert "searxng_search" not in tool_ids
    assert "tavily_search" not in tool_ids
    assert "keepass_get" not in tool_ids
    assert "keepass_search" not in tool_ids

    # 验证 3 项核心 Hook
    hook_ids = [h["id"] for h in data["hooks"]]
    assert len(hook_ids) == 3
    expected_hook_ids = {h["id"] for h in MEMORY_3_HOOKS}
    assert set(hook_ids) == expected_hook_ids


def test_client_capabilities_ops_plugin_strict_alignment(client):
    """
    Card-149: 验证请求 openviking-ops 时严格仅返回 17 运维特权工具 + 2 Hook。
    """
    resp = client.get("/api/v1/system/client-capabilities?plugin_id=openviking-ops")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "ok"
    assert data["plugin_id"] == "openviking-ops"
    assert len(data["plugins"]) == 1
    plugin = data["plugins"][0]
    assert plugin["id"] == "openviking-ops"

    tool_ids = [t["id"] for t in plugin["tools"]]
    assert len(tool_ids) == 17
    expected_ids = {t["id"] for t in OPS_17_TOOLS}
    assert set(tool_ids) == expected_ids
    assert "openviking_server_doctor" in tool_ids
    assert "openviking_retry_dead_letter" in tool_ids
    tool_names = [t["name"] for t in plugin["tools"]]
    assert "server_doctor" in tool_names

    # 验证 2 项运维专用 Hook
    hook_ids = [h["id"] for h in data["hooks"]]
    assert len(hook_ids) == 2
    expected_hook_ids = {h["id"] for h in OPS_2_HOOKS}
    assert set(hook_ids) == expected_hook_ids


def test_client_capabilities_fleet_plugin_strict_alignment(client):
    """
    Card-149: 验证请求 fleet-mesh 时严格仅返回 2 集群同频工具 + 1 Hook。
    """
    resp = client.get("/api/v1/system/client-capabilities?plugin_id=fleet-mesh")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "ok"
    assert data["plugin_id"] == "fleet-mesh"
    assert len(data["plugins"]) == 1
    plugin = data["plugins"][0]
    assert plugin["id"] == "fleet-mesh"

    tool_ids = [t["id"] for t in plugin["tools"]]
    assert len(tool_ids) == 2
    expected_ids = {t["id"] for t in FLEET_2_TOOLS}
    assert set(tool_ids) == expected_ids
    assert "openviking_fleet_check" in tool_ids
    assert "openviking_fleet_sync" in tool_ids
    tool_names = [t["name"] for t in plugin["tools"]]
    assert "fleet_check" in tool_names
    assert "fleet_sync" in tool_names

    # 验证 1 项集群专用 Hook
    hook_ids = [h["id"] for h in data["hooks"]]
    assert len(hook_ids) == 1
    expected_hook_ids = {h["id"] for h in FLEET_1_HOOKS}
    assert set(hook_ids) == expected_hook_ids


def test_dsh_independent_bridge_package_names():
    """
    Card-149: 验证插件注册表各独立插件映射出专属独立的 DSH 桥接器包名。
    """
    mem_bridge = PluginRegistry.get_client_bridge_info("openviking-memory")
    assert mem_bridge["package_name"] == "dsh-plugin-openviking-memory"
    assert mem_bridge["version"] == "2.0.13"
    assert "dsh-plugin-openviking-memory-2.0.13.tgz" in mem_bridge["package_url"]

    ops_bridge = PluginRegistry.get_client_bridge_info("openviking-ops")
    assert ops_bridge["package_name"] == "dsh-plugin-openviking-ops"
    assert ops_bridge["version"] == "1.0.1"
    assert "dsh-plugin-openviking-ops-1.0.1.tgz" in ops_bridge["package_url"]

    fleet_bridge = PluginRegistry.get_client_bridge_info("fleet-mesh")
    assert fleet_bridge["package_name"] == "dsh-plugin-openviking-fleet"
    assert fleet_bridge["version"] == "1.0.1"
    assert "dsh-plugin-openviking-fleet-1.0.1.tgz" in fleet_bridge["package_url"]


def test_validate_config_with_plugin_id(client):
    """
    Card-149: 验证客户端校验配置接口在指定 pluginId 时正确校验。
    """
    payload = {
        "endpointUrl": "http://127.0.0.1:1933",
        "userKey": "test-key-mock",
        "pluginId": "openviking-memory",
        "enabledTools": ["find", "read", "write"],
    }
    resp = client.post("/api/v1/system/client-capabilities/validate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert "message" in data
