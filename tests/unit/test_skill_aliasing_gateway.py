# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Test suite for Skill Aliasing & Virtual Projection Gateway."""

import pytest
from pathlib import Path
from openviking.service.skill_aliasing_router import SkillAliasingRouter

SKILLS_DIR = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

def test_alias_discovery_from_scenarios():
    router = SkillAliasingRouter(skills_root=SKILLS_DIR)
    mapping = router.get_alias_map()
    
    # 验证 park-grid-governance 下的 scenario 能够被自动发现为别名
    assert "mac-production-deploy" in mapping, "Failed to discover mac-production-deploy scenario"
    bundle_name, rel_path = mapping["mac-production-deploy"]
    assert bundle_name == "park-grid-governance"
    assert rel_path.name == "mac-production-deploy.md"

def test_explicit_alias_resolution():
    router = SkillAliasingRouter(skills_root=SKILLS_DIR)
    
    # 验证 cpa_squad -> cpa-squad 别名解析
    res = router.resolve("cpa_squad")
    assert res is not None
    assert res["target_name"] in ["cpa-squad", "quant-trading"]

def test_virtual_skill_detail_assembly():
    router = SkillAliasingRouter(skills_root=SKILLS_DIR)
    detail = router.get_virtual_skill("mac-production-deploy")
    
    assert detail is not None
    assert detail["name"] == "mac-production-deploy"
    assert detail["parent_bundle"] == "park-grid-governance"
    assert "content" in detail
    assert len(detail["content"]) > 100
    assert detail["uri"].startswith("viking://agent/skills/park-grid-governance/scenarios/mac-production-deploy.md")

def test_unknown_skill_returns_none():
    router = SkillAliasingRouter(skills_root=SKILLS_DIR)
    assert router.resolve("non_existent_crazy_skill_12345") is None
    assert router.get_virtual_skill("non_existent_crazy_skill_12345") is None
