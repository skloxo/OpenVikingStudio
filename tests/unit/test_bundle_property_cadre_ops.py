# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""TDD Test Suite for property-cadre-ops Domain Capability Bundle (Card-102)."""

import pytest
from pathlib import Path
import yaml
from openviking.service.detail_preserving_merger import MicroEntityExtractor, RetinaDetailAuditor

BUNDLE_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills/property-cadre-ops")
MODULES_DIR = BUNDLE_ROOT / "modules"


def test_property_cadre_bundle_structure():
    assert BUNDLE_ROOT.exists()
    assert (BUNDLE_ROOT / "SKILL.md").exists()
    assert (BUNDLE_ROOT / "ABSORPTION_PROVENANCE.json").exists()
    assert MODULES_DIR.is_dir()
    
    expected_modules = [
        "01_cadre_housing_assets.md",
        "02_smart_lock_and_access.md",
        "03_rent_billing_and_operations.md",
        "04_property_contracts_and_sla.md",
    ]
    for mod in expected_modules:
        mod_path = MODULES_DIR / mod
        assert mod_path.exists(), f"Module {mod} missing"
        content = mod_path.read_text(encoding="utf-8")
        lines = len(content.splitlines())
        assert 20 <= lines <= 350, f"Module {mod} line count {lines} out of sweet spot"


def test_property_cadre_skill_frontmatter_and_fsm():
    skill_md = (BUNDLE_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert skill_md.startswith("---")
    parts = skill_md.split("---", 2)
    assert len(parts) >= 3
    fm = yaml.safe_load(parts[1])
    
    assert fm["name"] == "property-cadre-ops"
    assert "干部公寓" in fm["triggers"]
    assert "智能门锁" in fm["triggers"]
    assert "878" in fm["triggers"] or "宽带台账" in fm["triggers"]
    assert "VFA" in fm["triggers"]
    
    # Check L1 Router Table integrity
    assert "modules/01_cadre_housing_assets.md" in skill_md
    assert "modules/02_smart_lock_and_access.md" in skill_md
    assert "modules/03_rent_billing_and_operations.md" in skill_md
    assert "modules/04_property_contracts_and_sla.md" in skill_md
    
    # Ensure no broken link typo
    assert "modules/02_smart_lock_access.md" not in skill_md


def test_property_cadre_micro_entities_preservation():
    all_texts = [(BUNDLE_ROOT / "SKILL.md").read_text(encoding="utf-8")]
    for f in MODULES_DIR.glob("*.md"):
        all_texts.append(f.read_text(encoding="utf-8"))
    pooled = "\n\n".join(all_texts)
    
    # 10 core permission IDs
    for pid in ["136", "138", "139", "145", "151", "152", "153", "158", "160", "161"]:
        assert pid in pooled, f"Permission ID {pid} missing"
        
    # Crucial accounts & financial sums
    assert "1646637326" in pooled  # 世纪华庭微信商户号
    assert "79,500" in pooled or "79500" in pooled  # 葡萄藤合同
    assert "116,630" in pooled or "116630" in pooled  # 鸿瑞辉合同
    assert "878" in pooled  # 宽带台账基准
    assert "19076061586" in pooled or "190 7606 1586" in pooled  # 硬件工程师谢工


def test_natural_language_intent_routing():
    skill_md = (BUNDLE_ROOT / "SKILL.md").read_text(encoding="utf-8")
    fm = yaml.safe_load(skill_md.split("---", 2)[1])
    triggers = fm.get("triggers", [])
    
    test_queries = [
        ("给越南来的出差干部安排宿舍", ["干部", "出差", "住宿", "客房", "越干"]),
        ("退宿确认后需要立即注销门锁开门权限", ["退宿", "门锁", "智能门锁", "门禁"]),
        ("核对本月878条在网宽带台账和VFA费用转嫁", ["宽带", "宽带台账", "878", "VFA", "费用转嫁"]),
        ("查询北京葡萄藤软件和鸿瑞辉硬件维保合同", ["葡萄藤", "鸿瑞辉", "维保费", "门锁验收"]),
    ]
    
    for query, expected_keywords in test_queries:
        hit = any(kw in query and kw in triggers for kw in expected_keywords)
        assert hit, f"Query '{query}' failed to trigger property-cadre-ops keywords"
