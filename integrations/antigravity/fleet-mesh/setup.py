#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenViking Fleet Mesh Plugin Installer & Health Inspector (setup.py).

Antigravity IDE 官方标准自举向导：
1. 自内聚驱动直连：彻底拔除外部桌面路径硬编码，MCP 配置 100% 指向插件目录内 `server.py`；
2. 多节点网络自适应：优先探测本地 `127.0.0.1:1933`，离线自动切换 `OPENVIKING_API` / `https://vk.tide.red`；
3. 动态节点身份推导：自动解析 `antigravity@{hostname}`，拒绝写死单一机器代号与假用户名；
4. 对称生命周期与幽灵清洗：支持 `--install` / `--inspect` / `--uninstall`，自动清理残留别名。
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import stat
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, Tuple

# SECTION: Windows UTF-8 Stdio Safeguard
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PLUGIN_NAME = "fleet-mesh"
PLUGIN_SRC_DIR = Path(__file__).resolve().parent
GEMINI_CONFIG_DIR = Path.home() / ".gemini" / "config"
DEFAULT_TARGET_DIR = GEMINI_CONFIG_DIR / "plugins" / PLUGIN_NAME
DEFAULT_PUBLIC_API = "https://vk.tide.red"
DEFAULT_LOCAL_API = "http://127.0.0.1:1933"
GHOST_MCP_ALIASES = ("fleet", "openviking-fleet", "fleet_mesh")


def get_plugin_version() -> str:
    """Single Source of Truth: read version directly from plugin.json."""
    pj = PLUGIN_SRC_DIR / "plugin.json"
    if pj.is_file():
        try:
            data = json.loads(pj.read_text(encoding="utf-8-sig"))
            return str(data.get("version", "1.0.6")).strip()
        except Exception:
            pass
    return "1.0.6"


PLUGIN_VERSION = get_plugin_version()


def get_python_cmd() -> str:
    py_exe = sys.executable.replace("\\", "/")
    return f'"{py_exe}"' if " " in py_exe else py_exe


def _probe_local_health(url: str = DEFAULT_LOCAL_API, timeout: float = 0.6) -> bool:
    try:
        req = urllib.request.Request(f"{url.rstrip('/')}/health")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def resolve_best_api(preferred_api: str = "", target_dir: Path | None = None) -> str:
    """Resolve API URL: explicit CLI -> env -> live local loopback -> existing config -> public hub."""
    if preferred_api and str(preferred_api).strip():
        return str(preferred_api).strip().rstrip("/")
    env_api = os.environ.get("OPENVIKING_API", "").strip()
    if env_api:
        return env_api.rstrip("/")
    if _probe_local_health(DEFAULT_LOCAL_API):
        return DEFAULT_LOCAL_API
    check_dir = target_dir or DEFAULT_TARGET_DIR
    for cfg_path in (
        check_dir / "config.json",
        GEMINI_CONFIG_DIR / "plugins" / "openviking-memory" / "config.json",
    ):
        if cfg_path.is_file():
            try:
                api_url = str(json.loads(cfg_path.read_text(encoding="utf-8-sig")).get("api_url", "")).strip()
                if api_url:
                    return api_url.rstrip("/")
            except Exception:
                pass
    return DEFAULT_PUBLIC_API


def resolve_actor_peer(preferred_peer: str = "", target_dir: Path | None = None) -> str:
    """Derive adaptive actor peer identity without hardcoded node names."""
    if preferred_peer and str(preferred_peer).strip():
        return str(preferred_peer).strip()
    env_peer = os.environ.get("OPENVIKING_ACTOR_PEER", "").strip()
    if env_peer:
        return env_peer
    check_dir = target_dir or DEFAULT_TARGET_DIR
    cfg_path = check_dir / "config.json"
    if cfg_path.is_file():
        try:
            saved = str(json.loads(cfg_path.read_text(encoding="utf-8-sig")).get("actor_peer", "")).strip()
            if saved:
                return saved
        except Exception:
            pass
    host = (platform.node() or socket.gethostname() or "satellite").strip().lower()
    return f"antigravity@{host}"


