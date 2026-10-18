#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
tests/unit/test_paradigm_a_sync_and_release.py - 范式 A 原生构建、增量同步与网络安全门禁单测
"""

import os
import sys
import pytest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from sync_to_wsl import (
    is_9p_mount,
    to_wsl_path,
    build_rsync_command,
    SYNC_EXCLUDES,
    DEFAULT_WSL_SERVICE_DIR,
)


def test_is_9p_mount_detection():
    """验证 9P 虚拟文件系统挂载点检测第一性原理"""
    assert is_9p_mount("/mnt/c/Users/Skl/Desktop/coding") is True
    assert is_9p_mount("/mnt/d/projects/openviking") is True
    assert is_9p_mount("/home/skloxo/services/openviking") is False
    assert is_9p_mount("/var/log/openviking") is False


def test_to_wsl_path_conversion():
    """验证 Windows 盘符路径向 WSL2 Linux 路径的精准转换"""
    assert to_wsl_path("C:\\Users\\Skl\\Desktop") == "/mnt/c/Users/Skl/Desktop"
    assert to_wsl_path("D:/projects/openviking") == "/mnt/d/projects/openviking"
    # Linux path should remain intact
    assert to_wsl_path("/home/skloxo/test") == "/home/skloxo/test"


def test_rsync_command_excludes_protection():
    """验证增量同步排除列表严格保护 node_modules、.venv 与运行态缓存"""
    cmd = build_rsync_command("/src/path", "/dst/path", delete=True)
    cmd_str = " ".join(cmd)

    assert "rsync -av --delete" in cmd_str
    # 核心保护目录必须全部排除，杜绝跨 9P 踩坑
    assert "--exclude=node_modules" in cmd
    assert "--exclude=.git" in cmd
    assert "--exclude=.venv" in cmd
    assert "--exclude=dist" in cmd
    assert "--exclude=assets" in cmd
    assert "--exclude=__pycache__" in cmd
    assert "--exclude=.pytest_cache" in cmd


def test_release_step_has_9p_guard():
    """静态验真 release_step.py 必须包含 9P 物理隔离与原生目录重定向逻辑"""
    release_script = SCRIPTS_DIR / "release_step.py"
    assert release_script.is_file(), "release_step.py 必须存在"
    content = release_script.read_text(encoding="utf-8")

    assert "is_9p_mount" in content, "必须调用 is_9p_mount 识别 9P 虚拟文件系统"
    assert "sync_source" in content, "必须在 9P 拦截时触发源码增量同步"
    assert "sync_dist_back" in content, "必须将原生产物 dist/ 增量回传至宿主"
    assert "DEFAULT_WSL_SERVICE_DIR" in content or "live_service_dir" in content
    assert "npm" in content and "build" in content


def test_zero_bare_invoke_webrequest_across_repo():
    """静态视网膜门禁：验证相关 PowerShell 脚本中的 Invoke-WebRequest 必须附带 -UseBasicParsing"""
    coding_root = SCRIPTS_DIR.parent.parent
    target_dirs = [
        SCRIPTS_DIR.parent / "scripts",
        coding_root / "asset-management" / "scripts",
        coding_root / "dify" / "cli" / "scripts",
        coding_root / "scripts",
    ]
    violations = []

    for t_dir in target_dirs:
        if not t_dir.is_dir():
            continue
        for ps_path in t_dir.glob("*.ps1"):
            try:
                lines = ps_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                for idx, line in enumerate(lines, 1):
                    if "Invoke-WebRequest" in line and "-UseBasicParsing" not in line:
                        violations.append(f"{ps_path}:{idx}: {line.strip()}")
            except Exception:
                pass

    assert len(violations) == 0, f"发现未加 -UseBasicParsing 的裸写 Invoke-WebRequest 命令:\n" + "\n".join(violations)
