# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-162 Unit Test: 20 Core Capability Bundles Pure Materialization & Skill Aliasing Projection.

Validates that:
1. Top-level skills directory contains strictly 20 domain capability bundles.
2. Every bundle contains a valid SKILL.md and .abstract.md index.
3. Critical crystallized scenarios (web-search-pro, global-agent-core, clash_verge_governance,
   deepseek-harness-ops) are resolvable as virtual projections with high fidelity.
4. Edge cases (case sensitivity, normalization, non-existent skills) fail-fast safely.
"""

from pathlib import Path
import pytest
from openviking.service.skill_aliasing_router import SkillAliasingRouter

SKILLS_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

EXPECTED_20_BUNDLES = sorted([
    "ai-harness-ops",
    "antigravity-host-ops",
    "cloud-infra-ops",
    "cockpit-ui",
    "codebase-engineering",
    "cpa_squad",
    "credential-vault",
    "developer-productivity",
    "document-governance",
    "living-asset-system",
    "multimodal-media",
    "network-tunnel-ops",
    "openviking",
    "park-grid-governance",
    "presentation-designer",
    "property-cadre-ops",
    "quant-trading",
    "security-audit-compliance",
    "session-handover",
    "web-harvest-pro",
])


@pytest.fixture
def router():
    if not SKILLS_ROOT.exists():
        pytest.skip("Viking skills directory not found on host")
    return SkillAliasingRouter(skills_root=SKILLS_ROOT)


def test_strictly_20_top_level_bundles():
    """Verify top-level directory has strictly 20 capability bundles and no loose single skills."""
    if not SKILLS_ROOT.exists():
        pytest.skip("Viking skills directory not found")

    dirs = sorted([
        d.name for d in SKILLS_ROOT.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])
    assert len(dirs) == 20, f"Expected strictly 20 bundles, found {len(dirs)}: {dirs}"
    assert dirs == EXPECTED_20_BUNDLES


def test_all_bundles_contain_skill_and_abstract():
    """Verify all 20 bundles have SKILL.md and .abstract.md files."""
    if not SKILLS_ROOT.exists():
        pytest.skip("Viking skills directory not found")

    for bundle_name in EXPECTED_20_BUNDLES:
        b_dir = SKILLS_ROOT / bundle_name
        skill_md = b_dir / "SKILL.md"
        abstract_md = b_dir / ".abstract.md"
        assert skill_md.exists(), f"Bundle {bundle_name} missing SKILL.md"
        assert abstract_md.exists(), f"Bundle {bundle_name} missing .abstract.md"
        assert skill_md.stat().st_size > 50, f"Bundle {bundle_name} SKILL.md is empty or too small"
        assert abstract_md.stat().st_size > 10, f"Bundle {bundle_name} .abstract.md is empty"


def test_web_search_pro_scenario_projection(router):
    """Verify web-search-pro resolves to web-harvest-pro with is_virtual=True."""
    res = router.resolve("web-search-pro")
    assert res is not None
    assert res["type"] == "scenario_projection"
    assert res["bundle_name"] == "web-harvest-pro"
    assert res["is_virtual"] is True

    virtual_skill = router.get_virtual_skill("web-search-pro")
    assert virtual_skill is not None
    assert virtual_skill["name"] == "web-search-pro"
    assert virtual_skill["parent_bundle"] == "web-harvest-pro"
    assert virtual_skill["is_virtual"] is True
    assert "content" in virtual_skill and len(virtual_skill["content"]) > 100
    assert "viking://agent/skills/web-harvest-pro/scenarios/web-search-pro.md" in virtual_skill["uri"]


def test_core_crystallized_scenarios_resolution(router):
    """Verify critical granular scenarios across bundles resolve with zero breaking."""
    cases = [
        ("deepseek-harness-ops", "ai-harness-ops"),
        ("agent-governance-guardrails", "ai-harness-ops"),
        ("clash_verge_governance", "network-tunnel-ops"),
        ("capability-bundle-crystallizer", "openviking"),
        ("global-agent-core", "codebase-engineering"),
        ("tide-trading-dev", "antigravity-host-ops"),
    ]
    for skill_name, expected_bundle in cases:
        res = router.resolve(skill_name)
        assert res is not None, f"Failed to resolve {skill_name}"
        assert res["bundle_name"] == expected_bundle, (
            f"Expected {skill_name} in {expected_bundle}, got {res['bundle_name']}"
        )
        assert res["is_virtual"] is True


def test_bundle_direct_resolution(router):
    """Verify top-level bundle resolves directly without virtual flag."""
    res = router.resolve("codebase-engineering")
    assert res is not None
    assert res["type"] == "bundle"
    assert res["bundle_name"] == "codebase-engineering"
    assert res["is_virtual"] is False


def test_normalization_and_aliases(router):
    """Verify hyphen/underscore normalization and explicit aliases."""
    res_cpa = router.resolve("cpa-squad")
    assert res_cpa is not None
    assert res_cpa["bundle_name"] == "cpa_squad"

    res_keepass = router.resolve("keepass-vault")
    assert res_keepass is not None
    assert res_keepass["bundle_name"] == "credential-vault"

    # Non-existent skill fails gracefully
    assert router.resolve("definitely-non-existent-skill-xyz") is None
    assert router.get_virtual_skill("definitely-non-existent-skill-xyz") is None
