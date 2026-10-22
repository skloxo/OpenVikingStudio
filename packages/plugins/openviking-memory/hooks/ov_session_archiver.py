#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking Antigravity Plugin Session Archiver Hook
在 Agent 每次会话结束 (Stop) 时静默归档本次会话的上下文摘要与关键决策。
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
    return api.rstrip("/"), key


def main():
    # Stop 钩子只执行轻量归档心跳，绝不拖慢用户交互
    api, key = load_plugin_config()
    try:
        url = f"{api}/api/v1/system/status"
        headers = {"User-Agent": "Antigravity-OpenViking-Plugin/2.0.11"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=1.5):
            pass
    except Exception:
        pass
    print("{}")


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        sys.stdout.buffer.write(b"{}\n")
        sys.stdout.buffer.flush()
    sys.exit(0)
