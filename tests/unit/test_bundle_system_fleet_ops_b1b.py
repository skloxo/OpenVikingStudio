# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
'''TDD Test Suite for system-fleet-ops Domain Capability Bundle (B1B Audited).'''

import pytest
from pathlib import Path
import yaml
from openviking.service.auto_crystallizer_b1b import AutoCrystallizerB1B

BUNDLE_DIR = Path("/home/skloxo/.openviking/data/viking/default/agent/skills/system-fleet-ops")

def test_b1b_delivery_scorecard():
    skill_md = (BUNDLE_DIR / "SKILL.md").read_text(encoding="utf-8")
    lines = len(skill_md.splitlines())
    assert lines <= 100, f"SKILL.md line count out of sweet spot: {lines}"
    
    prov = (BUNDLE_DIR / "ABSORPTION_PROVENANCE.json").read_text(encoding="utf-8")
    assert "B1B-Audited" in prov

def test_b1b_retina_zero_loss():
    scenarios = list((BUNDLE_DIR / "scenarios").glob("*.md"))
    assert len(scenarios) == 124, f"Loss of scenarios: {len(scenarios)} != 124"

def test_b1b_no_broken_links():
    skill_md = (BUNDLE_DIR / "SKILL.md").read_text(encoding="utf-8")
    import re
    link_matches = re.findall(r"\[.*?\]\((modules/.*?\.md)\)", skill_md)
    assert len(link_matches) == 5
    for link in link_matches:
        assert (BUNDLE_DIR / link).exists(), f"Broken link: {link}"

def test_b1b_high_precision_intent():
    skill_md = (BUNDLE_DIR / "SKILL.md").read_text(encoding="utf-8")
    fm = yaml.safe_load(skill_md.split("---", 2)[1])
    triggers = [t.lower() for t in fm.get("triggers", [])]
    
    # Must hit positive domain queries
    assert any("systemd" in t for t in triggers)
    assert any("僵尸进程" in t for t in triggers)
    assert any("性能探针" in t for t in triggers)
    assert any("卫星集群" in t for t in triggers)
    
    # Must NOT contain generic stop words
    for bad in ["系统", "服务", "管理", "配置", "测试", "脚本"]:
        assert bad not in triggers, f"Generic stop-word found in triggers: {bad}"
