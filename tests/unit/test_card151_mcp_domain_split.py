# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Card-151: FastMCP 工具分域解耦单元测试 (TDD 视网膜门禁)
验证 58 工具精确解耦为 37 (记忆核心) + 17 (系统运维) + 2 (集群同频) + 2 (算力协同)，
杜绝特权工具越界与普通 Agent 视网膜大杂烩。
"""

import os
import sys
from pathlib import Path
import pytest

# 注入 mcp-openviking 路径
STUDIO_ROOT = Path(__file__).resolve().parent.parent.parent
MCP_DIR = STUDIO_ROOT / "mcp-openviking"
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

from _core.config import (
    MEMORY_37_TOOL_NAMES,
    OPS_17_TOOL_NAMES,
    FLEET_2_TOOL_NAMES,
    CPA_2_TOOL_NAMES,
    resolve_mcp_mode,
)


def test_tool_collections_mathematical_partition():
    """验证四大工具集合的数学完全划分：无交集、无遗漏，总数恰好为 58。"""
    assert len(MEMORY_37_TOOL_NAMES) == 37, f"Memory tools count mismatch: {len(MEMORY_37_TOOL_NAMES)} != 37"
    assert len(OPS_17_TOOL_NAMES) == 17, f"Ops tools count mismatch: {len(OPS_17_TOOL_NAMES)} != 17"
    assert len(FLEET_2_TOOL_NAMES) == 2, f"Fleet tools count mismatch: {len(FLEET_2_TOOL_NAMES)} != 2"
    assert len(CPA_2_TOOL_NAMES) == 2, f"CPA tools count mismatch: {len(CPA_2_TOOL_NAMES)} != 2"

    # 两两互斥判定 (Disjoint sets)
    assert MEMORY_37_TOOL_NAMES.isdisjoint(OPS_17_TOOL_NAMES), "Memory and Ops tools must be strictly disjoint!"
    assert MEMORY_37_TOOL_NAMES.isdisjoint(FLEET_2_TOOL_NAMES), "Memory and Fleet tools must be strictly disjoint!"
    assert MEMORY_37_TOOL_NAMES.isdisjoint(CPA_2_TOOL_NAMES), "Memory and CPA tools must be strictly disjoint!"
    assert OPS_17_TOOL_NAMES.isdisjoint(FLEET_2_TOOL_NAMES), "Ops and Fleet tools must be strictly disjoint!"
    assert OPS_17_TOOL_NAMES.isdisjoint(CPA_2_TOOL_NAMES), "Ops and CPA tools must be strictly disjoint!"
    assert FLEET_2_TOOL_NAMES.isdisjoint(CPA_2_TOOL_NAMES), "Fleet and CPA tools must be strictly disjoint!"

    total_union = MEMORY_37_TOOL_NAMES | OPS_17_TOOL_NAMES | FLEET_2_TOOL_NAMES | CPA_2_TOOL_NAMES
    assert len(total_union) == 58, f"Total tools union must be exactly 58, got {len(total_union)}"


def test_mode_resolution_cli_and_env():
    """验证 resolve_mcp_mode 正确解析 memory, ops, fleet, cpa, all。"""
    assert resolve_mcp_mode(argv=["--mode=memory"]) == "memory"
    assert resolve_mcp_mode(argv=["--mode", "ops"]) == "ops"
    assert resolve_mcp_mode(argv=["--mode=fleet"]) == "fleet"
    assert resolve_mcp_mode(argv=["--mode=cpa"]) == "cpa"
    assert resolve_mcp_mode(argv=["--mode=all"]) == "all"

    assert resolve_mcp_mode(env={"OPENVIKING_MCP_MODE": "memory"}) == "memory"
    assert resolve_mcp_mode(env={"OPENVIKING_MCP_MODE": "ops"}) == "ops"
    assert resolve_mcp_mode(env={"OPENVIKING_MCP_MODE": "fleet"}) == "fleet"
    assert resolve_mcp_mode(env={"OPENVIKING_MCP_MODE": "cpa"}) == "cpa"


def test_server_registration_memory_mode():
    """验证在 memory 模式下，注册的工具数量恰好为 37 且绝无运维特权工具。"""
    from mcp.server.fastmcp import FastMCP
    from _core.decorators import create_mcp_tool_decorator
    from tools import (
        register_memory_tools, register_code_tools, register_filesystem_tools,
        register_skills_tools, register_sessions_tools, register_system_tools,
        register_observability_tools, register_cpa_tools, register_fleet_tools
    )

    mcp = FastMCP("test_memory")
    mcp_tool = create_mcp_tool_decorator(mcp, "memory")

    tools = {}
    tools.update(register_memory_tools(mcp, mcp_tool))
    tools.update(register_code_tools(mcp, mcp_tool))
    tools.update(register_filesystem_tools(mcp, mcp_tool))
    tools.update(register_skills_tools(mcp, mcp_tool))
    tools.update(register_sessions_tools(mcp, mcp_tool))
    tools.update(register_system_tools(mcp, mcp_tool))
    tools.update(register_observability_tools(mcp, mcp_tool))
    tools.update(register_cpa_tools(mcp, mcp_tool))
    tools.update(register_fleet_tools(mcp, mcp_tool))

    registered_names = set(tools.keys())
    assert len(registered_names) == 37, f"Expected 37 memory tools, got {len(registered_names)}: {registered_names}"
    assert registered_names == MEMORY_37_TOOL_NAMES

    # 严禁泄露任何运维工具
    for ops_tool in OPS_17_TOOL_NAMES:
        assert ops_tool not in registered_names, f"Ops tool '{ops_tool}' leaked into memory mode!"


def test_server_registration_ops_mode():
    """验证在 ops 模式下，注册的工具数量恰好为 17 运维特权工具。"""
    from mcp.server.fastmcp import FastMCP
    from _core.decorators import create_mcp_tool_decorator
    from tools import (
        register_memory_tools, register_code_tools, register_filesystem_tools,
        register_skills_tools, register_sessions_tools, register_system_tools,
        register_observability_tools, register_cpa_tools, register_fleet_tools
    )

    mcp = FastMCP("test_ops")
    mcp_tool = create_mcp_tool_decorator(mcp, "ops")

    tools = {}
    tools.update(register_memory_tools(mcp, mcp_tool))
    tools.update(register_code_tools(mcp, mcp_tool))
    tools.update(register_filesystem_tools(mcp, mcp_tool))
    tools.update(register_skills_tools(mcp, mcp_tool))
    tools.update(register_sessions_tools(mcp, mcp_tool))
    tools.update(register_system_tools(mcp, mcp_tool))
    tools.update(register_observability_tools(mcp, mcp_tool))
    tools.update(register_cpa_tools(mcp, mcp_tool))
    tools.update(register_fleet_tools(mcp, mcp_tool))

    registered_names = set(tools.keys())
    assert len(registered_names) == 17, f"Expected 17 ops tools, got {len(registered_names)}: {registered_names}"
    assert registered_names == OPS_17_TOOL_NAMES


def test_server_registration_fleet_mode():
    """验证在 fleet 模式下，注册的工具数量恰好为 2 (集群同频工具)。"""
    from mcp.server.fastmcp import FastMCP
    from _core.decorators import create_mcp_tool_decorator
    from tools import (
        register_memory_tools, register_code_tools, register_filesystem_tools,
        register_skills_tools, register_sessions_tools, register_system_tools,
        register_observability_tools, register_cpa_tools, register_fleet_tools
    )

    mcp = FastMCP("test_fleet")
    mcp_tool = create_mcp_tool_decorator(mcp, "fleet")

    tools = {}
    tools.update(register_memory_tools(mcp, mcp_tool))
    tools.update(register_code_tools(mcp, mcp_tool))
    tools.update(register_filesystem_tools(mcp, mcp_tool))
    tools.update(register_skills_tools(mcp, mcp_tool))
    tools.update(register_sessions_tools(mcp, mcp_tool))
    tools.update(register_system_tools(mcp, mcp_tool))
    tools.update(register_observability_tools(mcp, mcp_tool))
    tools.update(register_cpa_tools(mcp, mcp_tool))
    tools.update(register_fleet_tools(mcp, mcp_tool))

    registered_names = set(tools.keys())
    assert len(registered_names) == 2, f"Expected 2 fleet tools, got {len(registered_names)}: {registered_names}"
    assert registered_names == FLEET_2_TOOL_NAMES


def test_server_registration_cpa_mode():
    """验证在 cpa 模式下，注册的工具数量恰好为 2 (算力协同工具)。"""
    from mcp.server.fastmcp import FastMCP
    from _core.decorators import create_mcp_tool_decorator
    from tools import (
        register_memory_tools, register_code_tools, register_filesystem_tools,
        register_skills_tools, register_sessions_tools, register_system_tools,
        register_observability_tools, register_cpa_tools, register_fleet_tools
    )

    mcp = FastMCP("test_cpa")
    mcp_tool = create_mcp_tool_decorator(mcp, "cpa")

    tools = {}
    tools.update(register_memory_tools(mcp, mcp_tool))
    tools.update(register_code_tools(mcp, mcp_tool))
    tools.update(register_filesystem_tools(mcp, mcp_tool))
    tools.update(register_skills_tools(mcp, mcp_tool))
    tools.update(register_sessions_tools(mcp, mcp_tool))
    tools.update(register_system_tools(mcp, mcp_tool))
    tools.update(register_observability_tools(mcp, mcp_tool))
    tools.update(register_cpa_tools(mcp, mcp_tool))
    tools.update(register_fleet_tools(mcp, mcp_tool))

    registered_names = set(tools.keys())
    assert len(registered_names) == 2, f"Expected 2 cpa tools, got {len(registered_names)}: {registered_names}"
    assert registered_names == CPA_2_TOOL_NAMES


if __name__ == "__main__":
    print("Running test_tool_collections_mathematical_partition...")
    test_tool_collections_mathematical_partition()
    print("✅ test_tool_collections_mathematical_partition passed")

    print("Running test_mode_resolution_cli_and_env...")
    test_mode_resolution_cli_and_env()
    print("✅ test_mode_resolution_cli_and_env passed")

    print("Running test_server_registration_memory_mode...")
    test_server_registration_memory_mode()
    print("✅ test_server_registration_memory_mode passed (37 tools exact)")

    print("Running test_server_registration_ops_mode...")
    test_server_registration_ops_mode()
    print("✅ test_server_registration_ops_mode passed (17 tools exact)")

    print("Running test_server_registration_fleet_mode...")
    test_server_registration_fleet_mode()
    print("✅ test_server_registration_fleet_mode passed (2 tools exact)")

    print("Running test_server_registration_cpa_mode...")
    test_server_registration_cpa_mode()
    print("✅ test_server_registration_cpa_mode passed (2 tools exact)")

    print("\n🎉 ALL 6 TESTS PASSED FULLY! (Card-151 Domain Split SSOT Verified)")
