# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: tools.observability ──────────────────────────────────────────
"""
用途: 系统运行态可观测指标、Harness 门锁防御、Token 消耗统计与 Prometheus 指标
依赖: _core.config
被调用: mcp_openviking_server.py
"""

# SECTION: Imports
import json
import logging
import os
import sys
import time
from typing import Any, Callable, Dict
import urllib.request
from urllib.request import Request
from pydantic import Field
from mcp.server.fastmcp import FastMCP
from _core.config import (
    _get_config,
    _run_cli,
    http_client,
    _format_result,
    _has_error,
    _handle_http_error,
    _make_error,
    CLI_ONLY_MODE,
)

logger = logging.getLogger("openviking-mcp")

# SECTION: Harness Metrics State & Guard
METRICS_FILE_PATH = os.path.expanduser("~/.openviking/harness_metrics.json")


def _load_harness_metrics() -> Dict[str, Any]:
    try:
        if os.path.exists(METRICS_FILE_PATH):
            with open(METRICS_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {
        "total_calls": 0,
        "find_calls": 0,
        "store_calls": 0,
        "lessons_count": 0,
        "last_active_timestamp": 0.0,
        "actor_peers": {},
    }


HARNESS_METRICS: Dict[str, Any] = _load_harness_metrics()


def _save_harness_metrics():
    try:
        os.makedirs(os.path.dirname(METRICS_FILE_PATH), exist_ok=True)
        with open(METRICS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(HARNESS_METRICS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"无法保存 harness metrics 到磁盘: {e}")


def _record_harness_call(call_type: str, actor_peer: str = "default"):
    HARNESS_METRICS["total_calls"] = HARNESS_METRICS.get("total_calls", 0) + 1
    HARNESS_METRICS["last_active_timestamp"] = time.time()
    if call_type == "find":
        HARNESS_METRICS["find_calls"] = HARNESS_METRICS.get("find_calls", 0) + 1
    elif call_type == "store":
        HARNESS_METRICS["store_calls"] = HARNESS_METRICS.get("store_calls", 0) + 1
    elif "blocked" in call_type:
        HARNESS_METRICS["blocked_calls"] = HARNESS_METRICS.get("blocked_calls", 0) + 1

    if actor_peer:
        peers = HARNESS_METRICS.setdefault("actor_peers", {})
        peers[actor_peer] = peers.get(actor_peer, 0) + 1

    _save_harness_metrics()


def _harness_pre_execution_guard(tool_name: str, payload: Dict[str, Any]) -> tuple[bool, str]:
    """NeMo Guardrails 式物理前置拦截门锁：物理阻断违规脚本与非法部署行为"""
    file_path = str(payload.get("path") or payload.get("TargetFile") or payload.get("filepath") or "")
    cmd_str = str(payload.get("command") or payload.get("CommandLine") or "")

    if any(p in file_path for p in ["/scripts/", "/public/"]):
        if any(file_path.endswith(ext) for ext in [".py", ".json", ".sh"]):
            _record_harness_call("blocked_script_violation", actor_peer="antigravity")
            return False, f"[Harness Guard Intercepted] 物理阻断：严禁在 scripts/ 或 public/ 创建游离脚本 {os.path.basename(file_path)}！请直改源码。"

    if "web_studio/dist" in cmd_str and not payload.get("user_approved_deploy"):
        _record_harness_call("blocked_deploy_violation", actor_peer="antigravity")
    return True, ""

# SECTION: Tool Registration
def register_observability_tools(mcp: FastMCP, mcp_tool: Callable) -> Dict[str, Callable]:
    registered: Dict[str, Callable] = {}

    @mcp_tool()
    def openviking_harness_stats() -> str:
        """获取 OpenViking Harness 网关的调用计数与可观测统计 (v1.1.23a)"""
        return _format_result({
            "status": "ok",
            "harness_metrics": HARNESS_METRICS,
            "mode": "both" if not CLI_ONLY_MODE else "cli_only",
        })
    registered["openviking_harness_stats"] = openviking_harness_stats

    @mcp_tool()
    def openviking_usage_stats(
        reset: bool = Field(default=False, description="是否重置统计数据"),
    ) -> str:
        """获取 OpenViking token 消耗统计。支持重置计数器。"""
        if reset:
            if CLI_ONLY_MODE or not http_client.available:
                result = _run_cli(["stats", "--reset"])
            else:
                result = http_client.post("/api/v1/system/stats/reset")
                if _has_error(result):
                    result = _run_cli(["stats", "--reset"])
            return _format_result(result)

        if CLI_ONLY_MODE or not http_client.available:
            result = _run_cli(["stats", "--json"])
            if _has_error(result):
                result = _run_cli(["stats"])
            return _format_result(result)

        result = http_client.get("/api/v1/system/stats")
        if _has_error(result):
            result = _run_cli(["stats", "--json"])
            if _has_error(result):
                result = _run_cli(["stats"])
        return _format_result(result)
    registered["openviking_usage_stats"] = openviking_usage_stats

    @mcp_tool()
    def openviking_observer(
        component: str = Field(description="组件名：queue/vikingdb/models/lock/retrieval/system"),
    ) -> str:
        """查看指定组件的 Observer 状态"""
        valid = {"queue", "vikingdb", "models", "lock", "retrieval", "system"}
        if component not in valid:
            return _make_error(f"无效组件: {component}。可选: {', '.join(sorted(valid))}")
        result = http_client.get(f"/api/v1/observer/{component}")
        return _format_result(result)
    registered["openviking_observer"] = openviking_observer

    @mcp_tool()
    def openviking_metrics() -> str:
        """获取 Prometheus 格式的指标数据"""
        cfg = _get_config()
        url = f"{cfg['api']}/metrics"
        headers = {}
        if cfg["api_key"]:
            headers["Authorization"] = f"Bearer {cfg['api_key']}"
        try:
            req = Request(url, headers=headers)
            mcp_mod = sys.modules.get("mcp_openviking_server")
            active_urlopen = getattr(mcp_mod, "urlopen", urllib.request.urlopen)
            with active_urlopen(req, timeout=10) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            return _handle_http_error(e)
    registered["openviking_metrics"] = openviking_metrics

    return registered
