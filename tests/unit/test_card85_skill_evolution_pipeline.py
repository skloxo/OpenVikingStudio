# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test suite for Card-85: Skill Evolution & Crystallization Pipeline Orchestrator."""

import os
from pathlib import Path
import shutil
import tempfile
import pytest

from openviking.service.skill_evolution_pipeline import SkillEvolutionPipeline
from openviking.service.skill_evolution_types import (
    PipelineStage,
    SkillClusterCandidate,
)


@pytest.fixture
def mock_skills_env(tmp_path):
    """Sets up a sandboxed mock skills filesystem with homogenous skills."""
    skills_root = tmp_path / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)

    # 1. Candidate skill A: feishu-bitable
    skill_a = skills_root / "feishu-bitable"
    skill_a.mkdir()
    (skill_a / "SKILL.md").write_text(
        """---
name: feishu-bitable
description: 飞书多维表格自动化读写与数据同步工具
allowed-tools:
  - openviking_find
  - openviking_read
---

# Feishu Bitable Skill
## 1. 触发意图与场景
- 触发关键词：飞书多维表格、bitable、飞书记录写入

## 2. 边界约束 (When NOT to use)
- 严禁用于飞书云文档常规文字排版。

## 3. 标准操作 SOP
1. 解析 table_id 与 app_token；
2. 构造数据 payload；
3. 执行接口调用并检验返回。
""",
        encoding="utf-8",
    )
    # Auxiliary script
    scripts_dir = skill_a / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "bitable_client.py").write_text("# Mock bitable client helper", encoding="utf-8")

    # 2. Candidate skill B: feishu-doc
    skill_b = skills_root / "feishu-doc"
    skill_b.mkdir()
    (skill_b / "SKILL.md").write_text(
        """---
name: feishu-doc
description: 飞书云文档创建与富文本导出
allowed-tools:
  - openviking_write
---

# Feishu Doc Skill
## 1. 触发意图与场景
- 触发关键词：飞书文档、创建云文档、feishu doc

## 2. 边界约束 (When NOT to use)
- 禁止用于多维表格计算。

## 3. 标准操作 SOP
1. 校验文档标题与父文件夹；
2. 生成 Markdown 正文并上报；
3. 输出分享链接。
""",
        encoding="utf-8",
    )

    # 3. Unrelated skill: git-pr
    skill_c = skills_root / "git-pr"
    skill_c.mkdir()
    (skill_c / "SKILL.md").write_text(
        """---
name: git-pr
description: GitHub PR 自动化提交与状态轮询
---
# Git PR SOP
1. git push origin branch
2. gh pr create
""",
        encoding="utf-8",
    )

    pipeline = SkillEvolutionPipeline(root_skills_dir=skills_root)
    pipeline.backup_root = tmp_path / "quarantine"
    return pipeline, skills_root


def test_identify_homogenous_clusters(mock_skills_env):
    """Test clustering algorithm correctly groups Feishu skills and ignores singletons."""
    pipeline, _ = mock_skills_env
    clusters = pipeline.identify_homogenous_clusters()

    cluster_ids = [c.cluster_id for c in clusters]
    assert "feishu-suite" in cluster_ids
    feishu_cluster = next(c for c in clusters if c.cluster_id == "feishu-suite")
    assert "feishu-bitable" in feishu_cluster.candidate_slugs
    assert "feishu-doc" in feishu_cluster.candidate_slugs
    assert feishu_cluster.target_slug == "feishu-hub"


def test_crystallize_cluster_dry_run(mock_skills_env):
    """Test dry_run execution completes all stages without modifying disk files."""
    pipeline, skills_root = mock_skills_env
    clusters = pipeline.identify_homogenous_clusters()
    feishu_cluster = next(c for c in clusters if c.cluster_id == "feishu-suite")

    res = pipeline.crystallize_cluster(feishu_cluster, dry_run=True)
    assert res.success is True
    assert res.target_slug == "feishu-hub"
    assert res.final_judge_score >= 70.0
    assert len(res.stages) == 7

    stage_names = [s.stage.value for s in res.stages]
    assert "detect_collisions" in stage_names
    assert "health_audit" in stage_names
    assert "remediation_draft" in stage_names
    assert "asset_heritage" in stage_names
    assert "attempt_judge" in stage_names

    # In dry run, target dir should not be created on disk
    assert not (skills_root / "feishu-hub").exists()


