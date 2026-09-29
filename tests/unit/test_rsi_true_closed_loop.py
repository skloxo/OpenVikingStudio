# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""针对 Card-26 (v1.5.90) 的 RSI 昼夜双轮真闭环单元测试套件。

涵盖:
  1. 白昼轨迹 SQLite 物理落盘与重启后自愈恢复 (100% 恢复率);
  2. RSIHoldoutBenchmark 五大核心不变量真实盲测与拦截能力;
  3. 夜间做梦消除 [True] * ... 假装通过，全链路真实数据驱动;
  4. 技能文档 # EVOLVE-BLOCK 物理受控回填与退化阻断门禁;
  5. 门禁历史与演进履历 SQLite 持久化审计。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from openviking.core.rsi_day_night_engine import DualSplitGateResult, RSIDayNightEngine, RSIPhase
from openviking.core.rsi_holdout_benchmark import RSIHoldoutBenchmark
from openviking.core.rsi_trajectory_store import RSITrajectoryStore
from openviking.core.trainable_skill_policy import TrainableSkillDocument


@pytest.fixture
def clean_store_and_engine(tmp_path: Path):
    RSIDayNightEngine.reset_instance()
    RSITrajectoryStore.reset_instance()
    db_file = tmp_path / "test_rsi.db"
    store = RSITrajectoryStore.get_instance(db_file)
    engine = RSIDayNightEngine.get_instance(store=store)
    yield store, engine, db_file
    RSIDayNightEngine.reset_instance()
    RSITrajectoryStore.reset_instance()


def test_sqlite_trajectory_persistence_and_recovery(clean_store_and_engine):
    """测试白昼轨迹 SQLite 物理落盘与跨实例 100% 恢复。"""
    store, engine, db_file = clean_store_and_engine

    sess1 = "sess_daytime_alpha"
    sess2 = "sess_daytime_beta"

    # 白昼记录多回合
    engine.record_turn(sess1, {"turn_id": 0, "role": "user", "content": "analyze code", "student_log_prob": -1.2, "teacher_log_prob": -0.4})
    engine.record_turn(sess1, {"turn_id": 1, "role": "assistant", "content": "done", "student_log_prob": -0.8, "teacher_log_prob": -0.2})
    engine.record_turn(sess2, {"turn_id": 0, "role": "user", "content": "run test", "student_log_prob": -0.5, "teacher_log_prob": -0.1})

    summary_before = engine.summary()
    assert summary_before["total_trajectories_collected"] == 2
    assert summary_before["total_turns_collected"] == 3

    # 模拟服务重启：重置单例并用同一个 db 重新实例化
    RSIDayNightEngine.reset_instance()
    recovered_engine = RSIDayNightEngine(store=store, auto_load_db=True)

    summary_after = recovered_engine.summary()
    assert summary_after["total_trajectories_collected"] == 2
    assert summary_after["total_turns_collected"] == 3

    # 验证轨迹内容完整性
    turns1 = recovered_engine._trajectories.get(sess1)
    assert turns1 is not None and len(turns1) == 2
    assert turns1[0]["turn_id"] == 0
    assert turns1[1]["content"] == "done"


def test_rsi_holdout_benchmark_invariants():
    """测试 RSIHoldoutBenchmark 五大核心不变量与退化检测。"""
    valid_skill = """---
name: sample-skill
description: A clean test skill
---
# HEADER
# EVOLVE-BLOCK-START
def execute(ctx):
    return ctx.action()
# EVOLVE-BLOCK-END
# FOOTER
"""
    doc = TrainableSkillDocument(valid_skill, skill_name="sample-skill")
    rep = RSIHoldoutBenchmark.run_holdout_suite(doc)
    assert rep.total_cases == 5
    assert rep.passed_cases == 5
    assert rep.pass_rate == 1.0

    # 1. 凭据泄漏拦截测试 (Invariant 2)
    fake_token = "ghp_" + ("x" * 25)
    leaky_text = valid_skill + f"\nTOKEN = '{fake_token}'"
    rep_leak = RSIHoldoutBenchmark.run_holdout_suite(candidate_text=leaky_text)
    leak_case = next(c for c in rep_leak.results if c.name == "invariant_zero_secrets")
    assert leak_case.passed is False

    # 2. NO GREEN EVER 拦截测试 (Invariant 4)
    green_text = valid_skill + "\n<div className=\"bg-green-500 text-green-100\">Bad</div>"
    rep_green = RSIHoldoutBenchmark.run_holdout_suite(candidate_text=green_text)
    green_case = next(c for c in rep_green.results if c.name == "invariant_no_green_ever")
    assert green_case.passed is False

    # 3. 超过 500 行安全红线拦截测试 (Invariant 3)
    long_text = valid_skill + "\n# filler\n" * 550
    rep_long = RSIHoldoutBenchmark.run_holdout_suite(candidate_text=long_text)
    long_case = next(c for c in rep_long.results if c.name == "invariant_complexity_guard")
    assert long_case.passed is False


