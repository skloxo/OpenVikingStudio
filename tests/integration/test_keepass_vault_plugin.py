# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
KeePass Vault Plugin Architecture & SSOT Verification Tests.
Card-212: 验证 keepass-vault 插件统一母港、四位一体结构、FastMCP 算子、物理快照 Hook 与安装对齐。
"""

import ast
import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
KP_PLUGIN_DIR = REPO_ROOT / "packages" / "plugins" / "keepass-vault"
INSTALLED_DIR = Path.home() / ".gemini" / "config" / "plugins" / "keepass-vault"


def test_keepass_plugin_metadata():
    """验证 plugin.json 元数据及版本规范 (Card-212)."""
    pjson_path = KP_PLUGIN_DIR / "plugin.json"
    assert pjson_path.exists(), "plugin.json 必须存在于母港 packages/plugins/keepass-vault"
    with open(pjson_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["name"] == "keepass-vault"
    assert meta["version"] == "1.2.1"
    assert "凭据保险库" in meta["description"]
    assert "keepass" in meta["keywords"]
    assert "vault" in meta["keywords"]
    assert "integration" in meta
    channels = [c["id"] for c in meta["integration"]["channels"]]
    assert "antigravity" in channels


def test_keepass_plugin_structure_cleanliness():
    """验证插件四位一体目录结构纯净度."""
    assert (KP_PLUGIN_DIR / "server.py").exists(), "FastMCP server.py 必须存在"
    assert (KP_PLUGIN_DIR / "setup.py").exists(), "标准自举脚本 setup.py 必须存在"
    assert (KP_PLUGIN_DIR / "hooks.json").exists(), "生命周期声明 hooks.json 必须存在"
    assert (KP_PLUGIN_DIR / "mcp_config.json").exists(), "私有 mcp_config.json 必须存在"
    assert (KP_PLUGIN_DIR / "rules" / "AGENTS.md").exists(), "规则契约 rules/AGENTS.md 必须存在"
    assert (KP_PLUGIN_DIR / "hooks" / "vault_guard.py").exists(), "物理守卫 Hook 脚本必须存在"
    
    # 技能认知层检验
    skill_file = KP_PLUGIN_DIR / "skills" / "keepass-vault" / "SKILL.md"
    assert skill_file.exists(), "专属技能 keepass-vault/SKILL.md 必须存在"
    content = skill_file.read_text(encoding="utf-8")
    assert "name: keepass-vault" in content
    assert "查库第一公理" in content
    assert "vault-guard" in content


def test_keepass_tools_ast():
    """使用 AST 静态分析验证 9 大核心 MCP 工具定义完整性."""
    server_file = KP_PLUGIN_DIR / "server.py"
    assert server_file.exists(), "server.py 必须存在"
    tree = ast.parse(server_file.read_text(encoding="utf-8"))
    
    tool_names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if (isinstance(dec, ast.Attribute) and dec.attr == "tool") or (
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Attribute)
                    and dec.func.attr == "tool"
                ):
                    tool_names.add(node.name)
                    break
    
    expected_tools = {
        "keepass_status",
        "keepass_search",
        "keepass_get",
        "keepass_add",
        "keepass_edit",
        "keepass_rm",
        "keepass_list_tree",
        "keepass_analyze",
        "keepass_export_attachment",
    }
    assert expected_tools.issubset(tool_names), f"缺失核心工具: {expected_tools - tool_names}"


def test_keepass_tarballs_built():
    """验证不可变分发包已成功构建并落盘."""
    pub_tar = REPO_ROOT / "public" / "keepass-vault-1.2.1.tgz"
    dsh_tar = REPO_ROOT / "public" / "dsh-plugin-keepass-vault-1.2.1.tgz"
    assert pub_tar.exists(), "public/keepass-vault-1.2.1.tgz 必须存在"
    assert dsh_tar.exists(), "public/dsh-plugin-keepass-vault-1.2.1.tgz 必须存在"
    assert pub_tar.stat().st_size > 5000, "分发包体积异常"
    assert dsh_tar.stat().st_size > 5000, "DSH 适配分发包体积异常"


def test_keepass_installed_ssot():
    """验证宿主环境已部署且与母本 100% 对齐 SSOT."""
    assert INSTALLED_DIR.exists(), "宿主插件目录必须存在"
    inst_pj = INSTALLED_DIR / "plugin.json"
    assert inst_pj.exists(), "宿主 plugin.json 必须存在"
    with open(inst_pj, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("version") == "1.2.1"
    
    cfg_file = Path.home() / ".gemini" / "config" / "config.json"
    assert cfg_file.exists()
    with open(cfg_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    assert "keepass-vault" in cfg.get("plugins", {})
    assert cfg["plugins"]["keepass-vault"]["installedFrom"]["version"] == "1.2.1"
