# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: tools.fleet ───────────────────────────────────────────────────
"""
用途: OpenViking 卫星智能体集群自动化运维、巡检与一键同频 (MCP 工具层)
功能:
- openviking_fleet_check: 全集群卫星节点健康巡检 (2080Ti, 3070, Mac Studio)
- openviking_fleet_sync: 一键向集群分发最新 satellite_mcp_server 与 AGENTS.md
- openviking_fleet_probe: 指定节点端到端真实 MCP 数据检索与 403 探活
依赖: 标准库 (subprocess, json, pathlib, os, urllib)
被调用: mcp_openviking_server.py
"""

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from pydantic import Field
from mcp.server.fastmcp import FastMCP

from _core.config import _make_error

logger = logging.getLogger("openviking-mcp")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SATELLITE_SRC = REPO_ROOT / "project" / "OpenVikingStudio" / "mcp-openviking" / "satellite_mcp_server.py"
if not SATELLITE_SRC.exists():
    # 备用路径解析
    SATELLITE_SRC = Path(__file__).resolve().parent.parent / "satellite_mcp_server.py"

GLOBAL_SATELLITE_AGENTS_MD = """# 🛰️ OpenViking 卫星节点研发规范 (AGENTS.md SSOT)

1. **节点身份**：本机为 OpenViking 卫星节点智能体，连接至中枢体外大脑 `https://vk.tide.red`。
2. **Hook 与 MCP 协同契约**：
   - 上下文注入【OpenViking 核心记忆预取】小抄时，视为已知事实，严禁重复发起相同的 `openviking_find` 盲搜；
   - 需深读全文直接调用 `openviking_read` 传入对应 URI；
   - 解决重大 Bug 根因、突破死锁或沉淀新范式时，必须主动调用 `openviking_record_evolution_lesson` 写入体外大脑。
3. **视觉与设计规范**：
   - NO GREEN EVER 🚫（界面中性基准，正向冰青 cyan-500，异常玫瑰红 rose-500）；
   - 单文件行数黄金甜点区 100~300 行，严禁超过 500 行。
"""


def _check_local_2080ti() -> Dict[str, Any]:
    res = {"node": "2080Ti (Local / Windows)", "status": "ok", "checks": {}}
    import urllib.request
    try:
        req = urllib.request.Request("http://127.0.0.1:1933/health")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            res["checks"]["vk_core_health"] = resp.status == 200
    except Exception as e:
        res["checks"]["vk_core_health"] = False
        res["status"] = "error"
        res["error"] = str(e)

    win_mimo_dir = Path("/mnt/c/Users/Skl/.config/mimocode")
    if win_mimo_dir.exists():
        res["checks"]["mimo_agents_md"] = (win_mimo_dir / "AGENTS.md").exists()
        res["checks"]["mimo_config"] = (win_mimo_dir / "mimocode.jsonc").exists()
    else:
        res["checks"]["win_mimo"] = "not_found"
    return res


def _exec_3070_cmd(cmd: str, timeout: int = 10) -> subprocess.CompletedProcess:
    ssh_cmd = [
        "sshpass", "-p", "Skl3289568",
        "ssh", "-p", "6022",
        "-o", "StrictHostKeyChecking=no",
        "-o", "PubkeyAuthentication=no",
        "-o", "PreferredAuthentications=password",
        "-o", f"ConnectTimeout={timeout}",
        "AzureAD\\s@tide.red@8.129.0.26",
        cmd
    ]
    return subprocess.run(ssh_cmd, capture_output=True, text=True, errors="replace", timeout=timeout + 3)


