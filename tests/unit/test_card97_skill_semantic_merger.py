# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""TDD Test Suite for Card-97: Code Block Freeze & Bounded Semantic 3-Way Merge."""

import ast
import pytest

from openviking.service.skill_semantic_merger import (
    CodeBlockFreezeVerifier,
    MergeResult,
    SkillSemanticMerger,
)

BASE_MATURE_SKILL = """---
name: git-conflict-resolver
version: 1.2.0
domain: git
description: Resolves git 3-way merge and rebase conflicts cleanly.
triggers:
  - git merge conflict
  - fix rebase
allowed-tools:
  - openviking_find
---

# Git Conflict Resolver

Standard operational procedure for resolving merge conflicts.

```bash
git checkout --theirs path/to/file
git add path/to/file
git rebase --continue
```

```python
def check_conflict_markers(filepath: str) -> bool:
    with open(filepath, "r", encoding="utf-8") as f:
        return "<<<<<<<" in f.read()
```
"""

INCOMING_DELTA_SKILL = """---
name: git-conflict-resolver-turbo
version: 1.0.0
domain: git
description: Resolves git conflicts with special handling for lockfiles and dry-run flag.
triggers:
  - git lockfile conflict
  - yarn lock conflict
allowed-tools:
  - openviking_find
---

# Git Conflict Resolver Turbo

Extra edge-case handling for lockfiles with `--dry-run` and `--auto-resolve-lock`.

```bash
git checkout --theirs package-lock.json
npm install --package-lock-only
```

```python
def check_conflict_markers(filepath: str) -> bool:
    # Attempting to mutate original function with a bug!
    return False
```
"""


@pytest.fixture
def merger():
    return SkillSemanticMerger()


def test_code_block_extraction_and_hashing():
    """Verify code blocks in markdown are extracted with deterministic sha256 hashes."""
    blocks = CodeBlockFreezeVerifier.extract_code_blocks(BASE_MATURE_SKILL)
    assert len(blocks) == 2
    assert blocks[0].lang == "bash"
    assert "git checkout --theirs" in blocks[0].code
    assert len(blocks[0].sha256) == 64
    assert blocks[1].lang == "python"
    assert "def check_conflict_markers" in blocks[1].code


def test_code_block_freeze_prevents_tampering(merger):
    """Verify mature code blocks cannot be overwritten or mutated by incoming skill."""
    result = merger.merge(
        base_content=BASE_MATURE_SKILL,
        incoming_content=INCOMING_DELTA_SKILL,
    )

    assert result.code_mutation_detected is False
    assert result.frozen_block_count == 2
    # Verify original mature code blocks are 100% physically intact
    assert "return \"<<<<<<<\" in f.read()" in result.merged_content
    assert "return False" not in result.merged_content  # The poisoned replacement was rejected!


def test_delta_triggers_and_flags_absorbed(merger):
    """Verify unique triggers and parameters from incoming skill are safely appended."""
    result = merger.merge(
        base_content=BASE_MATURE_SKILL,
        incoming_content=INCOMING_DELTA_SKILL,
    )

    assert "git lockfile conflict" in result.delta_triggers_added
    assert "yarn lock conflict" in result.delta_triggers_added
    assert "--dry-run" in result.delta_params_absorbed or "--auto-resolve-lock" in result.delta_params_absorbed
    assert "## 🚀 Absorbed Advanced Variants & Edge-Case Flags" in result.merged_content
    assert "npm install --package-lock-only" in result.merged_content


def test_version_bump_and_metadata_preservation(merger):
    """Verify version is safely bumped and metadata is preserved."""
    result = merger.merge(
        base_content=BASE_MATURE_SKILL,
        incoming_content=INCOMING_DELTA_SKILL,
    )

    assert "version: 1.2.1" in result.merged_content
    assert "name: git-conflict-resolver" in result.merged_content
    assert "domain: git" in result.merged_content


def test_post_merge_ast_validation(merger):
    """Verify merged document passes AST syntax check on all python blocks."""
    result = merger.merge(
        base_content=BASE_MATURE_SKILL,
        incoming_content=INCOMING_DELTA_SKILL,
    )

    assert result.ast_valid is True
    # Parse python blocks to double check
    blocks = CodeBlockFreezeVerifier.extract_code_blocks(result.merged_content)
    for b in blocks:
        if b.lang == "python":
            ast.parse(b.code)
