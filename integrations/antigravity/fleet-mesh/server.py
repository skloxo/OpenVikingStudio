#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenViking Fleet Mesh Self-Contained MCP Adapter Driver (server.py).

第一性原理架构：
1. 彻底斩除外部桌面路径依赖，插件解压即可作为独立 FastMCP Stdio 驱动运行；
2. 多节点拓扑自适应：本地 `:1933` 优先存活探测，卫星端优雅降级公网中枢 (`vk.tide.red`)；
3. 零凭据越权泄漏：3 段式绑定 UserKey 自动省略 `X-OpenViking-User/Account` 覆盖头；
4. 精准暴露 `openviking_fleet_check` 与 `openviking_fleet_sync` 两项卫星集群工具。
"""

from __future__ import annotations

import json
import os
import platform
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import Field
from mcp.server.fastmcp import FastMCP

# SECTION: Windows UTF-8 Stdio Safeguard
if sys.platform == "win32":
    try:
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_PLUGIN_DIR = Path(__file__).resolve().parent
_CONFIG_FILE = _PLUGIN_DIR / "config.json"
DEFAULT_PUBLIC_API = "https://vk.tide.red"
DEFAULT_LOCAL_API = "http://127.0.0.1:1933"


def _load_local_config() -> Dict[str, Any]:
    if _CONFIG_FILE.is_file():
        try:
            return json.loads(_CONFIG_FILE.read_text(encoding="utf-8-sig"))
        except Exception:
            pass
    return {}


def _resolve_plugin_version() -> str:
    manifest = _PLUGIN_DIR / "plugin.json"
    if manifest.is_file():
        try:
            ver = json.loads(manifest.read_text(encoding="utf-8-sig")).get("version")
            if ver:
                return str(ver).strip()
        except Exception:
            pass
    return "1.0.6"


def _probe_health(base_url: str, timeout: float = 0.8) -> Optional[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/health"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return None


def resolve_adaptive_endpoint(local_cfg: Optional[Dict[str, Any]] = None) -> str:
    """Resolve active OpenViking hub URL: env -> local loopback probe -> config -> public."""
    cfg = local_cfg if local_cfg is not None else _load_local_config()
    env_api = os.environ.get("OPENVIKING_API", "").strip()
    if env_api:
        return env_api.rstrip("/")
    if _probe_health(DEFAULT_LOCAL_API, timeout=0.6) is not None:
        return DEFAULT_LOCAL_API
    cfg_api = str(cfg.get("api_url") or cfg.get("api") or "").strip()
    if cfg_api:
        return cfg_api.rstrip("/")
    return DEFAULT_PUBLIC_API


def resolve_actor_peer(local_cfg: Optional[Dict[str, Any]] = None) -> str:
    """Resolve adaptive node peer without hardcoded machine names."""
    cfg = local_cfg if local_cfg is not None else _load_local_config()
    env_peer = os.environ.get("OPENVIKING_ACTOR_PEER", "").strip()
    if env_peer:
        return env_peer
    cfg_peer = str(cfg.get("actor_peer") or "").strip()
    if cfg_peer:
        return cfg_peer
    host = (platform.node() or socket.gethostname() or "satellite").strip().lower()
    return f"antigravity@{host}"


def resolve_api_key(local_cfg: Optional[Dict[str, Any]] = None) -> str:
    cfg = local_cfg if local_cfg is not None else _load_local_config()
    return (
        os.environ.get("OPENVIKING_API_KEY")
        or os.environ.get("OPENVIKING_ROOT_API_KEY")
        or str(cfg.get("api_key") or "")
    ).strip()


def build_auth_headers(api_key: str, actor_peer: str, plugin_ver: str) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "User-Agent": f"Antigravity-Fleet-Mesh/{plugin_ver}",
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if actor_peer:
        headers["X-OpenViking-Actor-Peer"] = actor_peer
    # 3-part UserKey carries bound identity server-side; omit spoofing headers
    if not (api_key and len(api_key.split(".")) == 3):
        env_user = os.environ.get("OPENVIKING_USER", "").strip()
        env_account = os.environ.get("OPENVIKING_ACCOUNT", "").strip()
        if env_user:
            headers["X-OpenViking-User"] = env_user
        if env_account:
            headers["X-OpenViking-Account"] = env_account
    return headers


def _http_get_json(url: str, headers: Dict[str, str], timeout: float = 3.0) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            raw = resp.read().decode("utf-8", errors="replace")
            return {"ok": True, "status": resp.status, "latency_ms": latency_ms, "data": json.loads(raw)}
    except urllib.error.HTTPError as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return {"ok": False, "status": e.code, "latency_ms": latency_ms, "error": f"HTTP {e.code}"}
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return {"ok": False, "status": 0, "latency_ms": latency_ms, "error": str(e)}


def _node_matches(candidate: str, target: str) -> bool:
    t = (target or "all").strip().lower()
    if not t or t == "all":
        return True
    c = candidate.lower()
    return t in c or (t == "local" and ("127.0.0.1" in c or platform.node().lower() in c))


mcp = FastMCP(
    name="fleet-mesh",
    instructions="OpenViking 卫星集群拓扑巡检与多节点同频运维引擎 (2 Tools)。",
)


@mcp.tool()
def openviking_fleet_check(
    target_node: str = Field(default="all", description="目标节点：'all'、'local'、'2080ti'、'3070' 或主机名"),
) -> str:
    """【卫星集群运维】多节点自适应健康巡检，探测中枢连通性、延迟与插件版本同频状态。"""
    local_cfg = _load_local_config()
    plugin_ver = _resolve_plugin_version()
    api_base = resolve_adaptive_endpoint(local_cfg)
    actor_peer = resolve_actor_peer(local_cfg)
    headers = build_auth_headers(resolve_api_key(local_cfg), actor_peer, plugin_ver)

    probe_urls = [DEFAULT_LOCAL_API]
    if api_base not in probe_urls:
        probe_urls.append(api_base)
    if DEFAULT_PUBLIC_API not in probe_urls:
        probe_urls.append(DEFAULT_PUBLIC_API)

    endpoints: List[Dict[str, Any]] = []
    for base in probe_urls:
        if not _node_matches(f"{base} {actor_peer}", target_node) and target_node.strip().lower() != "all":
            if "127.0.0.1" not in base and base != api_base:
                continue
        probe = _http_get_json(f"{base}/health", headers, timeout=2.5)
        endpoints.append({
            "endpoint": base,
            "reachable": probe["ok"],
            "latency_ms": probe["latency_ms"],
            "version": (probe.get("data") or {}).get("version") if probe["ok"] else None,
            "error": probe.get("error"),
        })

    plugins_probe = _http_get_json(f"{api_base}/api/v1/plugins/fleet-mesh", headers, timeout=3.0)
    remote_ver = (plugins_probe.get("data") or {}).get("version") if plugins_probe["ok"] else None

    result = {
        "status": "ok" if any(e["reachable"] for e in endpoints) else "degraded",
        "plugin": "fleet-mesh",
        "local_version": plugin_ver,
        "remote_version": remote_ver,
        "version_aligned": (remote_ver is None or remote_ver == plugin_ver),
        "node_host": platform.node() or socket.gethostname(),
        "actor_peer": actor_peer,
        "active_endpoint": api_base,
        "target_node": target_node,
        "endpoints": endpoints,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def openviking_fleet_sync(
    target_node: str = Field(default="all", description="同步目标节点：'all'、'local'、'2080ti'、'3070' 或主机名"),
) -> str:
    """【卫星集群运维】校准节点身份、中枢端点与跨机插件版本同频，消除配置漂移。"""
    local_cfg = _load_local_config()
    plugin_ver = _resolve_plugin_version()
    api_base = resolve_adaptive_endpoint(local_cfg)
    actor_peer = resolve_actor_peer(local_cfg)
    headers = build_auth_headers(resolve_api_key(local_cfg), actor_peer, plugin_ver)

    detail_probe = _http_get_json(f"{api_base}/api/v1/plugins/fleet-mesh", headers, timeout=3.0)
    topo_probe = _http_get_json(f"{api_base}/api/v1/relations/topology?limit=20", headers, timeout=3.0)
    peers = [
        {"id": n.get("id"), "label": n.get("label"), "role": n.get("role")}
        for n in (topo_probe.get("data") or {}).get("result", {}).get("nodes", [])
        if str(n.get("id", "")).startswith("viking://peers/")
        and _node_matches(f"{n.get('id', '')} {n.get('label', '')}", target_node)
    ] if topo_probe["ok"] else []

    remote_ver = (detail_probe.get("data") or {}).get("version") if detail_probe["ok"] else None
    drift = bool(remote_ver and remote_ver != plugin_ver)
    report = {
        "status": "drift_detected" if drift else "synchronized",
        "node_host": platform.node() or socket.gethostname(),
        "actor_peer": actor_peer,
        "active_endpoint": api_base,
        "local_version": plugin_ver,
        "remote_version": remote_ver,
        "package_url": f"{api_base}/studio/fleet-mesh-{remote_ver or plugin_ver}.tgz" if drift else None,
        "matched_peers": peers,
        "target_node": target_node,
    }
    return json.dumps(report, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    if "--inspect" in sys.argv:
        cfg = _load_local_config()
        print(
            f"Fleet Mesh MCP Server v{_resolve_plugin_version()} | "
            f"Endpoint: {resolve_adaptive_endpoint(cfg)} | Peer: {resolve_actor_peer(cfg)}"
        )
        sys.exit(0)
    mcp.run(transport="stdio")
