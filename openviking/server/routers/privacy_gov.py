# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Privacy Compliance Audit & Sensitive Credential Quarantine REST API Router (SSOT).

Endpoints:
  GET    /api/v1/privacy-gov/quarantine             ← 列出隔离仓条目
  POST   /api/v1/privacy-gov/quarantine             ← 隔离风险凭据实体
  GET    /api/v1/privacy-gov/quarantine/{id}        ← 获取单条隔离元数据
  POST   /api/v1/privacy-gov/quarantine/{id}/restore← 解冻恢复隔离条目
  DELETE /api/v1/privacy-gov/quarantine/{id}        ← 永久物理销毁清零
  GET    /api/v1/privacy-gov/audit-logs             ← 检索合规审计日记账流水
  GET    /api/v1/privacy-gov/audit-report           ← 导出聚合合规度量大盘
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.privacy_quarantine import PrivacyQuarantineEngine
from openviking.service.privacy_quarantine_types import (
    AuditAction,
    QuarantineStatus,
)

router = APIRouter(prefix="/api/v1/privacy-gov", tags=["privacy-gov"])


class QuarantineRequest(BaseModel):
    """隔离高危凭据请求。"""

    model_config = ConfigDict(strict=False)

    target_uri: str = Field(..., description="目标存储 URI 或文件路径")
    raw_content: str = Field(..., description="高危明文数据内容")
    reason: str = Field(..., description="隔离检测原因")
    category: str = Field("credential", description="泄密类型")
    actor: str = Field("cluster_agent", description="发现或上报主体")
    metadata: Mapping[str, Any] = Field(default_factory=dict, description="额外元数据")


class RestoreRequest(BaseModel):
    """解冻恢复隔离请求。"""

    model_config = ConfigDict(strict=False)

    reason: str = Field("verified_safe", description="解冻原因与复核记录")
    actor: str = Field("admin", description="操作主体")


class PurgeRequest(BaseModel):
    """物理销毁清零请求。"""

    model_config = ConfigDict(strict=False)

    reason: str = Field("permanent_destruction", description="销毁审批记录")
    actor: str = Field("compliance_officer", description="操作主体")


@router.get("/quarantine")
async def list_quarantined_items(
    status_filter: Optional[str] = Query(None, alias="status", description="过滤状态: QUARANTINED/RESTORED/PURGED"),
    category: Optional[str] = Query(None, description="过滤敏感分类"),
    ctx: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """列出隔离仓中的所有实体元数据。"""
    engine = PrivacyQuarantineEngine.get_instance()
    clean_status = status_filter if isinstance(status_filter, str) else None
    clean_category = category if isinstance(category, str) else None
    items = engine.list_quarantined(status=clean_status, category=clean_category)
    return {"status": "ok", "items": [i.to_dict() for i in items], "count": len(items)}


@router.post("/quarantine", status_code=status.HTTP_201_CREATED)
async def quarantine_item(
    req: QuarantineRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """将违规明文数据物理隔离入仓并登记合规审计日记账。"""
    engine = PrivacyQuarantineEngine.get_instance()
    item = engine.quarantine(
        target_uri=req.target_uri,
        raw_content=req.raw_content,
        reason=req.reason,
        category=req.category,
        actor=req.actor,
        metadata=req.metadata,
    )
    return {"status": "ok", "item": item.to_dict()}


@router.get("/quarantine/{quarantine_id}")
async def get_quarantined_item(
    quarantine_id: str,
    ctx: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """获取指定隔离 ID 的详细元数据。"""
    engine = PrivacyQuarantineEngine.get_instance()
    item = engine.get_quarantined(quarantine_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quarantine item not found: {quarantine_id}",
        )
    return {"status": "ok", "item": item.to_dict()}


@router.post("/quarantine/{quarantine_id}/restore")
async def restore_quarantined_item(
    quarantine_id: str,
    req: RestoreRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """复核安全后解冻恢复隔离实体。"""
    engine = PrivacyQuarantineEngine.get_instance()
    try:
        updated = engine.restore(
            quarantine_id=quarantine_id, actor=req.actor, reason=req.reason
        )
        return {"status": "ok", "item": updated.to_dict()}
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quarantine item not found: {quarantine_id}",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/quarantine/{quarantine_id}")
async def purge_quarantined_item(
    quarantine_id: str,
    req: Optional[PurgeRequest] = None,
    ctx: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """安全清零并物理删除隔离仓中的泄密实体。"""
    engine = PrivacyQuarantineEngine.get_instance()
    reason = req.reason if req else "permanent_destruction"
    actor = req.actor if req else "compliance_officer"
    try:
        success = engine.purge(
            quarantine_id=quarantine_id, actor=actor, reason=reason
        )
        return {"status": "ok", "purged": success}
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quarantine item not found: {quarantine_id}",
        )


@router.get("/audit-logs")
async def list_audit_logs(
    limit: int = Query(50, ge=1, le=500, description="返回的最大条数"),
    action: Optional[str] = Query(None, description="过滤审计行为: MASK/SCAN/QUARANTINE/RESTORE/PURGE"),
    ctx: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """检索合规审计流水日志。"""
    engine = PrivacyQuarantineEngine.get_instance()
    clean_limit = limit if isinstance(limit, int) else 50
    clean_action = action if isinstance(action, str) else None
    entries = engine.list_audit_entries(limit=clean_limit, action=clean_action)
    return {"status": "ok", "entries": [e.to_dict() for e in entries], "count": len(entries)}


@router.get("/audit-report")
async def get_compliance_report(
    ctx: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """获取聚合合规审计度量大盘与分类统计指标。"""
    engine = PrivacyQuarantineEngine.get_instance()
    report = engine.get_compliance_report()
    return {"status": "ok", "report": report.to_dict()}
