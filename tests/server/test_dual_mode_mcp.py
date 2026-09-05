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
import json
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

    # Must contain essential remote recall, code search, and self-evolution tools
    expected_satellite_tools = {
        "openviking_find",
        "openviking_search",
        "openviking_smart_read",
        "openviking_read",
        "openviking_store",
        "openviking_write",
        "openviking_code_search",
        "openviking_code_outline",
        "openviking_code_expand",
        "openviking_grep",
        "openviking_tree",
        "openviking_skills",
        "openviking_get_relations",
        "openviking_ping",
        "openviking_health",
        "openviking_record_evolution_lesson",
    }
    for tool_name in expected_satellite_tools:
        assert tool_name in registered_tools, f"Expected {tool_name} in satellite tools"

    # Verify strong attention trigger header in openviking_find docstring
    find_tool = next(t for t in mod.mcp._tool_manager.list_tools() if t.name == "openviking_find")
    assert "【Mandatory First Step / 开局必调】" in (find_tool.description or "")

    # Must NOT contain destructive or system-level tools
    assert "openviking_server_control" not in registered_tools
    assert "openviking_backup" not in registered_tools
    assert "openviking_restore" not in registered_tools
    assert "openviking_delete_resource" not in registered_tools
    assert "openviking_server_init" not in registered_tools
    assert "openviking_privacy" not in registered_tools


def test_openviking_ping_metadata_handshake():
    """Verify openviking_ping returns mode, auth, tools count and platform info."""
    mod = _reload_mcp_module("satellite")
    res_str = mod.openviking_ping()
    data = json.loads(res_str)

    assert data.get("mode") == "satellite"
    assert "tools_count" in data
    assert "platform" in data
    assert "authenticated" in data



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


def test_record_evolution_lesson_dual_writes_to_master_memory(tmp_path):
    """Verify openviking_record_evolution_lesson appends to local skill and mirrors to Master Memory."""
    mod = _reload_mcp_module("satellite")
    
    # 模拟目标 skill 路径
    test_skill_dir = tmp_path / "skills" / "test-skill"
    test_skill_dir.mkdir(parents=True)
    test_skill_file = test_skill_dir / "SKILL.md"
    test_skill_file.write_text("# Test Skill\nInitial content\n", encoding="utf-8")

    written_payloads = []

    def fake_post(endpoint, payload):
        written_payloads.append((endpoint, payload))
        return {"status": "ok", "result": {"uri": payload.get("uri")}}

    orig_exists = os.path.exists
    with patch("mcp_openviking_server.http_client.post", side_effect=fake_post):
        with patch("mcp_openviking_server.os.path.exists", side_effect=lambda p: str(p) == str(test_skill_file) or orig_exists(p)):
            res_str = mod.openviking_record_evolution_lesson(
                skill_name=str(test_skill_file),
                lesson_title="测试防丢镜像",
                context="单元测试验证",
                reflection="验证双写机制",
                lesson="知识永远不回滚"
            )

    res = json.loads(res_str)
    assert res.get("status") == "ok"
    assert "master_memory_uri" in res
    assert res["master_memory_uri"].startswith("viking://resources/master_memory/evolution_lessons/")
    assert res["mirror_status"] == "synced"

    # 验证本地技能内容被追加
    assert "测试防丢镜像" in test_skill_file.read_text(encoding="utf-8")
    assert "知识永远不回滚" in test_skill_file.read_text(encoding="utf-8")

    # 验证向 Master Memory 提交了双写请求
    assert len(written_payloads) == 1
    endpoint, payload = written_payloads[0]
    assert endpoint == "/api/v1/content/write"
    assert payload["uri"] == res["master_memory_uri"]
    assert "测试防丢镜像" in payload["content"]
    assert "知识永远不回滚" in payload["content"]