def test_script_and_asset_heritage(mock_skills_env):
    """Test asset heritage protocol copies auxiliary Python scripts to target skill directory."""
    pipeline, skills_root = mock_skills_env
    clusters = pipeline.identify_homogenous_clusters()
    feishu_cluster = next(c for c in clusters if c.cluster_id == "feishu-suite")

    res = pipeline.crystallize_cluster(feishu_cluster, dry_run=False)
    assert res.success is True
    assert any("bitable_client.py" in f for f in res.inherited_files)

    # Check target skill dir on disk
    target_dir = skills_root / "feishu-hub"
    assert target_dir.exists()
    assert (target_dir / "SKILL.md").exists()
    assert (target_dir / "scripts" / "bitable_client.py").exists()

    # Check that SKILL.md contains aliases
    content = (target_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "feishu-bitable" in content
    assert "feishu-doc" in content


def test_judge_gate_bounded_retry_and_blocking(tmp_path):
    """Test malformed skill fails judge gate and terminates gracefully without infinite loops."""
    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    # Create 2 garbage skills that fail judge gate
    s1 = skills_root / "garbage-feishu-1"
    s1.mkdir()
    (s1 / "SKILL.md").write_text("bad text without structure", encoding="utf-8")

    s2 = skills_root / "garbage-feishu-2"
    s2.mkdir()
    (s2 / "SKILL.md").write_text("another broken skill", encoding="utf-8")

    pipeline = SkillEvolutionPipeline(root_skills_dir=skills_root)
    pipeline.backup_root = tmp_path / "quarantine"

    candidate = SkillClusterCandidate(
        cluster_id="feishu-suite",
        domain_name="Feishu",
        target_slug="feishu-hub",
        candidate_slugs=["garbage-feishu-1", "garbage-feishu-2"],
    )

    res = pipeline.crystallize_cluster(candidate, dry_run=True, max_attempts=2)
    # Should safely terminate with failure rather than loop indefinitely
    assert res.success is False
    assert "blocked" in (res.error or "").lower()


def test_atomic_backup_and_rollback(mock_skills_env):
    """Test atomic snapshot creation and one-click rollback."""
    pipeline, skills_root = mock_skills_env
    clusters = pipeline.identify_homogenous_clusters()
    feishu_cluster = next(c for c in clusters if c.cluster_id == "feishu-suite")

    res = pipeline.crystallize_cluster(feishu_cluster, dry_run=False)
    assert res.success is True
    assert (skills_root / "feishu-hub").exists()

    # The candidate was physically archived out of active skills_root
    assert not (skills_root / "feishu-bitable").exists()

    # Rollback restores candidates and removes generated master skill
    rollback_ok = pipeline.rollback_cluster("feishu-suite")
    assert rollback_ok is True
    assert (skills_root / "feishu-bitable").exists()
    assert (skills_root / "feishu-bitable" / "scripts" / "bitable_client.py").exists()
    assert not (skills_root / "feishu-hub").exists()


def test_full_pipeline_run(mock_skills_env):
    """Test full pipeline run generates summary report with objective metric anchors."""
    pipeline, _ = mock_skills_env
    report = pipeline.run_pipeline(dry_run=True)

    assert report.clusters_identified >= 1
    assert report.clusters_crystallized >= 1
    assert report.avg_health_after > report.avg_health_before
    assert report.collisions_after == 0


def test_crystallized_content_synthesis_broad_description_and_router(mock_skills_env):
    """Test that crystallization produces broad synthesized descriptions and sub-scenario routers."""
    pipeline, skills_root = mock_skills_env
    clusters = pipeline.identify_homogenous_clusters()
    feishu_cluster = next(c for c in clusters if c.cluster_id == "feishu-suite")

    res = pipeline.crystallize_cluster(feishu_cluster, dry_run=False)
    assert res.success is True

    master_skill_md = skills_root / "feishu-hub" / "SKILL.md"
    assert master_skill_md.exists()
    content = master_skill_md.read_text(encoding="utf-8")

    # Frontmatter contains broad description covering whole ecosystem, not narrow seed description
    assert "飞书/Lark 生态全能操作中枢" in content
    assert "多维表格" in content

    # Contains Sub-Scenario Navigation Router
    assert "领域多工序导航路由 (Sub-Scenario Router)" in content
    assert "§1. CLI 认证与身份切换" in content
    assert "§2. 文档与知识库协同" in content
    assert "§3. 多维表格与数据资产" in content

    # Aggregated tools
    assert "allowed-tools:" in content
    assert "aliases:" in content
