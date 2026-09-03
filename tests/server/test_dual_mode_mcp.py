# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

"""Unit tests for Dual-Mode MCP Architecture (Core vs Satellite mode).

Verifies that:
1. Core mode registers the full 50+ tools including system control, backup, and mutation.
2. Satellite mode strictly registers safe-subset tools (find, search, smart_read, record_lesson, etc.)
   and physically skips registering sensitive / destructive tools.
3. Satellite mode HTTP client enforces network jitter retry with exponential backoff.
"""

import importlib
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from urllib.error import URLError


def _reload_mcp_module(mode: str):
    """Dynamically load or reload the mcp_openviking_server module in a specific mode."""
    mcp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../mcp-openviking"))
    if mcp_dir not in sys.path:
        sys.path.insert(0, mcp_dir)

    os.environ["OPENVIKING_MCP_MODE"] = mode
    if "mcp_openviking_server" in sys.modules:
        mod = importlib.reload(sys.modules["mcp_openviking_server"])
    else:
        mod = importlib.import_module("mcp_openviking_server")
    return mod


def test_dual_mode_core_registers_all_tools():
    """Verify Core Mode registers 50+ tools including sensitive operations."""
    mod = _reload_mcp_module("core")
    registered_tools = {tool.name for tool in mod.mcp._tool_manager.list_tools()}

    # Core must have 50+ tools
    assert len(registered_tools) >= 50

    # Core must have destructive/management tools
    assert "openviking_server_control" in registered_tools
    assert "openviking_backup" in registered_tools
    assert "openviking_restore" in registered_tools
    assert "openviking_delete_resource" in registered_tools
    assert "openviking_find" in registered_tools
    assert "openviking_record_evolution_lesson" in registered_tools


def test_dual_mode_satellite_registers_safe_subset_only():
    """Verify Satellite Mode strictly isolates sensitive tools and registers only safe tools."""
    mod = _reload_mcp_module("satellite")
    registered_tools = {tool.name for tool in mod.mcp._tool_manager.list_tools()}

    # Satellite mode must have exact whitelist subset (<= 20 tools)
    assert len(registered_tools) <= 20

    # Must contain essential remote recall and self-evolution tools
    assert "openviking_find" in registered_tools
    assert "openviking_search" in registered_tools
    assert "openviking_smart_read" in registered_tools
    assert "openviking_record_evolution_lesson" in registered_tools
    assert "openviking_health" in registered_tools
    assert "openviking_ping" in registered_tools

    # Must NOT contain destructive or system-level tools
    assert "openviking_server_control" not in registered_tools
    assert "openviking_backup" not in registered_tools
    assert "openviking_restore" not in registered_tools
    assert "openviking_delete_resource" not in registered_tools
    assert "openviking_server_init" not in registered_tools


def test_dual_mode_satellite_http_retry_resilience():
    """Verify Satellite Mode retries on transient network errors (FRP jitter)."""
    mod = _reload_mcp_module("satellite")
    client = mod.OpenVikingHTTPClient()

    attempt_count = 0

    def fake_urlopen(req, timeout):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise URLError("FRP Tunnel Timeout")
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"status": "ok", "recovered": true}'
        mock_resp.__enter__.return_value = mock_resp
        return mock_resp

    with patch("mcp_openviking_server.urlopen", side_effect=fake_urlopen):
        with patch("time.sleep", return_value=None):
            resp = client._request("GET", "/api/v1/health")
            assert resp.get("status") == "ok"
            assert resp.get("recovered") is True
            assert attempt_count == 3
