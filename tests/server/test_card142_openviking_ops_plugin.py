# -*- coding: utf-8 -*-
"""Card-142 单元测试套件：系统运维治理插件 (openviking-ops) 独立 Quad 封装与静默守护闭环

核心断言规约：
1. openviking-ops 独立封装为标准 Quad Plugin (17 Tools + 2 Hooks + 1 Skill + GUI)；
2. 17 项运维特权工具完整登记，高危操作 (delete, mv, rename, control) 显式标注 is_dangerous=True；
3. 2 项运维专用 Hook 守卫完整登记 (ov_ops_drift_sentinel, ov_ops_audit_logger)；
4. 插件专用于后台专用运维 Agent / 巡检 Engine，与普通业务 Agent 物理隔离。
"""

import pytest
from openviking.service.plugin_registry import PluginRegistry
from openviking.service.builtin_plugins_core import OPS_17_TOOL_NAMES


def test_ops_17_tool_names_contract():
    """验证运维特权工具单一真相源清单完备度 (Card-189 移除伪概念 dspy 后为 16 项)。"""
    assert len(OPS_17_TOOL_NAMES) == 16
    # 存储与资源挂载 (5 项)
    assert "openviking_add_resource" in OPS_17_TOOL_NAMES
    assert "openviking_list_resources" in OPS_17_TOOL_NAMES
    assert "openviking_delete_resource" in OPS_17_TOOL_NAMES
    assert "openviking_reindex" in OPS_17_TOOL_NAMES
    assert "openviking_commit" in OPS_17_TOOL_NAMES
    # 文件与目录底层写改 (3 项)
    assert "openviking_mv" in OPS_17_TOOL_NAMES
    assert "openviking_rename" in OPS_17_TOOL_NAMES
    assert "openviking_webdav_info" in OPS_17_TOOL_NAMES
    # 系统自愈与纯度度量 (2 项)
    assert "openviking_memory_purity_report" in OPS_17_TOOL_NAMES
    assert "openviking_retry_dead_letter" in OPS_17_TOOL_NAMES
    # 系统监听 (3 项)
    assert "openviking_list_watches" in OPS_17_TOOL_NAMES
    assert "openviking_cancel_watch" in OPS_17_TOOL_NAMES
    assert "openviking_manage_watch" in OPS_17_TOOL_NAMES
    # 服务控制与体检 (3 项)
    assert "openviking_server_control" in OPS_17_TOOL_NAMES
    assert "openviking_server_init" in OPS_17_TOOL_NAMES
    assert "openviking_server_doctor" in OPS_17_TOOL_NAMES


def test_openviking_ops_quad_plugin_definition():
    """验证 openviking-ops 插件四位一体完整性。"""
    registry = PluginRegistry.get_instance()
    plugin = registry.get_plugin("openviking-ops")
    assert plugin is not None
    assert plugin.plugin_id == "openviking-ops"
    assert plugin.name == "OpenViking 系统运维治理"
    assert plugin.version == "1.0.3"

    # 1. 16 项 MCP 工具 (Card-189 移除伪概念 dspy 后为 16 项)
    assert len(plugin.tools) == 16
    tool_names = [t.name for t in plugin.tools]
    for expected in OPS_17_TOOL_NAMES:
        assert expected in tool_names

    # 高危破坏性操作安全门禁标记
    dangerous_tools = [t.name for t in plugin.tools if getattr(t, "is_dangerous", False)]
    assert "openviking_delete_resource" in dangerous_tools
    assert "openviking_mv" in dangerous_tools
    assert "openviking_rename" in dangerous_tools
    assert "openviking_server_control" in dangerous_tools

    # 2. 2 项运维专属 Hook 守卫
    assert len(plugin.hooks) == 2
    hook_ids = [h.hook_id for h in plugin.hooks]
    assert "ov_ops_drift_sentinel" in hook_ids
    assert "ov_ops_audit_logger" in hook_ids

    # 3. 运维专属 Skill 认知导轨
    assert plugin.skill is not None
    assert plugin.skill.skill_id == "openviking-ops"
    assert "后台哨兵" in plugin.skill.description or "自愈" in plugin.skill.description

    # 4. GUI 控制面板 schema
    assert plugin.gui is not None
    assert "sentinelDaemon" in plugin.gui.settings_fields
    assert "dlqMaxRetries" in plugin.gui.settings_fields
    assert plugin.gui.dashboard_route == "/settings"


def test_ops_tools_bidirectional_mapping_and_aliases():
    """验证工具反查映射与短别名兼容性。"""
    registry = PluginRegistry.get_instance()
    # 物理前缀与短名均精准映射至 openviking-ops
    assert registry.get_plugin_id_by_tool("openviking_server_doctor") == "openviking-ops"
    assert registry.get_plugin_id_by_tool("server_doctor") == "openviking-ops"
    assert registry.get_plugin_id_by_tool("openviking_retry_dead_letter") == "openviking-ops"
    assert registry.get_plugin_id_by_tool("retry_dead_letter") == "openviking-ops"

    # 别名解析
    assert registry.resolve_alias("ops") == "openviking-ops"
