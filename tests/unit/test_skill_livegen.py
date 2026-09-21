# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Skill LiveGen Service and REST Router (SSOT).

Card 14: Card-Skill-LiveGen-Editor-And-Sandbox-Validation (v1.5.71)
"""

import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from openviking.service.skill_livegen_service import (
    SkillLiveGenService,
    SkillScaffoldRequest,
)
from openviking.server.app import create_app
from openviking.server.config import ServerConfig


@pytest.fixture(autouse=True)
def _reset_livegen_service():
    SkillLiveGenService.reset_instance()
    yield
    SkillLiveGenService.reset_instance()


def test_generate_scaffold_standard():
    svc = SkillLiveGenService.get_instance()
    req = SkillScaffoldRequest(
        name="test-automation-skill",
        description="自动化回归测试技能，触发关键词包含 测试, 自动化, CI",
        allowed_tools=["run_command", "view_file"],
        tags=["qa", "testing"],
        template_type="standard",
    )
    content = svc.generate_scaffold(req)
    assert "name: test-automation-skill" in content
    assert "allowed-tools: run_command view_file" in content
    assert "# test-automation-skill 标准工程技能规范" in content
    assert "tags: [qa, testing]" in content or "qa" in content


def test_generate_scaffold_diagnosis_and_ui():
    svc = SkillLiveGenService.get_instance()
    # Diagnosis template
    diag_req = SkillScaffoldRequest(
        name="bug-triage",
        description="排查并诊断系统崩溃与异常",
        template_type="diagnosis",
    )
    diag_content = svc.generate_scaffold(diag_req)
    assert "故障诊断与根因分析 SOP" in diag_content
    assert "Fail-Fast 契约" in diag_content

    # UI template
    ui_req = SkillScaffoldRequest(
        name="cockpit-hud",
        description="座舱高密排版规范",
        template_type="ui",
    )
    ui_content = svc.generate_scaffold(ui_req)
    assert "座舱级高密设计体系规范" in ui_content
    assert "NO GREEN EVER 🚫" in ui_content


def test_validate_draft_valid_and_line_status():
    svc = SkillLiveGenService.get_instance()
    # 1. 紧凑型 (<100行)
    content = (
        "---\n"
        "name: my-clean-skill\n"
        "description: 简单实用技能\n"
        "---\n\n"
        "# My Clean Skill\n\n"
        "正文内容。\n"
    )
    res = svc.validate_draft(content)
    assert res.valid is True
    assert res.name == "my-clean-skill"
    assert res.line_status == "compact"
    assert len(res.errors) == 0

    # 2. 黄金甜点区 (100~300行)
    sweet_lines = ["---\nname: sweet-skill\ndescription: 甜点技能\n---\n\n# Sweet Skill\n"]
    for i in range(120):
        sweet_lines.append(f"- 条目 {i}: 严格遵循工程规范\n")
    res_sweet = svc.validate_draft("".join(sweet_lines))
    assert res_sweet.valid is True
    assert res_sweet.line_status == "sweet_spot"

    # 3. 超标 (>500行)
    long_lines = ["---\nname: long-skill\ndescription: 超长技能\n---\n\n# Long Skill\n"]
    for i in range(520):
        long_lines.append(f"- 超出条目 {i}\n")
    res_long = svc.validate_draft("".join(long_lines), strict=True)
    assert res_long.line_status == "exceeded"
    assert any(w.get("rule") == "body_max_lines" for w in res_long.warnings)


def test_validate_draft_invalid_frontmatter():
    svc = SkillLiveGenService.get_instance()
    # 缺少 description
    invalid_content = (
        "---\n"
        "name: no-desc-skill\n"
        "---\n\n"
        "正文缺少描述。\n"
    )
    res = svc.validate_draft(invalid_content)
    assert res.valid is False
    assert any(e.get("rule") == "description_required" for e in res.errors)


def test_simulate_trigger_hits_and_misses():
    svc = SkillLiveGenService.get_instance()
    content = (
        "---\n"
        "name: sqlite-lock-fix\n"
        "description: 解决 SQLite 数据库死锁、并发写入超时与 WAL 模式优化\n"
        "tags: [sqlite, lock, concurrency]\n"
        "---\n\n"
        "# SQLite Lock Fix Guide\n"
    )
    queries = [
        "数据库报 database is locked 错误，需要排查并发死锁",
        "帮我优化一下 sqlite 的 WAL 模式和超时设置",
        "今天天气怎么样？",
    ]
    sim = svc.simulate_trigger(content, queries)
    assert sim.skill_name == "sqlite-lock-fix"
    assert sim.total_queries == 3
    assert sim.passed_queries == 2
    assert sim.pass_rate >= 0.60

    # Query 0 命中
    assert sim.results[0].matched is True
    assert sim.results[0].confidence >= 0.35
    assert any("死锁" in kw or "sqlite" in kw.lower() for kw in sim.results[0].matched_keywords)

    # Query 2 未命中
    assert sim.results[2].matched is False
    assert sim.results[2].confidence < 0.35


def test_publish_skill_lifecycle():
    svc = SkillLiveGenService.get_instance()
    with tempfile.TemporaryDirectory() as tmpdir:
        content = (
            "---\n"
            "name: livegen-test-skill\n"
            "description: 创生测试技能发布验证\n"
            "---\n\n"
            "# LiveGen Test Skill\n\n"
            "这是测试发布的技能正文。\n"
        )
        pub_res = svc.publish_skill("livegen-test-skill", content, base_dir=tmpdir)
        assert pub_res.success is True
        assert pub_res.skill_name == "livegen-test-skill"
        assert Path(pub_res.target_path).exists()
        assert Path(pub_res.target_path).read_text(encoding="utf-8") == content
        assert len(pub_res.content_hash) == 16

        # 校验不通过时阻断发布
        bad_res = svc.publish_skill("bad-skill", "缺少 YAML 头部", base_dir=tmpdir)
        assert bad_res.success is False
        assert "校验失败" in bad_res.message


def test_rest_api_livegen_endpoints():
    from openviking.server.auth import get_request_context
    from openviking.server.identity import RequestContext, Role, UserIdentifier

    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    # 1. POST /api/v1/skills/livegen/scaffold
    resp = client.post(
        "/api/v1/skills/livegen/scaffold",
        json={
            "name": "api-demo-skill",
            "description": "API 演示技能",
            "allowed_tools": ["read_url_content"],
            "template_type": "standard",
        },
    )
    assert resp.status_code == 200
    scaffold_data = resp.json()
    assert "name: api-demo-skill" in scaffold_data["content"]

    # 2. POST /api/v1/skills/livegen/validate
    val_resp = client.post(
        "/api/v1/skills/livegen/validate",
        json={"content": scaffold_data["content"], "strict": True},
    )
    assert val_resp.status_code == 200
    assert val_resp.json()["valid"] is True

    # 3. POST /api/v1/skills/livegen/simulate
    sim_resp = client.post(
        "/api/v1/skills/livegen/simulate",
        json={
            "content": scaffold_data["content"],
            "queries": ["请使用 api-demo-skill 进行演示", "无关问题"],
        },
    )
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    assert sim_data["total_queries"] == 2
    assert sim_data["passed_queries"] >= 1

    # 4. GET /api/v1/skills/livegen/stats
    stats_resp = client.get("/api/v1/skills/livegen/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_scaffolds"] >= 1
    assert stats["total_validations"] >= 1