def resolve_credentials(target_dir: Path, preferred_key: str = "") -> str:
    """Resolve API key from CLI arg -> env -> existing plugin config -> openviking-memory -> ovcli.conf."""
    if preferred_key and preferred_key.strip():
        return preferred_key.strip()
    env_key = os.environ.get("OPENVIKING_API_KEY", "").strip()
    if env_key:
        return env_key
    for cfg_path in (
        target_dir / "config.json",
        GEMINI_CONFIG_DIR / "plugins" / "openviking-memory" / "config.json",
        Path.home() / ".openviking" / "ovcli.conf",
    ):
        if cfg_path.is_file():
            try:
                data = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
                key = str(data.get("api_key") or "").strip()
                if key:
                    return key
            except Exception:
                pass
    return ""


def _read_json_file(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _write_json_file(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def register_in_ide_config(plugin_name: str, version: str) -> None:
    cfg_file = GEMINI_CONFIG_DIR / "config.json"
    if not cfg_file.is_file():
        return
    try:
        cfg = _read_json_file(cfg_file)
        plugins = cfg.setdefault("plugins", {})
        plugins[plugin_name] = {
            "enabled": True,
            "installedFrom": {
                "id": f"antigravity/plugin/{plugin_name}",
                "marketplace": "openviking-studio",
                "version": version,
            },
        }
        _write_json_file(cfg_file, cfg)
        print(f"  ✔ 成功在 IDE config.json 注册表登记 {plugin_name} (v{version})")
    except Exception as e:
        print(f"  ⚠️ 注册 IDE config.json 失败: {e}")


def unregister_from_ide_config(plugin_name: str) -> None:
    cfg_file = GEMINI_CONFIG_DIR / "config.json"
    if not cfg_file.is_file():
        return
    try:
        cfg = _read_json_file(cfg_file)
        plugins = cfg.get("plugins", {})
        if isinstance(plugins, dict) and plugin_name in plugins:
            del plugins[plugin_name]
            _write_json_file(cfg_file, cfg)
            print(f"  ✔ 已从 IDE config.json 注销 {plugin_name}")
    except Exception as e:
        print(f"  ⚠️ 注销 IDE config.json 失败: {e}")


def sync_mcp_fleet(api: str, key: str, target_dir: Path, actor_peer: str) -> None:
    """Bind private & global MCP entries to the self-contained target server.py."""
    server_script = (target_dir / "server.py").resolve().as_posix()
    py_cmd = sys.executable.replace("\\", "/")
    env_payload = {
        "OPENVIKING_API": api,
        "OPENVIKING_API_KEY": key,
        "OPENVIKING_ACTOR_PEER": actor_peer,
        "PYTHONIOENCODING": "utf-8",
    }

    p_mcp = {"mcpServers": {"core": {"command": py_cmd, "args": [server_script], "env": env_payload}}}
    _write_json_file(target_dir / "mcp_config.json", p_mcp)
    print(f"  ✔ 插件私有 mcp_config.json 已直连自内聚 server.py (Peer: {actor_peer})")

    g_mcp_path = GEMINI_CONFIG_DIR / "mcp_config.json"
    if g_mcp_path.is_file():
        try:
            g_data = _read_json_file(g_mcp_path)
            servers = g_data.setdefault("mcpServers", {})
            for alias in GHOST_MCP_ALIASES:
                servers.pop(alias, None)
            servers[PLUGIN_NAME] = {"command": py_cmd, "args": [server_script], "env": env_payload}
            _write_json_file(g_mcp_path, g_data)
            print("  ✔ 全局 mcp_config.json fleet-mesh 已对齐并清洗残留别名")
        except Exception as e:
            print(f"  ⚠️ 全局 mcp_config.json 联动失败: {e}")


def install_plugin(target_dir: Path, api: str, key: str, actor_peer: str = "") -> Tuple[str, str]:
    peer = resolve_actor_peer(actor_peer, target_dir=target_dir)
    print(f"📦 正在准备安装 OpenViking 卫星同频插件 (v{PLUGIN_VERSION}) 至: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    is_same_dir = False
    try:
        is_same_dir = target_dir.resolve() == PLUGIN_SRC_DIR.resolve()
    except Exception:
        pass

    if not is_same_dir:
        for item_name in ("skills", "plugin.json", "server.py", "setup.py", "README.md"):
            src = PLUGIN_SRC_DIR / item_name
            dst = target_dir / item_name
            if not src.exists():
                continue
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

    cfg_file = target_dir / "config.json"
    config_data = {
        "api_url": api,
        "api_key": key,
        "actor_peer": peer,
        "node_host": platform.node() or socket.gethostname(),
    }
    _write_json_file(cfg_file, config_data)
    try:
        os.chmod(cfg_file, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass
    print("  ✔ config.json 凭据与节点身份落盘完成 (0600)")

    register_in_ide_config(PLUGIN_NAME, PLUGIN_VERSION)
    sync_mcp_fleet(api, key, target_dir, peer)
    print(f"🎉 OpenViking 卫星同频插件 (v{PLUGIN_VERSION}) 部署完成！API: {api} | Peer: {peer}")
    return api, peer


def inspect_plugin(target_dir: Path) -> bool:
    print(f"🔍 正在巡检 {PLUGIN_NAME} 插件: {target_dir}")
    ok = True
    for name in ("plugin.json", "server.py", "config.json", "mcp_config.json"):
        exists = (target_dir / name).is_file()
        print(f"  {'✔' if exists else '✘'} 构件存在: {name}")
        ok = ok and exists
    mcp_data = _read_json_file(target_dir / "mcp_config.json")
    args = mcp_data.get("mcpServers", {}).get("core", {}).get("args", [])
    if args and "Desktop/coding/OpenVikingStudio" not in str(args[0]).replace("\\", "/"):
        print(f"  ✔ 自内聚路径校验通过: {args[0]}")
    else:
        print(f"  ✘ MCP 路径非法或缺失: {args}")
        ok = False
    cfg = _read_json_file(target_dir / "config.json")
    api = str(cfg.get("api_url") or DEFAULT_PUBLIC_API).rstrip("/")
    reachable = _probe_local_health(api, timeout=1.5)
    print(f"  {'✔' if reachable else '⚠️'} 中枢连通探针: {api} ({'HTTP 200' if reachable else 'unreachable'})")
    return ok


def uninstall_plugin(target_dir: Path) -> None:
    unregister_from_ide_config(PLUGIN_NAME)
    g_mcp_path = GEMINI_CONFIG_DIR / "mcp_config.json"
    if g_mcp_path.is_file():
        g_data = _read_json_file(g_mcp_path)
        servers = g_data.get("mcpServers", {})
        if isinstance(servers, dict):
            removed = False
            for k in (PLUGIN_NAME, *GHOST_MCP_ALIASES):
                if k in servers:
                    servers.pop(k, None)
                    removed = True
            if removed:
                _write_json_file(g_mcp_path, g_data)
                print("  ✔ 已清理全局 mcp_config.json fleet-mesh 注册项")
    if target_dir.exists() and target_dir.resolve() != PLUGIN_SRC_DIR.resolve():
        shutil.rmtree(target_dir, ignore_errors=True)
        print(f"  ✔ 已移除插件目录: {target_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenViking 卫星同频插件标准自举安装向导")
    parser.add_argument("action", nargs="?", choices=("install", "inspect", "uninstall"), help="兼容旧式位置子命令")
    parser.add_argument("--install", action="store_true", help="安装插件至 Antigravity 插件目录")
    parser.add_argument("--inspect", action="store_true", help="巡检插件自内聚安装与连通状态")
    parser.add_argument("--uninstall", action="store_true", help="卸载插件并清理注册表")
    parser.add_argument("--target", type=str, default="", help="指定安装目标目录")
    parser.add_argument("--api", type=str, default="", help="OpenViking API 地址")
    parser.add_argument("--key", type=str, default="", help="OpenViking API Key")
    parser.add_argument("--peer", type=str, default="", help="指定节点 Actor Peer 标识")
    args = parser.parse_args()

    target_dir = Path(args.target).resolve() if args.target else DEFAULT_TARGET_DIR
    if args.uninstall or args.action == "uninstall":
        uninstall_plugin(target_dir)
        return
    if args.inspect or args.action == "inspect":
        sys.exit(0 if inspect_plugin(target_dir) else 1)

    api = resolve_best_api(args.api, target_dir=target_dir)
    key = resolve_credentials(target_dir, args.key)
    install_plugin(target_dir, api, key, actor_peer=args.peer)


if __name__ == "__main__":
    main()
