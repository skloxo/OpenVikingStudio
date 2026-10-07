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

    # 验证 memory 插件四位一体完整性
    memory = reg1.get_plugin("openviking-memory")
    assert memory is not None
    assert memory.skill.skill_id == "openviking-memory-ops"
    assert len(memory.hooks) >= 1
    assert len(memory.tools) >= 5

    # 验证工具反查插件 ID
    assert reg1.get_plugin_id_by_tool("openviking_find") == "openviking-memory"
    assert reg1.get_plugin_id_by_tool("keepass_get") == "keepass-vault"
    assert reg1.get_plugin_id_by_tool("searxng_search") == "network-search"


def test_is_tool_authorized_logic():
    """验证 is_tool_authorized 权限判别逻辑。"""
    registry = PluginRegistry.get_instance()
    
    grants = {
        "openviking-memory": ["openviking_find", "openviking_read"],
        "network-search": ["*"],
    }

    # 已显式授权的工具
    assert registry.is_tool_authorized(grants, "openviking_find") is True
    assert registry.is_tool_authorized(grants, "openviking_read") is True

    # 未被授权的同一插件工具
    assert registry.is_tool_authorized(grants, "openviking_write") is False

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


def test_get_plugin_detail_endpoint(client):
    """验证 GET /api/v1/plugins/{plugin_id} 详情及 404 容错。"""
    # 正常获取
    resp = client.get("/api/v1/plugins/openviking-memory")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plugin_id"] == "openviking-memory"
    assert data["skill"]["skill_id"] == "openviking-memory-ops"

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
