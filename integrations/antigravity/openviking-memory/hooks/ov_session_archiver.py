#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking Antigravity Plugin Session Archiver Hook (v2.0.41)
生命周期事件: Stop
职责契约：
1. 本钩子仅执行轻量级 Fail-Open 存活探测与状态心跳，耗时 <= 100ms；
2. 严禁在 Stop 阶段发起高延迟大模型同步熔炼（避免击穿 3s 超时门禁与注意力劫持）；
3. 记忆与经验结晶严格收口在任务结案收尾契约与 session-handover 门禁中。
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
    # Stop 钩子保持绝对静默，不干扰心流，不向主脑倒灌未经验证草稿
    api, key = load_plugin_config()
    try:
        url = f"{api}/api/v1/system/status"
        headers = {"User-Agent": "Antigravity-OpenViking-Plugin/2.0.41"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=1.0):
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
