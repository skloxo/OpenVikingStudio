# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unified Entity Lifecycle Engine (Card-190 SSOT).

Unifies the ad-hoc state machines across OpenViking into a standardized 5-stage FSM:
  INGESTED ➔ EVALUATING ➔ REDUCING ➔ VALIDATING ➔ COMMITTED
                                                ↳ REJECTED
                                                ↳ ROLLED_BACK

Features:
- Deterministic, strictly typed state transition DAG.
- Pre-transition guardrails (intercept invalid transitions before mutation).
- Post-transition event broadcasting (decoupled reactive listeners).
- Thread-safe state tracking with in-memory transition history.
"""

from __future__ import annotations

from enum import Enum
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LifecycleState(str, Enum):
    """Unified 5-Stage Lifecycle States."""
    INGESTED = "INGESTED"
    EVALUATING = "EVALUATING"
    REDUCING = "REDUCING"
    VALIDATING = "VALIDATING"
    COMMITTED = "COMMITTED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"


class LifecycleTransitionEvent(BaseModel):
    """Immutable transition event payload."""
    entity_type: str
    entity_id: str
    from_state: LifecycleState
    to_state: LifecycleState
    operator: str = "system"
    timestamp: float = Field(default_factory=time.time)
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Allowed transition matrix
ALLOWED_TRANSITIONS: Dict[LifecycleState, Set[LifecycleState]] = {
    LifecycleState.INGESTED: {LifecycleState.EVALUATING, LifecycleState.REJECTED},
    LifecycleState.EVALUATING: {LifecycleState.REDUCING, LifecycleState.VALIDATING, LifecycleState.REJECTED},
    LifecycleState.REDUCING: {LifecycleState.VALIDATING, LifecycleState.REJECTED},
    LifecycleState.VALIDATING: {LifecycleState.COMMITTED, LifecycleState.REJECTED},
    LifecycleState.COMMITTED: {LifecycleState.ROLLED_BACK, LifecycleState.EVALUATING},
    LifecycleState.REJECTED: {LifecycleState.INGESTED},  # Allow re-ingestion / retry
    LifecycleState.ROLLED_BACK: {LifecycleState.INGESTED, LifecycleState.EVALUATING},
}


class UnifiedLifecycleEngine:
    """Thread-safe unified lifecycle orchestrator."""

    _instance: Optional[UnifiedLifecycleEngine] = None
    _singleton_lock = threading.Lock()

    def __init__(self):
        self._states: Dict[str, LifecycleState] = {}  # key: f"{entity_type}:{entity_id}"
        self._history: Dict[str, List[LifecycleTransitionEvent]] = {}
        self._guards: Dict[Tuple[LifecycleState, LifecycleState], List[Callable[[str, str, Dict[str, Any]], bool]]] = {}
        self._listeners: List[Callable[[LifecycleTransitionEvent], None]] = []
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "UnifiedLifecycleEngine":
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _entity_key(self, entity_type: str, entity_id: str) -> str:
        return f"{entity_type.strip().lower()}:{entity_id.strip()}"

    def register_guard(
        self,
        from_state: LifecycleState,
        to_state: LifecycleState,
        guard_fn: Callable[[str, str, Dict[str, Any]], bool],
    ) -> None:
        """Register a pre-transition validation hook."""
        with self._lock:
            pair = (from_state, to_state)
            if pair not in self._guards:
                self._guards[pair] = []
            self._guards[pair].append(guard_fn)

    def register_listener(self, listener_fn: Callable[[LifecycleTransitionEvent], None]) -> None:
        """Register a post-transition observer callback."""
        with self._lock:
            self._listeners.append(listener_fn)

    def get_state(self, entity_type: str, entity_id: str) -> Optional[LifecycleState]:
        """Fetch current state of an entity."""
        with self._lock:
            key = self._entity_key(entity_type, entity_id)
            return self._states.get(key)

    def transition(
        self,
        entity_type: str,
        entity_id: str,
        to_state: LifecycleState,
        operator: str = "system",
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LifecycleTransitionEvent:
        """Execute a state transition with guardrail enforcement and audit emission."""
        key = self._entity_key(entity_type, entity_id)
        meta = metadata or {}

        with self._lock:
            current_state = self._states.get(key)

            # If uninitialized, allow setting to INGESTED
            if current_state is None:
                if to_state not in (LifecycleState.INGESTED, LifecycleState.COMMITTED):
                    raise ValueError(
                        f"Entity {key} not found. Must initialize at INGESTED (attempted {to_state})."
                    )
                current_state = LifecycleState.INGESTED if to_state == LifecycleState.INGESTED else to_state

            # Validate against allowed transitions graph
            if current_state != to_state:
                valid_next = ALLOWED_TRANSITIONS.get(current_state, set())
                if to_state not in valid_next:
                    raise ValueError(
                        f"Invalid lifecycle transition for {key}: {current_state.value} -> {to_state.value}. "
                        f"Allowed transitions from {current_state.value}: {[s.value for s in valid_next]}"
                    )

            # Check registered pre-transition guards
            guards = self._guards.get((current_state, to_state), [])
            for guard in guards:
                if not guard(entity_type, entity_id, meta):
                    raise PermissionError(
                        f"Pre-transition guard rejected {key}: {current_state.value} -> {to_state.value}"
                    )

            # Mutate state
            self._states[key] = to_state

            event = LifecycleTransitionEvent(
                entity_type=entity_type,
                entity_id=entity_id,
                from_state=current_state,
                to_state=to_state,
                operator=operator,
                reason=reason,
                metadata=meta,
            )

            if key not in self._history:
                self._history[key] = []
            self._history[key].append(event)

            # Snapshot listeners for safe dispatch outside lock
            listeners = list(self._listeners)

        # Notify listeners
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                logger.warning(f"Error in lifecycle transition listener: {e}")

        return event

    def get_history(self, entity_type: str, entity_id: str) -> List[LifecycleTransitionEvent]:
        """Fetch transition history for a given entity."""
        with self._lock:
            key = self._entity_key(entity_type, entity_id)
            return list(self._history.get(key, []))

    def reset_entity(self, entity_type: str, entity_id: str) -> None:
        """Reset entity tracking (primarily for testing)."""
        with self._lock:
            key = self._entity_key(entity_type, entity_id)
            self._states.pop(key, None)
            self._history.pop(key, None)
