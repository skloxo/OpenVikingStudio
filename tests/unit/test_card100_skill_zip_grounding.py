# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Card-100: SkillZip 759 全域真资产打通与原子回写闭环 (SkillZip Real-Skill Grounding & In-Place Replacement).
"""

import os
from pathlib import Path
import tempfile
import pytest
from fastapi.testclient import TestClient

from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role, UserIdentifier
from openviking.service.skill_provenance_tracker import SkillProvenanceTracker
from openviking.service.skill_zip_apply import SkillZipApplyService


@pytest.fixture
def temp_skills_workspace():
    """构造用于真实文件落盘与快照备份的隔离工作区。"""
    with tempfile.TemporaryDirectory(prefix="test_skillzip_grounding_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        skills_root = tmp_path / "user_skills"
        skills_root.mkdir(parents=True, exist_ok=True)

        backup_root = tmp_path / "quarantine"
        backup_root.mkdir(parents=True, exist_ok=True)

        skill_dir = skills_root / "sample-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"

        initial_content = """---
name: sample-skill
description: 原始臃肿版测试技能
---

# Interface
- input: query: str
- output: res: str

# Workflow
1. Step one is checking parameters thoroughly.
2. Step two is processing the query.
3. Step three is returning the result.

# Contracts
- Invariant: Result must not be empty.
"""
        skill_file.write_text(initial_content, encoding="utf-8")

        yield {
            "temp_dir": tmp_path,
            "skills_root": skills_root,
            "backup_root": backup_root,
            "skill_file": skill_file,
            "skill_dir": skill_dir,
        }


def test_find_skill_file(temp_skills_workspace):
    """验证服务能在候选目录中准确定位目标技能的真实 SKILL.md。"""
    ws = temp_skills_workspace
    service = SkillZipApplyService(
        backup_root=ws["backup_root"],
        candidate_dirs=[ws["skills_root"]],
    )

    found = service.find_skill_file("sample-skill")
    assert found is not None
    assert found == ws["skill_file"]

    assert service.find_skill_file("non-existent-skill") is None


def test_apply_in_place_success(temp_skills_workspace):
    """验证原地原子安全覆写、快照创建与内容覆写。"""
    ws = temp_skills_workspace
    service = SkillZipApplyService(
        backup_root=ws["backup_root"],
        candidate_dirs=[ws["skills_root"]],
    )

    compressed_content = """---
name: sample-skill
description: SkillZip 压缩后的紧凑版技能
---

# Interface
- input: query: str -> output: res: str

# Workflow
1. Validate params. 2. Process query. 3. Return res.

# Contracts
- Invariant: Result must not be empty.
"""

    result = service.apply_compressed_skill(
        skill_slug="sample-skill",
        compressed_content=compressed_content,
        mode="in_place",
    )

    assert result["status"] == "ok"
    assert result["mode"] == "in_place"
    assert "sample-skill" in result["skill_slug"]

    # 1. 验证目标文件被真实物理更新
    updated = ws["skill_file"].read_text(encoding="utf-8")
    assert "SkillZip 压缩后的紧凑版技能" in updated

    # 2. 验证快照目录存在备份文件且保留旧内容
    backups = list(ws["backup_root"].glob("*.bak.md"))
    assert len(backups) == 1
    assert "原始臃肿版测试技能" in backups[0].read_text(encoding="utf-8")


def test_apply_compact_variant(temp_skills_workspace):
    """验证发布为紧凑衍生版 (SKILL.compact.md) 模式。"""
    ws = temp_skills_workspace
    service = SkillZipApplyService(
        backup_root=ws["backup_root"],
        candidate_dirs=[ws["skills_root"]],
    )

    compressed_content = """---
name: sample-skill
description: 衍生紧凑版
---

# Interface
- compact schema
"""

    result = service.apply_compressed_skill(
        skill_slug="sample-skill",
        compressed_content=compressed_content,
        mode="compact_variant",
    )

    assert result["status"] == "ok"
    assert result["mode"] == "compact_variant"
    compact_file = ws["skill_dir"] / "SKILL.compact.md"
    assert compact_file.exists()
    assert "衍生紧凑版" in compact_file.read_text(encoding="utf-8")

    # 原 SKILL.md 未被破坏
    assert "原始臃肿版测试技能" in ws["skill_file"].read_text(encoding="utf-8")


def test_syntax_gate_rejection(temp_skills_workspace):
    """验证 AST 与 YAML 门禁：损坏的 Python 代码块或缺失标头必须物理拦截。"""
    ws = temp_skills_workspace
    service = SkillZipApplyService(
        backup_root=ws["backup_root"],
        candidate_dirs=[ws["skills_root"]],
    )

    # 缺少 YAML 标头
    with pytest.raises(ValueError, match="缺少合规的 YAML Frontmatter"):
        service.apply_compressed_skill("sample-skill", "# No frontmatter")

    # 破损 Python 代码块
    bad_code = """---
name: sample-skill
---
```python
def invalid_code(:
    syntax error
```
"""
    with pytest.raises(ValueError, match="存在 Python 语法错误"):
        service.apply_compressed_skill("sample-skill", bad_code)


def test_api_apply_endpoint(temp_skills_workspace):
    """验证 FastAPI /api/v1/skills/zip/apply 端点。"""
    ws = temp_skills_workspace
    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    valid_content = """---
name: sample-skill
description: API 测试压缩覆写
---

# Interface: compact
"""

    resp = client.post(
        "/api/v1/skills/zip/apply",
        json={
            "skill_slug": "sample-skill",
            "compressed_content": valid_content,
            "mode": "in_place",
            "target_path": str(ws["skill_file"]),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["skill_slug"] == "sample-skill"
    assert ws["skill_file"].read_text(encoding="utf-8") == valid_content
