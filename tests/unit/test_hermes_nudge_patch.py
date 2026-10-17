# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Hermes Nudge Engine and Patch Engine.

测试套件:
  test_nudge_async_review           Periodic Nudge 异步轨迹复盘
  test_patch_micro_surgery_limit    补丁 ≤30 行硬性门禁拦截
  test_patch_apply_and_revert       微补丁原子化应用与一键回滚
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from openviking.core.hermes_experience_store import HermesExperienceStore
from openviking.core.hermes_nudge_engine import HermesNudgeEngine
from openviking.core.hermes_patch_engine import HermesPatchEngine, MAX_PATCH_LINES


def test_nudge_async_review():
    """测试 Nudge 异步副进程复盘流程。"""
    store = HermesExperienceStore.get_instance()
    nudge = HermesNudgeEngine.get_instance()

    session_id = "sess-nudge-test"
    store.record_message(session_id=session_id, role="user", content="Build the project")
    store.record_message(session_id=session_id, role="assistant", content="Error: compilation failed")

    res = nudge.trigger_nudge(session_id)
    assert res["status"] == "queued"

    # 等待后台 worker 消费当前 session
    target_rec = None
    for _ in range(30):
        recent = nudge.list_recent_reviews(limit=50)
        matching = [r for r in recent if r.session_id == session_id]
        if matching:
            target_rec = matching[0]
            break
        time.sleep(0.1)

    status = nudge.get_status()
    assert status["completed_reviews"] >= 1
    assert target_rec is not None
    assert target_rec.session_id == session_id
    assert target_rec.proposed_patch_needed is True


def test_patch_micro_surgery_limit():
    """测试微补丁 ≤30 行硬性门禁拦截 (防止 Edit 模式全量重写)。"""
    patch_engine = HermesPatchEngine.get_instance()

    # 生成超过 30 行的大补丁
    huge_content = "\n".join([f"line_{i} = {i}" for i in range(MAX_PATCH_LINES + 5)])

    with pytest.raises(ValueError) as excinfo:
        patch_engine.propose_patch(
            skill_name="test-skill",
            file_path="fake/path.py",
            target_content="old_line = 1",
            replacement_content=huge_content,
            reason="Exceeding limit test",
        )
    assert "exceeds micro-surgery limit" in str(excinfo.value)


def test_patch_apply_and_revert():
    """测试微补丁原子化应用与一键回滚。"""
    patch_engine = HermesPatchEngine.get_instance()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("def foo():\n    return 41\n")
        temp_file = f.name

    try:
        # 1. 提议微补丁 (≤30行)
        patch = patch_engine.propose_patch(
            skill_name="math-skill",
            file_path=temp_file,
            target_content="    return 41",
            replacement_content="    return 42",
            reason="Fix return value",
        )
        assert patch.status == "proposed"
        assert patch.target_line_count == 1
        assert patch.replacement_line_count == 1

        # 2. 应用微补丁
        applied = patch_engine.apply_patch(patch.patch_id)
        assert applied.status == "applied"
        assert applied.applied_at is not None
        content_after_apply = Path(temp_file).read_text(encoding="utf-8")
        assert "return 42" in content_after_apply

        # 3. 回滚微补丁
        reverted = patch_engine.revert_patch(patch.patch_id)
        assert reverted.status == "reverted"
        assert reverted.reverted_at is not None
        content_after_revert = Path(temp_file).read_text(encoding="utf-8")
        assert "return 41" in content_after_revert
    finally:
        Path(temp_file).unlink(missing_ok=True)
