# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Harness 12-State Deterministic Finite State Machine (FSM).
(Card-Harness-SpecDrivenFSM - v1.5.07)

Derived from Alibaba Qwen Data Warehouse Harness & Qwen Skill-SP:
Guarantees Agent = Model + Harness, engineering bottom-line enforcement.
Eliminates unconstrained conversational drift. Replaces ad-hoc chat loops with a
strictly governed, auditable 12-state transition graph with zero-loss checkpointing.
"""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Dict, List, Optional, Set, Tuple


class HarnessState(str, Enum):
    """The 12 Canonical States of Enterprise Agent Execution."""
    IDLE = "IDLE"                      # Ready, waiting for task specification
    SPEC_INGEST = "SPEC_INGEST"        # Parsing and freezing task spec P
    DECOMPOSE = "DECOMPOSE"            # Breaking into tracer-bullet tickets & DAG
    DISPATCH = "DISPATCH"              # Assigning ticket to specialist sandbox
    RUNNING = "RUNNING"                # Specialist code generation/execution
    VERIFY = "VERIFY"                  # Multi-metric physical gate validation
    EVALUATE = "EVALUATE"              # Independent evaluator dual-axis review
    CHECKPOINT = "CHECKPOINT"          # Persisting structured state checkpoint CP
    RECOVERING = "RECOVERING"          # Tri-fault taxonomy recovery & self-healing
    COMPLETED = "COMPLETED"            # All tickets verified and delivered
    ABORTED = "ABORTED"                # Early brake or budget exhaustion
    FAILED = "FAILED"                  # Terminal unrecoverable error


class InvalidTransitionError(RuntimeError):
    """Raised when an illegal FSM state jump is attempted."""
    pass


@dataclass(frozen=True)
class StateTransitionRecord:
    """Immutable audit entry for state transitions."""
    from_state: HarnessState
    to_state: HarnessState
    reason: str
    timestamp: float = field(default_factory=time.time)
    payload_hash: Optional[str] = None


class HarnessFSM:
    """
    Deterministic 12-State Finite State Machine governing multi-agent lifecycle.
    Validates state transitions against an immutable directed graph.
    """

    # Permitted transitions: Current State -> Set of Allowed Next States
    TRANSITION_GRAPH: Dict[HarnessState, Set[HarnessState]] = {
        HarnessState.IDLE: {HarnessState.SPEC_INGEST, HarnessState.ABORTED},
        HarnessState.SPEC_INGEST: {HarnessState.DECOMPOSE, HarnessState.FAILED, HarnessState.ABORTED},
        HarnessState.DECOMPOSE: {HarnessState.DISPATCH, HarnessState.FAILED, HarnessState.ABORTED},
        HarnessState.DISPATCH: {HarnessState.RUNNING, HarnessState.RECOVERING, HarnessState.FAILED, HarnessState.ABORTED},
        HarnessState.RUNNING: {HarnessState.VERIFY, HarnessState.RECOVERING, HarnessState.FAILED, HarnessState.ABORTED},
        HarnessState.VERIFY: {HarnessState.EVALUATE, HarnessState.RECOVERING, HarnessState.FAILED, HarnessState.ABORTED},
        HarnessState.EVALUATE: {HarnessState.CHECKPOINT, HarnessState.DECOMPOSE, HarnessState.DISPATCH, HarnessState.FAILED, HarnessState.ABORTED},
        HarnessState.CHECKPOINT: {HarnessState.DISPATCH, HarnessState.COMPLETED, HarnessState.FAILED, HarnessState.ABORTED},
        HarnessState.RECOVERING: {HarnessState.DISPATCH, HarnessState.RUNNING, HarnessState.FAILED, HarnessState.ABORTED},
        HarnessState.COMPLETED: set(),  # Terminal state
        HarnessState.ABORTED: set(),    # Terminal state
        HarnessState.FAILED: set(),     # Terminal state
    }

    def __init__(self, initial_state: HarnessState = HarnessState.IDLE) -> None:
        self._current_state: HarnessState = initial_state
        self._history: List[StateTransitionRecord] = []
        self._retry_count: int = 0
        self._max_retries: int = 3

    @property
    def current_state(self) -> HarnessState:
        return self._current_state

    @property
    def is_terminal(self) -> bool:
        return self._current_state in (HarnessState.COMPLETED, HarnessState.ABORTED, HarnessState.FAILED)

    @property
    def history(self) -> List[StateTransitionRecord]:
        return list(self._history)

    @property
    def retry_count(self) -> int:
        return self._retry_count

    def can_transition(self, target_state: HarnessState) -> bool:
        """Checks if a transition to target_state is permitted."""
        allowed = self.TRANSITION_GRAPH.get(self._current_state, set())
        return target_state in allowed

    def transition_to(
        self,
        target_state: HarnessState,
        reason: str = "",
        payload_hash: Optional[str] = None,
    ) -> StateTransitionRecord:
        """
        Executes an audited state transition.
        Raises InvalidTransitionError if the jump violates the transition graph.
        """
        if not self.can_transition(target_state):
            raise InvalidTransitionError(
                f"Illegal state transition from {self._current_state.value} to {target_state.value}. "
                f"Permitted destinations: {[s.value for s in self.TRANSITION_GRAPH.get(self._current_state, set())]}"
            )

        if target_state == HarnessState.RECOVERING:
            self._retry_count += 1
            if self._retry_count > self._max_retries:
                # Exceeded maximum recovery retries -> terminal FAILED
                record = StateTransitionRecord(
                    from_state=self._current_state,
                    to_state=HarnessState.FAILED,
                    reason=f"Recovery retry budget exceeded ({self._retry_count} > {self._max_retries}).",
                    payload_hash=payload_hash,
                )
                self._current_state = HarnessState.FAILED
                self._history.append(record)
                return record

        record = StateTransitionRecord(
            from_state=self._current_state,
            to_state=target_state,
            reason=reason or f"Normal flow to {target_state.value}",
            payload_hash=payload_hash,
        )
        self._current_state = target_state
        self._history.append(record)
        return record

    def abort(self, reason: str = "Braked by orchestrator") -> StateTransitionRecord:
        """Emergency active brake transition to ABORTED."""
        record = StateTransitionRecord(
            from_state=self._current_state,
            to_state=HarnessState.ABORTED,
            reason=reason,
        )
        self._current_state = HarnessState.ABORTED
        self._history.append(record)
        return record

    def reset_to_idle(self) -> None:
        """Resets the state machine for a new execution cycle."""
        self._current_state = HarnessState.IDLE
        self._history.clear()
        self._retry_count = 0
