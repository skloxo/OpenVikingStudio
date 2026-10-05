# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Card-99 单元测试：SkillOpt 759 全域资产对齐与物理回写落盘测试 (SkillOpt 759 SSOT & Apply Gate Tests)
"""

import os
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from openviking.service.skill_opt_service import SkillOptService
from openviking.service.skill_opt_apply import SkillOptApplyService
from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role, UserIdentifier


@pytest.fixture
def temp_skills_workspace():
    """建立临时沙盒用于验证原子物理写盘与快照备份。"""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_skillopt_grounding_"))
    skills_root = temp_dir / "user_skills"
    backup_root = temp_dir / "quarantine"
    skills_root.mkdir(parents=True, exist_ok=True)
    backup_root.mkdir(parents=True, exist_ok=True)

    # 构造一个合规的标准技能文件
    skill_dir = skills_root / "my-test-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_content = """---
name: my-test-skill
description: 用于验证 SkillOpt 物理落盘与快照备份的测试技能。
tools:
  - openviking_find
---

# My Test Skill SOP

## 典型调用
```python
def test_func():
    return 42
```
"""
    skill_file.write_text(skill_content, encoding="utf-8")

    yield {
        "temp_dir": temp_dir,
        "skills_root": skills_root,
        "backup_root": backup_root,
        "skill_file": skill_file,
    }

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_batch_audit_real_paths():
    """验证 batch_audit_skills 真实物理对齐（759 个技能）。"""
    service = SkillOptService()
    summary = service.batch_audit_skills()
    assert summary.total_audited == 759, f"Expected 759 audited skills, got {summary.total_audited}"
    assert summary.avg_score > 0
    assert "S" in summary.grade_counts
    assert "D" in summary.grade_counts


def test_apply_patch_success(temp_skills_workspace):
    """验证原子物理回写、快照创建与内容覆写。"""
    ws = temp_skills_workspace
    service = SkillOptApplyService(
        backup_root=ws["backup_root"],
        candidate_dirs=[ws["skills_root"]],
    )

    new_content = """---
name: my-test-skill
description: 经过 SkillOpt 调优后的高质量技能规约。
tools:
  - openviking_find
  - openviking_read
---

# Optimized Skill

## 边界约束与负向判定
- **严禁滥用**：非本领域任务严禁调用。
```python
def run_task():
    print("optimized")
```
"""

    result = service.apply_patch(
        skill_slug="my-test-skill",
        optimized_content=new_content,
    )

    assert result["status"] == "ok"
    assert "my-test-skill" in result["skill_slug"]

    # 1. 验证目标文件被真实物理更新
    updated_file_content = ws["skill_file"].read_text(encoding="utf-8")
    assert "经过 SkillOpt 调优后的高质量技能规约" in updated_file_content

    # 2. 验证快照目录存在备份文件
    backup_files = list(ws["backup_root"].glob("*.bak.md"))
    assert len(backup_files) == 1
    backup_text = backup_files[0].read_text(encoding="utf-8")
    assert "用于验证 SkillOpt 物理落盘与快照备份的测试技能" in backup_text


def test_apply_patch_syntax_gate(temp_skills_workspace):
    """验证 AST 门禁：损坏的 Python 代码块或缺失标头必须物理拦截。"""
    ws = temp_skills_workspace
    service = SkillOptApplyService(
        backup_root=ws["backup_root"],
        candidate_dirs=[ws["skills_root"]],
    )

    # 缺少 YAML 标头
    with pytest.raises(ValueError, match="缺少合规的 YAML Frontmatter"):
        service.apply_patch("my-test-skill", "# No frontmatter content")

    # 包含损坏的 Python 代码块
    bad_python_content = """---
name: my-test-skill
description: 损坏的代码块测试
---

```python
def broken_syntax(
    return 123
```
"""
    with pytest.raises(ValueError, match="Python 代码块 #1 语法解析错误"):
        service.apply_patch("my-test-skill", bad_python_content)

    # 原始文件绝不应被破坏
    original_text = ws["skill_file"].read_text(encoding="utf-8")
    assert "用于验证 SkillOpt 物理落盘" in original_text


def test_apply_patch_not_found(temp_skills_workspace):
    """验证不存在的技能抛出 FileNotFoundError。"""
    ws = temp_skills_workspace
    service = SkillOptApplyService(
        backup_root=ws["backup_root"],
        candidate_dirs=[ws["skills_root"]],
    )

    with pytest.raises(FileNotFoundError, match="未能在系统中找到技能"):
        service.apply_patch(
            skill_slug="ghost-non-existent-skill",
            optimized_content="---\nname: ghost\ndescription: test\n---\n",
        )


def test_api_apply_patch_endpoint(temp_skills_workspace):
    """验证 FastAPI /api/v1/skill-opt/apply 路由端点。"""
    ws = temp_skills_workspace
    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    valid_content = """---
name: my-test-skill
description: API 调优落盘测试
tools:
  - openviking_find
---

# API Test
"""

    resp = client.post(
        "/api/v1/skill-opt/apply",
        json={
            "skill_slug": "my-test-skill",
            "optimized_content": valid_content,
            "target_path": str(ws["skill_file"]),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "my-test-skill" in data["skill_slug"]
