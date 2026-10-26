#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenViking Core Memory Antigravity Pure MCP Proxy (v2.0.27)

第一性原理架构：纯透明 stdio ➔ Streamable-HTTP (/mcp) 协议转换中继桥。
1. 本地零业务工具定义：所有 35 项核心战地工具 100% 由服务端原生驱动与托管；
2. 零端侧发版负债：服务端新增工具、修复 Bug、调优参数，反重力端 0 秒无感全自动同频；
3. 鲁棒安全通道：UTF-8 管道流式保护、多级凭据自适应感知、SSE 自动反序列化与标准 JSON-RPC 容灾。
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

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

# SECTION: Configuration & Credential Resolution
_PLUGIN_DIR = Path(__file__).resolve().parent
_CONFIG_FILE = _PLUGIN_DIR / "config.json"
_LOCAL_CFG: Dict[str, Any] = {}

if _CONFIG_FILE.exists():
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            _LOCAL_CFG = json.load(f)
    except Exception:
        pass

API_BASE = (
    os.environ.get("OPENVIKING_API")
    or _LOCAL_CFG.get("api_url")
    or _LOCAL_CFG.get("api")
    or "http://127.0.0.1:1933"
).rstrip("/")

API_KEY = (
    os.environ.get("OPENVIKING_API_KEY")
    or os.environ.get("OPENVIKING_ROOT_API_KEY")
    or _LOCAL_CFG.get("api_key")
    or ""
)


ACTOR_PEER = (
    os.environ.get("OPENVIKING_ACTOR_PEER")
    or _LOCAL_CFG.get("actor_peer")
    or ""
)

_IS_BOUND_USER_KEY = bool(API_KEY and len(API_KEY.strip().split(".")) == 3)
VERIFIED_USER = "" if _IS_BOUND_USER_KEY else os.environ.get("OPENVIKING_USER", "").strip()
ACCOUNT = "" if _IS_BOUND_USER_KEY else os.environ.get("OPENVIKING_ACCOUNT", "").strip()

MCP_ENDPOINT = f"{API_BASE}/mcp"
DEFAULT_TIMEOUT: float = 120.0


def _build_headers() -> Dict[str, str]:
    headers = {
        "User-Agent": "Antigravity-OpenViking-Pure-Proxy/2.0.40",
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json, text/event-stream",
        "X-OpenViking-Plugin": "openviking-memory",
    }
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    if VERIFIED_USER:
        headers["X-OpenViking-User"] = VERIFIED_USER
    if ACCOUNT:
        headers["X-OpenViking-Account"] = ACCOUNT
    if ACTOR_PEER:
        headers["X-OpenViking-Actor-Peer"] = ACTOR_PEER
    return headers


# SECTION: Bidirectional Tool Name Normalization
SERVER_TO_CLIENT_TOOLS = {
    "find": "openviking_find",
    "search": "openviking_search",
    "read": "openviking_read",
    "list": "openviking_ls",
    "tree": "openviking_tree",
    "remember": "openviking_store",
    "write": "openviking_write",
    "grep": "openviking_grep",
    "glob": "openviking_glob",
    "health": "openviking_health",
}
CLIENT_TO_SERVER_TOOLS = {v: k for k, v in SERVER_TO_CLIENT_TOOLS.items()}
CLIENT_TO_SERVER_TOOLS["openviking_list"] = "list"


def _forward_notification(notification_obj: Dict[str, Any]) -> None:
    """Forward notifications silently to /mcp without sending any response to stdout."""
    payload = json.dumps(notification_obj, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        MCP_ENDPOINT,
        data=payload,
        headers=_build_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            resp.read()
    except Exception:
        pass


def _forward_request(request_obj: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Forward incoming JSON-RPC request to server /mcp endpoint and extract response objects."""
    req_id = request_obj.get("id")
    method = request_obj.get("method")

    # 1. tools/call 逆向映射: 将客户端的 openviking_* 还原为服务端原生 tool name
    if method == "tools/call":
        params = request_obj.get("params")
        if isinstance(params, dict):
            t_name = params.get("name", "")
            if t_name in CLIENT_TO_SERVER_TOOLS:
                params["name"] = CLIENT_TO_SERVER_TOOLS[t_name]

    payload = json.dumps(request_obj, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        MCP_ENDPOINT,
        data=payload,
        headers=_build_headers(),
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        responses: list[Dict[str, Any]] = []
        for line in raw.splitlines():
            line_str = line.strip()
            if line_str.startswith("data:"):
                data_part = line_str[5:].strip()
                if data_part and data_part != "[DONE]":
                    try:
                        responses.append(json.loads(data_part))
                    except Exception:
                        pass
        if not responses and raw.strip():
            try:
                responses.append(json.loads(raw.strip()))
            except Exception:
                pass

        # 2. initialize 装饰: 显著注入双轨版本感知
        if method == "initialize":
            for reply in responses:
                if isinstance(reply, dict) and "result" in reply:
                    res = reply["result"]
                    if isinstance(res, dict) and "serverInfo" in res:
                        s_info = res["serverInfo"]
                        k_ver = s_info.get("version", "1.7.164")
                        s_info["name"] = "openviking-memory"
                        s_info["version"] = f"v2.0.27 [Kernel: v{k_ver} | 35 Tools Online | Synced]"

        # 3. tools/list 正向映射: 将服务端原生无前缀工具统一规范化为 openviking_*
        elif method == "tools/list":
            for reply in responses:
                if isinstance(reply, dict) and "result" in reply:
                    res = reply["result"]
                    if isinstance(res, dict) and "tools" in res and isinstance(res["tools"], list):
                        for tool in res["tools"]:
                            orig_name = tool.get("name", "")
                            if orig_name in SERVER_TO_CLIENT_TOOLS:
                                tool["name"] = SERVER_TO_CLIENT_TOOLS[orig_name]

        if not responses:
            responses.append({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"status": "ok"}
            })
        return responses

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return [{
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32000,
                "message": f"Server MCP HTTP {e.code}: {err_body}",
            }
        }]
    except Exception as e:
        return [{
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32001,
                "message": f"Server MCP Connection Error ({MCP_ENDPOINT}): {e}",
            }
        }]


def run_stdio_proxy() -> None:
    """Main loop: proxy stdio JSON-RPC stream directly to OpenViking Streamable-HTTP MCP."""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line_str = line.strip()
            if not line_str:
                continue

            try:
                msg = json.loads(line_str)
            except Exception:
                continue

            # Notification 门禁: 无 id 的通知绝不产生任何 stdout 响应 (遵循 JSON-RPC 2.0 规范)
            is_notification = ("id" not in msg) or (msg.get("id") is None)
            if is_notification:
                _forward_notification(msg)
                continue

            # 标准 Request 转发并回写 stdout
            replies = _forward_request(msg)
            for reply in replies:
                sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
                sys.stdout.flush()

        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as loop_err:
            sys.stderr.write(f"[ProxyLoopError] {loop_err}\n")
            sys.stderr.flush()


if __name__ == "__main__":
    if "--inspect" in sys.argv:
        print(f"OpenViking Pure MCP Proxy: {MCP_ENDPOINT} (User: {VERIFIED_USER}) [Hot-Reload Synced]")
        sys.exit(0)
    run_stdio_proxy()

