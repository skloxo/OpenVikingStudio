# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-193 专项测试：存量技能微手术热更新与微观技术实体 Diff 审计引擎 (SSOT)."""

import pytest
from pathlib import Path
import tempfile
import yaml

from openviking.service.skill_mutation_engine import (
    SkillMutationEngine,
    MutationVerdict,
)
from openviking.storage.skill_ingestion_store import SkillIngestionStore, IngestionStatus
from openviking.service.skill_autonomous_pipeline import SkillAutonomousPipeline


SAMPLE_BASE_SKILL = """---
name: sample-tool-skill
version: 1.0.0
description: 测试基础工具规范
allowed-tools:
  - run_command
---

# Sample Tool Skill

## 核心操作规约
执行数据处理前必须核实环境参数：
```bash
python3 -m tool --env=prod --timeout=30s --cluster=main
```

- 环境变量：${TOOL_KEY}
- API 地址：https://api.viking.internal/v1/health
"""

SAMPLE_PATCHED_SKILL = """---
name: sample-tool-skill
version: 1.0.0
description: 测试基础工具规范
allowed-tools:
  - run_command
---

# Sample Tool Skill

## 核心操作规约
执行数据处理前必须核实环境参数：
```bash
python3 -m tool --env=prod --timeout=5s --cluster=main
```

- 环境变量：${TOOL_KEY}
- API 地址：https://api.viking.internal/v2/health
"""

SAMPLE_VANDALIZED_SKILL = """---
name: sample-tool-skill
version: 1.0.0
description: 被恶意截断或清空的技能
---

# Empty Skill
没有任何代码块和工具了。
"""


@pytest.fixture
def temp_skills_workspace():
    """创建一个具备真实大包与场景的隔离技能根目录。"""
    tmp_dir = Path(tempfile.mkdtemp(prefix="card193_skills_"))
    bundle_dir = tmp_dir / "cloud-infra-ops"
    scenarios_dir = bundle_dir / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    
    # 建立一个存量场景
    target_scenario = scenarios_dir / "sample-tool-skill.md"
    target_scenario.write_text(SAMPLE_BASE_SKILL, encoding="utf-8")

    yield tmp_dir, target_scenario


def test_lineage_router_detects_existing_scenario(temp_skills_workspace):
    """测试血缘路由器能够精准定位已有大包场景，而不是当成新物种。"""
    skills_root, target_scenario = temp_skills_workspace
    engine = SkillMutationEngine(skills_root=skills_root)

    found, bundle_name, target_path = engine.find_existing_target("sample-tool-skill")
    assert found is True
    assert bundle_name == "cloud-infra-ops"
    assert target_path == target_scenario


def test_micro_patch_single_line_change_passes_and_increments_version(temp_skills_workspace):
    """测试 1 行致命参数修改（重叠率 99%）被精准捕获为黄金热补丁，并自增版本号。"""
    skills_root, target_scenario = temp_skills_workspace
    engine = SkillMutationEngine(skills_root=skills_root)

    verdict, summary, patched_content = engine.audit_mutation(
        skill_name="sample-tool-skill",
        incoming_content=SAMPLE_PATCHED_SKILL,
    )

    assert verdict == MutationVerdict.APPLY_PATCH
    assert "https://api.viking.internal/v2/health" in summary or "diff" in summary.lower() or "entities" in summary.lower()
    assert "version: 1.0.1" in patched_content
    assert "--timeout=5s" in patched_content

    # 执行物理热更新
    apply_res = engine.apply_mutation(
        skill_name="sample-tool-skill",
        patched_content=patched_content,
        target_path=target_scenario,
    )
    assert apply_res["status"] == "MUTATED"
    # 验证物理文件被原地微手术替换
    new_content = target_scenario.read_text(encoding="utf-8")
    assert "--timeout=5s" in new_content
    assert "https://api.viking.internal/v2/health" in new_content


def test_anti_vandalism_gate_blocks_accidental_code_clearing(temp_skills_workspace):
    """测试防洗劫门禁：当新提交恶意或意外清空核心代码块时，触发视网膜安全阻断。"""
    skills_root, target_scenario = temp_skills_workspace
    engine = SkillMutationEngine(skills_root=skills_root)

    verdict, summary, _ = engine.audit_mutation(
        skill_name="sample-tool-skill",
        incoming_content=SAMPLE_VANDALIZED_SKILL,
    )

    assert verdict == MutationVerdict.REJECTED_VANDALISM
    assert "清空" in summary or "vandalism" in summary.lower() or "code block" in summary.lower()


def test_identical_content_returns_noop(temp_skills_workspace):
    """测试幂等防抖：完全相同的内容返回 NO_CHANGE，不产生脏提交。"""
    skills_root, target_scenario = temp_skills_workspace
    engine = SkillMutationEngine(skills_root=skills_root)

    verdict, summary, _ = engine.audit_mutation(
        skill_name="sample-tool-skill",
        incoming_content=SAMPLE_BASE_SKILL,
    )

    assert verdict == MutationVerdict.NO_CHANGE
    assert "identical" in summary.lower() or "相同" in summary


def test_pipeline_integrates_mutation_channel(temp_skills_workspace):
    """端到端集成测试：流水线在处理已有技能的 1 行微调时，走热更新通道而非新建大包。"""
    skills_root, target_scenario = temp_skills_workspace
    store = SkillIngestionStore.get_instance()
    pipeline = SkillAutonomousPipeline(skills_root=skills_root, store=store)

    rec = store.enqueue_skill(
        skill_name="sample-tool-skill",
        raw_content=SAMPLE_PATCHED_SKILL,
        author="hotfix-engineer",
    )

    cycle_res = pipeline.process_one_cycle(batch_size=5)
    matched = [r for r in cycle_res.get("results", []) if r.get("skill_name") == "sample-tool-skill"]
    assert len(matched) == 1
    res = matched[0]
    assert res["status"] == "COMMITTED"
    assert res.get("decision") == "MUTATE_EXISTING"
    assert res.get("target_bundle") == "cloud-infra-ops"
