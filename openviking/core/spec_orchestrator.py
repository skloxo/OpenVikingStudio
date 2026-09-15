# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Spec-Driven Multi-Agent Orchestrator: Role Separation & File-Driven Bus.
(Card-Harness-SpecDrivenFSM - v1.5.07)

Derived from Alibaba Qwen Data Warehouse Harness & Qwen Skill-SP:
1. Physical Role Separation: Orchestrator schedules and audits; Specialists execute
   narrow-interface tickets in sandboxes; Evaluators perform independent verification.
2. Generator != Evaluator Invariant: Prevents self-review collusion.
3. Spec File-Driven Bus: Replaces noisy multi-turn chat memory with structured
   file path passing and immutable CP checkpoint manifests.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import os
import time
from typing import Dict, List, Optional, Tuple

from openviking.core.harness_fsm import HarnessFSM, HarnessState, InvalidTransitionError


class AgentRoleType(str, Enum):
    """Rigid agent specializations preventing monolithic drift."""
    ORCHESTRATOR = "ORCHESTRATOR"  # Coordinator: Planning, DAG, and dispatch only. Zero code-writing.
    SPECIALIST = "SPECIALIST"      # Deep-module worker: Executes narrow tickets in sandbox.
    EVALUATOR = "EVALUATOR"        # Independent auditor: Verifies acceptance against spec P.


class RoleViolationError(PermissionError):
    """Raised when an agent role performs an unauthorized operation."""
    pass


class EvaluatorCollusionError(PermissionError):
    """Raised when the generator attempts to evaluate its own deliverable."""
    pass


@dataclass(frozen=True)
class SpecFileArtifact:
    """Immutable tracked artifact in the file-driven bus."""
    file_path: str
    sha256_hash: str
    description: str = ""


@dataclass(frozen=True)
class CheckpointManifest:
    """Structured CP checkpoint snapshot for state restoration."""
    checkpoint_id: str
    state: HarnessState
    active_role: AgentRoleType
    artifacts: List[SpecFileArtifact] = field(default_factory=list)
    audit_trail: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


class SpecDrivenOrchestrator:
    """
    Coordinates multi-agent execution via 12-state FSM and structured file manifests.
    Enforces strict role isolation and anti-collusion evaluation.
    """

    def __init__(self, fsm: Optional[HarnessFSM] = None) -> None:
        self.fsm = fsm or HarnessFSM()
        self._artifacts: Dict[str, SpecFileArtifact] = {}
        self._checkpoints: Dict[str, CheckpointManifest] = {}
        self._last_generator_id: Optional[str] = None

    @property
    def current_state(self) -> HarnessState:
        return self.fsm.current_state

    @classmethod
    def compute_file_hash(cls, file_path: str) -> str:
        """Computes SHA-256 for a physical file on disk."""
        if not os.path.isfile(file_path):
            return hashlib.sha256(b"").hexdigest()[:16]
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        except Exception:
            return "unknown_hash"

    def register_artifact(self, file_path: str, description: str = "") -> SpecFileArtifact:
        """Registers a physical file into the spec-driven bus."""
        h = self.compute_file_hash(file_path)
        art = SpecFileArtifact(file_path=file_path, sha256_hash=h, description=description)
        self._artifacts[file_path] = art
        return art

    def dispatch_ticket(
        self,
        ticket_id: str,
        specialist_id: str,
        role: AgentRoleType,
    ) -> None:
        """
        Dispatches a tracer-bullet ticket to a specialist worker.
        Asserts that the orchestrator itself does not do code generation.
        """
        if role != AgentRoleType.SPECIALIST:
            raise RoleViolationError(
                f"Cannot dispatch work to {role.value}. Only SPECIALIST roles may execute code tasks."
            )

        if self.fsm.current_state != HarnessState.DISPATCH:
            if self.fsm.can_transition(HarnessState.DISPATCH):
                self.fsm.transition_to(HarnessState.DISPATCH, reason=f"Preparing dispatch for ticket {ticket_id}")

        self.fsm.transition_to(
            HarnessState.RUNNING,
            reason=f"Specialist {specialist_id} executing ticket {ticket_id}",
        )
        self._last_generator_id = specialist_id

    def submit_for_verification(self, changed_files: List[str]) -> None:
        """Advances state from RUNNING to VERIFY for physical gate checks."""
        for fp in changed_files:
            self.register_artifact(fp)

        self.fsm.transition_to(
            HarnessState.VERIFY,
            reason="Submitting changes to PhysicalDiffVerifier and TestRetinaRunner",
        )

    def evaluate_delivery(
        self,
        evaluator_id: str,
        evaluator_role: AgentRoleType,
        verdict_passed: bool,
        notes: str = "",
    ) -> None:
        """
        Independent evaluation step enforcing Generator != Evaluator invariant.
        """
        if evaluator_role != AgentRoleType.EVALUATOR:
            raise RoleViolationError(
                f"Role {evaluator_role.value} cannot evaluate deliverables. Only EVALUATOR is authorized."
            )

        # Anti-collusion assertion
        if evaluator_id == self._last_generator_id and self._last_generator_id is not None:
            raise EvaluatorCollusionError(
                f"Evaluator collusion detected! Generator '{self._last_generator_id}' "
                f"cannot evaluate their own deliverables. Independent evaluation required."
            )

        # Transition to EVALUATE if from VERIFY
        if self.fsm.current_state == HarnessState.VERIFY:
            self.fsm.transition_to(HarnessState.EVALUATE, reason=f"Evaluator {evaluator_id} reviewing")

        if verdict_passed:
            self.fsm.transition_to(
                HarnessState.CHECKPOINT,
                reason=f"Evaluation approved by {evaluator_id}: {notes}",
            )
        else:
            self.fsm.transition_to(
                HarnessState.DISPATCH,
                reason=f"Evaluation rejected by {evaluator_id}, routed back: {notes}",
            )

    def save_checkpoint(self, checkpoint_id: str) -> CheckpointManifest:
        """Persists current state and artifacts as a resumption checkpoint."""
        manifest = CheckpointManifest(
            checkpoint_id=checkpoint_id,
            state=self.fsm.current_state,
            active_role=AgentRoleType.ORCHESTRATOR,
            artifacts=list(self._artifacts.values()),
            audit_trail=[f"{r.from_state.value} -> {r.to_state.value} ({r.reason})" for r in self.fsm.history],
        )
        self._checkpoints[checkpoint_id] = manifest
        return manifest

    def complete_lifecycle(self, reason: str = "All tickets validated and delivered") -> None:
        """Terminates workflow with COMPLETED state."""
        if self.fsm.can_transition(HarnessState.COMPLETED):
            self.fsm.transition_to(HarnessState.COMPLETED, reason=reason)
