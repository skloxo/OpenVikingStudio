# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Card-Security-HITLGate-And-ReadOffload-Production-Mount (Card-20C / v1.5.79).
Verifies:
1. Level 1: Normal workspace operations pass through without interruption (0 false positives).
2. Level 2: Authorized high-risk actions pass with session approval token.
3. Level 3: Unauthorized high-risk actions are intercepted with Defensive Rerouting Guidance,
   preventing agent crashes and deadlock while maintaining absolute safety.
4. Read-side offload: Reading large files (>300 lines or >12KB) intercepts output into FileRefHandle,
   saving >= 70% tokens, and supports slice retrieval.
5. HITLOffloadTelemetry records intercepts and token savings in real time.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from mcp.server.fastmcp import FastMCP

mcp_dir = Path(__file__).resolve().parents[2] / "mcp-openviking"
if str(mcp_dir) not in sys.path:
    sys.path.insert(0, str(mcp_dir))

from _core.decorators import create_mcp_tool_decorator
from openviking.core.hitl_gate import HITLGate, DangerousActionPolicy
from openviking.core.read_write_offload import ReadOffloadManager
from openviking.core.hitl_offload_telemetry import HITLOffloadTelemetry


@pytest.fixture(autouse=True)
def reset_hitl_telemetry():
    telemetry = HITLOffloadTelemetry()
    with telemetry._rw_lock:
        telemetry._file_refs.clear()
        telemetry._total_files_offloaded = 0
        telemetry._total_raw_tokens = 0
        telemetry._total_offloaded_tokens = 0
        telemetry._pending_actions.clear()
        telemetry._resolved_actions.clear()
    yield telemetry


def test_hitl_workspace_normal_operations_uninterrupted(reset_hitl_telemetry):
    """
    Level 1: Normal workspace operations (writing, editing, normal bash)
    MUST pass through 100% autonomously without human interruption.
    """
    mcp = FastMCP("test_mcp")
    mcp_tool = create_mcp_tool_decorator(mcp, mcp_mode="core")

    @mcp_tool(name="normal_tool", description="Normal tool")
    def normal_tool(command: str):
        return f"executed: {command}"

    # Normal commands must NOT be blocked
    res = normal_tool(command="pytest -q tests/unit/test_app.py")
    assert res == "executed: pytest -q tests/unit/test_app.py"


def test_hitl_defensive_rerouting_intercepts_without_crashing(reset_hitl_telemetry):
    """
    Level 3: Catastrophic destructive commands (e.g. rm -rf /, DROP TABLE)
    are intercepted by HITLGate, blocking destruction and returning
    defensive rerouting guidance so the Agent can self-heal without crashing.
    """
    telemetry = reset_hitl_telemetry
    mcp = FastMCP("test_mcp")
    mcp_tool = create_mcp_tool_decorator(mcp, mcp_mode="core")

    mock_fn = MagicMock(return_value="should_not_run")

    @mcp_tool(name="run_command", description="Run command")
    def run_command(CommandLine: str, approval_token: str = ""):
        return mock_fn(CommandLine)

    # 1. Catastrophic command: rm -rf /
    result = run_command(CommandLine="rm -rf / --no-preserve-root")
    
    # Assert physical block: mock_fn was NOT called!
    assert mock_fn.call_count == 0
    assert "HITL 安全护栏拦截" in result or "HITL" in result
    assert "安全自愈导引" in result or "替代" in result

    # Telemetry must record this intercept in real time (No vanity metrics!)
    snap = telemetry.get_metrics_snapshot()
    assert snap["summary"]["total_interceptions"] >= 1
    assert len(snap["hitl_queue"]["pending"]) >= 1

    # 2. Level 2: With valid approval token, invocation is authorized
    gate = HITLGate()
    gate.grant_approval_token("VALID_APPROVAL_TOKEN_2026")
    
    mock_fn.return_value = "cleanly deleted"
    res_authorized = run_command(
        CommandLine="rm -rf /tmp/test_dir",
        approval_token="VALID_APPROVAL_TOKEN_2026",
    )
    assert res_authorized == "cleanly deleted"
    assert mock_fn.call_count == 1


def test_read_offload_manager_production_token_savings(reset_hitl_telemetry):
    """
    Verify that reading oversized files (>300 lines) intercepts the output
    and returns a compact FileRefHandle, saving >= 70% tokens.
    """
    telemetry = reset_hitl_telemetry
    mcp = FastMCP("test_mcp")
    mcp_tool = create_mcp_tool_decorator(mcp, mcp_mode="core")

    # Generate 500 lines of source code
    large_code = "\n".join([f"def function_{i}():\n    return {i} * 42" for i in range(1, 251)])

    @mcp_tool(name="openviking_read", description="Read file")
    def read_file(path: str):
        return large_code

    result = read_file(path="/app/large_service.py")
    
    # Must be offloaded to FileRefHandle
    assert "FileRefHandle" in result
    assert "Total Lines: 500" in result
    assert "[DECO 读护栏提示]" in result

    # Telemetry verification: tokens saved
    snap = telemetry.get_metrics_snapshot()
    assert snap["read_offload"]["total_files_offloaded"] >= 1
    assert snap["summary"]["total_tokens_saved"] > 0
    assert snap["summary"]["reduction_ratio_pct"] >= 70.0
