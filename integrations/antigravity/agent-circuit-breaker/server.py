#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Circuit Breaker MCP Server (v1.3.0 - 工业自适应弹性版)
提供断路器状态实时观测、自适应弹性预算监控、与一键重置接口。
"""

import sys
import os
import json
import tempfile
from pathlib import Path

# Stream UTF-8 safe
if hasattr(sys.stdin, "reconfigure"):
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


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


def handle_status(args: dict) -> dict:
    session_id = args.get("session_id", "").strip()
    states = get_active_states()
    if session_id:
        states = [s for s in states if s.get("_session_id") == session_id]

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
                status_tag = "🟢 正常"
            lines.append(f"| `{sid}` | {steps} / {limit} | {fails} | {status_tag} |")

    return {
        "content": [{"type": "text", "text": "\n".join(lines)}]
    }


def handle_reset(args: dict) -> dict:
    session_id = args.get("session_id", "").strip()
    sdir = get_state_dir()
    count = 0
    if session_id:
        target = sdir / f"cb_{session_id}.json"
        if target.exists():
            target.unlink(missing_ok=True)
            count = 1
    else:
        for f in sdir.glob("cb_*.json"):
            f.unlink(missing_ok=True)
            count += 1

    return {
        "content": [{"type": "text", "text": f"✅ 已成功重置并清空 {count} 个会话的断路器熔断计数器与状态缓存。"}]
    }


def main():
    """标准 JSON-RPC 2.0 stdio MCP 处理循环"""
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            req = json.loads(line)
        except Exception:
            continue

        method = req.get("method")
        msg_id = req.get("id")

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "agent-circuit-breaker", "version": "1.3.0"},
                    "capabilities": {"tools": {}}
                }
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif method == "notifications/initialized":
            pass

        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": "circuit_breaker_status",
                            "description": "查看当前 Antigravity 宿主断路器的运行状态、活跃会话步数与错误计数监控大屏",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "session_id": {"type": "string", "description": "可选：指定会话ID查询切片"}
                                }
                            }
                        },
                        {
                            "name": "circuit_breaker_reset",
                            "description": "重置并清空断路器会话状态缓存与报错计数器",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "session_id": {"type": "string", "description": "可选：指定重置的会话ID，缺省重置全部"}
                                }
                            }
                        }
                    ]
                }
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif method == "tools/call":
            params = req.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})

            if name == "circuit_breaker_status":
                res = handle_status(args)
            elif name == "circuit_breaker_reset":
                res = handle_reset(args)
            else:
                res = {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}

            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": res
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
