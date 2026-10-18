# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""TDD Test Suite for Card-96: Dynamic KNN Duplicate Detection & Skill Package Auto-Routing."""

import os
import tempfile
from pathlib import Path
import pytest
import yaml

from openviking.service.skill_package_router import (
    PathRewriterHook,
    RouteAction,
    RouteDecision,
    SkillPackageRouter,
)


@pytest.fixture
def temp_vault_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def router(temp_vault_dir):
    return SkillPackageRouter(vault_root=temp_vault_dir)


EXISTING_GIT_SKILL = """---
name: git-conflict-resolver
version: 1.0.0
domain: git
description: Resolves git 3-way merge and rebase conflicts cleanly.
triggers:
  - git merge conflict
  - fix rebase
  - git conflict
allowed-tools:
  - openviking_find
---

# Git Conflict Resolver
Detailed SOP for resolving git conflicts.
"""

EXISTING_K8S_SKILL = """---
name: k8s-pod-debugger
version: 1.0.0
domain: devops
description: Debugs crashed Kubernetes pods and captures event logs.
triggers:
  - k8s crashloop
  - pod debugging
  - container crashed
allowed-tools:
  - openviking_find
---

# K8s Pod Debugger
Instructions on inspecting pod events.
"""


def test_empty_catalog_routes_to_new_package(router):
    """When library is empty, new skill should form a new package."""
    decision = router.analyze_routing(
        skill_name="k8s-pod-debugger",
        content=EXISTING_K8S_SKILL,
        existing_skills=[],
    )
    assert decision.action == RouteAction.NEW_PACKAGE
    assert decision.target_package == "devops"
    assert decision.top1_score == 0.0


def test_duplicate_skill_triggers_merge_action(router):
    """Near-identical skill with high similarity and margin triggers MERGE action."""
    existing = [
        {"name": "git-conflict-resolver", "content": EXISTING_GIT_SKILL, "domain": "git"},
        {"name": "k8s-pod-debugger", "content": EXISTING_K8S_SKILL, "domain": "devops"},
    ]

    # Incoming skill is a duplicate/variant of git-conflict-resolver
    incoming_git = """---
name: git-merge-conflict-fixer
version: 1.0.1
domain: git
description: Resolves git 3-way merge and rebase conflicts cleanly with extra diagnostics.
triggers:
  - git merge conflict
  - fix rebase
  - git conflict
allowed-tools:
  - openviking_find
---

# Git Conflict Resolver
Detailed SOP for resolving git conflicts.
"""
    decision = router.analyze_routing(
        skill_name="git-merge-conflict-fixer",
        content=incoming_git,
        existing_skills=existing,
    )
    assert decision.action == RouteAction.MERGE
    assert decision.target_package == "git"
    assert decision.top1_candidate == "git-conflict-resolver"
    assert decision.top1_score >= 0.85
    assert decision.margin >= 0.08


def test_same_domain_skill_triggers_package_add(router):
    """Skill in same domain but with distinct procedure triggers PACKAGE_ADD."""
    existing = [
        {"name": "git-conflict-resolver", "content": EXISTING_GIT_SKILL, "domain": "git"},
        {"name": "k8s-pod-debugger", "content": EXISTING_K8S_SKILL, "domain": "devops"},
    ]

    incoming_git_bisect = """---
name: git-bisect-debugger
version: 1.0.0
domain: git
description: Binary search git history using git bisect to pinpoint regressions.
triggers:
  - git bisect
  - find breaking commit
  - pinpoint regression
allowed-tools:
  - openviking_find
---

# Git Bisect SOP
Steps to automate bisect run.
"""
    decision = router.analyze_routing(
        skill_name="git-bisect-debugger",
        content=incoming_git_bisect,
        existing_skills=existing,
    )
    assert decision.action == RouteAction.PACKAGE_ADD
    assert decision.target_package == "git"


def test_novel_domain_skill_triggers_new_package(router):
    """Skill in completely novel domain triggers NEW_PACKAGE."""
    existing = [
        {"name": "git-conflict-resolver", "content": EXISTING_GIT_SKILL, "domain": "git"},
    ]

    incoming_quant = """---
name: quant-alpha-screener
version: 1.0.0
domain: quantitative-finance
description: Screen cross-sectional equities using factor momentum.
triggers:
  - alpha factors
  - momentum screening
  - quant portfolio
allowed-tools:
  - openviking_find
---

# Quant Alpha Screener
Calculate cross sectional rank.
"""
    decision = router.analyze_routing(
        skill_name="quant-alpha-screener",
        content=incoming_quant,
        existing_skills=existing,
    )
    assert decision.action == RouteAction.NEW_PACKAGE
    assert decision.target_package == "quantitative-finance"


def test_materialize_package_structure(router, temp_vault_dir):
    """Verify package directory, PACKAGE.yaml, and subskills layout."""
    pkg_path = router.materialize_package(
        package_name="git",
        subskills=[
            ("git-conflict-resolver", EXISTING_GIT_SKILL),
        ],
    )

    assert pkg_path.exists()
    assert (pkg_path / "PACKAGE.yaml").exists()
    assert (pkg_path / "INDEX.md").exists()
    assert (pkg_path / "subskills" / "git-conflict-resolver" / "SKILL.md").exists()

    with open(pkg_path / "PACKAGE.yaml", "r", encoding="utf-8") as f:
        pkg_meta = yaml.safe_load(f)
    assert pkg_meta["name"] == "git"
    assert "git-conflict-resolver" in pkg_meta["subskills"]


def test_path_rewriter_hook():
    """Verify relative paths in scripts are normalized without corrupting commands."""
    raw_markdown = """
Run the diagnostics script:
```bash
python scripts/diagnose.py --verbose
```
And inspect ./scripts/config.json.
"""
    rewritten = PathRewriterHook.rewrite_paths(
        content=raw_markdown,
        package_name="devops",
        skill_name="k8s-pod-debugger",
    )
    assert "${PACKAGE_ROOT}/subskills/k8s-pod-debugger/scripts/diagnose.py" in rewritten
    assert "${PACKAGE_ROOT}/subskills/k8s-pod-debugger/scripts/config.json" in rewritten
