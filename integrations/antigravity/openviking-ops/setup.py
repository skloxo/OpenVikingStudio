#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking System Ops Plugin Installer & Health Inspector.
Antigravity IDE 官方标准自举向导：提供 16 项运维特权工具与认知层技能的自内聚部署。
"""

import argparse
import json
import os
import shutil
import stat
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

PLUGIN_NAME = "openviking-ops"
PLUGIN_SRC_DIR = Path(__file__).resolve().parent
GEMINI_CONFIG_DIR = Path.home() / ".gemini" / "config"
DEFAULT_TARGET_DIR = GEMINI_CONFIG_DIR / "plugins" / PLUGIN_NAME


def get_plugin_version() -> str:
    pj = PLUGIN_SRC_DIR / "plugin.json"
    if pj.exists():
        try:
            with open(pj, "r", encoding="utf-8") as f:
                return json.load(f).get("version", "1.0.4")
        except Exception:
            pass
    return "1.0.4"


PLUGIN_VERSION = get_plugin_version()


def get_python_cmd() -> str:
    py_exe = sys.executable.replace("\\", "/")
    return f'"{py_exe}"' if " " in py_exe else py_exe


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
        plugins = cfg.get("plugins", {})
        plugins[plugin_name] = {
            "installedFrom": {
                "id": f"openviking/plugin/{plugin_name}",
                "marketplace": "openviking-marketplace",
                "version": version
            }
        }
        cfg["plugins"] = plugins
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print(f"  ✔ 成功在 IDE config.json 注册表登记 {plugin_name} (v{version})")
    except Exception as e:
        print(f"  ⚠️ 注册 IDE config.json 失败: {e}")


def sync_mcp_ops(api: str, key: str, target_dir: Path):
    server_script = (target_dir / "server.py").resolve().as_posix()
    py_cmd = sys.executable.replace("\\", "/")

    p_mcp = {
        "mcpServers": {
            "openviking-ops": {
                "command": py_cmd,
                "args": [server_script],
                "env": {
                    "OPENVIKING_API": api,
                    "OPENVIKING_API_KEY": key,
                    "OPENVIKING_ACTOR_PEER": "antigravity@2080Ti",
                    "PYTHONIOENCODING": "utf-8"
                }
            }
        }
    }
    with open(target_dir / "mcp_config.json", "w", encoding="utf-8") as f:
        json.dump(p_mcp, f, indent=2, ensure_ascii=False)
    print("  ✔ 插件目录 mcp_config.json 生成完成 (自内聚 server.py)")

    g_mcp_path = GEMINI_CONFIG_DIR / "mcp_config.json"
    if g_mcp_path.exists():
        try:
            with open(g_mcp_path, "r", encoding="utf-8") as f:
                g_data = json.load(f)
            servers = g_data.get("mcpServers", {})
            servers["openviking-ops"] = {
                "command": py_cmd,
                "args": [server_script],
                "env": {
                    "OPENVIKING_API": api,
                    "OPENVIKING_API_KEY": key,
                    "OPENVIKING_ACTOR_PEER": "antigravity@2080Ti",
                    "PYTHONIOENCODING": "utf-8"
                }
            }
            g_data["mcpServers"] = servers
            with open(g_mcp_path, "w", encoding="utf-8") as f:
                json.dump(g_data, f, indent=2, ensure_ascii=False)
            print("  ✔ 全局 mcp_config.json openviking-ops 条目联动完成")
        except Exception as e:
            print(f"  ⚠️ 全局 mcp_config.json 联动失败: {e}")


def install_plugin(target_dir: Path, api: str, key: str):
    print(f"📦 正在准备安装 OpenViking 运维特权插件 (v{PLUGIN_VERSION}) 至: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    copy_items = ["hooks", "skills", "plugin.json", "mcp_config.json", "server.py", "setup.py"]
    for item_name in copy_items:
        src = PLUGIN_SRC_DIR / item_name
        dst = target_dir / item_name
        if src.exists():
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

    # 渲染 hooks.json (双 Hook 物理守卫)
    py_cmd = get_python_cmd()
    audit_script = (target_dir / "hooks" / "ov_ops_audit.py").resolve()
    audit_path = str(audit_script).replace("\\", "/")
    audit_cmd = f'{py_cmd} -E -s -S "{audit_path}"' if " " in audit_path else f"{py_cmd} -E -s -S {audit_path}"

    sentinel_script = (target_dir / "hooks" / "ov_ops_sentinel.py").resolve()
    sentinel_path = str(sentinel_script).replace("\\", "/")
    sentinel_cmd = f'{py_cmd} -E -s -S "{sentinel_path}"' if " " in sentinel_path else f"{py_cmd} -E -s -S {sentinel_path}"

    hooks_cfg = {
        "openviking-ops-sentinel": {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": sentinel_cmd,
                            "timeout": 3
                        }
                    ]
                }
            ]
        },
        "openviking-ops-audit": {
            "PreToolUse": [
                {
                    "matcher": "openviking_server_control",
                    "hooks": [
                        {
                            "type": "command",
                            "command": audit_cmd,
                            "timeout": 3
                        }
                    ]
                }
            ]
        }
    }
    with open(target_dir / "hooks.json", "w", encoding="utf-8") as f:
        json.dump(hooks_cfg, f, indent=2, ensure_ascii=False)
    print("  ✔ hooks.json 审计守卫构建完成 (双 Hook 物理守卫: sentinel + audit)")

    # 凭据配置
    cfg_data = {
        "api_url": api,
        "api_key": key,
        "verified_user": "admin"
    }
    cfg_file = target_dir / "config.json"
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(cfg_data, f, indent=2, ensure_ascii=False)
    try:
        os.chmod(cfg_file, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass
    print("  ✔ config.json 凭据落盘完成 (0600)")

    register_in_ide_config(PLUGIN_NAME, PLUGIN_VERSION)
    sync_mcp_ops(api, key, target_dir)

    print(f"\n🎉 OpenViking 运维特权插件 (v{PLUGIN_VERSION}) 安装就绪！")


def main():
    parser = argparse.ArgumentParser(description="OpenViking 运维插件标准自举安装器")
    parser.add_argument("--install", action="store_true", help="安装插件")
    parser.add_argument("--api", type=str, default="", help="API 地址")
    parser.add_argument("--key", type=str, default="", help="API Key")
    parser.add_argument("--target", type=str, default="", help="目标目录")

    args = parser.parse_args()
    target_dir = Path(args.target).resolve() if args.target else DEFAULT_TARGET_DIR

    api = resolve_best_api(args.api)
    key = args.key or os.environ.get("OPENVIKING_API_KEY", "")
    if not key:
        cfg = target_dir / "config.json"
        if cfg.exists():
            try:
                with open(cfg, "r", encoding="utf-8") as f:
                    key = json.load(f).get("api_key", "")
            except Exception:
                pass
    if not key:
        mem_cfg = GEMINI_CONFIG_DIR / "plugins" / "openviking-memory" / "config.json"
        if mem_cfg.exists():
            try:
                with open(mem_cfg, "r", encoding="utf-8") as f:
                    key = json.load(f).get("api_key", "")
            except Exception:
                pass
    if not key:
        g_mcp = GEMINI_CONFIG_DIR / "mcp_config.json"
        if g_mcp.exists():
            try:
                with open(g_mcp, "r", encoding="utf-8") as f:
                    g_data = json.load(f)
                key = g_data.get("mcpServers", {}).get("openviking-memory", {}).get("env", {}).get("OPENVIKING_API_KEY", "")
            except Exception:
                pass

    install_plugin(target_dir, api, key)


if __name__ == "__main__":
    main()