def test_run_nighttime_cycle_real_evaluation(clean_store_and_engine):
    """测试夜间做梦使用真实 Holdout 盲测与真实会话信用分配。"""
    store, engine, _ = clean_store_and_engine

    # 收集一条正常轨迹与一条失误轨迹
    engine.record_turn("s1", {"student_log_prob": -1.0, "teacher_log_prob": -0.2})
    engine.record_turn("s2", {"student_log_prob": -0.3, "teacher_log_prob": -0.2})

    # 不传任何伪造结果，全自动真实跑
    cycle = engine.run_nighttime_cycle(baseline_holdout_pass_rate=0.8)

    assert cycle["status"] == "completed"
    assert cycle["evaluated_sessions"] == 2
    assert "benchmark_report" in cycle and cycle["benchmark_report"] is not None
    assert cycle["gate_passed"] is True
    assert cycle["regression_detected"] is False

    # 检查 SQLite 门禁历史落盘
    history = store.get_gate_history(limit=5)
    assert len(history) == 1
    assert history[0]["passed"] is True
    assert history[0]["baseline_holdout_pass_rate"] == 0.8


def test_physical_evolve_skill_policy_write_back(tmp_path: Path, clean_store_and_engine):
    """测试物理受控演进闭环: 门禁通过则真实写入文件，门禁退化则物理阻断。"""
    store, engine, _ = clean_store_and_engine

    skill_file = tmp_path / "SKILL.md"
    initial_content = """---
name: evolving-skill
description: Test evolve
---
# UNTOUCHED FROZEN HEADER
# EVOLVE-BLOCK-START
def run():
    print("v1")
# EVOLVE-BLOCK-END
# UNTOUCHED FROZEN FOOTER
"""
    skill_file.write_text(initial_content, encoding="utf-8")

    # 场景 1: 合法演进 -> 通过双 Split 门禁并物理写入
    evolve_res = engine.evolve_skill_policy(
        target_skill_path=skill_file,
        block_index=0,
        new_content="def run():\n    print('v2 optimized')",
        baseline_holdout_pass_rate=0.8,
    )
    assert evolve_res["status"] == "evolved_and_persisted"
    assert evolve_res["gate_passed"] is True

    # 验证物理文件内容已更新
    saved_text = skill_file.read_text(encoding="utf-8")
    assert "v2 optimized" in saved_text
    assert "# UNTOUCHED FROZEN HEADER" in saved_text

    # 场景 2: 注入破坏性退化 (含有禁用的绿色) -> 门禁阻断，拒绝物理写盘
    poison_res = engine.evolve_skill_policy(
        target_skill_path=skill_file,
        block_index=0,
        new_content="className = 'bg-green-500'",  # 触犯 NO GREEN EVER
        baseline_holdout_pass_rate=0.9,  # 提高要求触发 regression
    )
    assert poison_res["status"] == "blocked_regression_prevented"
    assert poison_res["gate_passed"] is False

    # 验证物理文件依然保持 v2，未被绿色污染篡改
    current_text = skill_file.read_text(encoding="utf-8")
    assert "bg-green-500" not in current_text
    assert "v2 optimized" in current_text


def test_rsi_api_endpoints(clean_store_and_engine, tmp_path: Path):
    """测试 /api/v1/rsi/trajectories, /gates/history 以及 /evolve REST 接口。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from openviking.server.routers.rsi import router as rsi_router

    store, engine, _ = clean_store_and_engine
    engine.record_turn("sess_api_01", {"turn_id": 0, "content": "hi", "student_log_prob": -0.2, "teacher_log_prob": -0.1})

    app = FastAPI()
    app.include_router(rsi_router)
    client = TestClient(app)

    # 1. GET /api/v1/rsi/trajectories
    r_traj = client.get("/api/v1/rsi/trajectories")
    assert r_traj.status_code == 200
    traj_data = r_traj.json()
    assert traj_data["total_sessions"] >= 1
    assert any(s["session_id"] == "sess_api_01" for s in traj_data["sessions"])

    # 2. Trigger nighttime cycle to generate gate history
    r_cycle = client.post("/api/v1/rsi/cycle/run_nighttime", json={})
    assert r_cycle.status_code == 200

    # 3. GET /api/v1/rsi/gates/history
    r_gates = client.get("/api/v1/rsi/gates/history")
    assert r_gates.status_code == 200
    gates_data = r_gates.json()
    assert len(gates_data) >= 1
    assert "passed" in gates_data[0]

    # 4. POST /api/v1/rsi/evolve
    skill_file = tmp_path / "API_SKILL.md"
    skill_file.write_text("""# TITLE\n# EVOLVE-BLOCK-START\ndef step(): pass\n# EVOLVE-BLOCK-END\n# END\n""", encoding="utf-8")
    r_evolve = client.post("/api/v1/rsi/evolve", json={
        "target_skill_path": str(skill_file),
        "block_index": 0,
        "new_content": "def step(): return True",
        "baseline_holdout_pass_rate": 0.8,
    })
    assert r_evolve.status_code == 200
    evolve_data = r_evolve.json()
    assert evolve_data["status"] == "evolved_and_persisted"
    assert evolve_data["gate_passed"] is True

