# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit Tests for Card-195: Adaptive Skills Path & Zero-Latency Indexing (SSOT)."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import pytest

from openviking.service.skill_path_resolver import (
    resolve_skills_root,
    resolve_master_memory_root,
)
from openviking.service.skill_autonomous_pipeline import SkillAutonomousPipeline
from openviking.storage.skill_ingestion_store import SkillIngestionStore, IngestionStatus


def test_resolve_skills_root_env_override(monkeypatch):
    """验证环境变量 OPENVIKING_SKILLS_DIR 具有最高优先级并自动建目录。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        target_path = Path(tmp_dir) / "custom_agent_skills"
        monkeypatch.setenv("OPENVIKING_SKILLS_DIR", str(target_path))
        
        resolved = resolve_skills_root()
        assert resolved == target_path
        assert resolved.exists()


def test_resolve_skills_root_default_fallback(monkeypatch):
    """验证未设置环境变量时优雅回退至用户目录或工作区。"""
    monkeypatch.delenv("OPENVIKING_SKILLS_DIR", raising=False)
    monkeypatch.delenv("OPENVIKING_DATA_DIR", raising=False)
    monkeypatch.delenv("OPENVIKING_HOME", raising=False)
    
    resolved = resolve_skills_root(account_id="test_acc")
    assert resolved.exists()
    assert "test_acc" in str(resolved)
    assert "skills" in str(resolved)


def test_resolve_master_memory_root(monkeypatch):
    """验证主记忆库路径动态自适应解析与环境变量覆盖。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        custom_mem = Path(tmp_dir) / "custom_master_mem"
        monkeypatch.setenv("OPENVIKING_MASTER_MEMORY_DIR", str(custom_mem))
        
        resolved = resolve_master_memory_root()
        assert resolved == custom_mem
        assert resolved.exists()


def test_pipeline_instant_alias_refresh_after_commit(monkeypatch):
    """验证流水线在 Stage 5 提交后，别名路由器实时强刷，立即能通过别名投影召回。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        skills_dir = Path(tmp_dir) / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        db_path = Path(tmp_dir) / "test_ingestion.db"
        
        store = SkillIngestionStore(db_path=db_path)
        pipeline = SkillAutonomousPipeline(skills_root=skills_dir, store=store)
        
        # 预先建立宿主大包
        parent_bundle = skills_dir / "cloud-infra-ops"
        parent_bundle.mkdir(parents=True, exist_ok=True)
        (parent_bundle / "SKILL.md").write_text(
            "---\nname: cloud-infra-ops\nversion: 1.0.0\ndescription: Cloud ops\n---\n# Cloud Infra Ops",
            encoding="utf-8",
        )
        (parent_bundle / "scenarios").mkdir(parents=True, exist_ok=True)
        
        # 投递一个需要归并的技能
        skill_payload = """---
name: aws-s3-sync-ops
version: 1.0.0
description: AWS S3 bucket syncing and lifecycle compliance.
allowed-tools:
  - run_command
  - view_file
---

# AWS S3 Bucket Sync Operations

## 步骤 1. 前置凭据校验
```bash
aws sts get-caller-identity
```

## 步骤 2. 执行数据同步与校验
```bash
aws s3 sync s3://prod-data s3://backup-data --delete
```
若返回 Exit Code 0，判定为同步成功。遇到 502 时重试。
"""
        receipt = store.enqueue_skill(
            skill_name="aws-s3-sync-ops",
            raw_content=skill_payload,
            author="tester",
        )
        
        # 此时别名表中尚未有 aws-s3-sync-ops
        before_res = pipeline.aliasing_router.resolve("aws-s3-sync-ops")
        assert before_res is None
        
        # 执行一轮流水线处理
        cycle_res = pipeline.process_one_cycle(batch_size=1)
        assert cycle_res["processed_count"] == 1
        assert cycle_res["results"][0]["status"] == "COMMITTED"
        
        # 关键验证：Stage 5 落盘完成后，aliasing_router 必须已被强制刷新，0 延迟立即能解析该别名！
        after_res = pipeline.aliasing_router.resolve("aws-s3-sync-ops")
        assert after_res is not None
        assert after_res["target_name"] == "aws-s3-sync-ops"
        assert Path(after_res["file_path"]).exists()
