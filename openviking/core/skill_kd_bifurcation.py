"""
Teacher-Student Decision Bifurcation Extractor (SKILL-KD Architecture).

Implements:
1. Trajectory representation for weak student and expert teacher models.
2. Bifurcation point localization: Finds the exact turn where student's action diverged from teacher's.
3. Candidate rule generation: Formulates concise, targeted intervention rules from bifurcations.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TrajectoryTurn(BaseModel):
    """Single turn in an agent execution trajectory."""
    turn_idx: int
    action_type: str = "tool_call"  # "tool_call", "thought", "command", "response"
    action_content: str
    observation: str = ""
    is_success: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentTrajectory(BaseModel):
    """Full execution trajectory of an agent solving a task."""
    agent_id: str  # e.g. "student_local_7b" or "teacher_claude_opus"
    task_id: str
    task_description: str
    turns: List[TrajectoryTurn] = Field(default_factory=list)
    final_success: bool = False
    duration_sec: float = 0.0


class BifurcationPoint(BaseModel):
    """Localized point where student trajectory diverged critically from teacher."""
    bifurcation_id: str = Field(default_factory=lambda: f"bif_{uuid.uuid4().hex[:8]}")
    turn_idx: int
    student_action: str
    teacher_action: str
    divergence_reason: str
    state_context: str
    impact_level: str = "critical"  # "critical", "moderate", "minor"


class CandidateRulePatch(BaseModel):
    """A candidate intervention rule extracted from a bifurcation point."""
    patch_id: str = Field(default_factory=lambda: f"rule_{uuid.uuid4().hex[:8]}")
    rule_content: str
    applicable_scenario: str
    bifurcation_id: str
    derived_from_turn: int
    created_at: float = Field(default_factory=time.time)
    verified_green: bool = False
    verification_notes: str = ""


class DecisionBifurcationExtractor:
    """Extracts critical decision divergence between student and teacher."""

    @staticmethod
    def extract_bifurcations(
        student_traj: AgentTrajectory,
        teacher_traj: AgentTrajectory,
    ) -> List[BifurcationPoint]:
        """
        Scans both trajectories turn-by-turn to locate where the student took an erroneous
        path while the teacher took the optimal path.
        """
        bifurcations: List[BifurcationPoint] = []
        max_turns = min(len(student_traj.turns), len(teacher_traj.turns))

        for idx in range(max_turns):
            s_turn = student_traj.turns[idx]
            t_turn = teacher_traj.turns[idx]

            # Compare actions
            s_act = s_turn.action_content.strip()
            t_act = t_turn.action_content.strip()

            # Divergence criteria:
            # 1. Action types differ or actions differ significantly
            # 2. Student turn failed or deviated from teacher's proven successful action
            if (s_turn.action_type != t_turn.action_type or s_act != t_act) and not s_turn.is_success:
                reason = (
                    f"Student executed '{s_act[:60]}...' resulting in failure, "
                    f"whereas teacher executed '{t_act[:60]}...' successfully."
                )
                bifurcations.append(BifurcationPoint(
                    turn_idx=idx,
                    student_action=s_act,
                    teacher_action=t_act,
                    divergence_reason=reason,
                    state_context=s_turn.observation[:120],
                    impact_level="critical" if not student_traj.final_success else "moderate",
                ))

        # If no turn-level failure flagged, but teacher succeeded and student failed
        if not bifurcations and teacher_traj.final_success and not student_traj.final_success:
            # Pick first diverging turn
            for idx in range(max_turns):
                s_turn = student_traj.turns[idx]
                t_turn = teacher_traj.turns[idx]
                if s_turn.action_content.strip() != t_turn.action_content.strip():
                    bifurcations.append(BifurcationPoint(
                        turn_idx=idx,
                        student_action=s_turn.action_content.strip(),
                        teacher_action=t_turn.action_content.strip(),
                        divergence_reason="First branching decision that led to outcome divergence.",
                        state_context=s_turn.observation[:120],
                        impact_level="critical",
                    ))
                    break

        return bifurcations

    @staticmethod
    def generate_candidate_rules(
        bifurcations: List[BifurcationPoint],
        task_scenario: str = "general_coding",
    ) -> List[CandidateRulePatch]:
        """
        Transforms bifurcations into concise, actionable rule patches.
        Ensures rules are actionable constraints rather than generic thoughts.
        """
        rules: List[CandidateRulePatch] = []

        for bif in bifurcations:
            # Synthesize targeted rule
            rule_text = (
                f"When in state ({bif.state_context.strip() or 'similar scenario'}), "
                f"DO NOT perform '{bif.student_action[:50]}'. "
                f"INSTEAD, execute '{bif.teacher_action[:50]}'."
            )
            rules.append(CandidateRulePatch(
                rule_content=rule_text,
                applicable_scenario=task_scenario,
                bifurcation_id=bif.bifurcation_id,
                derived_from_turn=bif.turn_idx,
            ))

        return rules
