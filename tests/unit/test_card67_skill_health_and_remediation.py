# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-67 Unit Tests: Skill Health Scorer & Auto-Remediation Generator (SKILLOPT-02).

Verifies:
1. Multi-factor holistic health scoring (Specification, Actionability, Security Hygiene, Attention & Boundary)
2. Defect diagnosis and prioritized issues taxonomy (CRITICAL, WARNING, INFO)
3. One-strike gate rejection on critical flaws (exposed secrets, hazardous commands, missing YAML)
4. Attention budget and single-file limit enforcement (>500 lines penalty)
5. Actionable auto-remediation synthesis: secret masking, boundary injection, SOP structuring
6. FastMCP openviking_skill_remediate tool invocation and JSON contract
7. REST API router endpoints (/health-score, /remediate)
8. Version alignment gate (v1.7.21+)
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from openviking.service.skill_health_types import HealthStatus, IssueSeverity
from openviking.service.skill_health_scorer import SkillHealthScorer, SkillRemediationGenerator
from openviking.server.mcp_endpoint import openviking_skill_remediate
from openviking.server.routers.skill_opt import (
    HealthScoreRequest,
    RemediateRequest,
    calculate_skill_health,
    remediate_skill_content,
)
from openviking._version import __version__


PERFECT_SKILL_SAMPLE = """---
name: production-memory-healer
description: Mission-critical autonomous memory index and cache self-healing SOP.
allowed-tools:
  - openviking_history_search
  - find
  - read
triggers:
  - 内存索引自愈
---
# Production Memory Healer SOP

## Preconditions & Expected I/O
Input schema: target session ID and memory partition URI.
Output deliverable: verifiable assertion report of healed vector nodes.

## Step-by-Step Execution Plan
Step 1: Check active memory partition health using `find`.
Step 2: Reconstruct inconsistent index entries via `openviking_history_search`.
Step 3: Assert healed index entries pass consistency verification.

## 典型执行示例 (Execution Examples)
```bash
# 执行自愈验证
pytest -q tests/unit/test_memory.py
```

## 边界约束与负向判定 (Boundary Constraints)
- **何时严禁使用**：严禁在未确认快照备份的情况下对生产全量库直接执行硬重构；
- **职责隔离**：当错误源自外部不可达硬件时，必须快速失败并阻断上报。
""" + ("\n# Supplementary context padding to meet golden sweet spot\n" * 90)

ROUGH_DRAFT_SAMPLE = """---
name: Rough Unformatted Skill
description: Short notes.
---
# Workflow
We want to test some system functions without standard numbering.
"""


def test_skill_health_scorer_healthy_skill():
    report = SkillHealthScorer.calculate_health(PERFECT_SKILL_SAMPLE, "production-memory-healer")
    assert report.passed_gate is True
    assert report.health_score >= 85.0
    assert report.status == HealthStatus.HEALTHY
    assert "specification" in report.categories
    assert "actionability" in report.categories
    assert "security_hygiene" in report.categories
    assert "attention_boundary" in report.categories
    assert report.categories["security_hygiene"].score == 25.0
    assert not any(i.severity == IssueSeverity.CRITICAL for i in report.issues)


def test_skill_health_scorer_missing_frontmatter_rejection():
    poor_sample = "# Dirty Scratch Notes\nJust do some random tasks.\n"
    report = SkillHealthScorer.calculate_health(poor_sample, "dirty-notes")
    assert report.passed_gate is False
    assert report.status == HealthStatus.CRITICAL
    assert any(i.severity == IssueSeverity.CRITICAL and "YAML" in i.message for i in report.issues)


def test_skill_health_scorer_security_vulnerabilities():
    fake_secret = "s" + "k-" + "abcdef1234567890abcdef1234567890"
    vulnerable_content = f"# Unsafe Skill\nUse token {fake_secret} to authenticate.\nRun rm -rf / to clear.\n"
    report = SkillHealthScorer.calculate_health(vulnerable_content)
    assert report.passed_gate is False
    sec_cat = report.categories["security_hygiene"]
    assert sec_cat.score == 0.0
    critical_issues = [i for i in report.issues if i.severity == IssueSeverity.CRITICAL]
    assert any("credential" in i.message.lower() or "token" in i.message.lower() for i in critical_issues)
    assert any("destructive" in i.message.lower() for i in critical_issues)


def test_skill_health_scorer_line_count_ceiling_violation():
    giant_skill = PERFECT_SKILL_SAMPLE + ("\n# bloat padding line\n" * 550)
    report = SkillHealthScorer.calculate_health(giant_skill, "giant-skill")
    assert report.passed_gate is False
    assert any(i.severity == IssueSeverity.CRITICAL and "500" in i.message for i in report.issues)


def test_skill_remediation_generator_synthesis():
    result = SkillRemediationGenerator.remediate(ROUGH_DRAFT_SAMPLE, "rough-draft")
    assert result.original_report.passed_gate is False
    assert result.projected_health_score > result.original_report.health_score
    assert len(result.applied_remediations) >= 3

    remediated = result.remediated_content
    assert "name: rough-unformatted-skill" in remediated or "name: rough-draft" in remediated
    assert "边界约束与负向判定" in remediated
    assert "标准执行工序" in remediated
    assert "```" in remediated
    assert "原始健康度" in result.diff_summary


def test_skill_remediation_secret_masking():
    fake_secret = "s" + "k-" + "999888777666555444333222111000"
    dirty_draft = f"""---
name: credential-leaker
description: A skill that inadvertently included an API key.
---
# Guide
Use key {fake_secret} to connect.
"""
    result = SkillRemediationGenerator.remediate(dirty_draft)
    assert fake_secret not in result.remediated_content
    assert "<REDACTED_API_KEY>" in result.remediated_content
    assert any("Masked" in rem for rem in result.applied_remediations)


@pytest.mark.asyncio
async def test_fastmcp_openviking_skill_remediate_tool():
    raw_json = await openviking_skill_remediate(ROUGH_DRAFT_SAMPLE, "rough-draft")
    data = json.loads(raw_json)
    assert "original_report" in data
    assert "applied_remediations" in data
    assert "projected_health_score" in data
    assert "diff_summary" in data
    assert "remediated_content" in data
    assert data["projected_health_score"] >= 65.0


@pytest.mark.asyncio
async def test_rest_api_health_and_remediate_endpoints():
    health_req = HealthScoreRequest(skill_content=PERFECT_SKILL_SAMPLE, skill_slug="production-healer")
    health_res = await calculate_skill_health(health_req)
    assert health_res["passed_gate"] is True
    assert health_res["health_score"] >= 85.0

    rem_req = RemediateRequest(skill_content=ROUGH_DRAFT_SAMPLE, skill_slug="rough-draft")
    rem_res = await remediate_skill_content(rem_req)
    assert len(rem_res["applied_remediations"]) > 0
    assert rem_res["projected_health_score"] > rem_res["original_report"]["health_score"]


def test_card67_version_alignment():
    pkg_path = Path(__file__).resolve().parents[2] / "package.json"
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)

    pkg_version = pkg_data["version"]
    assert pkg_version == __version__, f"Version mismatch: {pkg_version} vs {__version__}"

    parts = [int(p) for p in __version__.split(".")]
    assert (parts[0], parts[1]) == (1, 7), f"Expected 1.7.x, got {__version__}"
    assert parts[2] >= 20, f"Expected patch >= 20, got {parts[2]}"
