#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenViking CPA Squad Plugin Installer (v1.0.1).
Antigravity IDE 官方标准自举向导：提供 2 个跨模型算力协同工兵工具的解耦部署。
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

PLUGIN_NAME = "cpa-squad"
PLUGIN_SRC_DIR = Path(__file__).resolve().parent
GEMINI_CONFIG_DIR = Path.home() / ".gemini" / "config"
DEFAULT_TARGET_DIR = GEMINI_CONFIG_DIR / "plugins" / PLUGIN_NAME


def get_plugin_version() -> str:
    pj = PLUGIN_SRC_DIR / "plugin.json"
    if pj.exists():
        try:
            with open(pj, "r", encoding="utf-8") as f:
                return json.load(f).get("version", "1.0.1")
        except Exception:
            pass
    return "1.0.1"


PLUGIN_VERSION = get_plugin_version()


def resolve_best_api(preferred_api: str = "") -> str:
    if preferred_api and str(preferred_api).strip():
        return str(preferred_api).strip().rstrip("/")
    local_api = "http://127.0.0.1:1933"
    try:
        req = urllib.request.Request(f"{local_api}/health")
        with urllib.request.urlopen(req, timeout=0.6) as resp:
            if resp.status == 200:
                return local_api
    except Exception:
        pass
    env_api = os.environ.get("OPENVIKING_API", "").strip()
    return env_api.rstrip("/") if env_api else "https://vk.tide.red"


def register_in_ide_config(plugin_name: str, version: str):
    cfg_file = GEMINI_CONFIG_DIR / "config.json"
    if not cfg_file.exists():
        return
    try:
        with open(cfg_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "plugins" not in cfg:
            cfg["plugins"] = {}
        cfg["plugins"][plugin_name] = {
            "installedFrom": {
                "id": f"openviking/plugin/{plugin_name}",
                "marketplace": "openviking-marketplace",
                "version": version
            }
        }
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"  ✔ 宿主注册表写入: ~/.gemini/config/config.json -> {plugin_name} v{version}")
    except Exception as e:
        print(f"  ⚠ 宿主注册表更新跳过: {e}")


def install_plugin(target_dir: Path, api: str, key: str):
    print(f"📦 正在准备安装 OpenViking CPA 算力插件 (v{PLUGIN_VERSION}) 至: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    copy_items = ["skills", "plugin.json", "mcp_config.json", "setup.py"]
    for item_name in copy_items:
        src = PLUGIN_SRC_DIR / item_name
        dst = target_dir / item_name
        if src.exists():
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

    final_api = resolve_best_api(api)
    config_data = {
        "api_url": final_api,
        "api_key": key or "",
        "cpa_url": "https://api.deepseek.com",
        "cpa_key": ""
    }
    with open(target_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    register_in_ide_config(PLUGIN_NAME, PLUGIN_VERSION)
    print(f"🎉 OpenViking CPA 算力插件标准部署完成！(cpa-squad 2 Tools 已生效, API: {final_api})")


def main():
    parser = argparse.ArgumentParser(description="OpenViking CPA 算力插件安装向导")
    parser.add_argument("--install", action="store_true", help="安装插件至 Antigravity 插件目录")
    parser.add_argument("--target", type=str, default="", help="指定安装目标目录")
    parser.add_argument("--api", type=str, default="", help="OpenViking API 地址")
    parser.add_argument("--key", type=str, default="", help="OpenViking API Key")
    args = parser.parse_args()

    target_dir = Path(args.target).resolve() if args.target else DEFAULT_TARGET_DIR
    api = args.api or "http://127.0.0.1:1933"
    key = args.key or ""
    install_plugin(target_dir, api, key)


if __name__ == "__main__":
    main()