def _check_remote_3070() -> Dict[str, Any]:
    res = {"node": "RTX 3070 (Remote Windows)", "status": "ok", "checks": {}}
    try:
        cp = _exec_3070_cmd("echo 3070-ok", timeout=5)
        if cp.returncode != 0 or "3070-ok" not in cp.stdout:
            res["status"] = "unreachable"
            res["error"] = cp.stderr.strip() or "SSH connection failed"
            return res
        res["checks"]["ssh_connected"] = True

        check_header = _exec_3070_cmd('cmd.exe /c type C:\\Users\\Skl\\.openviking\\satellite_mcp_server.py | findstr /N /C:X-OpenViking-User')
        res["checks"]["mcp_header_403_safe"] = (
            'os.environ.get("OPENVIKING_USER", "default")' in check_header.stdout or '"default"' in check_header.stdout
        )
        if not res["checks"]["mcp_header_403_safe"]:
            res["status"] = "warning"

        check_agents = _exec_3070_cmd('powershell -Command "Test-Path C:\\Users\\Skl\\.config\\mimocode\\AGENTS.md"')
        res["checks"]["mimo_agents_md"] = "True" in check_agents.stdout

        probe_py = (
            "import sys; "
            "sys.path.append('C:/Users/Skl/.openviking'); "
            "from satellite_mcp_server import SatelliteHTTPClient; "
            "c = SatelliteHTTPClient(); "
            "r = c._request('POST', '/api/v1/search/find', {'query': 'health', 'limit': 1}); "
            "print('STATUS:' + str(r.get('status')))"
        )
        test_mcp_cmd = (
            "$env:OPENVIKING_API='https://vk.tide.red'; "
            "$env:OPENVIKING_API_KEY='ZGVmYXVsdA.ZGVmYXVsdA.NmRjZTAxYTRiYWZlNDFlNTkwODRlYzQyZWJiYWQ3YTI4Y2E1NjRkZjc4Y2Q5YzAzOTFhYWQyZWU5NjkyMjgxNQ'; "
            f"& 'C:/Users/Skl/.venv-openviking/Scripts/python.exe' -c \"{probe_py}\""
        )
        cp_test = _exec_3070_cmd(test_mcp_cmd, timeout=12)
        res["checks"]["mcp_query_probe"] = "STATUS:ok" in cp_test.stdout
        if not res["checks"]["mcp_query_probe"]:
            res["status"] = "warning"
            res["mcp_test_error"] = cp_test.stdout.strip() or cp_test.stderr.strip()

        peer_probe = (
            "import sys, os; sys.path.append('C:/Users/Skl/.openviking'); "
            "from satellite_mcp_server import get_resolved_actor_peer; "
            "os.environ['OPENVIKING_CLIENT'] = 'antigravity'; p1 = get_resolved_actor_peer(); "
            "os.environ['OPENVIKING_CLIENT'] = 'workbuddy'; p2 = get_resolved_actor_peer(); "
            "print(f'PEERS:{p1}|{p2}')"
        )
        cp_peer = _exec_3070_cmd(f"& 'C:/Users/Skl/.venv-openviking/Scripts/python.exe' -c \"{peer_probe}\"", timeout=8)
        res["checks"]["peers_isolated"] = "PEERS:antigravity@3070|workbuddy@3070" in cp_peer.stdout

    except Exception as e:
        res["status"] = "error"
        res["error"] = str(e)
    return res


def _check_mac_studio() -> Dict[str, Any]:
    res = {"node": "Mac Studio (M3 Ultra)", "status": "ok", "checks": {}}
    cmd = [
        "ssh", "-p", "13100",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=4",
        "fsk@8.129.0.26",
        "echo mac-studio-ok"
    ]
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if cp.returncode == 0 and "mac-studio-ok" in cp.stdout:
            res["checks"]["ssh_connected"] = True
        else:
            res["status"] = "unreachable"
            res["error"] = cp.stderr.strip() or "Connection timed out"
    except Exception as e:
        res["status"] = "unreachable"
        res["error"] = str(e)
    return res


