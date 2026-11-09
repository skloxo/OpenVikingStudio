#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tududi Task Manager 官方标准自举向导与宿主集成引擎 (setup.py)
专为 Google Antigravity IDE / Desktop 打造：
1. 单一真相源 (SSOT) 动态直连 plugin.json 提取版本；
2. 自动化凭据装配：支持 --token / --key / 环境变量 / 现有配置继承；
3. 双轨注册机制：联动注册宿主 config.json 注册表与私有 mcp_config.json (core)；
4. 支持对称生命周期 (--install / --uninstall / --inspect)。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict
import requests

# Windows UTF-8 Stdio Safeguard
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PLUGIN_NAME = "tududi"
PLUGIN_SRC_DIR = Path(__file__).resolve().parent
GEMINI_CONFIG_DIR = Path.home() / ".gemini" / "config"
ANTIGRAVITY_DIR = Path.home() / ".gemini" / "antigravity"
DEFAULT_TARGET_DIR = GEMINI_CONFIG_DIR / "plugins" / PLUGIN_NAME


def get_plugin_version() -> str:
    pj = PLUGIN_SRC_DIR / "plugin.json"
    if pj.is_file():
        try:
            with open(pj, "r", encoding="utf-8") as f:
                return json.load(f).get("version", "1.1.2")
        except Exception:
            pass
    return "1.1.2"


PLUGIN_VERSION = get_plugin_version()


def sync_assets_to_target(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    if PLUGIN_SRC_DIR.resolve() != target_dir.resolve():
        copy_items = [
            "plugin.json",
            "package.json",
            "hooks.json",
            "server.py",
            "setup.py",
            "README.md",
            "tools.json",
            "index.js",
            "schema.js",
            "cordis.patch.yml",
            "assets",
            "hooks",
            "rules",
            "skills",
        ]
        for item in copy_items:
            src = PLUGIN_SRC_DIR / item
            dst = target_dir / item
            if src.exists():
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)

    # 动态渲染绝对路径 hooks.json，注入 -X utf8 -E -s -S 隔离防护
    py_exe = sys.executable.replace("\\", "/")
    guard_py = (target_dir / "hooks" / "tududi_guard.py").resolve().as_posix()
    hooks_cfg = {
        "tududi-okr-gtd-guard": {
            "PreToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{py_exe} -X utf8 -E -s -S {guard_py}",
                            "timeout": 3,
                        }
                    ],
                }
            ]
        }
    }
    with open(target_dir / "hooks.json", "w", encoding="utf-8") as f:
        json.dump(hooks_cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")


def configure_credentials(
    target_dir: Path,
    token: str | None = None,
    public_url: str | None = None,
    internal_url: str | None = None,
) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = target_dir / "config.json"
    cfg: Dict[str, Any] = {
        "public_url": public_url or "https://todo.tide.red/api/mcp",
        "internal_url": internal_url or "http://10.128.226.5:3002/api/mcp",
        "api_token": token or "",
        "timeout": 20,
    }
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                old = json.load(f)
            if not token and old.get("api_token"):
                cfg["api_token"] = old["api_token"]
            if not public_url and old.get("public_url"):
                cfg["public_url"] = old["public_url"]
            if not internal_url and old.get("internal_url"):
                cfg["internal_url"] = old["internal_url"]
        except Exception:
            pass

    if not cfg["api_token"]:
        cfg["api_token"] = os.environ.get("TUDUDI_API_TOKEN", "")

    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")

    if cfg["api_token"]:
        masked = cfg["api_token"][:7] + "***"
        print(f"  ✔ [凭据配置] {cfg_file} -> Token 配置成功 ({masked})")
    else:
        print(f"  ⚠️ [凭据告警] {cfg_file} 已生成，但 Token 为空！请执行: python setup.py --install --token <TOKEN>")


def register_in_ide_config(version: str) -> None:
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
                "id": f"antigravity/plugin/{PLUGIN_NAME}",
                "marketplace": "openviking-studio",
                "version": version,
            },
        }
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"  ✔ [宿主注册表] {cfg_file} -> {PLUGIN_NAME} (v{version}) 写入成功")
    except Exception as e:
        print(f"  ⚠️ [宿主注册表] 注册跳过: {e}")


def unregister_from_ide_config() -> None:
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


