# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
'''TDD Test Suite for system-fleet-ops Domain Capability Bundle (Card-104).'''

import pytest
from pathlib import Path
import yaml

BUNDLE_DIR = Path("/home/skloxo/.openviking/data/viking/default/agent/skills/system-fleet-ops")
MODULES_DIR = BUNDLE_DIR / "modules"
SCENARIOS_DIR = BUNDLE_DIR / "scenarios"

def test_system_fleet_bundle_structure():
    assert BUNDLE_DIR.exists()
    assert (BUNDLE_DIR / "SKILL.md").exists()
    assert (BUNDLE_DIR / "ABSORPTION_PROVENANCE.json").exists()
    assert MODULES_DIR.is_dir()
    assert SCENARIOS_DIR.is_dir()
    
    mods = list(MODULES_DIR.glob("*.md"))
    assert len(mods) == 5
    for m in mods:
        lines = len(m.read_text(encoding="utf-8").splitlines())
        assert 15 <= lines <= 250, f"Module line count out of sweet spot"

def test_system_fleet_scenarios_preservation():
    scenarios = list(SCENARIOS_DIR.glob("*.md"))
    assert len(scenarios) == 124, f"Expected 124 scenarios, found {len(scenarios)}"

def test_system_fleet_skill_fsm_lines():
    skill_md = (BUNDLE_DIR / "SKILL.md").read_text(encoding="utf-8")
    lines = len(skill_md.splitlines())
    assert lines <= 100, f"SKILL.md too bloated: {lines} lines"
    for i in range(1, 6):
        assert f"modules/0{i}_" in skill_md

def test_system_fleet_intent_routing():
    skill_md = (BUNDLE_DIR / "SKILL.md").read_text(encoding="utf-8")
    fm = yaml.safe_load(skill_md.split("---", 2)[1])
    triggers = [t.lower() for t in fm.get("triggers", [])]
    
    queries = [
        ("查看系统服务 systemd 并重启 openviking 守护进程", ["systemd", "systemctl", "daemon", "service", "系统服务", "守护进程"]),
        ("排查内存泄漏并清理僵尸孤儿进程", ["process", "memory", "leak", "gc", "kill", "内存泄漏", "僵尸进程", "孤儿进程"]),
        ("编写跨平台 Bash 脚本并检查退出码", ["bash", "shell", "script", "terminal", "Bash脚本", "退出码"]),
        ("检查磁盘空间 df 与 CPU 内存水位线探针", ["disk", "cpu", "ram", "probe", "monitor", "磁盘空间", "性能探针", "水位线"]),
        ("巡检卫星节点并进行集群配置同步", ["fleet", "satellite", "node", "cluster", "mesh", "卫星节点", "卫星集群", "集群巡检", "节点同步", "巡检"]),
        ("使用 journalctl 分析服务崩溃日志", ["systemd", "systemctl", "service", "linux", "journalctl", "服务崩溃"]),
        ("检测当前系统中是否存在文件描述符 FD 泄漏", ["process", "fd", "memory", "gc", "文件描述符", "FD泄漏"]),
        ("利用 top 查看系统负载与内存使用率", ["cpu", "ram", "top", "monitor", "内存占用", "负载监控"]),
        ("配置远程节点 SSH 免密与 rsync 文件同步", ["fleet", "satellite", "ssh", "node", "远程节点"]),
        ("排查 WSL2 虚拟机中的 Linux 守护进程", ["wsl", "linux", "daemon", "service", "守护进程"]),
    ]
    for q, kws in queries:
        hit = any(kw.lower() in q.lower() and any(kw.lower() in t for t in triggers) for kw in kws)
        assert hit, f"Query '{q}' failed intent trigger"
