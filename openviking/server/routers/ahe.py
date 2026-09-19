# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""AHE 契约三元组自演进 REST API 路由。

端点:
  POST /api/v1/ahe/manifest           ← 创建契约 Manifest
  GET  /api/v1/ahe/manifest           ← 列出 Manifest
  GET  /api/v1/ahe/manifest/{id}      ← 查询单个 Manifest
  POST /api/v1/ahe/manifest/{id}/verify   ← Polar 判官验证
  POST /api/v1/ahe/manifest/{id}/violate  ← 手动上报违约 + 归因聚类
  GET  /api/v1/ahe/manifest/{id}/drift    ← 快照漂移检测
  GET  /api/v1/ahe/clusters           ← 根因聚类目录
  GET  /api/v1/ahe/summary            ← 全局汇总
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from openviking.core.ahe_engine import AHEEngine
from openviking.core.ahe_manifest import AHEManifest, AHEStatus, MechanismKind
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/ahe", tags=["ahe"])

_engine = AHEEngine.get_instance()


# ---------------------------------------------------------------------------
# 请求体 DTOs
# ---------------------------------------------------------------------------

class CreateManifestRequest(BaseModel):
    skill_name: str
    assumptions: Optional[List[Dict[str, Any]]] = None
    snapshot_paths: Optional[List[str]] = None


class ViolateRequest(BaseModel):
    mechanism: MechanismKind = MechanismKind.UNKNOWN
    description: str = ""


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------

@router.post("/manifest", response_model=AHEManifest)
async def create_manifest(req: CreateManifestRequest) -> AHEManifest:
    """创建并注册一个新的 AHE 契约 Manifest。"""
    return _engine.create_manifest(
        skill_name=req.skill_name,
        assumptions=req.assumptions,
        snapshot_paths=req.snapshot_paths,
    )


@router.get("/manifest", response_model=List[AHEManifest])
async def list_manifests(
    skill_name: Optional[str] = Query(default=None),
    status: Optional[AHEStatus] = Query(default=None),
) -> List[AHEManifest]:
    """列出所有 Manifest，支持按技能名或状态过滤。"""
    return _engine.list_manifests(skill_name=skill_name, status=status)


@router.get("/manifest/{manifest_id}", response_model=AHEManifest)
async def get_manifest(manifest_id: str) -> Dict[str, Any]:
    """查询单个 Manifest。"""
    m = _engine.get_manifest(manifest_id)
    if m is None:
        return {"error": f"Not found: {manifest_id}"}
    return m


@router.post("/manifest/{manifest_id}/verify")
async def verify_manifest(manifest_id: str, cwd: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    """对 Manifest 中所有假设调用 Polar 判官，返回不可伪造的沙箱验证结果。"""
    return _engine.verify_manifest(manifest_id, cwd=cwd)


@router.post("/manifest/{manifest_id}/violate")
async def violate_manifest(manifest_id: str, req: ViolateRequest) -> Dict[str, Any]:
    """手动上报 Manifest 违约，触发根因聚类 + 补丁冲突检测。"""
    return _engine.ingest_violation(
        manifest_id=manifest_id,
        mechanism=req.mechanism,
        description=req.description,
    )


@router.get("/manifest/{manifest_id}/drift")
async def check_drift(manifest_id: str) -> Dict[str, Any]:
    """检测文件快照漂移，作为可回滚判定依据。"""
    return _engine.check_snapshot_drift(manifest_id)


@router.get("/clusters")
async def list_clusters() -> Dict[str, Any]:
    """返回根因机制聚类目录（按发生频率降序）。"""
    catalog = _engine._catalog
    return {
        "clusters": [
            {
                "cluster_id": c.cluster_id,
                "mechanism": c.mechanism.value,
                "description": c.description,
                "occurrence_count": c.occurrence_count,
                "patched": c.patched,
                "patch_commit": c.patch_commit,
                "first_seen_at": c.first_seen_at,
                "last_seen_at": c.last_seen_at,
            }
            for c in catalog.get_all()
        ],
        "summary": catalog.summary(),
    }


@router.get("/summary")
async def ahe_summary() -> Dict[str, Any]:
    """AHE 全局汇总：Manifest 统计 + 聚类统计。"""
    return _engine.global_summary()
