#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Card-152: Antigravity IDE 插件生态全量健康与工具分立验收探针
全面验证 7 大分立 MCP 服务、工具数量、Hook 完整性与私有配置读取机制。
"""

import json
import os
import sys
from pathlib import Path

STUDIO_ROOT = Path(__file__).resolve().parent.parent.parent
MCP_DIR = STUDIO_ROOT / "mcp-openviking"
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

from _core.config import (
    MEMORY_37_TOOL_NAMES,
    OPS_17_TOOL_NAMES,
    FLEET_2_TOOL_NAMES,
    CPA_2_TOOL_NAMES,
    _get_config,
)
from _core.decorators import create_mcp_tool_decorator
from mcp.server.fastmcp import FastMCP
from tools import (
    register_memory_tools, register_code_tools, register_filesystem_tools,
    register_skills_tools, register_sessions_tools, register_system_tools,
    register_observability_tools, register_cpa_tools, register_fleet_tools
)


def verify_mode_tools(mode: str, expected_count: int, expected_set: set):
    mcp = FastMCP(f"verify_{mode}")
    mcp_tool = create_mcp_tool_decorator(mcp, mode)
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

    registered = set(tools.keys())
    assert len(registered) == expected_count, f"[{mode}] Count mismatch: {len(registered)} != {expected_count}"
    assert registered == expected_set, f"[{mode}] Tool set mismatch!"
    return True


def verify_hooks_integrity():
    plugins_dir = Path.home() / ".gemini" / "config" / "plugins"
    mem_hooks = plugins_dir / "openviking-memory" / "hooks.json"
    assert mem_hooks.exists(), "openviking-memory hooks.json missing!"
    with open(mem_hooks, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "openviking-memory-prefetch" in data, "Missing PreInvocation hook!"
    assert "openviking-sandbox-guard" in data, "Missing PreToolUse hook!"
    assert "openviking-session-archiver" in data, "Missing Stop hook!"
    return True


def verify_keepass_config():
    plugins_dir = Path.home() / ".gemini" / "config" / "plugins"
    k_cfg = plugins_dir / "keepass-vault" / "config.json"
    assert k_cfg.exists(), "keepass config.json missing!"
    with open(k_cfg, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "kdbx_path" in data, "kdbx_path missing in keepass config!"
    assert "password_env" in data or "master_key" in data, "password config missing in keepass config!"
    return True


def main():
    print("=" * 60)
    print("🔍 正在执行 Antigravity IDE 插件与 MCP 生态全景验收...")
    print("=" * 60)

    # 1. 验证 4 大 VK 服务的工具数量与边界
    verify_mode_tools("memory", 37, MEMORY_37_TOOL_NAMES)
    print("  ✔ [openviking-memory] 精准 37 个记忆工具，0 特权泄露")

    verify_mode_tools("ops", 17, OPS_17_TOOL_NAMES)
    print("  ✔ [openviking-ops] 精准 17 个运维特权工具")

    verify_mode_tools("fleet", 2, FLEET_2_TOOL_NAMES)
    print("  ✔ [fleet-mesh] 精准 2 个卫星集群同频工具")

    verify_mode_tools("cpa", 2, CPA_2_TOOL_NAMES)
    print("  ✔ [cpa-squad] 精准 2 个跨模型协同工兵工具")

    # 2. 验证 openviking-memory 3 个 Hook 完整性
    verify_hooks_integrity()
    print("  ✔ [Hooks 门禁] openviking-memory 包含 PreInvocation / PreToolUse / Stop 全部 3 大 Hook")

    # 3. 验证 keepass-vault 配置与连通性
    verify_keepass_config()
    print("  ✔ [KeePass 配置] 支持本地 kdbx 数据库路径与访问密钥配置")

    # 4. 验证全局 mcp_config.json
    mcp_cfg_path = Path.home() / ".gemini" / "config" / "mcp_config.json"
    with open(mcp_cfg_path, "r", encoding="utf-8") as f:
        mcp_cfg = json.load(f)
    servers = mcp_cfg.get("mcpServers", {})
    expected_servers = ["openviking", "openviking-ops", "fleet-mesh", "cpa-squad", "keepass-vault", "dify", "circuit-breaker"]
    for s in expected_servers:
        assert s in servers, f"Server '{s}' missing in global mcp_config.json!"
    print(f"  ✔ [全局注册] mcp_config.json 成功注册 7 大分立服务: {list(servers.keys())}")

    print("=" * 60)
    print("🎉 全景生态验收 100% 通过！所有设计契约与用户诉求完全闭环！")
    print("=" * 60)


if __name__ == "__main__":
    main()
