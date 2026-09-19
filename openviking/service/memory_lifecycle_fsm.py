# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Memory Lifecycle Finite State Machine & Automated Conflict Linking Service.
(Card-Memory-LifecycleFSM / v1.5.32)

First Principles:
1. "Memories are living beliefs with lifecycles, not static immutable deadweights."
2. Three-state canonical machine:
   - active: Current authoritative, accepted belief/axiom/rule.
   - disputed: Under conflict or contested by opposing observations, pending consensus.
   - superseded: Overruled and replaced by a newer revision or verified discovery.
3. Strict Lineage Pointers:
   - A superseded memory MUST link forward via `superseded_by: <uri>`.
   - A superseding memory MAY link backward via `supersedes_uri: <uri>`.
4. Asymmetric Demotion:
   - `superseded` memories are penalized by 0.20x in search (sink to bottom, never eclipse active truths).
   - `disputed` memories are penalized by 0.50x and highlighted for human/agent review.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryStatus(str, Enum):
    """Canonical lifecycle states for memory items."""
    ACTIVE = "active"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"


class LifecycleTransitionEvent(str, Enum):
    """Valid events that trigger lifecycle state transitions."""
    CREATE = "create"
    DISPUTE = "dispute"
    RESOLVE = "resolve"
    SUPERSEDE = "supersede"
    REVERT = "revert"


class InvalidLifecycleTransitionError(ValueError):
    """Raised when an invalid state machine transition is attempted."""
    pass


class MemoryLifecycleRecord(BaseModel):
    """Typed DTO representing the lifecycle state and lineage of a memory unit."""
    uri: str
    status: MemoryStatus = MemoryStatus.ACTIVE
    superseded_by: Optional[str] = None
    supersedes_uri: Optional[str] = None
    disputed_reason: Optional[str] = None
    updated_at: float = Field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "status": self.status.value,
            "superseded_by": self.superseded_by,
            "supersedes_uri": self.supersedes_uri,
            "disputed_reason": self.disputed_reason,
            "updated_at": self.updated_at,
        }


class MemoryLifecycleFSM:
    """Deterministic finite state machine governing memory status transitions."""

    # Allowed transitions: (current_status, event) -> target_status
    _TRANSITIONS = {
        (None, LifecycleTransitionEvent.CREATE): MemoryStatus.ACTIVE,
        (MemoryStatus.ACTIVE, LifecycleTransitionEvent.DISPUTE): MemoryStatus.DISPUTED,
        (MemoryStatus.ACTIVE, LifecycleTransitionEvent.SUPERSEDE): MemoryStatus.SUPERSEDED,
        (MemoryStatus.DISPUTED, LifecycleTransitionEvent.RESOLVE): MemoryStatus.ACTIVE,
        (MemoryStatus.DISPUTED, LifecycleTransitionEvent.SUPERSEDE): MemoryStatus.SUPERSEDED,
        (MemoryStatus.SUPERSEDED, LifecycleTransitionEvent.REVERT): MemoryStatus.ACTIVE,
    }

    @classmethod
    def can_transition(
        cls,
        current_status: Optional[MemoryStatus],
        event: LifecycleTransitionEvent,
    ) -> bool:
        """Check if a transition is legal without raising exceptions."""
        return (current_status, event) in cls._TRANSITIONS

    @classmethod
    def transition(
        cls,
        record: MemoryLifecycleRecord,
        event: LifecycleTransitionEvent,
        *,
        target_uri: Optional[str] = None,
        reason: Optional[str] = None,
        now_ts: Optional[float] = None,
    ) -> MemoryLifecycleRecord:
        """
        Execute a deterministic state transition on the memory record.
        Raises InvalidLifecycleTransitionError if the jump is forbidden.
        """
        key = (record.status, event)
        if key not in cls._TRANSITIONS:
            raise InvalidLifecycleTransitionError(
                f"Illegal memory lifecycle transition: Cannot perform '{event.value}' "
                f"from status '{record.status.value}' for URI '{record.uri}'."
            )

        new_status = cls._TRANSITIONS[key]
        current_time = now_ts or time.time()

        # Handle event side-effects
        superseded_by = record.superseded_by
        disputed_reason = record.disputed_reason

        if event == LifecycleTransitionEvent.SUPERSEDE:
            if not target_uri:
                raise InvalidLifecycleTransitionError(
                    "Transition 'supersede' requires a non-empty target_uri pointing to successor memory."
                )
            superseded_by = target_uri
            disputed_reason = reason or "Superseded by verified newer revision."

        elif event == LifecycleTransitionEvent.DISPUTE:
            disputed_reason = reason or "Marked disputed due to conflicting evidence."

        elif event in (LifecycleTransitionEvent.RESOLVE, LifecycleTransitionEvent.REVERT):
            superseded_by = None
            disputed_reason = None

        return MemoryLifecycleRecord(
            uri=record.uri,
            status=new_status,
            superseded_by=superseded_by,
            supersedes_uri=record.supersedes_uri,
            disputed_reason=disputed_reason,
            updated_at=current_time,
        )

    @classmethod
    def link_superseded_pair(
        cls,
        old_record: MemoryLifecycleRecord,
        new_uri: str,
        reason: str = "Superseded by newer knowledge",
        now_ts: Optional[float] = None,
    ) -> tuple[MemoryLifecycleRecord, MemoryLifecycleRecord]:
        """
        Atomically link an old superseded memory to a new active successor.
        Returns (updated_old_record, new_successor_record).
        """
        updated_old = cls.transition(
            record=old_record,
            event=LifecycleTransitionEvent.SUPERSEDE,
            target_uri=new_uri,
            reason=reason,
            now_ts=now_ts,
        )

        new_successor = MemoryLifecycleRecord(
            uri=new_uri,
            status=MemoryStatus.ACTIVE,
            supersedes_uri=old_record.uri,
            updated_at=now_ts or time.time(),
        )

        return updated_old, new_successor

    @classmethod
    def build_lineage_chain(
        cls,
        target_uri: str,
        records: Dict[str, MemoryLifecycleRecord],
    ) -> Dict[str, Any]:
        """
        Traverse predecessor and successor lineage pointers for target_uri.
        Returns a structured genealogy dictionary.
        """
        current = records.get(target_uri)
        predecessors: List[Dict[str, Any]] = []
        successors: List[Dict[str, Any]] = []

        # Trace backward (who did this memory supersede?)
        cursor = current
        visited_back = {target_uri}
        while cursor and cursor.supersedes_uri and cursor.supersedes_uri not in visited_back:
            pred_uri = cursor.supersedes_uri
            visited_back.add(pred_uri)
            pred_rec = records.get(pred_uri)
            if pred_rec:
                predecessors.append(pred_rec.to_dict())
                cursor = pred_rec
            else:
                predecessors.append({"uri": pred_uri, "status": "unknown"})
                break

        # Trace forward (who superseded this memory?)
        cursor = current
        visited_fwd = {target_uri}
        while cursor and cursor.superseded_by and cursor.superseded_by not in visited_fwd:
            succ_uri = cursor.superseded_by
            visited_fwd.add(succ_uri)
            succ_rec = records.get(succ_uri)
            if succ_rec:
                successors.append(succ_rec.to_dict())
                cursor = succ_rec
            else:
                successors.append({"uri": succ_uri, "status": "unknown"})
                break

        return {
            "uri": target_uri,
            "status": current.status.value if current else "unknown",
            "record": current.to_dict() if current else None,
            "predecessors": predecessors,
            "successors": successors,
            "is_active_head": bool(current and current.status == MemoryStatus.ACTIVE and not current.superseded_by),
        }
