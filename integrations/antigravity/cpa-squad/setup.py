#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenViking CPA Squad Plugin Installer (v1.0.0).
Antigravity IDE 官方标准自举向导：提供 2 个跨模型算力协同工兵工具的解耦部署。
"""

import argparse
import json
import shutil
from pathlib import Path

PLUGIN_SRC_DIR = Path(__file__).resolve().parent
DEFAULT_TARGET_DIR = Path.home() / ".gemini" / "config" / "plugins" / "cpa-squad"


def install_plugin(target_dir: Path, api: str, key: str):
    print(f"📦 正在准备安装 OpenViking CPA 算力插件至: {target_dir}")
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

    # 写入 config.json
    config_data = {
        "api_url": api or "http://127.0.0.1:1933",
        "api_key": key or "",
        "cpa_url": "https://api.deepseek.com",
        "cpa_key": ""
    }
    with open(target_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"🎉 OpenViking CPA 算力插件标准部署完成！(cpa-squad 2 Tools 已生效)")


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
