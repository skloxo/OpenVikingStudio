# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
'''TDD Test Suite for system-fleet-ops Capability Bundle (B2B Anti-Overengineering).'''

import pytest
from pathlib import Path
import yaml
import re

BUNDLE_DIR = Path("/home/skloxo/.openviking/data/viking/default/agent/skills/system-fleet-ops")
MODULES_DIR = BUNDLE_DIR / "modules"
SCENARIOS_DIR = BUNDLE_DIR / "scenarios"

def test_b2b_budget_constraints():
    skill_md = (BUNDLE_DIR / "SKILL.md").read_text(encoding="utf-8")
    master_lines = len(skill_md.splitlines())
    assert master_lines <= 100, f"Master SKILL.md exceeded 100 lines: {master_lines}"
    
    for mod_file in MODULES_DIR.glob("*.md"):
        mod_lines = len(mod_file.read_text(encoding="utf-8").splitlines())
        assert mod_lines <= 200, f"Module {mod_file.name} exceeded 200 lines: {mod_lines}"

def test_b2b_clickable_scenario_links():
    clickable_links = 0
    for mod_file in MODULES_DIR.glob("*.md"):
        txt = mod_file.read_text(encoding="utf-8")
        links = re.findall(r"\[.*?\]\((\.\./scenarios/.*?\.md)\)", txt)
        clickable_links += len(links)
        for rel_link in links:
            target = (MODULES_DIR / rel_link).resolve()
            assert target.exists(), f"Broken scenario link: {rel_link}"
    assert clickable_links >= 30, f"Insufficient clickable links: {clickable_links}"

def test_b2b_actionable_code_blocks():
    total_code_blocks = 0
    for mod_file in MODULES_DIR.glob("*.md"):
        txt = mod_file.read_text(encoding="utf-8")
        blocks = re.findall(r"```bash\n(.*?)```", txt, re.DOTALL)
        total_code_blocks += len(blocks)
    assert total_code_blocks >= 4, f"Modules missing real code blocks: {total_code_blocks}"

def test_b2b_provenance_and_intent():
    prov = (BUNDLE_DIR / "ABSORPTION_PROVENANCE.json").read_text(encoding="utf-8")
    assert "B2B-Pragmatic" in prov
    
    skill_md = (BUNDLE_DIR / "SKILL.md").read_text(encoding="utf-8")
    fm = yaml.safe_load(skill_md.split("---", 2)[1])
    triggers = [t.lower() for t in fm.get("triggers", [])]
    
    # Must hit domain keywords
    assert any("systemd" in t for t in triggers)
    assert any("僵尸进程" in t for t in triggers)
    assert any("性能探针" in t for t in triggers)
    assert any("卫星集群" in t for t in triggers)
