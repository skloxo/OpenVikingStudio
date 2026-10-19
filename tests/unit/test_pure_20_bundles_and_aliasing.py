# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Capability Bundles Materialization & Skill Aliasing Projection Test Suite.

Validates that:
1. Top-level skills directory strictly consists of self-contained domain capability bundles (no loose naked scripts).
2. Domain bundles contain valid SKILL.md and metadata definitions.
3. Critical crystallized scenarios (web-search-pro, global-agent-core, clash_verge_governance,
   deepseek-harness-ops) are resolvable as virtual projections with high fidelity.
4. Edge cases (case sensitivity, normalization, non-existent skills) fail-fast safely.
"""

from pathlib import Path
import pytest
from openviking.service.skill_aliasing_router import SkillAliasingRouter

SKILLS_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")


@pytest.fixture
def router():
    if not SKILLS_ROOT.exists():
        pytest.skip("Viking skills directory not found on host")
    return SkillAliasingRouter(skills_root=SKILLS_ROOT)


def test_top_level_bundles_structural_hygiene():
    """Verify top-level skills directory contains only legitimate domain bundles and no loose scripts."""
    if not SKILLS_ROOT.exists():
        pytest.skip("Viking skills directory not found")

    top_level_items = list(SKILLS_ROOT.iterdir())
    bundle_dirs = [d for d in top_level_items if d.is_dir() and not d.name.startswith(".")]
    loose_files = [f for f in top_level_items if f.is_file() and not f.name.startswith(".")]

    # Enforce Zero loose scripts in top level
    assert len(loose_files) == 0, f"Found naked loose files in top level skills root: {loose_files}"

    # Enforce every bundle is a legitimate domain bundle with SKILL.md
    assert len(bundle_dirs) > 0, "Top level skills directory is unexpectedly empty"
    for b_dir in bundle_dirs:
        skill_md = b_dir / "SKILL.md"
        assert skill_md.exists(), f"Top-level directory '{b_dir.name}' is not a valid bundle (missing SKILL.md)"
        assert skill_md.stat().st_size > 30, f"Bundle '{b_dir.name}' SKILL.md is empty or corrupted"


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
        ("tide-trading-dev", "quant-trading"),
        ("grid-management", "park-grid-governance"),
        ("cadre-apartment", "property-cadre-ops"),
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
