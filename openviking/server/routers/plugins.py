# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Plugins Ecosystem & Quad-Model Registry REST Router.
SSOT: docs/architecture/ATOMIC_TASK_CARDS_MATRIX.md -> TASK-PLUG-04
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from openviking.models.plugin import PluginHealthProbe, QuadPluginDefinition
from openviking.service.plugin_probes import PluginProbeRunner
from openviking.service.plugin_registry import PluginRegistry

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])


class PluginsListResponse(BaseModel):
    """插件列表响应 DTO。"""
    total: int = Field(..., description="插件总数")
    plugins: List[QuadPluginDefinition] = Field(..., description="插件四位一体定义列表")


class PluginsHealthSummaryResponse(BaseModel):
    """插件健康探针概要响应 DTO。"""
    overall_status: str = Field(..., description="全局健康态 (healthy | degraded | down)")
    healthy_count: int = Field(..., description="健康运行中插件数量")
    total_count: int = Field(..., description="注册插件总数")
    healthy_rate: float = Field(100.0, description="健康百分比 (0.0 ~ 100.0)")
    average_latency_ms: float = Field(0.0, description="真实物理平均探针时延 (毫秒)")
    probes: Dict[str, PluginHealthProbe] = Field(..., description="各插件探针详情字典")


@router.get("", response_model=PluginsListResponse)
async def list_plugins(
    category: Optional[str] = Query(None, description="按分类过滤 (platform | user)"),
    with_probes: bool = Query(True, description="是否融合最新健康探针状态"),
) -> PluginsListResponse:
    """获取所有已装载插件的四位一体定义清单。"""
    registry = PluginRegistry.get_instance()
    plugins = registry.list_plugins(category=category)

    if with_probes:
        probes = await PluginProbeRunner.check_all_plugins()
        for p in plugins:
            if p.plugin_id in probes:
                p.health = probes[p.plugin_id]

    return PluginsListResponse(total=len(plugins), plugins=plugins)


@router.get("/health/summary", response_model=PluginsHealthSummaryResponse)
@router.get("/health", response_model=PluginsHealthSummaryResponse)
async def get_plugins_health_summary() -> PluginsHealthSummaryResponse:
    """获取全平台插件健康探针概览大盘数据。"""
    registry = PluginRegistry.get_instance()
    plugins = registry.list_plugins()
    probes = await PluginProbeRunner.check_all_plugins()

    healthy_count = sum(1 for p in probes.values() if p.status == "healthy")
    total = len(plugins)
    healthy_rate = round((healthy_count / total * 100.0), 1) if total > 0 else 0.0

    latencies = [p.latency_ms for p in probes.values() if p.latency_ms > 0]
    avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0.0

    if healthy_count == total and total > 0:
        overall = "healthy"
    elif healthy_count > 0:
        overall = "degraded"
    else:
        overall = "down"

    return PluginsHealthSummaryResponse(
        overall_status=overall,
        healthy_count=healthy_count,
        total_count=total,
        healthy_rate=healthy_rate,
        average_latency_ms=avg_latency,
        probes=probes,
    )


@router.get("/bridge/client-package")
async def get_client_bridge_package(
    response: Response,
    plugin_id: Optional[str] = Query(None, alias="plugin_id"),
) -> Dict[str, Any]:
    """获取独立客户端通信通道桥的下载元数据与接入规范。"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    bridge_info = PluginRegistry.get_client_bridge_info(plugin_id or "openviking-memory")
    return {
        "status": "success",
        "result": bridge_info,
    }


@router.get("/{plugin_id}", response_model=QuadPluginDefinition)
async def get_plugin_detail(plugin_id: str) -> QuadPluginDefinition:
    """获取指定插件的四位一体规格详情。"""
    registry = PluginRegistry.get_instance()
    plugin = registry.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    probes = await PluginProbeRunner.check_all_plugins()
    if plugin_id in probes:
        plugin.health = probes[plugin_id]

    return plugin


