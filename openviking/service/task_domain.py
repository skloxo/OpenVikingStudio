# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Persistence-neutral Task lifecycle constants and patch contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, Optional

_SENSITIVE_PATTERNS = re.compile(
    r"(?:api[_-]?key|token|secret|password|authorization)\s*[=:]\s*\S+",
    re.IGNORECASE,
)
_MAX_ERROR_LEN = 1000


def sanitize_error(error: str) -> str:
    """Redact credential-like tokens and bound persisted error length."""
    sanitized = _SENSITIVE_PATTERNS.sub("[REDACTED]", str(error))
    if len(sanitized) > _MAX_ERROR_LEN:
        sanitized = sanitized[:_MAX_ERROR_LEN] + "...[truncated]"
    return sanitized


class TaskStatus(str, Enum):
    """Lifecycle states of an async task."""

    PENDING = "pending"
    RUNNING = "running"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_TASK_STATUSES = (
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
)
ACTIVE_TASK_STATUSES = (
    TaskStatus.PENDING,
    TaskStatus.RUNNING,
    TaskStatus.CANCELLING,
)
TERMINAL_WORK_STATES = (WorkState.DONE, WorkState.FAILED, WorkState.CANCELLED)

_TASK_PATCHABLE_FIELDS = frozenset({"result", "stage", "meta", "auth"})


@dataclass(frozen=True)
class TaskPatch:
    """Atomic, field-scoped Task mutation for incremental stage/meta updates."""

    result: Optional[Dict[str, Any]] = None
    stage: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    auth: Optional[Dict[str, Any]] = None
    clear_fields: frozenset[str] = field(default_factory=frozenset)
    add_enqueue_complete_work_ids: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        clear_fields = frozenset(str(name) for name in self.clear_fields)
        unknown = clear_fields - _TASK_PATCHABLE_FIELDS
        if unknown:
            raise ValueError(f"unsupported TaskPatch clear fields: {sorted(unknown)}")
        for field_name in clear_fields:
            if getattr(self, field_name) is not None:
                raise ValueError(f"TaskPatch cannot update and clear {field_name}")
        object.__setattr__(self, "clear_fields", clear_fields)
        object.__setattr__(
            self,
            "add_enqueue_complete_work_ids",
            frozenset(str(work_id) for work_id in self.add_enqueue_complete_work_ids if work_id),
        )

    def is_empty(self) -> bool:
        return (
            self.result is None
            and self.stage is None
            and self.meta is None
            and self.auth is None
            and not self.clear_fields
            and not self.add_enqueue_complete_work_ids
        )
