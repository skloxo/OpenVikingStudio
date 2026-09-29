# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""RSI 昼夜双轮与可训练策略 REST API 路由。

【架构现状与守护说明 (SSOT Architectural Guard)】:
  - 本模块是 OpenViking 智能体递归自演进 (RSI) 的关键协议与状态机骨架；
  - 严禁删除 (DO NOT DELETE)：依据 Agent 认知连续性第一法则，任何跨会话 Agent 严禁删减此骨架；
  - 当前状态为接口契约与测试台阶段，完整的 SQLite 物理落盘与自动化 Holdout 盲测演进
    已正式立卡排期在 `REFACTORING_PLAN.md` ➔ `[P2] Card-26 (v1.5.90)` 闭环落地。

端点:
  GET  /api/v1/rsi/status           ← 当前昼夜状态与全局统计
  POST /api/v1/rsi/phase/switch     ← 切换昼夜模式
  POST /api/v1/rsi/trajectory/record← 白昼收集执行轨迹回合
  POST /api/v1/rsi/credit/evaluate  ← AgentOPSD 局部信用分配
  POST /api/v1/rsi/surface/inspect  ← 审查技能文档 # EVOLVE-BLOCK
  POST /api/v1/rsi/surface/update   ← 有界更新 # EVOLVE-BLOCK (冻结面保护)
  POST /api/v1/rsi/gate/verify_split← 双 Split 零退化门禁核验
  POST /api/v1/rsi/cycle/run_nighttime ← 夜间演进周期 (Card-26 持续演进)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from openviking.core.rsi_credit_allocator import RSICreditAllocator
from openviking.core.rsi_day_night_engine import DualSplitGateResult, RSIDayNightEngine, RSIPhase
from openviking.core.rsi_trajectory_store import RSITrajectoryStore
from openviking.core.trainable_skill_policy import SurfaceInspectionResult, TrainableSkillDocument

router = APIRouter(prefix="/api/v1/rsi", tags=["rsi"])


def _get_engine() -> RSIDayNightEngine:
    return RSIDayNightEngine.get_instance()


# ---------------------------------------------------------------------------
# 请求体 DTOs
# ---------------------------------------------------------------------------

class SwitchPhaseRequest(BaseModel):
    target_phase: Optional[RSIPhase] = None


class RecordTurnRequest(BaseModel):
    session_id: str
    turn_data: Dict[str, Any]


class EvaluateCreditRequest(BaseModel):
    session_id: Optional[str] = None
    turns: Optional[List[Dict[str, Any]]] = None
    gap_threshold: Optional[float] = None


class InspectSurfaceRequest(BaseModel):
    raw_text: str
    skill_name: Optional[str] = "unnamed"


class UpdateSurfaceRequest(BaseModel):
    raw_text: str
    block_index: int
    new_content: str
    skill_name: Optional[str] = "unnamed"


class VerifySplitRequest(BaseModel):
    train_results: List[bool]
    holdout_results: List[bool]
    baseline_holdout_pass_rate: Optional[float] = 0.8


# ---------------------------------------------------------------------------
# 端点实现
# ---------------------------------------------------------------------------

@router.get("/status")
async def get_rsi_status() -> Dict[str, Any]:
    """获取 RSI 昼夜引擎当前运行状态与统计。"""
    return _get_engine().summary()


@router.post("/phase/switch")
async def switch_rsi_phase(req: SwitchPhaseRequest) -> Dict[str, Any]:
    """手动或定时切换昼夜状态。"""
    new_phase = _get_engine().switch_phase(req.target_phase)
    return {"status": "switched", "current_phase": new_phase.value}


@router.post("/trajectory/record")
async def record_trajectory_turn(req: RecordTurnRequest) -> Dict[str, Any]:
    """白昼阶段收集执行轨迹回合。"""
    _get_engine().record_turn(req.session_id, req.turn_data)
    return {"status": "recorded", "session_id": req.session_id}


