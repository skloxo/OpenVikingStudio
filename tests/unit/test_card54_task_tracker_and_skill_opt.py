# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-54 专项测试：TaskTracker 探针静音与判空、SkillOpt 动态路径解耦与 AHE 异常平滑防御。"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from openviking.service.task_tracker import (
    get_task_tracker,
    has_task_tracker,
    set_task_tracker,
)
from openviking.service.task_card_manager import TaskCardManager
from openviking.service.skill_opt_service import SkillOptService
from openviking.service.skill_opt_types import SkillOptOptimizeRequest


@pytest.mark.asyncio
async def test_task_tracker_safe_probing():
    """验证 has_task_tracker 与 optional=True 探针静音，消灭长调用栈污染。"""
    # 模拟 tracker 未初始化状态
    set_task_tracker(None)

    assert has_task_tracker() is False
    # optional=True 应静默返回 None，不抛出 RuntimeError
    tracker = get_task_tracker(optional=True)
    assert tracker is None

    # optional=False (默认) 应抛出 RuntimeError
    with pytest.raises(RuntimeError, match="TaskTracker not initialized"):
        get_task_tracker(optional=False)

    # 模拟设置 tracker
    mock_tracker = MagicMock()
    set_task_tracker(mock_tracker)
    assert has_task_tracker() is True
    assert get_task_tracker() is mock_tracker
    assert get_task_tracker(optional=True) is mock_tracker

    # 还原
    set_task_tracker(None)


@pytest.mark.asyncio
async def test_task_card_manager_tracker_integration(tmp_path: Path):
    """验证 TaskCardManager 建卡与解决工单时安全调用 tracker 且不抛错。"""
    inbox = tmp_path / "inbox"
    resolved = tmp_path / "resolved"
    mgr = TaskCardManager(base_dir=tmp_path)

    # 1. 未初始化 tracker 情况下建卡，零异常
    set_task_tracker(None)
    card = await mgr.file_issue_card(
        title="Test Issue",
        priority="P1",
        module="core",
        symptom="Connection reset",
        initiator="agent-1",
    )
    assert card["status"] == "created"
    card_id = card["card_id"]

    # 2. 设置 mock tracker 情况下解决工单，验证流转联动
    mock_tracker = MagicMock()
    mock_tracker.complete = AsyncMock()
    set_task_tracker(mock_tracker)

    res = await mgr.resolve_card(
        card_id=card_id,
        resolution_tag="v1.7.8",
        commit_hash="abc1234",
        summary="Fixed safely",
    )
    assert res["status"] == "resolved"
    await asyncio.sleep(0.05)  # 等待异步 task 调度
    matching_calls = [
        c for c in mock_tracker.complete.call_args_list
        if c[1].get("task_id") == card_id
    ]
    assert len(matching_calls) == 1
    assert matching_calls[0][1]["result"]["summary"] == "Fixed safely"

    # 还原
    set_task_tracker(None)


def test_skill_opt_batch_audit_dynamic_discovery_and_dedup(tmp_path: Path, monkeypatch):
    """验证 SkillOptService 批量体检支持全域动态探测与同名去重。"""
    mock_home = tmp_path / "mock_home"
    mock_home.mkdir()
    mock_cwd = tmp_path / "mock_cwd"
    mock_cwd.mkdir()
    monkeypatch.setattr(Path, "home", lambda: mock_home)
    monkeypatch.setattr(Path, "cwd", lambda: mock_cwd)

    dir_a = tmp_path / "skills_a"
    dir_b = tmp_path / "skills_b"
    dir_a.mkdir()
    dir_b.mkdir()

    # 在 dir_a 创建 skill-1 和 skill-2
    s1_a = dir_a / "skill-1"
    s1_a.mkdir()
    (s1_a / "SKILL.md").write_text("---\nname: skill-1\ndescription: A valid skill.\n---\n## When not to use\nNever\n```bash\necho 1\n```\n", encoding="utf-8")

    s2_a = dir_a / "skill-2"
    s2_a.mkdir()
    (s2_a / "SKILL.md").write_text("---\nname: skill-2\ndescription: Second valid skill.\n---\n## When not to use\nNever\n```bash\necho 2\n```\n", encoding="utf-8")

    # 在 dir_b 创建同名 skill-1 (应去重) 和 skill-3
    s1_b = dir_b / "skill-1"
    s1_b.mkdir()
    (s1_b / "SKILL.md").write_text("---\nname: skill-1\ndescription: Duplicate skill.\n---\n", encoding="utf-8")

    s3_b = dir_b / "skill-3"
    s3_b.mkdir()
    (s3_b / "SKILL.md").write_text("---\nname: skill-3\ndescription: Third valid skill.\n---\n## When not to use\nNever\n```bash\necho 3\n```\n", encoding="utf-8")

    # 1. 显式指定目录审计：只扫描 dir_a
    svc = SkillOptService()
    summary_explicit = svc.batch_audit_skills(skills_dir=str(dir_a))
    assert summary_explicit.total_audited == 2

    # 2. 设置环境变量探测链，且 mock_home 为空
    monkeypatch.setenv("OPENVIKING_SKILLS_PATH", str(dir_a))
    monkeypatch.setenv("SKILLS_ROOT", str(dir_b))

    summary = svc.batch_audit_skills()

    # 应该扫描到 3 个去重后的技能 (skill-1, skill-2, skill-3)
    assert summary.total_audited == 3
    names = {r.skill_name for r in summary.results}
    assert names == {"skill-1", "skill-2", "skill-3"}
    assert summary.avg_score > 0


def test_skill_opt_ahe_gate_exception_resilience():
    """验证 SkillOptService.optimize_content 在 AHE 抛出异常时平滑降级而非 500 崩溃。"""
    svc = SkillOptService()
    req = SkillOptOptimizeRequest(
        skill_content="---\nname: test-skill\ndescription: simple skill\n---\nBody text\n",
        enable_ahe_gate=True,
    )

    with patch("openviking.core.ahe_engine.AHEEngine.get_instance", side_effect=RuntimeError("Simulated AHE crash")):
        res = svc.optimize_content(req)
        assert res.ahe_gate_passed is False
        assert "AHE gate execution failed: Simulated AHE crash" in str(res.ahe_blocked_reason)
        # 优化正文依然成功生成，服务未崩溃
        assert "optimized_content" in res.model_dump()
        assert res.optimized_score >= res.original_score
