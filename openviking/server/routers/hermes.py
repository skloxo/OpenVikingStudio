# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Hermes 经历与能力解耦、异步复盘与微手术 REST API 路由。

端点:
  POST /api/v1/hermes/experience             ← 记录真实经历消息
  GET  /api/v1/hermes/experience/search      ← 跨会话 FTS5 检索
  GET  /api/v1/hermes/experience/session/{id}← 获取会话全部消息
  POST /api/v1/hermes/nudge/trigger          ← 异步触发轨迹复盘
  GET  /api/v1/hermes/nudge/status           ← 复盘运行状态与历史
  POST /api/v1/hermes/patch/propose          ← 提议微补丁 (≤30行门禁)
  POST /api/v1/hermes/patch/{id}/apply       ← 应用微补丁
  POST /api/v1/hermes/patch/{id}/revert      ← 回滚微补丁
  GET  /api/v1/hermes/patches                ← 补丁列表
  GET  /api/v1/hermes/summary                ← 全局汇总
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from openviking.core.hermes_experience_store import HermesExperienceStore
from openviking.core.hermes_nudge_engine import HermesNudgeEngine
from openviking.core.hermes_patch_engine import HermesPatchEngine, SkillPatch

router = APIRouter(prefix="/api/v1/hermes", tags=["hermes"])

_exp_store = HermesExperienceStore.get_instance()
_nudge_engine = HermesNudgeEngine.get_instance()
_patch_engine = HermesPatchEngine.get_instance()


# ---------------------------------------------------------------------------
# 请求体 DTOs
# ---------------------------------------------------------------------------

class RecordExperienceRequest(BaseModel):
    session_id: str
    role: str
    content: str
    tool_calls: Optional[Any] = None
    meta: Optional[Dict[str, Any]] = None


class TriggerNudgeRequest(BaseModel):
    session_id: str


class ProposePatchRequest(BaseModel):
    skill_name: str
    file_path: str
    target_content: str
    replacement_content: str
    reason: str


# ---------------------------------------------------------------------------
# 经历存储与 FTS5 端点
# ---------------------------------------------------------------------------

@router.post("/experience")
async def record_experience(req: RecordExperienceRequest) -> Dict[str, Any]:
    """记录单条原始交互经历（只增不删）。"""
    msg = _exp_store.record_message(
        session_id=req.session_id,
        role=req.role,
        content=req.content,
        tool_calls=req.tool_calls,
        meta=req.meta,
    )
    return {"status": "recorded", "msg_id": msg.msg_id}


@router.get("/experience/search")
async def search_experiences(
    q: str = Query(..., description="FTS5 检索关键词"),
    limit: int = Query(default=20, ge=1, le=100),
) -> Dict[str, Any]:
    """跨会话 FTS5 真实消息检索。"""
    results = _exp_store.search_messages(query=q, limit=limit)
    return {"query": q, "total_matches": len(results), "matches": [r.model_dump() for r in results]}


@router.get("/experience/session/{session_id}")
async def get_session_experiences(session_id: str) -> Dict[str, Any]:
    """获取指定会话的所有真实经历消息。"""
    msgs = _exp_store.get_messages_by_session(session_id)
    return {"session_id": session_id, "count": len(msgs), "messages": [m.model_dump() for m in msgs]}


# ---------------------------------------------------------------------------
# Periodic Nudge 异步复盘端点
# ---------------------------------------------------------------------------

@router.post("/nudge/trigger")
async def trigger_nudge(req: TriggerNudgeRequest) -> Dict[str, Any]:
    """将指定会话排入异步副进程复盘队列。"""
    return _nudge_engine.trigger_nudge(req.session_id)


@router.get("/nudge/status")
async def get_nudge_status() -> Dict[str, Any]:
    """查询复盘队列与最近复盘记录。"""
    status = _nudge_engine.get_status()
    reviews = _nudge_engine.list_recent_reviews()
    return {**status, "recent_reviews": [r.model_dump() for r in reviews]}


# ---------------------------------------------------------------------------
# Patch 优先微手术端点
# ---------------------------------------------------------------------------

@router.post("/patch/propose", response_model=SkillPatch)
async def propose_patch(req: ProposePatchRequest) -> SkillPatch:
    """提议微手术补丁，强制校验 ≤30 行物理门禁。"""
    try:
        return _patch_engine.propose_patch(
            skill_name=req.skill_name,
            file_path=req.file_path,
            target_content=req.target_content,
            replacement_content=req.replacement_content,
            reason=req.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/patch/{patch_id}/apply", response_model=SkillPatch)
async def apply_patch(patch_id: str) -> SkillPatch:
    """原子化应用微手术补丁。"""
    try:
        return _patch_engine.apply_patch(patch_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/patch/{patch_id}/revert", response_model=SkillPatch)
async def revert_patch(patch_id: str) -> SkillPatch:
    """一键回滚微手术补丁。"""
    try:
        return _patch_engine.revert_patch(patch_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/patches", response_model=List[SkillPatch])
async def list_patches(
    skill_name: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
) -> List[SkillPatch]:
    """查询微手术补丁列表。"""
    return _patch_engine.list_patches(skill_name=skill_name, status=status)


# ---------------------------------------------------------------------------
# 全局汇总端点
# ---------------------------------------------------------------------------

@router.get("/summary")
async def hermes_summary() -> Dict[str, Any]:
    """Hermes 经历解耦、异步复盘与微补丁全局汇总。"""
    return {
        "experience": _exp_store.stats(),
        "nudge": _nudge_engine.get_status(),
        "patches": _patch_engine.summary(),
    }