@router.post("/credit/evaluate")
async def evaluate_credit(req: EvaluateCreditRequest) -> Dict[str, Any]:
    """执行 AgentOPSD 局部信用分配与关键回合标定。"""
    if req.session_id:
        res = _get_engine().evaluate_session_credits(req.session_id)
        if res is None:
            raise HTTPException(status_code=404, detail=f"No trajectory found for session: {req.session_id}")
        return res.model_dump()

    if req.turns:
        res = RSICreditAllocator.evaluate_trajectory(req.turns, gap_threshold=req.gap_threshold)
        return res.model_dump()

    raise HTTPException(status_code=400, detail="Must provide either session_id or turns list")


@router.post("/surface/inspect", response_model=SurfaceInspectionResult)
async def inspect_surface(req: InspectSurfaceRequest) -> SurfaceInspectionResult:
    """分析文档中的有界可编辑区块与冻结面指纹。"""
    doc = TrainableSkillDocument(req.raw_text, skill_name=req.skill_name or "unnamed")
    return doc.inspect()


@router.post("/surface/update")
async def update_surface(req: UpdateSurfaceRequest) -> Dict[str, Any]:
    """安全更新指定 index 的有界区块，确保外部冻结面绝对零篡改。"""
    try:
        doc = TrainableSkillDocument(req.raw_text, skill_name=req.skill_name or "unnamed")
        updated_doc = doc.update_block(req.block_index, req.new_content)
        return {
            "status": "updated",
            "updated_text": updated_doc.raw_text,
            "inspection": updated_doc.inspect().model_dump(),
        }
    except (IndexError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/gate/verify_split", response_model=DualSplitGateResult)
async def verify_dual_split(req: VerifySplitRequest) -> DualSplitGateResult:
    """双 Split 零退化回归门禁检验。"""
    return _get_engine().verify_dual_split_gate(
        train_results=req.train_results,
        holdout_results=req.holdout_results,
        baseline_holdout_pass_rate=req.baseline_holdout_pass_rate or 0.8,
    )


class RunNighttimeCycleRequest(BaseModel):
    baseline_holdout_pass_rate: Optional[float] = 0.8
    train_results: Optional[List[bool]] = None
    holdout_results: Optional[List[bool]] = None


@router.post("/cycle/run_nighttime")
async def run_nighttime_cycle_endpoint(req: Optional[RunNighttimeCycleRequest] = None) -> Dict[str, Any]:
    """运行夜间做梦与双 Split 零退化门禁自演进周期 (Card-20G / Card-26)。"""
    baseline = (req.baseline_holdout_pass_rate or 0.8) if req else 0.8
    train_res = req.train_results if req else None
    holdout_res = req.holdout_results if req else None
    return _get_engine().run_nighttime_cycle(
        baseline_holdout_pass_rate=baseline,
        train_results=train_res,
        holdout_results=holdout_res,
    )


@router.get("/trajectories")
async def list_persisted_trajectories(limit: int = Query(50, ge=1, le=200)) -> Dict[str, Any]:
    """获取 SQLite 持久化的白昼轨迹会话明细。"""
    engine = _get_engine()
    store = engine._store or RSITrajectoryStore.get_instance()
    trajs = store.load_trajectories(limit_sessions=limit)
    return {
        "total_sessions": len(trajs),
        "sessions": [
            {"session_id": sid, "turn_count": len(turns)}
            for sid, turns in trajs.items()
        ],
    }


@router.get("/gates/history")
async def list_gate_history(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    """获取 SQLite 持久化的双 Split 门禁历史记录。"""
    engine = _get_engine()
    store = engine._store or RSITrajectoryStore.get_instance()
    return store.get_gate_history(limit=limit)


class EvolveSkillRequest(BaseModel):
    target_skill_path: str
    block_index: int
    new_content: str
    baseline_holdout_pass_rate: Optional[float] = 0.8


@router.post("/evolve")
async def evolve_skill_endpoint(req: EvolveSkillRequest) -> Dict[str, Any]:
    """物理受控演进闭环：更新 # EVOLVE-BLOCK 并经双 Split 门禁验证后决定是否保存落盘。"""
    try:
        return _get_engine().evolve_skill_policy(
            target_skill_path=req.target_skill_path,
            block_index=req.block_index,
            new_content=req.new_content,
            baseline_holdout_pass_rate=req.baseline_holdout_pass_rate or 0.8,
        )
    except (FileNotFoundError, IndexError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