def _sync_to_3070() -> Dict[str, Any]:
    log_res = {"target": "RTX 3070", "satellite_mcp": False, "workbuddy_mcp": False, "agents_md": False, "antigravity_config": False}
    if not SATELLITE_SRC.exists():
        log_res["error"] = f"找不到源文件: {SATELLITE_SRC}"
        return log_res

    base_scp = ["sshpass", "-p", "Skl3289568", "scp", "-P", "6022", "-o", "StrictHostKeyChecking=no", "-o", "PubkeyAuthentication=no", "-o", "PreferredAuthentications=password"]
    cp = subprocess.run(base_scp + [str(SATELLITE_SRC), "AzureAD\\s@tide.red@8.129.0.26:C:/Users/Skl/.openviking/satellite_mcp_server.py"], capture_output=True, text=True, timeout=15)
    log_res["satellite_mcp"] = cp.returncode == 0

    cp_wb = subprocess.run(base_scp + [str(SATELLITE_SRC), "AzureAD\\s@tide.red@8.129.0.26:C:/Users/Skl/.workbuddy/openviking-mcp/satellite_mcp_server.py"], capture_output=True, text=True, timeout=15)
    log_res["workbuddy_mcp"] = cp_wb.returncode == 0

    tmp_agents = Path("/tmp/temp_agents_3070.md")
    tmp_agents.write_text(GLOBAL_SATELLITE_AGENTS_MD, encoding="utf-8")
    cp2 = subprocess.run(base_scp + [str(tmp_agents), "AzureAD\\s@tide.red@8.129.0.26:C:/Users/Skl/.config/mimocode/AGENTS.md"], capture_output=True, text=True, timeout=15)
    log_res["agents_md"] = cp2.returncode == 0
    if tmp_agents.exists():
        tmp_agents.unlink()

    # 自动保障 3070 反重力 IDE 拥有独立身份 antigravity@3070
    update_py = (
        "import json, os\n"
        "p = r'C:\\Users\\Skl\\.gemini\\config\\mcp_config.json'\n"
        "if os.path.exists(p):\n"
        "    with open(p, 'r', encoding='utf-8-sig') as f: data = json.load(f)\n"
        "    env = data.setdefault('mcpServers', {}).setdefault('openviking', {}).setdefault('env', {})\n"
        "    env['OPENVIKING_ACTOR_PEER'] = 'antigravity@3070'\n"
        "    env['OPENVIKING_CLIENT'] = 'antigravity'\n"
        "    env['OPENVIKING_NODE'] = '3070'\n"
        "    with open(p, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2, ensure_ascii=False)\n"
        "    print('CFG_OK')\n"
    )
    import base64
    b64 = base64.b64encode(update_py.encode("utf-8")).decode("ascii")
    cp_cfg = _exec_3070_cmd(f"C:\\Users\\Skl\\.venv-openviking\\Scripts\\python.exe -c \"import base64; exec(base64.b64decode('{b64}').decode('utf-8'))\"")
    log_res["antigravity_config"] = "CFG_OK" in cp_cfg.stdout
    return log_res


def _sync_to_local_2080ti() -> Dict[str, Any]:
    win_mimo_dir = Path("/mnt/c/Users/Skl/.config/mimocode")
    res = {"target": "2080Ti (Local)", "agents_md": False}
    if win_mimo_dir.exists():
        agents_md = win_mimo_dir / "AGENTS.md"
        agents_md.write_text(GLOBAL_SATELLITE_AGENTS_MD, encoding="utf-8")
        res["agents_md"] = True
    return res


# SECTION: Tool Registration
def register_fleet_tools(mcp: FastMCP, mcp_tool: Callable) -> Dict[str, Callable]:
    registered: Dict[str, Callable] = {}

    @mcp_tool()
    def openviking_fleet_check(
        target_node: str = Field(default="all", description="目标节点：'all'、'3070'、'2080ti'、'mac_studio'")
    ) -> str:
        """【卫星集群运维】全集群卫星节点健康巡检，排查 SSH 连通性、MCP 403 风险与 AGENTS.md 规范状态。"""
        results = []
        target = target_node.lower().strip()
        if target in ("all", "2080ti", "local"):
            results.append(_check_local_2080ti())
        if target in ("all", "3070", "remote"):
            results.append(_check_remote_3070())
        if target in ("all", "mac_studio", "mac"):
            results.append(_check_mac_studio())

        return json.dumps({"status": "ok", "fleet": results, "timestamp": int(time.time())}, indent=2, ensure_ascii=False)

    @mcp_tool()
    def openviking_fleet_sync(
        target_node: str = Field(default="all", description="同步目标节点：'all'、'3070'、'2080ti'")
    ) -> str:
        """【卫星集群运维】一键向卫星节点分发最新 satellite_mcp_server.py 脚本与全局 AGENTS.md 规范，自愈 403 与配置漂移。"""
        sync_results = []
        target = target_node.lower().strip()
        if target in ("all", "2080ti", "local"):
            sync_results.append(_sync_to_local_2080ti())
        if target in ("all", "3070", "remote"):
            sync_results.append(_sync_to_3070())

        return json.dumps({"status": "ok", "sync_summary": sync_results, "timestamp": int(time.time())}, indent=2, ensure_ascii=False)

    registered["openviking_fleet_check"] = openviking_fleet_check
    registered["openviking_fleet_sync"] = openviking_fleet_sync
    return registered
