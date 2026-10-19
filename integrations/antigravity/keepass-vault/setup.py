#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeePass Vault Plugin Installer & Health Inspector (v1.2.1).
Antigravity IDE 官方标准自举向导：支持 kdbx 数据库路径与访问密钥配置。
支持宿主注册表自动写入与健康自检。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# SECTION: Windows UTF-8 Stdio Safeguard
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PLUGIN_NAME = "keepass-vault"
PLUGIN_SRC_DIR = Path(__file__).resolve().parent
GEMINI_CONFIG_DIR = Path.home() / ".gemini" / "config"
DEFAULT_TARGET_DIR = GEMINI_CONFIG_DIR / "plugins" / PLUGIN_NAME


def get_plugin_version() -> str:
    pj = PLUGIN_SRC_DIR / "plugin.json"
    if pj.exists():
        try:
            with open(pj, "r", encoding="utf-8") as f:
                return json.load(f).get("version", "1.2.1")
        except Exception:
            pass
    return "1.2.1"


PLUGIN_VERSION = get_plugin_version()


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


def install_plugin(target_dir: Path, kdbx_path: str, master_key: str, password_env: str):
    print(f"📦 正在准备安装 KeePass Vault 插件 (v{PLUGIN_VERSION}) 至: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    copy_items = ["skills", "plugin.json", "mcp_config.json", "server.py", "setup.py"]
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
        "kdbx_path": kdbx_path or "C:/Users/Skl/Desktop/Key.kdbx",
        "key_file": "",
        "master_key": master_key or "",
        "password_env": password_env or "KPXC_MASTER_KEY"
    }
    with open(target_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    register_in_ide_config(PLUGIN_NAME, PLUGIN_VERSION)
    print(f"🎉 KeePass Vault 插件标准部署完成！(已配置 kdbx: {config_data['kdbx_path']})")


def inspect_plugin(target_dir: Path):
    print(f"🔍 正在巡检 KeePass Vault 插件: {target_dir}")
    cfg_file = target_dir / "config.json"
    server_file = target_dir / "server.py"
    if not cfg_file.exists() or not server_file.exists():
        print(f"❌ 关键构件缺失！")
        return False

    with open(cfg_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    print(f"  ✔ 本地数据库配置: {cfg.get('kdbx_path')}")
    print(f"  ✔ 密码环境变量配置: {cfg.get('password_env')}")
    cli_exists = shutil.which("keepassxc-cli") is not None
    print(f"  ✔ keepassxc-cli 系统命令可用: {cli_exists}")
    return True


def main():
    parser = argparse.ArgumentParser(description="KeePass Vault 插件安装向导")
    parser.add_argument("--install", action="store_true", help="安装插件至 Antigravity 插件目录")
    parser.add_argument("--inspect", action="store_true", help="检查插件健康状态")
    parser.add_argument("--target", type=str, default="", help="指定安装目标目录")
    parser.add_argument("--kdbx-path", type=str, default="", help="KeePass .kdbx 数据库路径")
    parser.add_argument("--master-key", type=str, default="", help="KeePass 主访问密钥")
    parser.add_argument("--password-env", type=str, default="KPXC_MASTER_KEY", help="密码环境变量名称")
    args = parser.parse_args()

    target_dir = Path(args.target).resolve() if args.target else DEFAULT_TARGET_DIR
    if args.inspect:
        inspect_plugin(target_dir)
        return

    install_plugin(target_dir, args.kdbx_path, args.master_key, args.password_env)
    print("\n" + "=" * 50)
    inspect_plugin(target_dir)


if __name__ == "__main__":
    main()
