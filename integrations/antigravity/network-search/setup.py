#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Network Search Gateway Plugin Installer (v1.1.2).
Antigravity IDE 官方标准自举向导：提供 12 个多引擎联网搜索与无头网页抓取工具的解耦部署。
支持拓扑自适应、宿主注册表写入与双轨 MCP 联动。
"""

import argparse
import json
import os
import shutil
import sys
import urllib.request
from pathlib import Path

# SECTION: Windows UTF-8 Stdio Safeguard
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PLUGIN_NAME = "network-search"
PLUGIN_SRC_DIR = Path(__file__).resolve().parent
GEMINI_CONFIG_DIR = Path.home() / ".gemini" / "config"
DEFAULT_TARGET_DIR = GEMINI_CONFIG_DIR / "plugins" / PLUGIN_NAME


def get_plugin_version() -> str:
    pj = PLUGIN_SRC_DIR / "plugin.json"
    if pj.exists():
        try:
            with open(pj, "r", encoding="utf-8") as f:
                return json.load(f).get("version", "1.1.2")
        except Exception:
            pass
    return "1.1.2"


PLUGIN_VERSION = get_plugin_version()


def install(target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)
    for item in ["plugin.json", "README.md", "server.py", "mcp_config.json", "config.json"]:
        src = PLUGIN_SRC_DIR / item
        if src.exists():
            shutil.copy2(src, target_dir / item)
    skills_src = PLUGIN_SRC_DIR / "skills"
    if skills_src.exists():
        skills_dst = target_dir / "skills"
        if skills_dst.exists():
            shutil.rmtree(skills_dst)
        shutil.copytree(skills_src, skills_dst)
    print(f"✅ 成功部署 {PLUGIN_NAME} v{PLUGIN_VERSION} 到 {target_dir}")


def main():
    parser = argparse.ArgumentParser(description=f"{PLUGIN_NAME} 自举安装向导 (v{PLUGIN_VERSION})")
    parser.add_argument("--target", type=str, default=str(DEFAULT_TARGET_DIR), help="安装目标目录")
    args = parser.parse_args()
    install(Path(args.target))


if __name__ == "__main__":
    main()
