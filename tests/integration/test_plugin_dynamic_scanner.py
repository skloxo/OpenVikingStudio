# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Plugin Dynamic Scanner & SSOT Decoupled Perception Gatekeeper Tests.
断言插件与插件中心彻底解耦，动态感知扫描、物理 AST 工具提取与 README 一源互通。
"""

import json
from pathlib import Path
import pytest

from openviking.service.plugin_scanner import scan_local_plugins
from openviking.service.plugin_registry import PluginRegistry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_dynamic_scanner_auto_discovers_all_plugins():
    """断言动态扫描器自动感知所有托管插件，无需硬编码。"""
    plugins, aliases, tool_map = scan_local_plugins()
    plugin_ids = {p.plugin_id for p in plugins}

    expected_plugins = {
        "openviking-memory",
        "openviking-ops",
        "agent-circuit-breaker",
        "keepass-vault",
        "fleet-mesh",
        "dify",
        "cpa-squad",
    }
    assert expected_plugins.issubset(plugin_ids), f"缺失预期插件: {expected_plugins - plugin_ids}"


def test_tools_count_matches_physical_server_py():
    """断言工具数量 100% 物理真实对齐，杜绝虚构假工具。"""
    plugins, _, tool_map = scan_local_plugins()
    plugin_map = {p.plugin_id: p for p in plugins}

    # 1. openviking-memory 核心战地工具精确为 35 项
    mem_plugin = plugin_map["openviking-memory"]
    assert len(mem_plugin.tools) == 35, f"openviking-memory 工具数应为 35，实际为 {len(mem_plugin.tools)}"

    # 2. openviking-ops 特权运维工具精确为 16 项
    ops_plugin = plugin_map["openviking-ops"]
    assert len(ops_plugin.tools) == 16, f"openviking-ops 工具数应为 16，实际为 {len(ops_plugin.tools)}"

    # 3. 杜绝未定义的幽灵假工具
    forbidden_fake_tools = {"ghost_nonexistent_tool", "fake_unimplemented_tool"}
    real_tools = set(tool_map.keys())
    assert forbidden_fake_tools.isdisjoint(real_tools), f"发现残留虚构假工具: {forbidden_fake_tools.intersection(real_tools)}"


def test_readme_ssot_content_loaded():
    """断言所有插件均加载原生 README.md，实现反重力与技能中心 Markdown 一源互通。"""
    plugins, _, _ = scan_local_plugins()
    for p in plugins:
        assert p.readme_content is not None, f"插件 [{p.plugin_id}] 缺失 README.md 正文"
        assert len(p.readme_content.strip()) > 100, f"插件 [{p.plugin_id}] README.md 正文过短"


def test_registry_dynamic_rescan_consistency():
    """断言单例 PluginRegistry 的 rescan 能动态感知最新磁盘状态。"""
    reg = PluginRegistry.get_instance()
    reg.rescan()

    plugins = reg.list_plugins()
    assert len(plugins) >= 7

    mem = reg.get_plugin("openviking-memory")
    assert mem is not None
    assert len(mem.tools) == 35

    ops = reg.get_plugin("openviking-ops")
    assert ops is not None
    assert len(ops.tools) == 16
