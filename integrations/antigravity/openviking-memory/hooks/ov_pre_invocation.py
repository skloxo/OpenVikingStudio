#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking Antigravity Plugin PreInvocation Hook (v2.0.11)
自包含钩子：从插件本地 config.json 读取凭据，
具备云端用户中心 (User Cockpit) 动态权限与 Hook 开关智能感知：
若在用户中心关闭了本 Hook 或对应插件，本地毫秒级短路，严格尊重云端管控。
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path


def load_plugin_config():
    plugin_dir = Path(__file__).resolve().parent.parent
    config_file = plugin_dir / "config.json"
    api = os.environ.get("OPENVIKING_API", "").strip()
    key = os.environ.get("OPENVIKING_API_KEY", "").strip()
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not api:
                    api = data.get("api_url", "").strip()
                if not key:
                    key = data.get("api_key", "").strip()
        except Exception:
            pass
    api = api or "http://127.0.0.1:1933"
    return api.rstrip("/"), key, plugin_dir


def is_hook_enabled_in_cloud(api: str, key: str, plugin_dir: Path) -> bool:
    """带 60s TTL 单调时钟缓存，动态感知云端用户中心是否开启了 ov_pre_invocation"""
    cache_file = plugin_dir / ".caps_cache.json"
    now = time.time()
    
    # 1. 尝试读本地快照缓存 (TTL 60s)
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if now - cached.get("timestamp", 0) < 60:
                    return cached.get("enabled", True)
        except Exception:
            pass

    # 2. 缓存过期时向云端快速拉取 (限时 1.2s，失败降级默认 True)
    try:
        url = f"{api}/api/v1/system/client-capabilities"
        headers = {"User-Agent": "Antigravity-OpenViking-Plugin/2.0.11"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=1.2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            hooks = data.get("hooks", [])
            is_enabled = True
            for h in hooks:
                if h.get("id") == "ov_pre_invocation":
                    is_enabled = bool(h.get("enabled", True))
                    break
            
            # 写入轻量快照
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump({"timestamp": now, "enabled": is_enabled}, f)
            except Exception:
                pass
            return is_enabled
    except Exception:
        # 网络抖动平滑降级，不阻断
        return True


def extract_query_from_stdin():
    try:
        if not sys.stdin.isatty():
            line = sys.stdin.readline()
            if line and line.strip():
                data = json.loads(line.strip())
                transcript_path = data.get("transcriptPath") or data.get("transcript_path")
                if transcript_path and os.path.exists(transcript_path):
                    with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        for line_item in reversed(lines[-40:]):
                            try:
                                entry = json.loads(line_item)
                                if entry.get("type") == "USER_INPUT" and entry.get("content"):
                                    return entry["content"].strip()
                            except Exception:
                                pass
    except Exception:
        pass
    return ""


def emit_json(payload: dict):
    try:
        data = json.dumps(payload, ensure_ascii=False)
        sys.stdout.buffer.write(data.encode("utf-8") + b"\n")
        sys.stdout.buffer.flush()
    except BaseException:
        sys.stdout.buffer.write(b"{}\n")
        sys.stdout.buffer.flush()


def main():
    api, key, plugin_dir = load_plugin_config()
    
    # 核心：云端用户中心 Hook 开关动态适配
    if not is_hook_enabled_in_cloud(api, key, plugin_dir):
        # 云端管理员关闭了该用户的预取 Hook，本地直接静默退出
        emit_json({})
        return

    query = extract_query_from_stdin()
    if not query or len(query) < 2:
        emit_json({})
        return

    lowered = query.lower()
    if lowered in {"ok", "yes", "好", "好的", "收到", "继续", "同意"}:
        emit_json({})
        return

    url = f"{api}/api/v1/search/find"
    payload = json.dumps({"query": query[:300], "limit": 2}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Antigravity-OpenViking-Plugin/2.0.11"
    }
    if key:
        headers["Authorization"] = f"Bearer {key}"

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=1.8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("result", {}).get("resources", [])
            if not items:
                emit_json({})
                return

            lines = [f"【OpenViking 核心记忆预取 ({api})】"]
            for r in items[:2]:
                uri = r.get("uri", "")
                abstract = (r.get("abstract") or "").replace("\n", " ").strip()
                if len(abstract) > 180:
                    abstract = abstract[:180] + "..."
                lines.append(f"- [{uri}]: {abstract}")

            hint = "\n".join(lines)
            # 严格对齐 Antigravity 官方 PreInvocation 注入契约 (injectSteps)
            output = {
                "injectSteps": [
                    {
                        "ephemeralMessage": hint
                    }
                ]
            }
            emit_json(output)
            return
    except Exception:
        pass

    emit_json({})


if __name__ == "__main__":
    # 最高级别物理屏障：任何异常直写 {} 并返回 0，严禁抛出非零退出码或阻塞宿主
    try:
        main()
    except BaseException:
        sys.stdout.buffer.write(b"{}\n")
        sys.stdout.buffer.flush()
    sys.exit(0)
