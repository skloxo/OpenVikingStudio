#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking Antigravity Plugin Session Archiver Hook (v2.0.42 - Async Detached Worker Edition)
生命周期事件: Stop
职责契约：
1. 本钩子仅执行轻量级 Fail-Open 存活探测，并脱钩唤醒后台独立 Miner 进程（耗时 <= 30ms）；
2. 严禁在 Stop 阶段发起阻塞式高延迟调用（绝对满足 3s 超时门禁）；
3. 真实会话脱水、踩坑自愈审计与 Master Memory 回填由后台 async_session_miner.py 异步完成。
"""

import json
import os
import subprocess
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


def extract_transcript_path() -> str:
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.readline()
            if raw and raw.strip():
                data = json.loads(raw.strip())
                return str(data.get("transcriptPath") or data.get("transcript_path") or "").strip()
    except Exception:
        pass
    return ""


def spawn_async_miner(transcript_path: str) -> None:
    miner_script = Path(__file__).resolve().parent / "async_session_miner.py"
    if not miner_script.exists() or not transcript_path or not os.path.exists(transcript_path):
        return

    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)

    try:
        subprocess.Popen(
            [sys.executable, str(miner_script), "--transcript", str(transcript_path)],
            creationflags=flags,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def main():
    transcript_path = extract_transcript_path()
    if transcript_path:
        spawn_async_miner(transcript_path)

    api, key = load_plugin_config()
    try:
        url = f"{api}/api/v1/system/status"
        headers = {"User-Agent": "Antigravity-OpenViking-Plugin/2.0.42"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=0.8):
            pass
    except Exception:
        pass

    sys.stdout.buffer.write(b"{}\n")
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        sys.stdout.buffer.write(b"{}\n")
        sys.stdout.buffer.flush()
    sys.exit(0)
