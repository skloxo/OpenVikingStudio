#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dify Orchestrator Plugin Installer & Health Inspector (v1.0.0).
Antigravity IDE 官方标准自举向导：提供 Dify 12 个控制面工具的解耦部署。
"""

import argparse
import json
import shutil
from pathlib import Path

PLUGIN_SRC_DIR = Path(__file__).resolve().parent
DEFAULT_TARGET_DIR = Path.home() / ".gemini" / "config" / "plugins" / "dify"


def install_plugin(target_dir: Path, api_url: str, admin_key: str, workspace_id: str):
    print(f"📦 正在准备安装 Dify 编排插件至: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    copy_items = ["plugin.json", "mcp_config.json", "dify_mcp_server.py", "setup.py"]
    for item_name in copy_items:
        src = PLUGIN_SRC_DIR / item_name
        dst = target_dir / item_name
        if src.exists():
            shutil.copy2(src, dst)

    # 写入 config.json
    config_data = {
        "api_url": api_url or "http://127.0.0.1:13000",
        "admin_key": admin_key or "",
        "workspace_id": workspace_id or ""
    }
    with open(target_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"🎉 Dify 编排插件标准部署完成！(已配置 API: {config_data['api_url']})")


def inspect_plugin(target_dir: Path):
    print(f"🔍 正在巡检 Dify 插件: {target_dir}")
    cfg_file = target_dir / "config.json"
    server_file = target_dir / "dify_mcp_server.py"
    if not cfg_file.exists() or not server_file.exists():
        print(f"❌ 关键构件缺失！")
        return False

    with open(cfg_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    print(f"  ✔ API URL 配置: {cfg.get('api_url')}")
    print(f"  ✔ Admin Key 状态: {'已配置' if cfg.get('admin_key') else '未配置'}")
    print(f"  ✔ Workspace ID: {cfg.get('workspace_id') or 'default'}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Dify 编排插件安装向导")
    parser.add_argument("--install", action="store_true", help="安装插件至 Antigravity 插件目录")
    parser.add_argument("--inspect", action="store_true", help="检查插件健康状态")
    parser.add_argument("--target", type=str, default="", help="指定安装目标目录")
    parser.add_argument("--api-url", type=str, default="", help="Dify API 控制台地址")
    parser.add_argument("--admin-key", type=str, default="", help="Dify Admin Key")
    parser.add_argument("--workspace-id", type=str, default="", help="Dify 工作区 UUID")
    args = parser.parse_args()

    target_dir = Path(args.target).resolve() if args.target else DEFAULT_TARGET_DIR
    if args.inspect:
        inspect_plugin(target_dir)
        return

    install_plugin(target_dir, args.api_url, args.admin_key, args.workspace_id)
    print("\n" + "=" * 50)
    inspect_plugin(target_dir)


if __name__ == "__main__":
    main()
