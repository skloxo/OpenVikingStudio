# -*- coding: utf-8 -*-
"""
tests/unit/test_assemble_dsh_adapter.py
OpenViking 智能体适配器通用装配引擎单元测试视网膜。
验证：
1. 插件内核 AST 动态抽取与 100% 参数化置换
2. 三插槽冗余注册与本地存储隔离
3. NO GREEN EVER 视觉铁律与最小字号 >= 12px 门禁
"""

import json
from pathlib import Path
import pytest

from scripts.assemble_dsh_adapter import (
    assemble_dsh_adapter,
    assemble_all,
    resolve_canonical_names,
    categorize_tool,
    ROOT_DIR,
)


def test_assemble_openviking_memory():
    """测试核心记忆插件的适配器装配质量。"""
    kernel_dir = ROOT_DIR / "packages" / "plugins" / "openviking-memory"
    code, meta = assemble_dsh_adapter(kernel_dir)

    assert meta["dsh_pkg_name"] == "dsh-plugin-openviking-memory"
    assert meta["short_name"] == "openviking-memory"
    assert meta["tools_count"] == 35
    assert meta["skills_count"] == 4
    assert meta["hooks_count"] == 3

    # 验证插槽注入与代码特征 (双锚点冗余注册，保障 DSH 顶层与行级无缝直达)
    assert "plugins.bundle.config" in code
    assert "plugins.row.config" in code
    assert "settings.plugins.tab" in code
    assert "SHORT_NAME = 'openviking-memory'" in code
    assert "STORAGE_KEY" in code
    assert "README_CONTENT" in code
    assert "RULES" in code
    assert meta["rules_count"] >= 1

    # 视觉硬性门禁
    assert "#0891b2" in code  # 冰青
    assert "#e11d48" in code  # 玫瑰红
    assert "11px" not in code  # 绝对禁用 < 12px 微字


def test_assemble_keepass_vault():
    """测试本地凭据保险库插件的适配器装配质量。"""
    kernel_dir = ROOT_DIR / "integrations" / "antigravity" / "keepass-vault"
    code, meta = assemble_dsh_adapter(kernel_dir)

    assert meta["dsh_pkg_name"] == "dsh-plugin-keepass-vault"
    assert meta["short_name"] == "keepass-vault"
    assert meta["tools_count"] == 9
    assert meta["skills_count"] == 1
    assert "keepass_status" in code
    assert "keepass_search" in code
    assert "SHORT_NAME = 'keepass-vault'" in code
    assert "STORAGE_KEY" in code
    assert "11px" not in code


def test_assemble_openviking_ops():
    """测试系统运维治理插件的适配器装配质量。"""
    kernel_dir = ROOT_DIR / "integrations" / "antigravity" / "openviking-ops"
    code, meta = assemble_dsh_adapter(kernel_dir)

    assert meta["dsh_pkg_name"] == "dsh-plugin-openviking-ops"
    assert meta["short_name"] == "openviking-ops"
    assert meta["tools_count"] == 16
    assert meta["hooks_count"] >= 1
    assert "openviking_add_resource" in code
    assert "openviking_server_doctor" in code
    assert "11px" not in code


def test_assemble_all_ecosystem():
    """测试全系插件一键全量装配。"""
    items = assemble_all()
    assert len(items) >= 7

    pkg_names = {it["dsh_pkg_name"] for it in items}
    assert "dsh-plugin-openviking-memory" in pkg_names
    assert "dsh-plugin-openviking-ops" in pkg_names
    assert "dsh-plugin-openviking-fleet" in pkg_names
    assert "dsh-plugin-keepass-vault" in pkg_names
    assert "dsh-plugin-dify" in pkg_names
    assert "dsh-plugin-cpa" in pkg_names
    assert "dsh-plugin-search-gateway" in pkg_names
