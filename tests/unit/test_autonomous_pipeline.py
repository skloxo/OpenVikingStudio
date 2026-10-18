# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Test suite for Autonomous Skill Pipeline & Incremental Governance."""

import pytest
import time
from pathlib import Path

from openviking.storage.skill_ingestion_store import (
    IngestionRecord,
    IngestionStatus,
    SkillIngestionStore,
)
from openviking.service.skill_autonomous_pipeline import SkillAutonomousPipeline
from openviking.service.skill_aliasing_router import SkillAliasingRouter

TEST_SKILLS_DIR = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

SAMPLE_VALID_SKILL = """---
name: mock-edge-tunnel-probe
description: 边缘路由器穿透探针与隧道健康诊断规约。
triggers:
  - edge-probe
  - 隧道诊断
  - 边缘路由器
allowed-tools:
  - run_command
  - view_file
---

# Mock Edge Tunnel Probe

## 1. 触发意图与场景
- 触发关键词：edge-probe, 隧道诊断, 边缘路由器。

## 2. 边界约束与负向判定
- **何时严禁使用**：当网络完全离线且无本地物理网卡时严禁执行；
- **职责隔离**：常规 DNS 刷新请移步 clash_verge_governance。

## 3. 标准排查清单 (Workflow)
1. 提取输入参数与网关配置 (input / 参数)；
2. 调用 run_command 探测边缘网关延迟与丢包率；
3. 执行 MTU 路径自适应测试并断言结果 (assert / 断言 / 返回值)；
4. 遇到报错与失败时 (error / 失败)，执行兜底重试与自愈恢复 (retry / 兜底 / 自愈)。

## 4. 工具调用示例
```bash
ping -c 4 192.168.1.1
```
"""


def test_autonomous_pipeline_single_cycle():
    store = SkillIngestionStore.get_instance()
    # 1. 模拟新技能投入收件箱暂存
    rec = store.enqueue_skill(
        skill_name="mock-edge-tunnel-probe",
        raw_content=SAMPLE_VALID_SKILL,
        author="test-suite",
    )
    receipt_id = rec.receipt_id
    
    # 2. 运行一轮自主流水线
    pipeline = SkillAutonomousPipeline(skills_root=TEST_SKILLS_DIR, store=store)
    result = pipeline.process_one_cycle(batch_size=10)
    
    assert result["processed_count"] >= 1, "Pipeline failed to claim and process pending record"
    item = next((r for r in result["results"] if r["receipt_id"] == receipt_id), None)
    assert item is not None, f"Target receipt {receipt_id} not in results: {result['results']}"
    assert item["quality_score"] >= 70.0, f"SkillOpt rejected valid skill: {item['quality_score']}"
    assert item["compressed"] is True, "SkillZip failed to compress"
    assert item["decision"] in ["MERGE_INTO_EXISTING", "SPAWN_NEW_BUNDLE"]
    
    # 3. 验证数据库状态流转为 COMMITTED
    updated_rec = store.get_record(receipt_id)
    assert updated_rec is not None
    assert updated_rec.status == IngestionStatus.COMMITTED
