# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Trainable Skill Policy and # EVOLVE-BLOCK surface mechanism.

测试套件:
  test_inspect_evolve_blocks                  分析有界可编辑区块与冻结面指纹
  test_update_block_preserves_frozen_surface  安全更新区块且冻结面绝对零篡改
  test_out_of_bounds_index                    越界索引防御拦截
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from openviking.core.trainable_skill_policy import TrainableSkillDocument

SAMPLE_SKILL_TEXT = """---
name: sample-skill
description: A sample skill with bounded evolve surfaces.
---

# Architecture Overview
This is a frozen system section that cannot be modified.

# EVOLVE-BLOCK-START
def execute_task(param: str) -> str:
    # Initial strategy logic
    return f"Processed: {param}"
# EVOLVE-BLOCK-END

# System Invariants
These rules are strictly frozen.
"""


def test_inspect_evolve_blocks():
    """测试分析文档中的有界可编辑区块与冻结面指纹。"""
    doc = TrainableSkillDocument(SAMPLE_SKILL_TEXT, skill_name="sample-skill")
    inspection = doc.inspect()

    assert inspection.has_evolve_blocks is True
    assert inspection.block_count == 1
    assert len(inspection.blocks) == 1
    assert "execute_task" in inspection.blocks[0].content
    assert inspection.blocks[0].line_count >= 3
    assert len(inspection.frozen_surface_sha256) == 64


def test_update_block_preserves_frozen_surface():
    """测试安全更新区块内容，且外部框架冻结面哈希严格一致。"""
    doc = TrainableSkillDocument(SAMPLE_SKILL_TEXT, skill_name="sample-skill")
    orig_inspection = doc.inspect()

    new_code = """def execute_task(param: str) -> str:
    # Enhanced strategy with caching
    return f"Optimized: {param}"
"""
    updated_doc = doc.update_block(0, new_code)
    new_inspection = updated_doc.inspect()

    # 1. 可编辑区块内容已更新
    assert "Optimized: {param}" in updated_doc.raw_text
    assert "Initial strategy" not in updated_doc.raw_text

    # 2. 外部冻结面哈希绝对不变
    assert new_inspection.frozen_surface_sha256 == orig_inspection.frozen_surface_sha256


def test_out_of_bounds_index():
    """测试越界索引防御。"""
    doc = TrainableSkillDocument(SAMPLE_SKILL_TEXT, skill_name="sample-skill")
    with pytest.raises(IndexError):
        doc.update_block(5, "some content")
    with pytest.raises(IndexError):
        doc.update_block(-1, "some content")
