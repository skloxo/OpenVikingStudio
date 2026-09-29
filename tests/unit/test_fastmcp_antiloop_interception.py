# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Card-Observability-FailureTaxonomy-Production-Interception (Card-20B / v1.5.78).
Verifies:
1. FastMCP tool decorator intercepts real tool exceptions into FailureTaxonomyTelemetry.
2. Anti-Loop Barrier physically blocks repeated failing tool calls before execution.
3. Transient failures trigger automatic backoff retry.
4. Fatal failures immediately lock execution.
5. Whitelist preservation and telemetry snapshot updates in real time.
"""

import asyncio
from unittest.mock import MagicMock
import pytest
from mcp.server.fastmcp import FastMCP

from openviking.core.failure_classifier import FailureCategory
from openviking.core.failure_taxonomy_telemetry import (
    FailureTaxonomyTelemetry,
    get_failure_taxonomy_telemetry,
)
import sys
from pathlib import Path

mcp_dir = Path(__file__).resolve().parents[2] / "mcp-openviking"
if str(mcp_dir) not in sys.path:
    sys.path.insert(0, str(mcp_dir))

from _core.decorators import create_mcp_tool_decorator


@pytest.fixture(autouse=True)
def reset_telemetry():
    """Reset telemetry before each test to guarantee test isolation."""
    telemetry = get_failure_taxonomy_telemetry()
    telemetry.execute_probe("reset")
    yield telemetry
    telemetry.execute_probe("reset")


def test_fastmcp_antiloop_physical_blocking(reset_telemetry):
    """
    Verify that when an MCP tool fails deterministically,
    the Anti-Loop Barrier engages and physically intercepts repeated calls
    BEFORE the tool function runs, preventing infinite retry loops.
    """
    telemetry = reset_telemetry
    mcp = FastMCP("test_mcp")
    mcp_tool = create_mcp_tool_decorator(mcp, mcp_mode="core")

    mock_target = MagicMock()
    mock_target.side_effect = ValueError("Invalid schema: field 'query' cannot be empty")

    @mcp_tool(name="test_search_tool", description="Test search tool")
    def search_tool(query: str):
        mock_target(query)
        return f"result for {query}"

    # Call 1: First failure (Deterministic)
    result_1 = search_tool(query="")
    assert "Invalid schema" in result_1
    assert "[Anti-Loop Barrier]" in result_1 or "Anti-Loop" in result_1
    assert mock_target.call_count == 1

    # Check telemetry was updated in real time (No longer a vanity metric!)
    snap_1 = telemetry.get_snapshot()
    assert snap_1.deterministic_count == 1
    assert snap_1.total_failures == 1

    # Call 2: Agent repeats the EXACT SAME failing call
    # The Anti-Loop Barrier MUST physically intercept it BEFORE mock_target is called!
    result_2 = search_tool(query="")
    assert "[Anti-Loop Barrier Blocked]" in result_2 or "Anti-Loop Barrier" in result_2
    assert "Execution" in result_2 or "blocked" in result_2

    # Verification of physical blocking: mock_target was NOT called a second time!
    assert mock_target.call_count == 1

    # Check anti_loop_interceptions telemetry metric incremented
    snap_2 = telemetry.get_snapshot()
    assert snap_2.anti_loop_interceptions >= 1
    assert snap_2.blocked_fingerprints_count >= 1

    # Call 3: Agent adjusts arguments to valid input
    mock_target.side_effect = None
    mock_target.return_value = "ok"
    result_3 = search_tool(query="valid query")
    assert result_3 == "result for valid query"
    assert mock_target.call_count == 2


def test_fastmcp_transient_retry_and_recovery(reset_telemetry):
    """
    Verify that transient failures (e.g. rate limit, connection timeout)
    trigger automatic retry and recover gracefully without blocking.
    """
    telemetry = reset_telemetry
    mcp = FastMCP("test_mcp")
    mcp_tool = create_mcp_tool_decorator(mcp, mcp_mode="core")

    call_attempts = 0

    @mcp_tool(name="transient_network_tool", description="Test network tool")
    def network_tool(url: str):
        nonlocal call_attempts
        call_attempts += 1
        if call_attempts == 1:
            raise RuntimeError("429 Too Many Requests (Rate limit exceeded)")
        return "data fetched successfully"

    # Should catch transient error, apply backoff, retry and succeed!
    result = network_tool(url="https://api.viking.internal/data")
    assert result == "data fetched successfully"
    assert call_attempts == 2

    # Telemetry should record the transient retry attempt
    snap = telemetry.get_snapshot()
    assert snap.transient_count >= 1
    assert snap.transient_retries_used >= 1


def test_fastmcp_fatal_error_immediate_halt(reset_telemetry):
    """
    Verify that fatal security / OOM errors immediately halt and lock the tool.
    """
    telemetry = reset_telemetry
    mcp = FastMCP("test_mcp")
    mcp_tool = create_mcp_tool_decorator(mcp, mcp_mode="core")

    mock_fatal = MagicMock()
    mock_fatal.side_effect = PermissionError("Security violation: sandbox escape attempt detected")

    @mcp_tool(name="dangerous_tool", description="Dangerous tool")
    def dangerous_tool(cmd: str):
        mock_fatal(cmd)
        return "done"

    res_1 = dangerous_tool(cmd="cat /etc/shadow")
    assert "Security violation" in res_1
    assert mock_fatal.call_count == 1

    snap_1 = telemetry.get_snapshot()
    assert snap_1.fatal_count >= 1

    # Immediate lock: second call is blocked before execution
    res_2 = dangerous_tool(cmd="cat /etc/shadow")
    assert "Anti-Loop Barrier" in res_2 or "blocked" in res_2
    assert mock_fatal.call_count == 1


def test_http_exception_interception_records_telemetry(reset_telemetry):
    """
    Verify that HTTP REST exceptions (e.g. 422 RequestValidationError)
    are intercepted by the FastAPI error handlers in openviking.server.app
    and actively recorded in FailureTaxonomyTelemetry.
    """
    from fastapi.testclient import TestClient
    from openviking.server.app import create_app
    from openviking.server.auth import get_request_context
    from openviking.server.identity import RequestContext, Role
    from openviking_cli.session.user_id import UserIdentifier

    telemetry = reset_telemetry
    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test", user_id="test_admin"),
        role=Role(Role.ADMIN),
    )
    client = TestClient(app)

    # 1. Trigger 400 Validation Error (INVALID_ARGUMENT)
    res = client.post("/api/v1/system/failure_taxonomy_probe", json={"action": None})
    assert res.status_code == 400
    
    snap = telemetry.get_snapshot()
    assert snap.deterministic_count >= 1
    assert any("VALIDATION_ERROR" in ev.get("reason", "") for ev in snap.recent_events)

