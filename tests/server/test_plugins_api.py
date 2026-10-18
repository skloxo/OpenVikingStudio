# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Server Tests for Plugin Center REST API and Plugin Registry.
SSOT: docs/architecture/ATOMIC_TASK_CARDS_MATRIX.md -> TASK-PLUG-05
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.routers.plugins import router as plugins_router
from openviking.service.plugin_registry import PluginRegistry


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(plugins_router)
    return TestClient(app)


def test_plugin_registry_singleton_and_builtins():
    """验证 PluginRegistry 单例与三大标杆插件完整性。"""
    reg1 = PluginRegistry.get_instance()
    reg2 = PluginRegistry.get_instance()
    assert reg1 is reg2

    plugins = reg1.list_plugins()
    plugin_ids = {p.plugin_id for p in plugins}
    assert "openviking-memory" in plugin_ids
    assert "keepass-vault" in plugin_ids
    assert "network-search" in plugin_ids

    # 验证核心战地记忆插件四位一体完整性 (FastMCP 34 战地工具 + 3 Hook)
    mem_plug = reg1.get_plugin("openviking-memory")
    assert mem_plug is not None
    assert mem_plug.version == "2.0.15"
    assert len(mem_plug.hooks) == 3
    assert len(mem_plug.tools) == 34

    # 验证解耦独立插件 cpa-squad、fleet-mesh 与 openviking-ops
    assert "cpa-squad" in plugin_ids
    assert "fleet-mesh" in plugin_ids
    assert "openviking-ops" in plugin_ids
    assert len(reg1.get_plugin("cpa-squad").tools) == 2
    assert len(reg1.get_plugin("fleet-mesh").tools) == 2
    assert len(reg1.get_plugin("openviking-ops").tools) == 17

    # 验证工具反查插件 ID
    assert reg1.get_plugin_id_by_tool("find") == "openviking-memory"
    assert reg1.get_plugin_id_by_tool("keepass_get") == "keepass-vault"
    assert reg1.get_plugin_id_by_tool("searxng_search") == "network-search"
    assert reg1.get_plugin_id_by_tool("openviking_cpa_consult") == "cpa-squad"
    assert reg1.get_plugin_id_by_tool("openviking_fleet_check") == "fleet-mesh"

    # 验证客户端桥梁元数据
    bridge = PluginRegistry.get_client_bridge_info()
    assert bridge["package_name"] in ("dsh-plugin-openviking-memory", "dsh-plugin-openviking")
    assert bridge["package_url"].endswith(".tgz")


def test_is_tool_authorized_logic():
    """验证 is_tool_authorized 权限判别逻辑。"""
    registry = PluginRegistry.get_instance()
    
    grants = {
        "openviking-memory": ["find", "read"],
        "network-search": ["*"],
    }

    # 已显式授权的工具
    assert registry.is_tool_authorized(grants, "find") is True
    assert registry.is_tool_authorized(grants, "read") is True

    # 未被授权的同一插件工具
    assert registry.is_tool_authorized(grants, "write") is False

    # 通配符 '*' 授权的插件工具
    assert registry.is_tool_authorized(grants, "searxng_search") is True
    assert registry.is_tool_authorized(grants, "crawl4ai_extract") is True

    # 完全未分配的插件 (KeePass)
    assert registry.is_tool_authorized(grants, "keepass_get") is False


def test_get_plugins_list_endpoint(client):
    """验证 GET /api/v1/plugins 接口返回三大插件四位一体全景树。"""
    resp = client.get("/api/v1/plugins")
    assert resp.status_code == 200
    data = resp.json()

    assert "total" in data
    assert data["total"] >= 3
    plugins = data["plugins"]
    ids = [p["plugin_id"] for p in plugins]
    assert "openviking-memory" in ids
    assert "keepass-vault" in ids
    assert "network-search" in ids

    # 校验每个插件四位一体字段齐全
    for p in plugins:
        assert "skill" in p
        assert "hooks" in p
        assert "tools" in p
        assert "gui" in p
        assert "health" in p
        assert p["health"]["status"] in ("healthy", "degraded", "down", "unknown")


