# -*- coding: utf-8 -*-
"""REST API router for Evolution CI/CD Pipeline & Offline Dreaming Gate.

Card-Evolution-CICD-DreamingGate (v1.5.43)
Exposes endpoints for 7-stage evolution pipelines, Dreaming defect mining,
autonomy ladder controls, and emergency rollbacks.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from openviking.core.evolution_cicd import (
    AutonomousLevel,
    EvolutionCICDPipeline,
)
from openviking.core.dreaming_gate import (
    DreamingDefectMiner,
)

router = APIRouter(prefix="/api/v1/evolution", tags=["evolution-cicd"])


class CreatePackageRequest(BaseModel):
    target_skill: str = Field(..., description="Name of the skill being modified")
    diff_patch: str = Field(..., description="Unified diff content of the modification")


class AdvancePackageRequest(BaseModel):
    package_id: str = Field(..., description="ID of the evolution package to advance")


class TriggerDreamingRequest(BaseModel):
    traces: Optional[List[Dict[str, Any]]] = Field(None, description="Optional traces to scan")


class SetAutonomyLevelRequest(BaseModel):
    level: AutonomousLevel = Field(..., description="Desired autonomy level (L0 to L3)")


class RollbackRequest(BaseModel):
    package_id: Optional[str] = Field(None, description="Optional specific package ID to revert")


@router.post("/pipeline/package")
def create_evolution_package(req: CreatePackageRequest) -> Dict[str, Any]:
    """Create a new candidate evolution package entering the pipeline."""
    pipeline = EvolutionCICDPipeline.get_instance()
    pkg = pipeline.create_package(target_skill=req.target_skill, diff_patch=req.diff_patch)
    return {
        "status": "success",
        "package": {
            "package_id": pkg.package_id,
            "target_skill": pkg.target_skill,
            "line_count": pkg.line_count,
            "current_stage": pkg.current_stage.value,
            "canary_traffic_pct": pkg.canary_traffic_pct,
            "passed_safety_gate": pkg.passed_safety_gate,
            "rolled_back": pkg.rolled_back,
        }
    }


@router.post("/pipeline/advance")
def advance_evolution_package(req: AdvancePackageRequest) -> Dict[str, Any]:
    """Advance a package through its current pipeline stage towards crystallization."""
    pipeline = EvolutionCICDPipeline.get_instance()
    success, msg = pipeline.advance_package(req.package_id)
    pkg = pipeline.packages.get(req.package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found.")

    return {
        "success": success,
        "message": msg,
        "package_id": pkg.package_id,
        "current_stage": pkg.current_stage.value,
        "canary_traffic_pct": pkg.canary_traffic_pct,
        "passed_safety_gate": pkg.passed_safety_gate,
        "rolled_back": pkg.rolled_back,
    }


@router.get("/pipeline/packages")
def list_evolution_packages() -> Dict[str, Any]:
    """List all registered evolution packages and their stages."""
    pipeline = EvolutionCICDPipeline.get_instance()
    return {
        "total": len(pipeline.packages),
        "packages": [
            {
                "package_id": p.package_id,
                "target_skill": p.target_skill,
                "line_count": p.line_count,
                "current_stage": p.current_stage.value,
                "canary_traffic_pct": p.canary_traffic_pct,
                "passed_safety_gate": p.passed_safety_gate,
                "rolled_back": p.rolled_back,
                "created_at": p.created_at,
            }
            for p in sorted(pipeline.packages.values(), key=lambda x: x.created_at, reverse=True)
        ]
    }


@router.post("/dreaming/trigger")
def trigger_offline_dreaming(req: Optional[TriggerDreamingRequest] = None) -> Dict[str, Any]:
    """Trigger offline asynchronous Dreaming defect mining and tri-gate fusion."""
    miner = DreamingDefectMiner.get_instance()
    traces = req.traces if req else None
    result = miner.run_dreaming_cycle(sample_traces=traces)
    return {"status": "success", "result": result}


@router.get("/dreaming/status")
def get_dreaming_status() -> Dict[str, Any]:
    """Retrieve current status of offline Dreaming miner and mined defect clusters."""
    miner = DreamingDefectMiner.get_instance()
    return {
        "status": miner.status.status,
        "last_run_timestamp": miner.status.last_run_timestamp,
        "total_traces_scanned": miner.status.total_traces_scanned,
        "defects_mined": miner.status.defects_mined,
        "crystals_fused": miner.status.crystals_fused,
        "defects": [d.__dict__ for d in miner.defects.values()],
    }


@router.get("/governance")
def get_governance_state() -> Dict[str, Any]:
    """Retrieve autonomy level, second-order metrics, and kill-switch status."""
    pipeline = EvolutionCICDPipeline.get_instance()
    metrics = pipeline.metrics
    metrics.evaluate_drift()
    return {
        "autonomous_level": pipeline.autonomous_level.value,
        "emergency_kill_switch_tripped": pipeline.emergency_kill_switch_tripped,
        "auto_downgrade_count": pipeline.auto_downgrade_count,
        "second_order_metrics": {
            "output_length_ratio": metrics.output_length_ratio,
            "refusal_rate": metrics.refusal_rate,
            "retry_rate": metrics.retry_rate,
            "drift_detected": metrics.drift_detected,
        }
    }


@router.post("/governance/level")
def set_autonomy_level(req: SetAutonomyLevelRequest) -> Dict[str, Any]:
    """Set the system autonomy level (Human Inviolable Decision Right)."""
    pipeline = EvolutionCICDPipeline.get_instance()
    pipeline.set_autonomous_level(req.level)
    return {
        "status": "success",
        "new_level": pipeline.autonomous_level.value,
    }


@router.post("/governance/rollback")
def emergency_rollback(req: Optional[RollbackRequest] = None) -> Dict[str, Any]:
    """Execute immediate emergency kill-switch, roll back canary, and drop to Level 0."""
    pipeline = EvolutionCICDPipeline.get_instance()
    target_id = req.package_id if req else None
    result = pipeline.trigger_emergency_rollback(package_id=target_id)
    return result
