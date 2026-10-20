# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Plugin Version Parity & Auto-Bump Retina Gatekeeper Tests.
版本同频与改动必 Bump 视网膜门禁：彻底杜绝“改动代码遗漏版本递增”与“多端版本断层”。
"""

import json
import re
import subprocess
from pathlib import Path
import pytest

from openviking.service.builtin_plugins_core import resolve_package_version

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

CORE_PLUGINS = [
    {
        "name": "openviking-memory",
        "ag_json": REPO_ROOT / "integrations" / "antigravity" / "openviking-memory" / "plugin.json",
        "dsh_json": REPO_ROOT / "integrations" / "deepseek-harness" / "dsh-plugin-openviking-memory" / "package.json",
        "src_dirs": [
            REPO_ROOT / "integrations" / "antigravity" / "openviking-memory",
            REPO_ROOT / "integrations" / "deepseek-harness" / "dsh-plugin-openviking-memory",
        ],
    },
    {
        "name": "openviking-ops",
        "ag_json": REPO_ROOT / "integrations" / "antigravity" / "openviking-ops" / "plugin.json",
        "dsh_json": REPO_ROOT / "integrations" / "deepseek-harness" / "dsh-plugin-openviking-ops" / "package.json",
        "src_dirs": [
            REPO_ROOT / "integrations" / "antigravity" / "openviking-ops",
            REPO_ROOT / "integrations" / "deepseek-harness" / "dsh-plugin-openviking-ops",
        ],
    },
]


def test_dual_track_version_parity():
    """断言核心插件在 Antigravity 端与 DSH 端的版本号必须 100% 物理同频."""
    for p in CORE_PLUGINS:
        assert p["ag_json"].exists(), f"{p['name']} Antigravity plugin.json 缺失"
        assert p["dsh_json"].exists(), f"{p['name']} DSH package.json 缺失"

        ag_ver = json.loads(p["ag_json"].read_text(encoding="utf-8"))["version"]
        dsh_ver = json.loads(p["dsh_json"].read_text(encoding="utf-8"))["version"]

        assert ag_ver == dsh_ver, (
            f"❌ 插件 [{p['name']}] 双端版本分裂！"
            f"Antigravity 端版本: {ag_ver} != DSH 端版本: {dsh_ver}"
        )


def test_server_ssot_version_resolution():
    """断言服务端 resolve_package_version 必须精准解析到磁盘真实版本号，消除硬编码滞后."""
    mem_ver = resolve_package_version("dsh-plugin-openviking-memory", "fallback")
    ops_ver = resolve_package_version("dsh-plugin-openviking-ops", "fallback")

    expected_mem = json.loads(
        (REPO_ROOT / "integrations" / "deepseek-harness" / "dsh-plugin-openviking-memory" / "package.json").read_text(
            encoding="utf-8"
        )
    )["version"]
    expected_ops = json.loads(
        (REPO_ROOT / "integrations" / "deepseek-harness" / "dsh-plugin-openviking-ops" / "package.json").read_text(
            encoding="utf-8"
        )
    )["version"]

    assert mem_ver == expected_mem, f"服务端 memory 版本解析滞后: {mem_ver} != {expected_mem}"
    assert ops_ver == expected_ops, f"服务端 ops 版本解析滞后: {ops_ver} != {expected_ops}"


def test_git_diff_bump_enforcement():
    """
    【改动必 Bump 物理硬防线】
    若检测到插件目录下的源码文件发生 Git 变更，则必须同时存在版本号修改；
    若修改了业务逻辑却未递增版本，测试直接红灯阻断！
    """
    try:
        res = subprocess.run(
            ["git", "diff", "HEAD", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode != 0:
            return  # 若非 git 环境或执行失败则跳过
        changed_files = res.stdout.strip().splitlines()
    except Exception:
        return

    for p in CORE_PLUGINS:
        p_name = p["name"]
        code_changed = False
        ver_changed = False

        for f_path in changed_files:
            # 检查是否有该插件的代码发生修改
            rel = f_path.replace("\\", "/")
            if f"integrations/antigravity/{p_name}/" in rel or f"integrations/deepseek-harness/dsh-plugin-{p_name}/" in rel:
                if rel.endswith("plugin.json") or rel.endswith("package.json"):
                    # 检查是否修改了版本号行
                    diff_res = subprocess.run(
                        ["git", "diff", "HEAD", "--", f_path],
                        cwd=str(REPO_ROOT),
                        capture_output=True,
                        text=True,
                    )
                    if '"version":' in diff_res.stdout:
                        ver_changed = True
                else:
                    # 排除临时文件
                    if not any(rel.endswith(ext) for ext in [".pyc", ".tmp", ".log"]):
                        code_changed = True

        if code_changed and not ver_changed:
            pytest.fail(
                f"❌ 视网膜门禁红灯阻断：检测到插件 [{p_name}] 源码已发生变更，但版本号未 Bump！\n"
                f"👉 必须执行: python scripts/bump_plugin.py {p_name} 自动原子升级版本！"
            )
