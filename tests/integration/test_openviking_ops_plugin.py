# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking Ops Plugin Architecture & Installation Verification Tests.
Card-201A: 验证 openviking-ops 插件元数据、三位一体结构、自内聚 server.py 与沙盒自举安装。
"""

import ast
import json
import importlib.util
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OPS_PLUGIN_DIR = REPO_ROOT / "integrations" / "antigravity" / "openviking-ops"


def test_ops_plugin_metadata():
    """验证 plugin.json 元数据及版本规范 (Card-201A)."""
    pjson_path = OPS_PLUGIN_DIR / "plugin.json"
    assert pjson_path.exists(), "plugin.json 必须存在"
    with open(pjson_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["name"] == "openviking-ops"
    assert meta["version"] == "1.0.4"
    assert "运维与管控特权" in meta["description"]
    assert "openviking" in meta["keywords"]
    assert "ops" in meta["keywords"]


def test_ops_plugin_structure_cleanliness():
    """验证插件目录纯净度：必须包含三大核心构件，且绝不残留误拷技能."""
    assert (OPS_PLUGIN_DIR / "server.py").exists(), "自内聚 FastMCP server.py 必须存在"
    assert (OPS_PLUGIN_DIR / "setup.py").exists(), "标准自举脚本 setup.py 必须存在"
    assert (OPS_PLUGIN_DIR / "hooks" / "ov_ops_audit.py").exists(), "审计 Hook 脚本必须存在"
    assert (OPS_PLUGIN_DIR / "hooks" / "ov_ops_sentinel.py").exists(), "巡检心跳 Hook 脚本必须存在"
    
    # 技能认知层检验
    skill_file = OPS_PLUGIN_DIR / "skills" / "openviking-ops" / "SKILL.md"
    assert skill_file.exists(), "专属技能 openviking-ops/SKILL.md 必须存在"
    
    # 绝不能存在误拷的外来技能
    skills_dir = OPS_PLUGIN_DIR / "skills"
    subdirs = [d.name for d in skills_dir.iterdir() if d.is_dir()]
    assert "antigravity-plugin-crafting" not in subdirs, "严禁残留 crafting 误拷技能"
    assert "openviking-plugin-ops" not in subdirs, "严禁残留 plugin-ops 误拷技能"
    assert subdirs == ["openviking-ops"], f"技能目录必须仅包含 openviking-ops, 实际: {subdirs}"


def test_ops_skill_frontmatter():
    """验证 openviking-ops/SKILL.md 的 YAML Frontmatter 与核心章节."""
    skill_file = OPS_PLUGIN_DIR / "skills" / "openviking-ops" / "SKILL.md"
    content = skill_file.read_text(encoding="utf-8")
    assert content.startswith("---"), "必须以 YAML frontmatter 开头"
    assert "name: openviking-ops" in content
    assert "description:" in content
    assert "十六项运维特权算子图谱" in content
    assert "openviking_server_doctor" in content
    assert "openviking_add_resource" in content


def test_ops_server_tools_schema():
    """静态 AST 解析 server.py，严格断言 16 项特权算子函数完整定义 (OPS_16_TOOL_NAMES SSOT)."""
    server_file = OPS_PLUGIN_DIR / "server.py"
    assert server_file.exists()
    tree = ast.parse(server_file.read_text(encoding="utf-8"))
    
    expected_tools = {
        "openviking_add_resource",
        "openviking_list_resources",
        "openviking_delete_resource",
        "openviking_reindex",
        "openviking_commit",
        "openviking_mv",
        "openviking_rename",
        "openviking_webdav_info",
        "openviking_memory_purity_report",
        "openviking_retry_dead_letter",
        "openviking_list_watches",
        "openviking_cancel_watch",
        "openviking_manage_watch",
        "openviking_server_control",
        "openviking_server_init",
        "openviking_server_doctor",
    }
    
    found_functions = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found_functions.add(node.name)
            
    missing_tools = expected_tools - found_functions
    assert not missing_tools, f"server.py 缺少特权算子定义: {missing_tools}"


def test_ops_setup_sandbox_install(tmp_path: Path, monkeypatch):
    """在 pytest 临时沙盒中运行 setup.py 自举安装，验证文件解耦复制与 mcp_config.json 路径动态绑定."""
    sandbox_target = tmp_path / "installed_plugins" / "openviking-ops"
    fake_gemini_config = tmp_path / ".gemini" / "config"
    fake_gemini_config.mkdir(parents=True, exist_ok=True)
    
    # 初始化一个虚拟的宿主 config.json 与 mcp_config.json
    (fake_gemini_config / "config.json").write_text(json.dumps({"plugins": {}}), encoding="utf-8")
    (fake_gemini_config / "mcp_config.json").write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
    
    # 动态导入 setup.py 中的 install_plugin
    setup_file = OPS_PLUGIN_DIR / "setup.py"
    spec = importlib.util.spec_from_file_location("ops_setup_module", setup_file)
    ops_setup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ops_setup)
    
    # 隔离 GEMINI_CONFIG_DIR 到沙盒
    monkeypatch.setattr(ops_setup, "GEMINI_CONFIG_DIR", fake_gemini_config)
    
    # 执行沙盒安装
    test_api = "https://mock.vk.tide.red"
    test_key = "test-secret-key-ops"
    ops_setup.install_plugin(sandbox_target, test_api, test_key)
    
    # 验证沙盒部署结果
    assert (sandbox_target / "server.py").exists(), "沙盒中必须包含自内聚 server.py"
    assert (sandbox_target / "plugin.json").exists()
    assert (sandbox_target / "hooks" / "ov_ops_audit.py").exists()
    assert (sandbox_target / "hooks" / "ov_ops_sentinel.py").exists()
    assert (sandbox_target / "skills" / "openviking-ops" / "SKILL.md").exists()
    
    # 验证沙盒中的 hooks.json 包含双 Hook
    hooks_data = json.loads((sandbox_target / "hooks.json").read_text(encoding="utf-8"))
    assert "openviking-ops-sentinel" in hooks_data
    assert "openviking-ops-audit" in hooks_data
    
    # 验证沙盒中的 mcp_config.json
    mcp_cfg_file = sandbox_target / "mcp_config.json"
    assert mcp_cfg_file.exists()
    with open(mcp_cfg_file, "r", encoding="utf-8") as f:
        mcp_data = json.load(f)
    server_entry = mcp_data["mcpServers"]["openviking-ops"]
    assert server_entry["env"]["OPENVIKING_API"] == test_api
    assert server_entry["env"]["OPENVIKING_API_KEY"] == test_key
    # 关键断言：args 必须指向沙盒内部的 server.py，而不是任何旧工作区路径
    installed_server_path = server_entry["args"][0]
    assert "Desktop/coding/OpenVikingStudio" not in installed_server_path, "严禁指向外部旧源码目录"
    assert Path(installed_server_path) == (sandbox_target / "server.py").resolve()
    
    # 验证虚拟宿主 config.json 登记
    host_cfg = json.loads((fake_gemini_config / "config.json").read_text(encoding="utf-8"))
    assert "openviking-ops" in host_cfg["plugins"]
    assert host_cfg["plugins"]["openviking-ops"]["installedFrom"]["version"] == "1.0.4"
