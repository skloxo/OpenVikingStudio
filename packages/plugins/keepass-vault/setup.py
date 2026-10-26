#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeePass Vault 官方标准自举向导与宿主集成引擎 (setup.py)
专为 Google Antigravity IDE / Desktop 打造：
1. 单一真相源 (SSOT) 动态直连 plugin.json 提取版本；
2. 双轨注册机制：联动注册宿主 config.json 注册表与 mcp_config.json；
3. 支持对称生命周期 (--install / --uninstall / --inspect)；
4. 物理隔离：受保护的私有 config.json 独立托管，绝不污染用户代码工作区。
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

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
    """单一真相源 (SSOT)：动态读取母本 plugin.json 提取版本号。"""
    pj = PLUGIN_SRC_DIR / "plugin.json"
    if pj.is_file():
        try:
            with open(pj, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("version", "1.2.1")
        except Exception:
            pass
    return "1.2.1"


PLUGIN_VERSION = get_plugin_version()


def get_python_cmd() -> str:
    return sys.executable.replace("\\", "/")


def register_in_ide_config(version: str) -> None:
    """写入宿主插件注册表 ~/.gemini/config/config.json"""
    cfg_file = GEMINI_CONFIG_DIR / "config.json"
    if not cfg_file.exists():
        return
    try:
        with open(cfg_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "plugins" not in cfg:
            cfg["plugins"] = {}
        cfg["plugins"][PLUGIN_NAME] = {
            "enabled": True,
            "installedFrom": {
                "id": f"openviking/plugin/{PLUGIN_NAME}",
                "marketplace": "openviking-studio",
                "version": version,
            },
        }
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"  ✔ [宿主注册表] ~/.gemini/config/config.json -> {PLUGIN_NAME} (v{version}) 写入成功")
    except Exception as e:
        print(f"  ⚠️ [宿主注册表] 注册跳过: {e}")


def unregister_from_ide_config() -> None:
    """从宿主注册表移除插件"""
    cfg_file = GEMINI_CONFIG_DIR / "config.json"
    if not cfg_file.exists():
        return
    try:
        with open(cfg_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "plugins" in cfg and PLUGIN_NAME in cfg["plugins"]:
            del cfg["plugins"][PLUGIN_NAME]
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
                f.write("\n")
            print(f"  ✔ [宿主注册表] 已安全注销 {PLUGIN_NAME}")
    except Exception as e:
        print(f"  ⚠️ [宿主注册表] 注销异常: {e}")


def register_mcp_servers(server_py_path: Path) -> None:
    """四维全覆盖双轨注册：联动写入 config 与 antigravity 的 mcp_config.json"""
    targets = [
        Path.home() / ".gemini" / "config" / "mcp_config.json",
        Path.home() / ".gemini" / "antigravity" / "mcp_config.json",
        Path.home() / ".gemini" / "antigravity-ide" / "mcp_config.json",
        Path.home() / ".gemini" / "mcp_config.json",
    ]
    py_exe = get_python_cmd()
    entry = {
        "command": py_exe,
        "args": [str(server_py_path.resolve()).replace("\\", "/")],
        "env": {"PYTHONIOENCODING": "utf-8"},
    }

    count = 0
    for t in targets:
        try:
            t.parent.mkdir(parents=True, exist_ok=True)
            cfg = {}
            if t.exists():
                with open(t, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            servers = cfg.get("mcpServers", {})
            servers[PLUGIN_NAME] = entry
            cfg["mcpServers"] = servers
            with open(t, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
                f.write("\n")
            count += 1
        except Exception:
            pass
    print(f"  ✔ [双轨 MCP] 已在 {count} 处宿主 mcp_config.json 成功挂载 {PLUGIN_NAME}")


def unregister_mcp_servers() -> None:
    """移除全局与私有 MCP 配置"""
    targets = [
        Path.home() / ".gemini" / "config" / "mcp_config.json",
        Path.home() / ".gemini" / "antigravity" / "mcp_config.json",
        Path.home() / ".gemini" / "antigravity-ide" / "mcp_config.json",
        Path.home() / ".gemini" / "mcp_config.json",
    ]
    for t in targets:
        if not t.exists():
            continue
        try:
            with open(t, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            servers = cfg.get("mcpServers", {})
            if PLUGIN_NAME in servers:
                del servers[PLUGIN_NAME]
                cfg["mcpServers"] = servers
                with open(t, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                    f.write("\n")
        except Exception:
            pass
    print(f"  ✔ [双轨 MCP] 已安全移除 {PLUGIN_NAME} 算子挂载")


def install_plugin(
    target_dir: Path,
    kdbx_path: str = "",
    master_key: str = "",
    password_env: str = "KPXC_MASTER_KEY",
) -> bool:
    print(f"📦 [keepass-vault] 正在部署 KeePass 凭据中枢 (v{PLUGIN_VERSION}) 至: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. 复制插件母本资产构件
    copy_items = [
        "plugin.json",
        "mcp_config.json",
        "hooks.json",
        "server.py",
        "setup.py",
        "README.md",
        "assets",
        "rules",
        "skills",
        "hooks",
    ]
    for item in copy_items:
        src = PLUGIN_SRC_DIR / item
        dst = target_dir / item
        if src.exists():
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

    # 2. 智能嗅探数据库路径
    final_kdbx = kdbx_path.strip()
    if not final_kdbx:
        desktop_kdbx = Path.home() / "Desktop" / "Key.kdbx"
        if desktop_kdbx.is_file():
            final_kdbx = str(desktop_kdbx).replace("\\", "/")

    # 3. 写入私有飞地受保护配置
    cfg_data: Dict[str, Any] = {
        "kdbx_path": final_kdbx or "C:/Users/Skl/Desktop/Key.kdbx",
        "master_key": master_key or "",
        "password_env": password_env or "KPXC_MASTER_KEY",
        "version": PLUGIN_VERSION,
    }

    # 若原有已有配置且未传新密码，保留原有密码
    existing_cfg = target_dir / "config.json"
    if existing_cfg.is_file() and not master_key:
        try:
            with open(existing_cfg, "r", encoding="utf-8") as f:
                old_c = json.load(f)
                if old_c.get("master_key"):
                    cfg_data["master_key"] = old_c["master_key"]
                if not kdbx_path and old_c.get("kdbx_path"):
                    cfg_data["kdbx_path"] = old_c["kdbx_path"]
        except Exception:
            pass

    with open(target_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(cfg_data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  ✔ [私有配置] 已写入受保护配置 (目标库: {cfg_data['kdbx_path']})")

    # 4. 注册宿主与 MCP
    register_in_ide_config(PLUGIN_VERSION)
    register_mcp_servers(target_dir / "server.py")

    print(f"🎉 KeePass 凭据保险箱插件部署成功！(v{PLUGIN_VERSION})")
    return True


def uninstall_plugin(target_dir: Path) -> bool:
    print(f"🗑️ [keepass-vault] 正在卸载插件: {target_dir}")
    unregister_from_ide_config()
    unregister_mcp_servers()

    if target_dir.exists():
        try:
            # 保留历史 .bak 快照防误删
            shutil.rmtree(target_dir)
            print(f"  ✔ [目录清理] 已彻底清除 {target_dir}")
        except Exception as e:
            print(f"  ⚠️ [目录清理] 部分文件清理异常: {e}")
    print(f"🎉 KeePass Vault 插件已完全卸载并恢复纯净状态。")
    return True


def inspect_plugin(target_dir: Path) -> Dict[str, Any]:
    print(f"🔍 [keepass-vault] 正在执行全链路物理真实自检...")
    cli_check = shutil.which("keepassxc-cli") is not None
    cfg_file = target_dir / "config.json"
    cfg: Dict[str, Any] = {}
    if cfg_file.is_file():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass

    kdbx_path = cfg.get("kdbx_path") or str(Path.home() / "Desktop" / "Key.kdbx")
    db_exists = os.path.isfile(kdbx_path)

    pwd_env = cfg.get("password_env", "KPXC_MASTER_KEY")
    master_key = cfg.get("master_key") or os.environ.get(pwd_env, "") or os.environ.get("KPXC_MASTER_KEY", "")

    can_unlock = False
    entry_count = 0
    unlock_err = ""

    if cli_check and db_exists and master_key:
        try:
            proc = subprocess.Popen(
                ["keepassxc-cli", "ls", "-q", kdbx_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            out, err = proc.communicate(input=master_key + "\n", timeout=8)
            if proc.returncode == 0:
                can_unlock = True
                lines = [l for l in out.splitlines() if l.strip()]
                entry_count = len(lines)
            else:
                unlock_err = err.strip()
        except Exception as e:
            unlock_err = str(e)

    report = {
        "plugin_version": PLUGIN_VERSION,
        "cli_available": cli_check,
        "db_path": kdbx_path,
        "db_exists": db_exists,
        "has_master_key": bool(master_key),
        "can_unlock": can_unlock,
        "entry_count": entry_count,
        "error": unlock_err,
    }

    print("==================================================")
    print(f"📋 插件版本: v{report['plugin_version']}")
    print(f"⚙️ keepassxc-cli 可用: {'✅ YES' if cli_check else '❌ NOT FOUND'}")
    print(f"📂 数据库文件: {kdbx_path} ({'✅ 存在' if db_exists else '❌ 不存在'})")
    print(f"🔑 主密钥已配置: {'✅ YES' if bool(master_key) else '❌ 缺失'}")
    print(f"🔓 解锁测试: {'✅ SUCCESS' if can_unlock else '❌ FAILED'}")
    if can_unlock:
        print(f"📊 根分组条目数: {entry_count} 条 (数据库完全正常)")
    elif unlock_err:
        print(f"⚠️ 解锁报错详情: {unlock_err}")
    print("==================================================")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="KeePass Vault 插件自举向导与健康自检")
    parser.add_argument("--install", action="store_true", help="安装插件并写入宿主注册表")
    parser.add_argument("--uninstall", action="store_true", help="卸载插件并清理注册表")
    parser.add_argument("--inspect", action="store_true", help="执行真实物理体检探针")
    parser.add_argument("--target", type=str, default="", help="指定目标安装路径")
    parser.add_argument("--kdbx", type=str, default="", help="指定 KeePass .kdbx 数据库文件路径")
    parser.add_argument("--key", type=str, default="", help="指定解密主密钥")
    parser.add_argument("--env-name", type=str, default="KPXC_MASTER_KEY", help="指定环境变量名称")
    args = parser.parse_args()

    target_dir = Path(args.target).resolve() if args.target else DEFAULT_TARGET_DIR

    if args.uninstall:
        uninstall_plugin(target_dir)
        return

    if args.inspect:
        inspect_plugin(target_dir)
        return

    # 默认执行安装
    kdbx_val = args.kdbx
    key_val = args.key

    # 若未带参数且非静默模式，提供自然友好的终端提示
    if not args.install and not kdbx_val and not key_val:
        desktop_kdbx = Path.home() / "Desktop" / "Key.kdbx"
        default_prompt = f" [{desktop_kdbx}]" if desktop_kdbx.is_file() else ""
        try:
            user_kdbx = input(f"📂 请输入 KeePass .kdbx 数据库路径{default_prompt}: ").strip()
            kdbx_val = user_kdbx or (str(desktop_kdbx) if desktop_kdbx.is_file() else "")
            key_val = getpass.getpass("🔑 请输入数据库解密主密码 (输入隐藏): ").strip()
        except Exception:
            pass

    install_plugin(target_dir, kdbx_path=kdbx_val, master_key=key_val, password_env=args.env_name)
    inspect_plugin(target_dir)


if __name__ == "__main__":
    main()
