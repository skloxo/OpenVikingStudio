#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking Antigravity Plugin PreInvocation Hook
自包含钩子：从插件本地 config.json 或环境变量读取地址与密钥，
在模型推理前自动提取用户意图并预取体外大脑关联记忆。
"""

import json
import os
import sys
import urllib.request
from pathlib import Path


def load_plugin_config():
    """读取插件本地配置 config.json，兼顾环境变量覆盖"""
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
    return api.rstrip("/"), key


def extract_query_from_stdin():
    """从 stdin 提取最近一条用户输入"""
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
            if raw.strip():
                data = json.loads(raw)
                transcript_path = data.get("transcript_path")
                if transcript_path and os.path.exists(transcript_path):
                    with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        for line in reversed(lines[-40:]):
                            try:
                                entry = json.loads(line)
                                if entry.get("type") == "USER_INPUT" and entry.get("content"):
                                    return entry["content"].strip()
                            except Exception:
                                pass
    except Exception:
        pass
    return ""


def main():
    api, key = load_plugin_config()
    query = extract_query_from_stdin()
    
    if not query or len(query) < 2:
        print("{}")
        return

    # 过滤简单确认词
    lowered = query.lower()
    if lowered in {"ok", "yes", "好", "好的", "收到", "继续", "同意"}:
        print("{}")
        return

    # 向 OpenViking 搜索先验记忆
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
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("result", {}).get("resources", [])
            if not items:
                print("{}")
                return
            
            lines = [f"【OpenViking 核心记忆预取 ({api})】"]
            for r in items[:2]:
                uri = r.get("uri", "")
                abstract = (r.get("abstract") or "").replace("\n", " ").strip()
                if len(abstract) > 180:
                    abstract = abstract[:180] + "..."
                lines.append(f"- [{uri}]: {abstract}")
            
            hint = "\n".join(lines)
            output = {"context_injection": hint}
            print(json.dumps(output, ensure_ascii=False))
            return
    except Exception:
        pass

    print("{}")


if __name__ == "__main__":
    main()
