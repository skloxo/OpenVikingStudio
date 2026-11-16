# -*- coding: utf-8 -*-
"""Agent Evolution CI/CD Pipeline & Autonomous Governance Engine.

Card-Evolution-CICD-DreamingGate (v1.5.43)
Implements 7-stage evolution lifecycle, 4-tier autonomous levels,
and 2nd-order metrics drift monitoring with instant auto-rollback.
"""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openviking.core.rsi_trajectory_store import RSITrajectoryStore
from openviking.core.skillhone_regression import (
    IsolatedSkillEvaluator,
    OptimizerFailureContext,
    build_optimizer_context,
    build_reviewable_change_summary,
    compute_bundle_fingerprint,
    sanitize_failure_text,
)


class PipelineStage(str, enum.Enum):
    """The 7-stage evolution change pipeline."""
    SIGNAL_AGGREGATION = "signal_aggregation"
    CANDIDATE_GENERATION = "candidate_generation"
    ISOLATED_EVALUATION = "isolated_evaluation"
    SAFETY_GATE = "safety_gate"
    CANARY_ROLLOUT = "canary_rollout"
    MONITORING_ROLLBACK = "monitoring_rollback"
    EXPERIENCE_CRYSTALLIZATION = "experience_crystallization"


class AutonomousLevel(str, enum.Enum):
    """Four-tier autonomy ladder for agent self-evolution."""
    LEVEL_0_OBSERVE = "level_0_observe"          # Observation only, no auto edits
    LEVEL_1_HUMAN_GATE = "level_1_human_gate"    # Human approval required before canary
    LEVEL_2_BOUNDED_AUTO = "level_2_bounded_auto"# Autonomous within golden limits (<=300 lines)
    LEVEL_3_FULL_EVOLVE = "level_3_full_evolve"  # Continuous self-evolution with instant rollback


@dataclass
class SecondOrderMetrics:
    """Second-order behavioral metrics to prevent agent goal drift."""
    output_length_ratio: float = 1.0   # Current length / baseline length (alert > 1.5)
    refusal_rate: float = 0.0          # Task rejection/hesitation rate (alert > 0.05)
    retry_rate: float = 0.0            # Turn retry or restart loop rate (alert > 0.10)
    drift_detected: bool = False       # True if any threshold is violated

    def evaluate_drift(self) -> bool:
        """Check if second-order behavior has drifted into hazardous zone."""
        self.drift_detected = (
            self.output_length_ratio > 1.5
            or self.refusal_rate > 0.05
            or self.retry_rate > 0.10
        )
        return self.drift_detected


@dataclass
class EvolutionChangePackage:
    """Encapsulates a candidate modification entering the 7-stage pipeline."""
    package_id: str
    target_skill: str
    diff_patch: str
    line_count: int
    skill_dir: Optional[str] = None
    package_files: Dict[str, str] = field(default_factory=dict)
    diagnosis: str = ""
    regression_commands: List[Any] = field(default_factory=list)
    enforce_regression: bool = False
    rejected_history_refs: List[Dict[str, Any]] = field(default_factory=list)
    patch_fingerprint: str = ""
    eval_evidence: Dict[str, Any] = field(default_factory=dict)
    decision: str = ""
    rationale: str = ""
    review_manifest: Dict[str, Any] = field(default_factory=dict)
    decision_recorded: bool = False
    current_stage: PipelineStage = PipelineStage.SIGNAL_AGGREGATION
    stage_history: List[Dict[str, Any]] = field(default_factory=list)
    canary_traffic_pct: int = 0
    passed_safety_gate: bool = False
    rolled_back: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def transition_to(self, stage: PipelineStage, details: str = "") -> None:
        self.current_stage = stage
        self.updated_at = time.time()
        self.stage_history.append({
            "stage": stage.value,
            "timestamp": self.updated_at,
            "details": details,
        })


