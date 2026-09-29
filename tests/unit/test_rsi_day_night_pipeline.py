# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Card-20G: RSI Day-Night Real Trajectory Collection & Dual-Split Regression Gate Pipeline.
(Card-RSI-DayNight-RealCollection-And-Gate / v1.5.83)
"""

from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.core.rsi_day_night_engine import DualSplitGateResult, RSIDayNightEngine, RSIPhase
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.rsi import router as rsi_router
from openviking.storage.queuefs.session_commit_msg import SessionCommitMsg
from openviking.storage.queuefs.session_commit_processor import SessionCommitProcessor
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture(autouse=True)
def reset_rsi():
    RSIDayNightEngine.reset_instance()
    yield
    RSIDayNightEngine.reset_instance()


def test_rsi_trajectory_collection_and_nighttime_cycle():
    """Verify trajectory recording, credit evaluation, and nighttime dual-split gate."""
    engine = RSIDayNightEngine.get_instance()
    assert engine.current_phase == RSIPhase.DAYTIME_COLLECTION

    # 1. Record daytime turns
    session_id = "sess_daytime_001"
    engine.record_turn(session_id, {"turn_index": 0, "role": "user", "content": "检查集群状态"})
    engine.record_turn(
        session_id,
        {
            "turn_index": 1,
            "role": "assistant",
            "content": "正在执行检查",
            "action": "openviking_find",
            "success": True,
        },
    )

    summary = engine.summary()
    assert summary["total_trajectories_collected"] == 1
    assert summary["total_turns_collected"] == 2

    # 2. Run nighttime cycle with normal pass
    night_res = engine.run_nighttime_cycle(
        baseline_holdout_pass_rate=0.75,
        train_results=[True, True, True, True],
        holdout_results=[True, True, True, True],
    )
    assert night_res["status"] == "completed"
    assert night_res["gate_passed"] is True
    assert night_res["regression_detected"] is False

    # 3. Run nighttime cycle with regression: holdout degrades below baseline -> BLOCKED
    blocked_res = engine.run_nighttime_cycle(
        baseline_holdout_pass_rate=0.85,
        train_results=[True, True],
        holdout_results=[True, False, False, False],  # 25% < 85%
    )
    assert blocked_res["gate_passed"] is False
    assert blocked_res["regression_detected"] is True
    assert "BLOCKED" in blocked_res["details"]


@pytest.mark.asyncio
async def test_session_commit_processor_rsi_wiring():
    """Verify that SessionCommitProcessor feeds real session turns into RSIDayNightEngine."""
    engine = RSIDayNightEngine.get_instance()

    session = MagicMock()
    session.session_id = "test_rsi_autowired_sess_888"

    mock_msg1 = MagicMock()
    mock_msg1.role = "user"
    mock_msg1.content = "计算 2080Ti 与 3070 算力配比"
    mock_msg1.parts = []
    mock_msg1.tool_calls = None

    mock_msg2 = MagicMock()
    mock_msg2.role = "assistant"
    mock_msg2.content = "配比计算完成，已分配。"
    mock_msg2.parts = []
    mock_msg2.tool_calls = [{"name": "compute", "arguments": {}}]

    session._read_archive_messages = AsyncMock(return_value=[mock_msg1, mock_msg2])

    commit_msg = SessionCommitMsg(
        session_id="test_rsi_autowired_sess_888",
        session_uri="viking://sessions/test_rsi_autowired_sess_888",
        archive_uri="viking://archives/test_rsi_autowired_sess_888/arc_001",
        task_id="task_rsi_001",
        user={"account_id": "default", "user_id": "commander"},
    )

    processor = SessionCommitProcessor(session_service=MagicMock(), service_loop=MagicMock())
    await processor._record_hermes_experience(session, commit_msg)

    # Check that turns arrived in RSIDayNightEngine
    assert "test_rsi_autowired_sess_888" in engine._trajectories
    turns = engine._trajectories["test_rsi_autowired_sess_888"]
    assert len(turns) == 2
    assert "2080Ti" in turns[0]["content"]


def test_rsi_nighttime_cycle_api():
    """Verify REST API /api/v1/rsi/cycle/run_nighttime and /api/v1/rsi/status."""
    app = FastAPI()
    app.include_router(rsi_router)
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    # Trigger nighttime cycle endpoint
    resp = client.post(
        "/api/v1/rsi/cycle/run_nighttime",
        json={
            "baseline_holdout_pass_rate": 0.8,
            "train_results": [True, True, True],
            "holdout_results": [True, True, True, True],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["gate_passed"] is True

    # Check /api/v1/rsi/status
    status_resp = client.get("/api/v1/rsi/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["dual_split_verifications"] >= 1
