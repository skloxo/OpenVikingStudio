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


@router.get("/health/summary", response_model=PluginsHealthSummaryResponse)
async def get_plugins_health_summary() -> PluginsHealthSummaryResponse:
    """获取全平台插件健康探针概览大盘数据。"""
    registry = PluginRegistry.get_instance()
    plugins = registry.list_plugins()
    probes = await PluginProbeRunner.check_all_plugins()

    healthy_count = sum(1 for p in probes.values() if p.status == "healthy")
    total = len(plugins)
    
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
        probes=probes,
    )


@router.get("/network-search/usage/summary")
async def get_network_search_usage_summary(
    month: Optional[str] = Query(None, description="查询月份 (YYYY-MM)，默认当月"),
) -> Dict[str, Any]:
    """直出 26-Key 指纹脱敏微缩健康矩阵与月度权威消耗汇总。"""
    from openviking.service.search_accounting_store import SearchAccountingStore
    from openviking.service.search_key_rotator import SearchKeyRotator

    rotator = SearchKeyRotator.get_instance()
    store = SearchAccountingStore.get_instance()

    overview = rotator.get_key_health_overview()
    db_stats = store.get_database_stats()

    return {
        "status": "success",
        "month": month or time.strftime("%Y-%m"),
        "total_keys": overview["total_keys"],
        "keys": overview["keys"],
        "watermarks": overview["watermarks"],
        "db_stats": db_stats,
        "updated_at": overview["updated_at"],
    }


@router.post("/network-search/usage/prune")
async def trigger_search_usage_prune(
    retention_days: int = Query(45, ge=1, le=365, description="保留明细天数，超期将归档并物理删除"),
) -> Dict[str, Any]:
    """手动触发搜索流水账滚动归档与物理清理 (消灭数据库膨胀)。"""
    from openviking.service.search_accounting_store import SearchAccountingStore

    store = SearchAccountingStore.get_instance()
    result = store.rollup_and_prune_older_than(retention_days=retention_days)
    return {
        "status": "success",
        "message": f"Successfully pruned and rolled up logs older than {retention_days} days",
        "result": result,
    }


@router.get("/bridge/client-package")
async def get_client_bridge_package(response: Response) -> Dict[str, Any]:
    """获取独立客户端通信通道桥 (dsh-plugin-openviking) 的下载元数据与接入规范。"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    bridge_info = PluginRegistry.get_client_bridge_info()
    return {
        "status": "success",
        "result": bridge_info,
    }


