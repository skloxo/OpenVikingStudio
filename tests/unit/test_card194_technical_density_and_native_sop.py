# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit Tests for Card-194: Technical Entity Density & Native SOP Extractor (SSOT)."""

from __future__ import annotations

import pytest

from openviking.service.skill_opt_judge import SkillOptJudge
from openviking.service.skill_native_sop_extractor import SkillNativeSOPExtractor
from openviking.service.skill_auto_remediator import SkillAutoRemediator


SAMPLE_WILD_GOLD_SKILL = """---
name: k8s-cluster-drain-ops
version: 1.0.0
description: Kubernetes node draining and pod disruption budget governance.
allowed-tools:
  - run_command
  - view_file
---

# Kubernetes 节点下线排障手册

生产集群下线节点必须遵循 PodDisruptionBudget 规约，物理阻断业务雪崩。

## 前置环境准备与集群连通性检查
确保当前 context 正确连接至生产 APIServer，并检查节点状态：
```bash
kubectl config current-context
kubectl get nodes -o wide --show-labels
export KUBECONFIG=/etc/kubernetes/admin.conf
```

## 驱逐节点与 Pod 优雅停机
设置节点为不可调度状态，并执行驱逐：
```bash
kubectl cordon node-prod-01
kubectl drain node-prod-01 --delete-emptydir-data --ignore-daemonsets --force --timeout=120s
```
若遇到 `Cannot evict pod: PodDisruptionBudget violated` 错误，严禁强杀，必须联系业务方扩容副本数。

## 物理关机与硬件维保
节点驱逐完成且返回 Exit Code 0 后，通过 IPMI 或系统管理指令安全下电：
```bash
curl -X POST https://ipmi.internal.cloud/api/v1/power/off -H "Authorization: Bearer ${IPMI_ADMIN_KEY}"
```
遇到 502 Bad Gateway 异常时触发重试，最多重试 2 次。
"""

SAMPLE_EMPTY_FLUFF_SKILL = """---
name: agile-best-practices
version: 1.0.0
description: Agile and clean architecture thoughts.
allowed-tools:
  - view_file
---

# 敏捷开发最佳实践与思想

我们要坚持高质量开发，注重代码的可维护性与扩展性。
在日常开发中，需要保持良好的沟通，遵循敏捷开发的基本原则。
每一次迭代都要认真对待，确保交付质量稳步提升。
架构设计上应当追求高内聚低耦合，减少不必要的复杂性。
"""


def test_technical_density_extraction_on_wild_gold():
    """测试高价值野生技能的技术实体密度量化，应识别大量 CLI、代码块、URL 与异常信号。"""
    density_info = SkillOptJudge.calculate_technical_density(SAMPLE_WILD_GOLD_SKILL)
    
    assert density_info["score"] >= 70.0
    assert density_info["code_blocks_count"] >= 3
    assert len(density_info["cli_commands"]) >= 3
    assert len(density_info["env_and_urls"]) >= 2
    assert len(density_info["guardrail_terms"]) >= 2
    assert len(density_info["error_signals"]) >= 2


def test_technical_density_filtering_on_fluff():
    """测试无实质技术实体的水文鸡汤，密度得分应极低。"""
    density_info = SkillOptJudge.calculate_technical_density(SAMPLE_EMPTY_FLUFF_SKILL)
    
    assert density_info["score"] < 30.0
    assert density_info["code_blocks_count"] == 0
    assert len(density_info["cli_commands"]) == 0


def test_wild_gold_promoted_in_judge():
    """测试野生技能即使缺少规范的 '1. ' 编号与显式断言词，也能依托技术密度被判定为真金。"""
    report = SkillOptJudge.evaluate_skill(SAMPLE_WILD_GOLD_SKILL, passing_score=70.0)
    
    assert report.total_score >= 70.0
    # 诊断日志中必须显式指出高密度技术实体
    assert any("Technical Density: High" in diag or "Raw Gold" in diag for diag in report.diagnostics)


def test_native_sop_extraction():
    """测试原生工序提取器从野生文档中提纯自然段落为标准 SOP，且保留原始命令。"""
    extractor = SkillNativeSOPExtractor()
    sop_result = extractor.extract_native_sop(SAMPLE_WILD_GOLD_SKILL)
    
    assert sop_result is not None
    assert "### 1. 前置环境准备与集群连通性检查" in sop_result or "### 1. " in sop_result
    assert "kubectl drain" in sop_result
    assert "kubectl config" in sop_result


def test_end_to_end_reshaping_with_native_extractor():
    """测试结合原生工序提取器的 SkillAutoRemediator 能够高质量塑形并达到 80+ 分。"""
    remediator = SkillAutoRemediator()
    reshaped_content, fixes = remediator.reshape_for_skillopt(
        content=SAMPLE_WILD_GOLD_SKILL,
        skill_name="k8s-cluster-drain-ops",
    )
    
    assert len(fixes) > 0
    # 重新评测必须满分或高分通过
    report = SkillOptJudge.evaluate_skill(reshaped_content, passing_score=70.0)
    assert report.passed is True
    assert report.total_score >= 80.0
