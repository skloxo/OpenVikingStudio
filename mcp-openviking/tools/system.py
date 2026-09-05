# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: tools.system ──────────────────────────────────────────────────
"""
用途: 系统健康、环境自检、服务生命周期管控、快照备份与版本协商
依赖: _core.config, tools.observability
被调用: mcp_openviking_server.py
"""

# SECTION: Imports
import logging
import sys
import time
from typing import Callable, Dict
from pydantic import Field
from mcp.server.fastmcp import FastMCP
from _core.config import (
    _get_config,
    _validate_uri,
    _make_error,
    _run_cli,
    http_client,
    _api_then_cli,
    _format_result,
    _has_error,
    _get_active_mode,
)
from .observability import HARNESS_METRICS

logger = logging.getLogger("openviking-mcp")

# SECTION: Tool Registration
def register_system_tools(mcp: FastMCP, mcp_tool: Callable) -> Dict[str, Callable]:
    registered: Dict[str, Callable] = {}

    @mcp_tool()
    def openviking_health() -> str:
        """检查 OpenViking 服务健康状态（合并 health/ready/status）"""
        def _api():
            health = http_client.get("/health")
            ready = http_client.get("/ready")
            status = http_client.get("/api/v1/system/status")
            return {
                "health": health,
                "ready": ready,
                "status": status,
            }

        def _cli():
            return _run_cli(["status"])

        return _api_then_cli(_api, ["status"])
    registered["openviking_health"] = openviking_health

    @mcp_tool()
    def openviking_system_status(
        wait_timeout: int = Field(default=0, description="等待后台处理完成的超时秒数（0=不等待）"),
        reset_stats: bool = Field(default=False, description="是否重置 token 统计"),
    ) -> str:
        """获取系统详细状态。可选等待后台处理、重置统计。"""
        w_to = int(wait_timeout) if isinstance(wait_timeout, (int, float)) else 0
        r_st = bool(reset_stats) if isinstance(reset_stats, bool) else False

        def _api():
            result = http_client.get("/api/v1/system/status")
            if isinstance(result, dict):
                result["harness_metrics"] = HARNESS_METRICS
            if w_to > 0 and "error" not in result:
                http_client.post("/api/v1/system/wait", {"timeout": w_to})
            return result

        def _cli():
            status_info = _run_cli(["status"])
            stats_args = ["status"]
            if r_st:
                stats_args.append("--reset")
            stats = _run_cli(stats_args)
            return {"status": status_info, "stats": stats, "harness_metrics": HARNESS_METRICS}

        return _api_then_cli(_api, ["status"])
    registered["openviking_system_status"] = openviking_system_status

    @mcp_tool()
    def openviking_list_watches(
        active_only: bool = Field(default=True, description="仅显示活跃任务"),
    ) -> str:
        """列出 watch 监控任务"""
        args = ["task", "watch", "ls"]
        if active_only:
            args.append("--active-only")
        return _format_result(_run_cli(args))
    registered["openviking_list_watches"] = openviking_list_watches

    @mcp_tool()
    def openviking_cancel_watch(
        target_uri: str = Field(description="要取消监控的 Viking URI"),
    ) -> str:
        """取消 watch 监控任务"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)
        return _format_result(_run_cli(["task", "watch", "rm", target_uri]))
    registered["openviking_cancel_watch"] = openviking_cancel_watch

    @mcp_tool()
    def openviking_manage_watch(
        target_uri: str = Field(description="Viking URI"),
        action: str = Field(description="操作：pause/resume/trigger"),
    ) -> str:
        """管理 watch 任务：暂停、恢复、手动触发"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)
        valid_actions = {"pause", "resume", "trigger"}
        if action not in valid_actions:
            return _make_error(f"无效操作: {action}。可选: {', '.join(sorted(valid_actions))}")
        return _format_result(_run_cli(["task", "watch", action, target_uri]))
    registered["openviking_manage_watch"] = openviking_manage_watch

    @mcp_tool()
    def openviking_export(
        target_uri: str = Field(description="要导出的 Viking URI"),
        output_path: str = Field(description="导出文件路径（.ovpack）"),
        include_vectors: bool = Field(default=False, description="包含向量快照"),
    ) -> str:
        """导出资源为 OVPack 格式"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)
        args = ["export", target_uri, output_path]
        if include_vectors:
            args.append("--include-vectors")
        return _format_result(_run_cli(args, timeout=300))
    registered["openviking_export"] = openviking_export

    @mcp_tool()
    def openviking_import(
        pack_path: str = Field(description="OVPack 文件路径"),
        target_uri: str = Field(description="导入目标 Viking URI"),
        on_conflict: str = Field(default="fail", description="冲突策略：fail, overwrite, skip"),
    ) -> str:
        """导入 OVPack 到 OpenViking"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)
        return _format_result(_run_cli(
            ["import", pack_path, target_uri, "--on-conflict", on_conflict],
            timeout=300,
        ))
    registered["openviking_import"] = openviking_import

    @mcp_tool()
    def openviking_backup(
        output_path: str = Field(description="备份文件路径（.ovpack）"),
    ) -> str:
        """全量备份 OpenViking"""
        return _format_result(_run_cli(["backup", output_path], timeout=600))
    registered["openviking_backup"] = openviking_backup

    @mcp_tool()
    def openviking_restore(
        pack_path: str = Field(description="备份文件路径（.ovpack）"),
        on_conflict: str = Field(default="overwrite", description="冲突策略"),
    ) -> str:
        """从备份恢复 OpenViking"""
        return _format_result(_run_cli(
            ["restore", pack_path, "--on-conflict", on_conflict],
            timeout=600,
        ))
    registered["openviking_restore"] = openviking_restore

    @mcp_tool()
    def openviking_server_control(
        action: str = Field(description="操作：start/stop/restart/status"),
        host: str = Field(default="127.0.0.1", description="监听地址（start 时使用）"),
        port: int = Field(default=1933, description="监听端口（start 时使用）"),
        config: str = Field(default="", description="配置文件路径（start 时使用）"),
    ) -> str:
        """OpenViking 服务器控制：启动、停止、重启、查看状态"""
        if action == "status":
            def _api():
                health = http_client.get("/health")
                if "error" not in health:
                    status = http_client.get("/api/v1/system/status")
                    return {"server": "running", "health": health, "status": status}
                return {"server": "not_running", "health": health}

            def _cli():
                result = _run_cli(["server", "status"])
                if _has_error(result):
                    return {"server": "not_running", "error": result.get("error")}
                return result

            return _api_then_cli(_api, ["server", "status"])

        elif action == "start":
            args = ["server", "start", "--host", host, "--port", str(port)]
            if config:
                args.extend(["--config", config])
            return _format_result(_run_cli(args, timeout=15))

        elif action == "stop":
            return _format_result(_run_cli(["server", "stop"], timeout=15))

        elif action == "restart":
            return _format_result(_run_cli(["server", "restart"], timeout=15))

        else:
            return _make_error(f"无效操作: {action}。可选: start, stop, restart, status")
    registered["openviking_server_control"] = openviking_server_control

    @mcp_tool()
    def openviking_server_init() -> str:
        """初始化 OpenViking 配置（交互式向导）"""
        return _format_result(_run_cli(["server", "init"], timeout=30))
    registered["openviking_server_init"] = openviking_server_init

    @mcp_tool()
    def openviking_server_doctor() -> str:
        """运行 OpenViking 配置诊断"""
        return _format_result(_run_cli(["server", "doctor"], timeout=30))
    registered["openviking_server_doctor"] = openviking_server_doctor

    @mcp_tool()
    def openviking_privacy(
        action: str = Field(description="操作：categories/list/get/upsert"),
        category: str = Field(default="", description="分类名（list/get/upsert 时必填）"),
        target_key: str = Field(default="", description="目标键（get/upsert 时必填）"),
        values_json: str = Field(default="", description="JSON 格式的值（upsert 时必填）"),
    ) -> str:
        """隐私配置管理：列出分类、查看/写入配置"""
        if action == "categories":
            return _format_result(_run_cli(["privacy", "categories"]))
        elif action == "list":
            if not category:
                return _make_error("list 操作需要 category 参数")
            return _format_result(_run_cli(["privacy", "list", category]))
        elif action == "get":
            if not category or not target_key:
                return _make_error("get 操作需要 category 和 target_key 参数")
            return _format_result(_run_cli(["privacy", "get", category, target_key]))
        elif action == "upsert":
            if not category or not target_key or not values_json:
                return _make_error("upsert 操作需要 category、target_key 和 values_json 参数")
            return _format_result(_run_cli([
                "privacy", "upsert", category, target_key,
                "--values-json", values_json,
            ]))
        else:
            return _make_error(f"无效操作: {action}。可选: categories, list, get, upsert")
    registered["openviking_privacy"] = openviking_privacy

    @mcp_tool()
    def openviking_consistency(
        target_uri: str = Field(default="viking://", description="检查范围 URI"),
        fix: bool = Field(default=False, description="是否自动修复"),
    ) -> str:
        """一致性检查：检测索引与存储的不一致"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)
        args = ["consistency", target_uri]
        if fix:
            args.append("--fix")
        return _format_result(_run_cli(args, timeout=120))
    registered["openviking_consistency"] = openviking_consistency

    @mcp_tool()
    def openviking_ping() -> str:
        """检测 OpenViking 连接状态与模式自检。返回运行模式、版本、连通性、网络延迟与可用工具数。"""
        cfg = _get_config()
        active_mode = _get_active_mode()

        status = {
            "status": "ok",
            "server_version": "1.4.32",
            "mode": active_mode,
            "api_url": cfg["api"],
            "authenticated": bool(cfg["api_key"]),
            "tools_count": len(list(mcp._tool_manager.list_tools())),
            "platform": sys.platform,
            "http_available": False,
            "cli_available": False,
            "latency_ms": -1.0,
        }

        # 测试 HTTP API 与延迟
        try:
            t0 = time.time()
            result = http_client.get("/health", timeout=5)
            latency = (time.time() - t0) * 1000.0
            if "error" not in result:
                status["http_available"] = True
                status["http_health"] = result
                status["latency_ms"] = round(latency, 2)
            else:
                status["status"] = "degraded"
                status["http_error"] = result.get("error")
        except Exception as e:
            status["status"] = "degraded"
            status["http_error"] = str(e)

        # 卫星模式下不强制要求本地 CLI
        if active_mode == "core":
            try:
                result = _run_cli(["--version"], timeout=10)
                if not _has_error(result):
                    status["cli_available"] = True
                    status["cli_version"] = result.get("output", result.get("version", "unknown"))
            except Exception as e:
                status["cli_error"] = str(e)

        return _format_result(status)
    registered["openviking_ping"] = openviking_ping

    return registered
