#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Circuit Breaker MCP Server (FastMCP Standard Edition)
依托官方标准 FastMCP 工业级框架，提供断路器状态实时观测、自适应弹性预算监控、与一键重置接口。
100% 完整支持 MCP 握手、Ping、Tools/List、Tools/Call 与 Pydantic 类型校验。
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Optional

# SECTION: Windows UTF-8 Stdio Safeguard
if sys.platform == "win32":
    try:
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from mcp.server.fastmcp import FastMCP

# 初始化官方 FastMCP 服务端
mcp = FastMCP("circuit-breaker")


def get_state_dir() -> Path:
    base = Path(tempfile.gettempdir()) / "antigravity_circuit_breaker"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_active_states() -> list:
    states = []
    for sf in get_state_dir().glob("cb_*.json"):
        try:
            with open(sf, "r", encoding="utf-8") as f:
                d = json.load(f)
                d["_session_id"] = sf.stem.replace("cb_", "")
                states.append(d)
        except Exception:
            pass
    return states


@mcp.tool(
    name="circuit_breaker_status",
    description="查看当前 Antigravity 宿主断路器的运行状态、活跃会话步数与错误计数监控大屏"
)
def circuit_breaker_status(session_id: Optional[str] = None):
    """查询断路器状态监控座舱"""
    states = get_active_states()
    if session_id:
        states = [s for s in states if s.get("_session_id") == session_id.strip()]

    total_intercepts = sum(
        1 for s in states if s.get("consecutive_failures", 0) >= 3 or s.get("step_count", 0) >= s.get("current_step_limit", 36)
    )

    lines = [
        "### 🛡️ Antigravity 自适应弹性断路器全局监控座舱",
        "- **运行模式**: 原生 Fail-Open + 自适应弹性预算 (健康 36 步 / 警戒 15 步 / 租约 +15 步)",
        f"- **当前受控会话数**: {len(states)}",
        f"- **警戒中会话数**: {total_intercepts}",
        "",
        "| 会话 ID | 单轮步数 / 动态上限 | 连续写失败 (限3) | 状态 |",
        "| :--- | :--- | :--- | :--- |"
    ]
    if not states:
        lines.append("| (暂无活跃会话) | 0 / 36 | 0 | 🟢 沉静正常 |")
    else:
        for s in states:
            sid = s.get("_session_id", "default")[:12]
            steps = s.get("step_count", 0)
            limit = s.get("current_step_limit", 36)
            fails = s.get("consecutive_failures", 0)
            if fails >= 3 or steps >= limit:
                status_tag = "🔴 触发求证"
            elif steps >= max(limit - 6, 10):
                status_tag = "🟡 临近预算"
            else:
                status_tag = "🔹 正常"
            lines.append(f"| `{sid}` | {steps} / {limit} | {fails} | {status_tag} |")

    return "\n".join(lines)


@mcp.tool(
    name="circuit_breaker_reset",
    description="重置并清空断路器会话状态缓存与报错计数器"
)
def circuit_breaker_reset(session_id: Optional[str] = None):
    """重置断路器会话状态缓存与计数器"""
    sdir = get_state_dir()
    count = 0
    if session_id:
        target = sdir / f"cb_{session_id.strip()}.json"
        if target.exists():
            target.unlink(missing_ok=True)
            count = 1
    else:
        for f in sdir.glob("cb_*.json"):
            f.unlink(missing_ok=True)
            count += 1
    return f"✅ 已成功重置并清空 {count} 个会话的断路器熔断计数器与状态缓存。"


if __name__ == "__main__":
    mcp.run(transport="stdio")