class EvolutionCICDPipeline:
    """Orchestrator for the 7-stage evolution pipeline and safety barriers."""

    _instance: Optional[EvolutionCICDPipeline] = None

    def __init__(self, store: Optional[RSITrajectoryStore] = None) -> None:
        self.autonomous_level = AutonomousLevel.LEVEL_2_BOUNDED_AUTO
        self.packages: Dict[str, EvolutionChangePackage] = {}
        self.metrics = SecondOrderMetrics()
        self.emergency_kill_switch_tripped = False
        self.auto_downgrade_count = 0
        self._store = store

    def _get_store(self) -> RSITrajectoryStore:
        return self._store or RSITrajectoryStore.get_instance()

    def set_store(self, store: Optional[RSITrajectoryStore]) -> None:
        """Bind an explicit RSITrajectoryStore instance (used for isolated testing/eval)."""
        self._store = store

    def prepare_optimizer_context(
        self,
        target_skill: str,
        raw_failure_signal: str = "",
    ) -> OptimizerFailureContext:
        """Provide sanitized failure context + historical rejections to optimizer (no test access)."""
        rejected = self._get_store().get_rejected_decisions(target_skill)
        return build_optimizer_context(target_skill, raw_failure_signal, rejected)

    def list_decisions(
        self,
        *,
        skill_name: Optional[str] = None,
        decision: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query persisted skill evolution decision history."""
        return self._get_store().list_skill_decisions(
            skill_name=skill_name,
            decision=decision,
            limit=limit,
        )

    def _record_decision_once(self, pkg: EvolutionChangePackage) -> None:
        if pkg.decision_recorded or pkg.decision not in ("accepted", "rejected"):
            return
        candidate_payload = {
            "diff_patch": pkg.diff_patch,
            "package_files": pkg.package_files,
            "review_manifest": pkg.review_manifest,
        }
        self._get_store().record_skill_decision(
            package_id=pkg.package_id,
            skill_name=pkg.target_skill,
            diagnosis=pkg.diagnosis,
            candidate_patches=candidate_payload,
            eval_evidence=pkg.eval_evidence,
            patch_fingerprint=pkg.patch_fingerprint,
            decision=pkg.decision,
            rationale=pkg.rationale,
        )
        pkg.decision_recorded = True

    @classmethod
    def get_instance(cls) -> EvolutionCICDPipeline:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_autonomous_level(self, level: AutonomousLevel) -> None:
        """Update autonomy ladder respecting human inviolable authority."""
        self.autonomous_level = level

    def trigger_emergency_rollback(self, package_id: Optional[str] = None) -> Dict[str, Any]:
        """Trip kill-switch, abort canary rollouts, and downgrade autonomy."""
        self.emergency_kill_switch_tripped = True
        rolled_back_ids: List[str] = []

        targets = [self.packages[package_id]] if package_id and package_id in self.packages else list(self.packages.values())
        for pkg in targets:
            if pkg.current_stage in (PipelineStage.CANARY_ROLLOUT, PipelineStage.MONITORING_ROLLBACK):
                pkg.rolled_back = True
                pkg.canary_traffic_pct = 0
                pkg.transition_to(PipelineStage.MONITORING_ROLLBACK, "Emergency rollback executed.")
                rolled_back_ids.append(pkg.package_id)

        # Auto-downgrade to Level 0 (Observation Only) on emergency
        self.autonomous_level = AutonomousLevel.LEVEL_0_OBSERVE
        self.auto_downgrade_count += 1
        return {
            "status": "emergency_rollback_success",
            "rolled_back_packages": rolled_back_ids,
            "new_level": self.autonomous_level.value,
        }

    def create_package(
        self,
        target_skill: str,
        diff_patch: str = "",
        *,
        skill_dir: Optional[str | Path] = None,
        package_files: Optional[Dict[str, str]] = None,
        diagnosis: str = "",
        raw_failure_signal: str = "",
        regression_commands: Optional[List[Any]] = None,
        enforce_regression: bool = False,
    ) -> EvolutionChangePackage:
        """Instantiate a new evolution change package with SkillHone rejection history context."""
        pkg_id = f"pkg_{uuid.uuid4().hex[:8]}"
        files_map = dict(package_files or {})
        raw_lines = [line for line in (diff_patch or "").splitlines() if line.strip()]
        if not raw_lines and files_map:
            raw_lines = [
                line
                for content in files_map.values()
                for line in str(content).splitlines()
                if line.strip()
            ]
        line_count = len(raw_lines)
        source_dir = Path(skill_dir) if skill_dir else None
        opt_ctx = self.prepare_optimizer_context(
            target_skill,
            raw_failure_signal or diagnosis,
        )
        fingerprint = compute_bundle_fingerprint(diff_patch, files_map)
        sanitized_diag = sanitize_failure_text(diagnosis or opt_ctx.sanitized_signal)
        review_manifest = build_reviewable_change_summary(
            skill_dir=source_dir,
            package_files=files_map,
            diff_patch=diff_patch,
        )
        pkg = EvolutionChangePackage(
            package_id=pkg_id,
            target_skill=target_skill,
            diff_patch=diff_patch,
            line_count=line_count,
            skill_dir=str(source_dir) if source_dir else None,
            package_files=files_map,
            diagnosis=sanitized_diag,
            regression_commands=list(regression_commands or []),
            enforce_regression=enforce_regression,
            rejected_history_refs=list(opt_ctx.avoided_rationales),
            patch_fingerprint=fingerprint,
            review_manifest=review_manifest,
        )
        pkg.transition_to(
            PipelineStage.SIGNAL_AGGREGATION,
            f"Signal received (prior_rejected={len(opt_ctx.avoided_fingerprints)}).",
        )
        self.packages[pkg_id] = pkg
        return pkg

    def advance_package(self, package_id: str) -> Tuple[bool, str]:
        """Advance package through the 7 stages with hard gatekeeper checks."""
        pkg = self.packages.get(package_id)
        if not pkg:
            return False, f"Package {package_id} not found."

        if self.emergency_kill_switch_tripped:
            return False, "Pipeline blocked: emergency kill-switch is currently active."

        if pkg.rolled_back:
            return False, "Cannot advance package: package has been rolled back."

        curr = pkg.current_stage

        # Stage 1 -> Stage 2
        if curr == PipelineStage.SIGNAL_AGGREGATION:
            pkg.transition_to(PipelineStage.CANDIDATE_GENERATION, "Generated concrete patch proposal.")
            return True, "Advanced to CANDIDATE_GENERATION."

        # Stage 2 -> Stage 3
        elif curr == PipelineStage.CANDIDATE_GENERATION:
            pkg.transition_to(PipelineStage.ISOLATED_EVALUATION, "Sandbox harness spun up.")
            return True, "Advanced to ISOLATED_EVALUATION."

        # Stage 3 -> Stage 4 (Isolated SkillHone Bundle + Regression Verification)
        elif curr == PipelineStage.ISOLATED_EVALUATION:
            uses_bundle_eval = bool(
                pkg.skill_dir or pkg.package_files or pkg.regression_commands or pkg.enforce_regression
            )
            if uses_bundle_eval:
                prior_rejected = self._get_store().get_rejected_decisions(pkg.target_skill)
                rejected_fps = {item.get("patch_fingerprint") for item in prior_rejected}
                if pkg.patch_fingerprint in rejected_fps:
                    pkg.decision = "rejected"
                    pkg.rationale = (
                        f"Candidate matches previously rejected patch fingerprint ({pkg.patch_fingerprint})."
                    )
                    pkg.eval_evidence = {"passed": False, "repeat_rejected": True}
                    self._record_decision_once(pkg)
                    return False, f"Isolated Evaluation rejected: {pkg.rationale}"

                evidence = IsolatedSkillEvaluator.evaluate(
                    skill_dir=pkg.skill_dir,
                    package_files=pkg.package_files,
                    regression_commands=pkg.regression_commands,
                )
                pkg.eval_evidence = evidence
                if not evidence["passed"]:
                    pkg.decision = "rejected"
                    pkg.rationale = str(evidence.get("rationale") or "Isolated regression failed.")
                    self._record_decision_once(pkg)
                    return False, f"Isolated Evaluation rejected: {pkg.rationale}"

            pkg.transition_to(PipelineStage.SAFETY_GATE, "Evaluating AST and safety rules.")
            return True, "Advanced to SAFETY_GATE."

        # Stage 4 -> Stage 5 (Hard Safety Barrier)
        elif curr == PipelineStage.SAFETY_GATE:
            # Rule 1: Single patch line count <= 300
            if pkg.line_count > 300:
                pkg.decision = "rejected"
                pkg.rationale = f"Safety Gate rejected: patch size ({pkg.line_count} lines) exceeds 300-line sweet spot."
                self._record_decision_once(pkg)
                return False, pkg.rationale
            # Rule 2: Level 1 requires explicit manual approval
            if self.autonomous_level == AutonomousLevel.LEVEL_1_HUMAN_GATE:
                if not pkg.passed_safety_gate:
                    pkg.passed_safety_gate = True
                    return False, "Safety Gate: awaiting explicit human approval under Level 1."
            elif self.autonomous_level == AutonomousLevel.LEVEL_0_OBSERVE:
                return False, "Safety Gate: autonomous modifications disallowed under Level 0."

            pkg.passed_safety_gate = True
            pkg.canary_traffic_pct = 10
            pkg.transition_to(PipelineStage.CANARY_ROLLOUT, "Canary traffic allocated at 10%.")
            return True, "Advanced to CANARY_ROLLOUT (10% canary traffic)."

        # Stage 5 -> Stage 6
        elif curr == PipelineStage.CANARY_ROLLOUT:
            pkg.canary_traffic_pct = 50
            pkg.transition_to(PipelineStage.MONITORING_ROLLBACK, "Canary increased to 50%; tracking 2nd-order metrics.")
            return True, "Advanced to MONITORING_ROLLBACK (50% canary)."

        # Stage 6 -> Stage 7 (Monitoring -> Final Crystallization)
        elif curr == PipelineStage.MONITORING_ROLLBACK:
            if self.metrics.evaluate_drift():
                pkg.rolled_back = True
                pkg.canary_traffic_pct = 0
                pkg.decision = "rejected"
                pkg.rationale = "Auto-rollback triggered: 2nd-order metric drift detected."
                pkg.transition_to(PipelineStage.MONITORING_ROLLBACK, "Drift alert: auto-rollback triggered!")
                self._record_decision_once(pkg)
                self._handle_auto_downgrade()
                return False, "Auto-rollback triggered: 2nd-order metric drift detected."

            pkg.canary_traffic_pct = 100
            pkg.decision = "accepted"
            pkg.rationale = str(
                pkg.eval_evidence.get("rationale")
                or "Passed isolated evaluation, safety gate, and canary monitoring."
            )
            pkg.transition_to(PipelineStage.EXPERIENCE_CRYSTALLIZATION, "100% promoted. Crystallized into memory.")
            self._record_decision_once(pkg)
            return True, "Advanced to EXPERIENCE_CRYSTALLIZATION (100% rollout complete)."

        elif curr == PipelineStage.EXPERIENCE_CRYSTALLIZATION:
            return True, "Package is already fully crystallized."

        return False, f"Unhandled stage {curr}."

    def _handle_auto_downgrade(self) -> None:
        """Step-down autonomy ladder when systemic drift or failure occurs."""
        self.auto_downgrade_count += 1
        if self.autonomous_level == AutonomousLevel.LEVEL_3_FULL_EVOLVE:
            self.autonomous_level = AutonomousLevel.LEVEL_2_BOUNDED_AUTO
        elif self.autonomous_level == AutonomousLevel.LEVEL_2_BOUNDED_AUTO:
            self.autonomous_level = AutonomousLevel.LEVEL_1_HUMAN_GATE
        elif self.autonomous_level == AutonomousLevel.LEVEL_1_HUMAN_GATE:
            self.autonomous_level = AutonomousLevel.LEVEL_0_OBSERVE