def register_mcp_config(target_dir: Path) -> None:
    py_exe = sys.executable.replace("\\", "/")
    srv_py = (target_dir / "server.py").resolve().as_posix()

    # 1. 自内聚动态写入插件私有 mcp_config.json (核心服务名 core，释放 64 字符工具名预算)
    try:
        p_mcp = {
            "mcpServers": {
                "core": {
                    "command": py_exe,
                    "args": [srv_py],
                    "env": {"PYTHONIOENCODING": "utf-8"},
                }
            }
        }
        with open(target_dir / "mcp_config.json", "w", encoding="utf-8") as f:
            json.dump(p_mcp, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  ✔ [私有MCP] {target_dir / 'mcp_config.json'} -> core 自内聚挂载完成")
    except Exception as e:
        print(f"  ⚠️ [私有MCP] 写入异常: {e}")

    # 2. 全局双轨联动写入宿主 mcp_config.json
    targets = [
        GEMINI_CONFIG_DIR / "mcp_config.json",
        ANTIGRAVITY_DIR / "mcp_config.json",
        Path.home() / ".gemini" / "antigravity-ide" / "mcp_config.json",
        Path.home() / ".gemini" / "mcp_config.json",
    ]
    for mcp_file in targets:
        if not mcp_file.parent.exists():
            continue
        cfg = {"mcpServers": {}}
        if mcp_file.exists():
            try:
                with open(mcp_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {"mcpServers": {}}
        if "mcpServers" not in cfg:
            cfg["mcpServers"] = {}
        cfg["mcpServers"][PLUGIN_NAME] = {
            "command": py_exe,
            "args": [srv_py],
            "env": {"PYTHONIOENCODING": "utf-8"},
        }
        with open(mcp_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"  ✔ [MCP注册] {mcp_file} -> {PLUGIN_NAME} 挂载完成")


def unregister_mcp_config() -> None:
    targets = [
        GEMINI_CONFIG_DIR / "mcp_config.json",
        ANTIGRAVITY_DIR / "mcp_config.json",
        Path.home() / ".gemini" / "antigravity-ide" / "mcp_config.json",
        Path.home() / ".gemini" / "mcp_config.json",
    ]
    for mcp_file in targets:
        if not mcp_file.exists():
            continue
        try:
            with open(mcp_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            servers = cfg.get("mcpServers", {})
            if PLUGIN_NAME in servers:
                del servers[PLUGIN_NAME]
                cfg["mcpServers"] = servers
                with open(mcp_file, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                    f.write("\n")
        except Exception:
            pass
    print(f"  ✔ [MCP注销] 已从全局 mcp_config.json 安全移除 {PLUGIN_NAME}")


def inspect(target_dir: Path) -> bool:
    print("=" * 60)
    print(f"🔍 检查 Tududi 反重力插件物理健康度 (v{PLUGIN_VERSION})")
    print("=" * 60)
    cfg_file = target_dir / "config.json"
    if not cfg_file.exists() and (PLUGIN_SRC_DIR / "config.json").exists():
        cfg_file = PLUGIN_SRC_DIR / "config.json"
    if not cfg_file.exists():
        print("  ❌ [配置缺失] config.json 不存在，请执行 setup.py --install --token <TOKEN>")
        return False
    with open(cfg_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    token = cfg.get("api_token", "")
    public_url = cfg.get("public_url", "")
    internal_url = cfg.get("internal_url", "")
    token_masked = token[:7] + "***" if len(token) > 10 else "***"
    print(f"  📍 公网端点: {public_url}")
    print(f"  📍 局域端点: {internal_url}")
    print(f"  🔑 凭据令牌: {token_masked}")

    if not token:
        print("  ❌ [Token缺失] api_token 为空，无法通过鉴权")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/event-stream",
    }
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    s = requests.Session()
    s.trust_env = False
    for target, req_timeout in [(public_url, 8), (internal_url, 2)]:
        try:
            r = s.post(target, headers=headers, json=payload, timeout=req_timeout)
            r.encoding = "utf-8"
            if r.status_code == 200:
                tools = []
                text_body = r.content.decode("utf-8", errors="replace").strip()
                for line in text_body.split("\n"):
                    if line.startswith("data: "):
                        tools = json.loads(line[6:]).get("result", {}).get("tools", [])
                        break
                print(f"  ✔ [链路连通] {target} -> 成功响应 200 OK，探测到 {len(tools)} 个 MCP 工具算子")
                return True
            else:
                print(f"  ⚠️ [链路告警] {target} -> HTTP {r.status_code}")
        except Exception as exc:
            print(f"  ⚠️ [链路不可达] {target} -> {exc}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Tududi Plugin Setup")
    parser.add_argument("--install", action="store_true", help="安装与注册插件")
    parser.add_argument("--token", "--key", dest="token", type=str, default=None, help="Tududi API Token (Bearer)")
    parser.add_argument("--api", "--public-url", dest="public_url", type=str, default=None, help="公网 MCP URL")
    parser.add_argument("--internal-url", type=str, default=None, help="内网 MCP URL")
    parser.add_argument("--target", type=str, default="", help="指定目标安装目录")
    parser.add_argument("--uninstall", action="store_true", help="卸载插件")
    parser.add_argument("--inspect", action="store_true", help="体检链路与工具健康度")
    args = parser.parse_args()

    target_dir = Path(args.target).resolve() if args.target else DEFAULT_TARGET_DIR

    if args.install:
        print(f"📦 开始安装与注册 Tududi 原生插件 (v{PLUGIN_VERSION})...")
        sync_assets_to_target(target_dir)
        configure_credentials(target_dir, args.token, args.public_url, args.internal_url)
        register_in_ide_config(PLUGIN_VERSION)
        register_mcp_config(target_dir)
        print("🎉 安装注册流程已完成！")
    elif args.uninstall:
        print("🗑️ 正在安全卸载 Tududi 插件...")
        unregister_from_ide_config()
        unregister_mcp_config()
        print("✔ 卸载完成。")
    elif args.inspect:
        ok = inspect(target_dir)
        sys.exit(0 if ok else 1)
    else:
        inspect(target_dir)


if __name__ == "__main__":
    main()