def test_get_plugin_detail_and_bridge_endpoints(client):
    """验证 GET /api/v1/plugins/{plugin_id} 详情及客户端桥梁包下载元数据。"""
    # 正常获取核心记忆插件
    resp = client.get("/api/v1/plugins/openviking-memory")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plugin_id"] == "openviking-memory"
    assert data["version"] == "2.0.15"
    assert len(data["tools"]) == 34

    # 验证获取解耦独立插件详情
    resp_cpa = client.get("/api/v1/plugins/cpa-squad")
    assert resp_cpa.status_code == 200
    assert resp_cpa.json()["plugin_id"] == "cpa-squad"
    assert len(resp_cpa.json()["tools"]) == 2

    resp_fleet = client.get("/api/v1/plugins/fleet-mesh")
    assert resp_fleet.status_code == 200
    assert resp_fleet.json()["plugin_id"] == "fleet-mesh"
    assert len(resp_fleet.json()["tools"]) == 2

    # 验证客户端桥梁独立接口
    resp_bridge = client.get("/api/v1/plugins/bridge/client-package")
    assert resp_bridge.status_code == 200
    bridge_data = resp_bridge.json()
    assert bridge_data["status"] == "success"
    assert bridge_data["result"]["package_name"] in ("dsh-plugin-openviking-memory", "dsh-plugin-openviking")

    # 不存在的插件返回 404
    resp_404 = client.get("/api/v1/plugins/non_existent_plugin")
    assert resp_404.status_code == 404


def test_get_plugins_health_summary_endpoint(client):
    """验证 GET /api/v1/plugins/health/summary 健康探针大盘接口。"""
    resp = client.get("/api/v1/plugins/health/summary")
    assert resp.status_code == 200
    data = resp.json()

    assert "overall_status" in data
    assert data["overall_status"] in ("healthy", "degraded", "down")
    assert "healthy_count" in data
    assert "total_count" in data
    assert data["total_count"] >= 3
    assert "probes" in data
    assert "openviking-memory" in data["probes"]


def test_search_usage_endpoints_removed_and_bridge_package(client):
    """验证侵入式外部搜索流水接口已彻底切除 (404)，且客户端通道桥包接口正常。"""
    resp = client.get("/api/v1/plugins/network-search/usage/summary")
    assert resp.status_code == 404

    resp_bridge = client.get("/api/v1/plugins/bridge/client-package")
    assert resp_bridge.status_code == 200
    bridge_data = resp_bridge.json()
    assert bridge_data["status"] == "success"
    assert "package_name" in bridge_data["result"]


def test_agent_bridge_verification_and_tool_call():
    """验证客户端桥梁通过 UserKey + AgentID 握手并真实调用 MCP 工具。"""
    from openviking.server.routers.agents import global_agents_router, router as user_agents_router
    from openviking.storage.agent_principal_store import AgentPrincipalStore

    app = FastAPI()
    app.include_router(user_agents_router)
    app.include_router(global_agents_router)
    c = TestClient(app)

    store = AgentPrincipalStore.get_instance()
    agent = store.register_agent(
        agent_id="ag_test_verify_001",
        agent_name="测试验证智能体",
        user_id="default",
        role_desc="桥梁连通性测试",
        allowed_tools=["find", "health", "read"],
        plugin_grants={"openviking-memory": ["find", "health"]},
    )

    # 1. 验证握手与真实工具调用
    verify_resp = c.post(
        f"/api/v1/agents/{agent.agent_id}/verify",
        json={"user_key": "vk-secret-test-key", "tool_name": "find"},
    )
    assert verify_resp.status_code == 200
    res = verify_resp.json()
    assert res["status"] == "ok"
    assert res["verified"] is True
    assert res["authenticated"] is True
    assert res["agent_id"] == "ag_test_verify_001"
    assert res["tested_tool"] == "find"
    assert "bridge_handshake" in res
    assert res["bridge_handshake"]["bridge_package"] == "dsh-plugin-openviking@1.5.1"
    assert res["tool_call_result"]["status"] == "success"

    # 2. 验证未授权工具被拦截 403
    unauth_resp = c.post(
        f"/api/v1/agents/{agent.agent_id}/verify",
        json={"user_key": "vk-secret-test-key", "tool_name": "write"},
    )
    assert unauth_resp.status_code == 403


