# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for SkillOpt Quality Gate and Auto-Optimization Engine."""

import pytest
from fastapi.testclient import TestClient

from openviking.server.app import create_app
from openviking.server.config import ServerConfig
from openviking.service.skill_opt_service import SkillOptService
from openviking.service.skill_opt_types import (
    SkillOptAttemptRequest,
    SkillOptOptimizeRequest,
)

SAMPLE_HIGH_QUALITY_SKILL = """---
name: diagnosing-bugs
description: 深度排查高难度 Bug、内存泄露与性能瓶颈的 SOP 闭环规约。
tools:
  - openviking_find
  - openviking_read
---

# Diagnosing Bugs SOP

## 1. 触发意图与场景 (When to Use)
- 触发关键词：程序崩溃、内存泄露、性能骤降、报错分析、死锁排查。

## 2. 边界约束与负向判定 (Boundary Constraints)
- **何时严禁使用**：当仅是简单编译错误或拼写错误时，严禁滥用本排障流程；
- **职责隔离**：常规业务代码重构请路由至 master-dev 技能。

## 3. 标准操作清单 (Workflow Steps)
1. 提取错误日志指纹；
2. 隔离最小复现用例；
3. 执行根因修复与回归门禁。

## 4. 工具调用示例
```bash
# 运行排查日志
pytest tests/unit/ -k test_leak -v
```
""" + "\n".join([f"# Step detail {i}" for i in range(100)])

SAMPLE_DEFECTIVE_SKILL = """# Just a markdown file without YAML frontmatter

No structure here, no tools, no boundaries.
Just text.
"""


def test_audit_high_quality_skill():
    service = SkillOptService()
    res = service.audit_content(SAMPLE_HIGH_QUALITY_SKILL, skill_name="diagnosing-bugs")

    assert res.skill_name == "diagnosing-bugs"
    assert res.total_score >= 85
    assert res.grade in ("S", "A")
    assert res.passed_gate is True
    assert len(res.dimensions) == 4

    spec = next(d for d in res.dimensions if d.name == "spec_integrity")
    assert spec.score >= 20
    assert spec.status == "good"

    density = next(d for d in res.dimensions if d.name == "token_density")
    assert density.score >= 18
    assert density.status == "good"


def test_audit_defective_skill():
    service = SkillOptService()
    res = service.audit_content(SAMPLE_DEFECTIVE_SKILL)

    assert res.total_score < 60
    assert res.grade in ("C", "D")
    assert res.passed_gate is False
    assert len(res.suggestions) > 0
    assert any("Frontmatter" in s for s in res.suggestions)


def test_token_density_penalty():
    service = SkillOptService()
    # Construct an oversized file with > 510 lines
    oversized = SAMPLE_HIGH_QUALITY_SKILL + "\n" + "\n".join([f"# Padding line {i}" for i in range(450)])
    res = service.audit_content(oversized)

    density = next(d for d in res.dimensions if d.name == "token_density")
    assert density.status == "critical"
    assert density.score <= 13
    assert any("物理红线" in d for d in density.details)


def test_attempt_execution_judge():
    service = SkillOptService()

    # Case 1: Match intent query
    req_match = SkillOptAttemptRequest(
        skill_content=SAMPLE_HIGH_QUALITY_SKILL,
        test_query="系统频繁出现内存泄露与死锁该如何排查",
    )
    result_match = service.attempt_execution(req_match)
    assert result_match.verdict == "PASS"
    assert result_match.matched_intent is True
    assert result_match.confidence >= 0.5
    assert len(result_match.triggered_tools) >= 1

    # Case 2: Unrelated query
    req_unrelated = SkillOptAttemptRequest(
        skill_content=SAMPLE_HIGH_QUALITY_SKILL,
        test_query="今天天气如何做一份红烧牛肉面",
    )
    result_unrelated = service.attempt_execution(req_unrelated)
    assert result_unrelated.verdict == "FAIL"
    assert result_unrelated.matched_intent is False


def test_optimize_content_patch():
    service = SkillOptService()
    req = SkillOptOptimizeRequest(skill_content=SAMPLE_DEFECTIVE_SKILL)
    res = service.optimize_content(req)

    assert res.optimized_score > res.original_score
    assert len(res.applied_fixes) > 0
    assert "name" in res.optimized_content
    assert "Boundary Constraints" in res.optimized_content
    assert "```" in res.optimized_content


def test_batch_audit_execution(tmp_path):
    # Setup mock skill directory
    skill_dir = tmp_path / "skills"
    sub = skill_dir / "my-test-skill"
    sub.mkdir(parents=True)
    (sub / "SKILL.md").write_text(SAMPLE_HIGH_QUALITY_SKILL, encoding="utf-8")

    service = SkillOptService()
    summary = service.batch_audit_skills(skills_dir=str(skill_dir))

    assert summary.total_audited == 1
    assert summary.avg_score >= 85
    assert summary.grade_counts["S"] + summary.grade_counts["A"] == 1


def test_skill_opt_rest_api():
    from openviking.server.auth import get_request_context
    from openviking.server.identity import RequestContext, Role, UserIdentifier

    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    # 1. Audit
    resp = client.post(
        "/api/v1/skill-opt/audit",
        json={"skill_content": SAMPLE_HIGH_QUALITY_SKILL, "skill_name": "test-skill"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["skill_name"] == "test-skill"
    assert data["total_score"] >= 80

    # 2. Attempt
    resp_att = client.post(
        "/api/v1/skill-opt/attempt",
        json={
            "skill_content": SAMPLE_HIGH_QUALITY_SKILL,
            "test_query": "服务报错内存泄露排查流程",
        },
    )
    assert resp_att.status_code == 200
    att_data = resp_att.json()
    assert att_data["verdict"] == "PASS"

    # 3. Optimize
    resp_opt = client.post(
        "/api/v1/skill-opt/optimize",
        json={"skill_content": SAMPLE_DEFECTIVE_SKILL},
    )
    assert resp_opt.status_code == 200
    opt_data = resp_opt.json()
    assert opt_data["optimized_score"] > opt_data["original_score"]

    # 4. Batch audit
    resp_batch = client.get("/api/v1/skill-opt/batch-audit")
    assert resp_batch.status_code == 200
    batch_data = resp_batch.json()
    assert "total_audited" in batch_data
