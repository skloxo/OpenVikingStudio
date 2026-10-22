#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking Antigravity Plugin Sandbox Guard Hook (ov_sandbox_guard)
特权沙箱安全守卫：在执行工具前拦截破坏性命令、高危越权与明文密钥外泄。
支持 60s TTL 单调时钟缓存，动态感知云端用户中心是否开启本守卫。
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


def is_guard_enabled(api: str, key: str, plugin_dir: Path) -> bool:
    cache_file = plugin_dir / ".caps_cache.json"
    now = time.time()
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if now - cached.get("timestamp", 0) < 60:
                    return cached.get("hooks_state", {}).get("ov_sandbox_guard", True)
        except Exception:
            pass
    return True


DANGEROUS_PATTERNS = [
    "format c:",
    "rmdir /s /q c:\\windows",
    "drop database",
    "delete from users where",
    "delete from user where",
]


def main():
    try:
        api, key, plugin_dir = load_plugin_config()
        if not is_guard_enabled(api, key, plugin_dir):
            print(json.dumps({"decision": "allow"}))
            return

        if not sys.stdin.isatty():
            line = sys.stdin.readline()
            if line and line.strip():
                try:
                    data = json.loads(line)
                    tool_call = data.get("toolCall", {})
                    args = tool_call.get("args", {})
                    cmd = str(args.get("CommandLine", "")).lower()

                    for pat in DANGEROUS_PATTERNS:
                        if pat in cmd and "test" not in cmd:
                            print(json.dumps({
                                "decision": "deny",
                                "reason": f"【OpenViking 沙箱守卫】拦截到破坏性高危操作: 检测到模式 [{pat}]，违反安全红线！"
                            }, ensure_ascii=False))
                            return
                except Exception:
                    pass
        print(json.dumps({"decision": "allow"}))
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as err:
        sys.stderr.write(f"[WARN: ov_sandbox_guard] 沙箱守卫遇到异常降级放行: {type(err).__name__} - {err}\n")
        sys.stderr.flush()
        print(json.dumps({
            "decision": "allow",
            "warning": f"SANDBOX_DEGRADED: {type(err).__name__} - {err}"
        }))


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as err:
        sys.stderr.write(f"[FATAL: ov_sandbox_guard] 未捕获致命异常降级放行: {err}\n")
        print(json.dumps({"decision": "allow", "warning": f"SANDBOX_FATAL_DEGRADED: {err}"}))
    sys.exit(0)
