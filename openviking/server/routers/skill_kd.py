"""
REST API router for SKILL-KD contrastive distillation & re-execution gate.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from openviking.core.skill_kd_bifurcation import (
    AgentTrajectory,
    BifurcationPoint,
    CandidateRulePatch,
    DecisionBifurcationExtractor,
    TrajectoryTurn,
)
from openviking.core.reexecution_gate import (
    ConsolidationSummary,
    DriftAwareRuleConsolidator,
    ReexecutionResult,
    ReexecutionSandboxGate,
    skill_kd_store,
)

router = APIRouter(prefix="/api/v1/skill-kd", tags=["SkillKD"])


class ExtractBifurcationRequest(BaseModel):
    student_trajectory: AgentTrajectory
    teacher_trajectory: AgentTrajectory
    task_scenario: str = "python_backend"


class ReexecuteRequest(BaseModel):
    patch_id: str
    task_id: str
    student_model_id: str = "student_local_7b"
    force_mock_outcome: Optional[bool] = None


class ConsolidateRequest(BaseModel):
    max_lines_limit: int = 300


def _seed_canonical_demo_data() -> None:
    """Pre-seeds canonical bifurcation demo if store is empty."""
    if skill_kd_store.get_metrics()["total_candidate_rules"] > 0:
        return

    # Canonical Case: Asyncio Task Cancellation Pitfall
    student_traj = AgentTrajectory(
        agent_id="student_local_7b",
        task_id="task_asyncio_cancel_01",
        task_description="Gracefully cancel background worker on SIGTERM without leaking tasks",
        turns=[
            TrajectoryTurn(
                turn_idx=0,
                action_type="command",
                action_content="grep -rn 'asyncio.create_task' src/",
                observation="Found 4 task creations in worker.py",
                is_success=True,
            ),
            TrajectoryTurn(
                turn_idx=1,
                action_type="tool_call",
                action_content="task.cancel() without awaiting asyncio.gather(return_exceptions=True)",
                observation="AssertionError: 2 pending tasks were destroyed while still running!",
                is_success=False,
            ),
        ],
        final_success=False,
    )

    teacher_traj = AgentTrajectory(
        agent_id="teacher_claude_opus",
        task_id="task_asyncio_cancel_01",
        task_description="Gracefully cancel background worker on SIGTERM without leaking tasks",
        turns=[
            TrajectoryTurn(
                turn_idx=0,
                action_type="command",
                action_content="grep -rn 'asyncio.create_task' src/",
                observation="Found 4 task creations in worker.py",
                is_success=True,
            ),
            TrajectoryTurn(
                turn_idx=1,
                action_type="tool_call",
                action_content="task.cancel() followed by await asyncio.gather(*tasks, return_exceptions=True)",
                observation="All tasks gracefully awaited. 0 leaked tasks. Test PASS.",
                is_success=True,
            ),
        ],
        final_success=True,
    )

    bifs = DecisionBifurcationExtractor.extract_bifurcations(student_traj, teacher_traj)
    rules = DecisionBifurcationExtractor.generate_candidate_rules(bifs, "asyncio_concurrency")

    for r in rules:
        skill_kd_store.add_rule(r)
        # Verify in sandbox
        res = ReexecutionSandboxGate.evaluate_rule_in_sandbox(
            r, "task_asyncio_cancel_01", "student_local_7b"
        )
        skill_kd_store.record_result(res)


_seed_canonical_demo_data()


@router.post("/bifurcation/extract")
def extract_bifurcations_and_rules(req: ExtractBifurcationRequest) -> Dict[str, Any]:
    """Extract decision bifurcations and generate candidate rules."""
    bifs = DecisionBifurcationExtractor.extract_bifurcations(
        req.student_trajectory, req.teacher_trajectory
    )
    rules = DecisionBifurcationExtractor.generate_candidate_rules(bifs, req.task_scenario)

    for r in rules:
        skill_kd_store.add_rule(r)

    return {
        "bifurcation_count": len(bifs),
        "bifurcations": bifs,
        "candidate_rules": rules,
    }


@router.post("/reexecute", response_model=ReexecutionResult)
def reexecute_rule(req: ReexecuteRequest) -> ReexecutionResult:
    """Run weak student in sandbox with rule to verify if task turns green."""
    rule = skill_kd_store.get_rule(req.patch_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule patch '{req.patch_id}' not found")

    result = ReexecutionSandboxGate.evaluate_rule_in_sandbox(
        patch=rule,
        task_id=req.task_id,
        student_model_id=req.student_model_id,
        force_mock_outcome=req.force_mock_outcome,
    )
    skill_kd_store.record_result(result)
    return result


@router.post("/rules/consolidate", response_model=ConsolidationSummary)
def consolidate_verified_rules(req: ConsolidateRequest) -> ConsolidationSummary:
    """Consolidate verified rules to prevent rule explosion (<= 300 lines)."""
    verified = skill_kd_store.list_rules(only_verified=True)
    return DriftAwareRuleConsolidator.consolidate(verified, req.max_lines_limit)


@router.get("/rules", response_model=List[CandidateRulePatch])
def list_rules(only_verified: bool = False) -> List[CandidateRulePatch]:
    """List candidate and verified rules."""
    return skill_kd_store.list_rules(only_verified=only_verified)


@router.get("/metrics")
def get_metrics() -> Dict[str, Any]:
    """Get operational metrics for SKILL-KD distillation and sandbox gates."""
    return skill_kd_store.get_metrics()
