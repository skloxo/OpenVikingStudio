# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Card-140: 外部微服务解耦与独立插件化测试 (CPA 跨模型算力与卫星集群同频物理剥离).
SSOT: REFACTORING_PLAN.md -> Card-140

First Principles:
1. "Zero Coupling": CPA and Fleet must be independent Quad plugins, decoupled from openviking-memory.
2. "Quad Plugin Integrity": Both cpa-squad and fleet-mesh must have Tools, Hooks, Skill, GUI, and Health.
3. "Fail-Safe Independence": When CPA or Fleet are offline or disabled, memory core remains 100% operational.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.routers.plugins import router as plugins_router
from openviking.service.plugin_registry import PluginRegistry


@pytest.fixture
def registry():
    PluginRegistry.reset_instance()
    reg = PluginRegistry.get_instance()
    yield reg
    PluginRegistry.reset_instance()


@pytest.fixture
def client(registry):
    app = FastAPI()
    app.include_router(plugins_router)
    return TestClient(app)


def test_cpa_and_fleet_are_registered_as_independent_quad_plugins(registry):
    """验证 cpa-squad 与 fleet-mesh 作为独立 Quad 插件注册，且具备完整的四位一体规范。"""
    plugin_ids = {p.plugin_id for p in registry.list_plugins()}
    assert "cpa-squad" in plugin_ids
    assert "fleet-mesh" in plugin_ids

    # 1. 验证 cpa-squad 四位一体
    cpa = registry.get_plugin("cpa-squad")
    assert cpa is not None
    assert cpa.name == "CPA 跨模型算力协同"
    assert cpa.category == "user"
    assert len(cpa.tools) == 2
    assert {t.name for t in cpa.tools} == {"openviking_cpa_consult", "openviking_cpa_fanout"}
    assert len(cpa.hooks) == 2
    hook_ids = {h.hook_id for h in cpa.hooks}
    assert "cpa_fallback_failover_hook" in hook_ids
    assert "cpa_cost_telemetry_hook" in hook_ids
    assert cpa.skill is not None
    assert cpa.skill.skill_id == "cpa-squad"
    assert cpa.gui is not None
    assert cpa.gui.dashboard_route == "/plugins"
    assert cpa.health.status == "healthy"

    # 2. 验证 fleet-mesh 四位一体
    fleet = registry.get_plugin("fleet-mesh")
    assert fleet is not None
    assert fleet.name == "卫星集群同频运维"
    assert fleet.category == "user"
    assert len(fleet.tools) == 2
    assert {t.name for t in fleet.tools} == {"openviking_fleet_check", "openviking_fleet_sync"}
    assert len(fleet.hooks) == 1
    assert fleet.hooks[0].hook_id == "fleet_heartbeat_sync_hook"
    assert fleet.skill is not None
    assert fleet.skill.skill_id == "satellite-fleet-ops"
    assert fleet.gui is not None
    assert fleet.gui.dashboard_route == "/plugins"
    assert fleet.health.status == "healthy"


def test_tool_to_plugin_mapping_decoupled(registry):
    """验证工具反查插件 ID 正确映射到 cpa-squad 与 fleet-mesh，且不再属于 openviking-memory。"""
    assert registry.get_plugin_id_by_tool("openviking_cpa_consult") == "cpa-squad"
    assert registry.get_plugin_id_by_tool("openviking_cpa_fanout") == "cpa-squad"
    assert registry.get_plugin_id_by_tool("cpa_consult") == "cpa-squad"
    assert registry.get_plugin_id_by_tool("cpa_fanout") == "cpa-squad"

    assert registry.get_plugin_id_by_tool("openviking_fleet_check") == "fleet-mesh"
    assert registry.get_plugin_id_by_tool("openviking_fleet_sync") == "fleet-mesh"
    assert registry.get_plugin_id_by_tool("fleet_check") == "fleet-mesh"
    assert registry.get_plugin_id_by_tool("fleet_sync") == "fleet-mesh"

    # 验证核心记忆插件已不包含 CPA 和 Fleet 工具
    mem = registry.get_plugin("openviking-memory")
    mem_tool_names = {t.name for t in mem.tools}
    assert "openviking_cpa_consult" not in mem_tool_names
    assert "openviking_cpa_fanout" not in mem_tool_names
    assert "openviking_fleet_check" not in mem_tool_names
    assert "openviking_fleet_sync" not in mem_tool_names
    # 58 剥离 4 项后为 54 项
    assert len(mem.tools) == 54


def test_plugins_rest_api_returns_cpa_and_fleet(client):
    """验证 GET /api/v1/plugins 接口能正常返回独立拆解后的 cpa-squad 与 fleet-mesh 插件。"""
    resp = client.get("/api/v1/plugins")
    assert resp.status_code == 200
    data = resp.json()
    plugin_ids = [p["plugin_id"] for p in data["plugins"]]
    assert "cpa-squad" in plugin_ids
    assert "fleet-mesh" in plugin_ids
    assert data["total"] >= 5  # openviking-memory, keepass-vault, network-search, dify, cpa-squad, fleet-mesh
