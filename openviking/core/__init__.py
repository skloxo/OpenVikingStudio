# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Core context abstractions for OpenViking."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openviking.core.building_tree import BuildingTree
    from openviking.core.context import Context, ContextType, ResourceContentType
    from openviking.core.directories import (
        PRESET_DIRECTORIES,
        DirectoryDefinition,
        DirectoryInitializer,
    )
    from openviking.core.skill_loader import SkillLoader

_EXPORTS = {
    "BuildingTree": ("openviking.core.building_tree", "BuildingTree"),
    "Context": ("openviking.core.context", "Context"),
    "ContextType": ("openviking.core.context", "ContextType"),
    "ResourceContentType": ("openviking.core.context", "ResourceContentType"),
    "SkillLoader": ("openviking.core.skill_loader", "SkillLoader"),
    "DirectoryDefinition": ("openviking.core.directories", "DirectoryDefinition"),
    "PRESET_DIRECTORIES": ("openviking.core.directories", "PRESET_DIRECTORIES"),
    "DirectoryInitializer": ("openviking.core.directories", "DirectoryInitializer"),
    "TreeEntry": ("openviking.core.pi_dual_loop", "TreeEntry"),
    "TreeHashSnapshot": ("openviking.core.pi_dual_loop", "TreeHashSnapshot"),
    "TreeDelta": ("openviking.core.pi_dual_loop", "TreeDelta"),
    "PiDualLoopSensor": ("openviking.core.pi_dual_loop", "PiDualLoopSensor"),
    "compute_tree_hash": ("openviking.core.pi_dual_loop", "compute_tree_hash"),
    "detect_delta": ("openviking.core.pi_dual_loop", "detect_delta"),
    # Two-Tier Agent Loop & Four-Layer Onion Guard (v1.5.01)
    "TwoTierAgentLoop": ("openviking.core.agent_loop", "TwoTierAgentLoop"),
    "OnionGuardConfig": ("openviking.core.agent_loop", "OnionGuardConfig"),
    "AgentMessage": ("openviking.core.agent_loop", "AgentMessage"),
    "ToolCallResult": ("openviking.core.agent_loop", "ToolCallResult"),
    "TurnResult": ("openviking.core.agent_loop", "TurnResult"),
    "AgentLoopStatus": ("openviking.core.agent_loop", "AgentLoopStatus"),
    "AgentLoopTelemetrySnapshot": ("openviking.core.agent_loop_telemetry", "AgentLoopTelemetrySnapshot"),
    "AgentLoopTelemetryCollector": ("openviking.core.agent_loop_telemetry", "AgentLoopTelemetryCollector"),
    "get_agent_loop_telemetry_collector": ("openviking.core.agent_loop_telemetry", "get_agent_loop_telemetry_collector"),
    # Harness Four Invariants & Telemetry (v1.5.03)
    "ExecutionBudget": ("openviking.core.harness_invariants", "ExecutionBudget"),
    "BudgetSnapshot": ("openviking.core.harness_invariants", "BudgetSnapshot"),
    "BudgetEnforcer": ("openviking.core.harness_invariants", "BudgetEnforcer"),
    "BudgetExceededError": ("openviking.core.harness_invariants", "BudgetExceededError"),
    "Checkpoint": ("openviking.core.harness_invariants", "Checkpoint"),
    "CheckpointRegistry": ("openviking.core.harness_invariants", "CheckpointRegistry"),
    "TraceEvent": ("openviking.core.harness_invariants", "TraceEvent"),
    "HarnessTrace": ("openviking.core.harness_invariants", "HarnessTrace"),
    "InvariantTelemetry": ("openviking.core.harness_invariants", "InvariantTelemetry"),
    # Spec-Driven Workspace & Compression Whitelist (v1.5.03)
    "WorkspaceMode": ("openviking.core.spec_driven_fs", "WorkspaceMode"),
    "AbstractWorkspace": ("openviking.core.spec_driven_fs", "AbstractWorkspace"),
    "SpecWorkspace": ("openviking.core.spec_driven_fs", "SpecWorkspace"),
    "WhitelistType": ("openviking.core.spec_driven_fs", "WhitelistType"),
    "ProtectedPayload": ("openviking.core.spec_driven_fs", "ProtectedPayload"),
    "CompressionWhitelist": ("openviking.core.spec_driven_fs", "CompressionWhitelist"),
    # Failure Classifier & Multi-Tenant Runtime Context (v1.5.03)
    "FailureCategory": ("openviking.core.failure_classifier", "FailureCategory"),
    "FailureFingerprint": ("openviking.core.failure_classifier", "FailureFingerprint"),
    "ClassificationDecision": ("openviking.core.failure_classifier", "ClassificationDecision"),
    "FailureClassifier": ("openviking.core.failure_classifier", "FailureClassifier"),
    "MultiTenantRuntimeContext": ("openviking.core.failure_classifier", "MultiTenantRuntimeContext"),
    # Hook Aspects & Dual-Sided Offload (v1.5.05)
    "HookAspect": ("openviking.core.hook_aspects", "HookAspect"),
    "AspectDecision": ("openviking.core.hook_aspects", "AspectDecision"),
    "AspectDecisionType": ("openviking.core.hook_aspects", "AspectDecisionType"),
    "AspectContext": ("openviking.core.hook_aspects", "AspectContext"),
    "HookAspectRegistry": ("openviking.core.hook_aspects", "HookAspectRegistry"),
    "AntiLazyCodeGuard": ("openviking.core.read_write_offload", "AntiLazyCodeGuard"),
    "LazyCodeOmissionError": ("openviking.core.read_write_offload", "LazyCodeOmissionError"),
    "ReadOffloadManager": ("openviking.core.read_write_offload", "ReadOffloadManager"),
    "FileRefHandle": ("openviking.core.read_write_offload", "FileRefHandle"),
    "HITLGate": ("openviking.core.hitl_gate", "HITLGate"),
    "DangerousActionPolicy": ("openviking.core.hitl_gate", "DangerousActionPolicy"),
    "HITLPermissionError": ("openviking.core.hitl_gate", "HITLPermissionError"),
    # Multi-Metric Delivery Gate & Anti-False-Exit-0 Guard (v1.5.06)
    "PhysicalDiffVerifier": ("openviking.core.physical_diff_verifier", "PhysicalDiffVerifier"),
    "DiffVerificationResult": ("openviking.core.physical_diff_verifier", "DiffVerificationResult"),
    "TestRetinaRunner": ("openviking.core.test_retina_runner", "TestRetinaRunner"),
    "TestRetinaResult": ("openviking.core.test_retina_runner", "TestRetinaResult"),
    "MultiMetricGate": ("openviking.core.multi_metric_gate", "MultiMetricGate"),
    "GateVerificationReport": ("openviking.core.multi_metric_gate", "GateVerificationReport"),
    # Spec-Driven FSM & Multi-Agent Orchestrator (v1.5.07)
    "HarnessState": ("openviking.core.harness_fsm", "HarnessState"),
    "HarnessFSM": ("openviking.core.harness_fsm", "HarnessFSM"),
    "InvalidTransitionError": ("openviking.core.harness_fsm", "InvalidTransitionError"),
    "StateTransitionRecord": ("openviking.core.harness_fsm", "StateTransitionRecord"),
    "AgentRoleType": ("openviking.core.spec_orchestrator", "AgentRoleType"),
    "RoleViolationError": ("openviking.core.spec_orchestrator", "RoleViolationError"),
    "EvaluatorCollusionError": ("openviking.core.spec_orchestrator", "EvaluatorCollusionError"),
    "SpecFileArtifact": ("openviking.core.spec_orchestrator", "SpecFileArtifact"),
    "CheckpointManifest": ("openviking.core.spec_orchestrator", "CheckpointManifest"),
    "SpecDrivenOrchestrator": ("openviking.core.spec_orchestrator", "SpecDrivenOrchestrator"),
    # Memory Quarantine & Anti-Entropy Dashboard (v1.5.10)
    "QuarantineItem": ("openviking.core.quarantine_manager", "QuarantineItem"),
    "QuarantineBatch": ("openviking.core.quarantine_manager", "QuarantineBatch"),
    "QuarantineManifestSnapshot": ("openviking.core.quarantine_manager", "QuarantineManifestSnapshot"),
    "RestoreDryRunResult": ("openviking.core.quarantine_manager", "RestoreDryRunResult"),
    "QuarantineManager": ("openviking.core.quarantine_manager", "QuarantineManager"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(__all__))


__all__ = [
    # Context
    "Context",
    "ContextType",
    "ResourceContentType",
    # Tree
    "BuildingTree",
    # Skill
    "SkillLoader",
    # Directories
    "DirectoryDefinition",
    "PRESET_DIRECTORIES",
    "DirectoryInitializer",
    # Pi Dual Loop (Change Perception Sensor)
    "TreeEntry",
    "TreeHashSnapshot",
    "TreeDelta",
    "PiDualLoopSensor",
    "compute_tree_hash",
    "detect_delta",
    # Two-Tier Agent Loop & Four-Layer Onion Guard (v1.5.01)
    "TwoTierAgentLoop",
    "OnionGuardConfig",
    "AgentMessage",
    "ToolCallResult",
    "TurnResult",
    "AgentLoopStatus",
    # Harness Four Invariants & Telemetry (v1.5.03)
    "ExecutionBudget",
    "BudgetSnapshot",
    "BudgetEnforcer",
    "BudgetExceededError",
    "Checkpoint",
    "CheckpointRegistry",
    "TraceEvent",
    "HarnessTrace",
    "InvariantTelemetry",
    # Spec-Driven Workspace & Compression Whitelist (v1.5.03)
    "WorkspaceMode",
    "AbstractWorkspace",
    "SpecWorkspace",
    "WhitelistType",
    "ProtectedPayload",
    "CompressionWhitelist",
    # Failure Classifier & Multi-Tenant Runtime Context (v1.5.03)
    "FailureCategory",
    "FailureFingerprint",
    "ClassificationDecision",
    "FailureClassifier",
    "MultiTenantRuntimeContext",
    # Hook Aspects & Dual-Sided Offload (v1.5.05)
    "HookAspect",
    "AspectDecision",
    "AspectDecisionType",
    "AspectContext",
    "HookAspectRegistry",
    "AntiLazyCodeGuard",
    "LazyCodeOmissionError",
    "ReadOffloadManager",
    "FileRefHandle",
    "HITLGate",
    "DangerousActionPolicy",
    "HITLPermissionError",
    # Multi-Metric Delivery Gate & Anti-False-Exit-0 Guard (v1.5.06)
    "PhysicalDiffVerifier",
    "DiffVerificationResult",
    "TestRetinaRunner",
    "TestRetinaResult",
    "MultiMetricGate",
    "GateVerificationReport",
    # Spec-Driven FSM & Multi-Agent Orchestrator (v1.5.07)
    "HarnessState",
    "HarnessFSM",
    "InvalidTransitionError",
    "StateTransitionRecord",
    "AgentRoleType",
    "RoleViolationError",
    "EvaluatorCollusionError",
    "SpecFileArtifact",
    "CheckpointManifest",
    "SpecDrivenOrchestrator",
    # Memory Quarantine & Anti-Entropy Dashboard (v1.5.10)
    "QuarantineItem",
    "QuarantineBatch",
    "QuarantineManifestSnapshot",
    "RestoreDryRunResult",
    "QuarantineManager",
]

