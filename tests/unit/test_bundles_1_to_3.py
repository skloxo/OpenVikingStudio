# -*- coding: utf-8 -*-
"""
TDD Test Suite for Bundles 1~3: codebase-engineering, credential-vault, network-tunnel-ops.
Aligns with the retina and FSM gatekeeper standards.
"""
import pytest
import yaml
from pathlib import Path

SKILLS_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

@pytest.mark.parametrize("bundle_name, min_modules", [
    ("codebase-engineering", 6),
    ("credential-vault", 4),
    ("network-tunnel-ops", 4),
])
def test_bundles_1_to_3_structure(bundle_name, min_modules):
    bundle_path = SKILLS_ROOT / bundle_name
    assert bundle_path.exists(), f"Bundle {bundle_name} does not exist"
    assert (bundle_path / "SKILL.md").exists()
    assert (bundle_path / "ABSORPTION_PROVENANCE.json").exists()
    
    modules_dir = bundle_path / "modules"
    assert modules_dir.is_dir()
    mods = list(modules_dir.glob("*.md"))
    assert len(mods) >= min_modules, f"{bundle_name} has {len(mods)} modules, expected >= {min_modules}"
    
    # Check each module line count within sweet spot (20~350)
    for m in mods:
        lines = len(m.read_text(encoding="utf-8").splitlines())
        assert 20 <= lines <= 350, f"{bundle_name}/{m.name} line count {lines} out of sweet spot"

@pytest.mark.parametrize("bundle_name, sample_query, expected_trigger", [
    ("codebase-engineering", "运行TDD测试并进行双轴代码审查", "tdd"),
    ("credential-vault", "使用KeePass查询数据库服务器密码并导出私钥", "keepass"),
    ("network-tunnel-ops", "配置创景CPE路由器关闭IPv6并检查FRP穿透", "cpe"),
])
def test_bundles_1_to_3_triggers(bundle_name, sample_query, expected_trigger):
    bundle_path = SKILLS_ROOT / bundle_name
    skill_md = (bundle_path / "SKILL.md").read_text(encoding="utf-8")
    fm = yaml.safe_load(skill_md.split("---", 2)[1])
    triggers = [t.lower() for t in fm.get("triggers", [])]
    assert any(expected_trigger.lower() in t for t in triggers), f"Trigger {expected_trigger} not found in {bundle_name}"
