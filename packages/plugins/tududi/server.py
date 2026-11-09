#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tududi Native FastMCP Stdio Gateway Bridge (tududi v1.0.2)
Connects Antigravity / Claude Desktop stdio clients directly to Tududi's native
JSON-RPC / SSE MCP endpoint (https://todo.tide.red/api/mcp).
1. Bypasses Windows system proxy (trust_env = False) for zero proxy-hijack hang;
2. Supports fast dual-link failover between public URL (8s) and LAN URL (2s);
3. Normalizes JSON Schema union types (e.g. ["number", "string"] -> "string") for strict LLM compatibility.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import requests

# Windows UTF-8 Stdio Safeguard
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_DIR = Path(__file__).resolve().parent
_CONFIG_FILE = _DIR / "config.json"

_CFG: Dict[str, Any] = {
    "public_url": "https://todo.tide.red/api/mcp",
    "internal_url": "http://10.128.226.5:3002/api/mcp",
    "api_token": "",
    "timeout": 8,
    "internal_timeout": 2,
}

if _CONFIG_FILE.exists():
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            _CFG.update(json.load(f))
    except Exception as e:
        sys.stderr.write(f"[WARN] Failed to load config.json: {e}\n")

# Environment overrides
if os.environ.get("TUDUDI_URL"):
    _CFG["public_url"] = os.environ["TUDUDI_URL"].rstrip("/") + "/api/mcp"
if os.environ.get("TUDUDI_API_TOKEN"):
    _CFG["api_token"] = os.environ["TUDUDI_API_TOKEN"]

session = requests.Session()
# Mandatory: bypass system HTTP/SOCKS proxies (Clash/Mihomo) for domestic & LAN endpoints
session.trust_env = False
session.headers.update({
    "Authorization": f"Bearer {_CFG['api_token']}",
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
})


def _normalize_tools_schema(result_str: str) -> str:
    """Normalizes union type arrays (e.g. ['number', 'string'] or ['string', 'null']) to 'string'."""
    try:
        data = json.loads(result_str)
        tools = data.get("result", {}).get("tools")
        if not isinstance(tools, list):
            return result_str
        for t in tools:
            schema = t.get("inputSchema")
            if not isinstance(schema, dict):
                continue
            props = schema.get("properties")
            if not isinstance(props, dict):
                continue
            for prop in props.values():
                if isinstance(prop, dict) and isinstance(prop.get("type"), list):
                    non_null = [x for x in prop["type"] if x != "null"]
                    prop["type"] = "string" if "string" in non_null else (non_null[0] if non_null else "string")
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return result_str



FORBIDDEN_TAGS = {
    "today", "someday", "汇报",
    "p0", "p1", "p2", "p3", "urgent", "high", "medium", "low",
    "紧急", "高优", "高优先级", "低优先级", "重要",
    "todo", "done", "in_progress", "待办", "进行中", "已完成", "未开始",
    "工作", "个人",
}

def _sanitize_task_args(tool_name: str, args: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
    import re
    changed = False
    new_args = dict(args)
    if tool_name in {"create_task", "update_task", "add_subtask"}:
        name = str(new_args.get("name", "") or "")
        if name:
            orig_name = name
            name = re.sub(r"^\[(运维|规划|开发|缺陷|汇报|待办|测试|P[0-9]|TASK)\]\s*", "", name).strip()
            codes = re.findall(r"[\(\[](T\d+-\d+|TASK-[A-Z0-9\-]+)[\)\]]", name, re.IGNORECASE)
            if codes:
                name = re.sub(r"\s*[\(\[](T\d+-\d+|TASK-[A-Z0-9\-]+)[\)\]]\s*", " ", name).strip()
                curr_note = str(new_args.get("note", "") or "")
                if "【关联编号】" not in curr_note:
                    code_str = f"\n\n【关联编号】\n{', '.join(codes)}"
                    new_args["note"] = (curr_note.strip() + code_str).strip()
                changed = True
            name = re.sub(r"^(O[1-4]-KR\d+|网格化管理平台|干部公寓|物业系统|智能门锁|AI监控|安防监控|滴滴企业打车|园区门户|仓储方案|Tududi)\s*[:：]\s*", "", name).strip()
            if name != orig_name:
                new_args["name"] = name
                changed = True

        tags = new_args.get("tags")
        if isinstance(tags, list):
            cleaned_tags = [t for t in tags if str(t).lstrip("#@").lower() not in FORBIDDEN_TAGS]
            if cleaned_tags != tags:
                new_args["tags"] = cleaned_tags
                changed = True

        if tool_name == "create_task" and not new_args.get("assigned_to"):
            new_args["assigned_to"] = "07mah9uku662d6u"
            changed = True

    return new_args, changed


def _post_tududi(payload: Dict[str, Any]) -> Optional[str]:
    """Posts payload to Tududi MCP endpoint with dual-link failover."""
    endpoints = [(_CFG["public_url"], float(_CFG.get("timeout", 8) or 8))]
    if _CFG.get("internal_url") and _CFG["internal_url"] != _CFG["public_url"]:
        endpoints.append((_CFG["internal_url"], float(_CFG.get("internal_timeout", 2) or 2)))

    last_err = None

    for target_url, req_timeout in endpoints:
        try:
            resp = session.post(target_url, json=payload, timeout=req_timeout)
            if resp.status_code == 202:
                return None

            resp.encoding = "utf-8"
            text_body = resp.content.decode("utf-8", errors="replace").strip()
            # Parse Server-Sent Events (SSE) data line
            for line in text_body.split("\n"):
                if line.startswith("data: "):
                    return line[6:].strip()

            if text_body.startswith("{"):
                return text_body
        except Exception as exc:
            last_err = exc
            continue

    if "id" in payload:
        return json.dumps({
            "jsonrpc": "2.0",
            "id": payload.get("id"),
            "error": {
                "code": -32603,
                "message": f"Tududi gateway error across all endpoints: {last_err}",
            },
        }, ensure_ascii=False)
    return None


def main() -> None:
    while True:
        try:
            raw_line = sys.stdin.readline()
            if not raw_line:
                break
            line_str = raw_line.strip()
            if not line_str:
                continue

            try:
                msg = json.loads(line_str)
            except Exception:
                continue

            method = msg.get("method")
            req_id = msg.get("id")

            # Gracefully handle MCP optional capabilities
            if method == "resources/list":
                if req_id is not None:
                    out = json.dumps({"jsonrpc": "2.0", "id": req_id, "result": {"resources": []}})
                    sys.stdout.write(out + "\n")
                    sys.stdout.flush()
                continue
            elif method == "prompts/list":
                if req_id is not None:
                    out = json.dumps({"jsonrpc": "2.0", "id": req_id, "result": {"prompts": []}})
                    sys.stdout.write(out + "\n")
                    sys.stdout.flush()
                continue

            # Auto-sanitize task inputs before forwarding
            if method == "tools/call":
                params = msg.get("params") or {}
                t_name = str(params.get("name", "") or "")
                t_args = params.get("arguments") or {}
                if isinstance(t_args, dict) and t_name in {"create_task", "update_task", "add_subtask"}:
                    cleaned_args, is_ch = _sanitize_task_args(t_name, t_args)
                    if is_ch:
                        params["arguments"] = cleaned_args
                        msg["params"] = params

            # Forward to Tududi native MCP endpoint
            result_str = _post_tududi(msg)
            if result_str and req_id is not None:
                if method == "tools/list":
                    result_str = _normalize_tools_schema(result_str)
                sys.stdout.write(result_str + "\n")
                sys.stdout.flush()

        except (KeyboardInterrupt, BrokenPipeError):
            break
        except Exception as loop_err:
            sys.stderr.write(f"[ERROR] tududi loop error: {loop_err}\n")
            continue


if __name__ == "__main__":
    main()
