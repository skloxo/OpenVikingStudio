# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Queue types, status models, and abstract base classes for QueueFS.
Decoupled to respect single-file size limits and maintain high cohesion.
"""

import abc
import collections
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
from uuid import uuid4


@dataclass
class QueueError:
    """Error record for failed queue processing."""

    timestamp: datetime
    message: str
    data: Optional[Dict[str, Any]] = None
    retried: bool = False
    retry_count: int = 0


@dataclass
class DLQEntry:
    """Dead-Letter Queue entry for auditing and self-healing replay."""

    id: str
    queue: str
    timestamp: str
    error: str
    data: Optional[Dict[str, Any]] = None
    retryable: bool = False
    retried: bool = False
    retry_count: int = 0


@dataclass
class QueueStatus:
    """Queue status representation with active health indicators."""

    pending: int = 0
    in_progress: int = 0
    processed: int = 0
    requeue_count: int = 0
    error_count: int = 0
    errors: List[QueueError] = field(default_factory=list)
    recent_error_rate: float = 0.0
    is_healthy: bool = True
    has_active_errors: bool = False

    @property
    def has_errors(self) -> bool:
        """Active error status aligned with first principles.

        Returns True only if the queue suffers from an active or critical error condition.
        Completed queues with minor historical transient errors (e.g. 5 errors in 5192 tasks)
        do not latch into an error state.
        """
        return self.has_active_errors

    @property
    def is_complete(self) -> bool:
        """Check if queue has drained all pending and in-progress work."""
        return self.pending == 0 and self.in_progress == 0


def evaluate_queue_health(
    in_progress: int,
    processed: int,
    error_count: int,
    recent_outcomes: Sequence[bool],
    pending: int = 0,
) -> Tuple[bool, bool, float]:
    """Evaluate queue health from first principles.

    Returns:
        tuple[is_healthy: bool, has_active_errors: bool, recent_error_rate: float]
    """
    total_finished = processed + error_count
    is_active = (pending > 0 or in_progress > 0)

    if is_active:
        if len(recent_outcomes) >= 5:
            recent_failures = sum(1 for ok in recent_outcomes if not ok)
            recent_rate = recent_failures / len(recent_outcomes)
            active_errors = recent_rate > 0.20
        elif processed == 0 and error_count >= 3:
            active_errors = True
            recent_rate = 1.0
        else:
            active_errors = False
            recent_rate = 0.0
    else:
        recent_rate = 0.0
        if total_finished == 0:
            active_errors = False
        elif processed == 0 and error_count > 0:
            active_errors = True
        else:
            active_errors = (error_count / total_finished) > 0.10

    return not active_errors, active_errors, recent_rate


class DLQStore:
    """In-memory bounded dead-letter queue storage for a named queue."""

    def __init__(self, queue_name: str, max_items: int = 1000):
        self.queue_name = queue_name
        self.max_items = max_items
        self._entries: List[Dict[str, Any]] = []

    def record(self, error_msg: str, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        entry = {
            "id": f"dlq_{uuid4().hex[:12]}",
            "queue": self.queue_name,
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "data": data,
            "retryable": data is not None,
            "retried": False,
            "retry_count": 0,
        }
        self._entries.append(entry)
        if len(self._entries) > self.max_items:
            self._entries = self._entries[-self.max_items :]
        return entry

    def get_entries(self, include_retried: bool = False, limit: int = 100) -> List[Dict[str, Any]]:
        items = [
            dict(e) for e in self._entries
            if include_retried or not e.get("retried", False)
        ]
        return items[-limit:]

    def get_retry_candidates(
        self,
        entry_ids: Optional[List[str]] = None,
        max_items: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        candidates = [
            e for e in self._entries
            if not e.get("retried", False) and e.get("retryable", False)
            and (entry_ids is None or e.get("id") in entry_ids)
        ]
        if max_items is not None and max_items > 0:
            candidates = candidates[:max_items]
        return candidates

    def mark_retried(self, entry_id: str, new_msg_id: str) -> None:
        for e in self._entries:
            if e.get("id") == entry_id:
                e["retried"] = True
                e["retry_count"] = e.get("retry_count", 0) + 1
                e["new_msg_id"] = new_msg_id
                break

    def clear(self) -> int:
        count = len(self._entries)
        self._entries.clear()
        return count


class EnqueueHookBase(abc.ABC):
    """Enqueue hook base class."""

    @abc.abstractmethod
    async def on_enqueue(self, data: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
        """Called before message enqueue."""
        return data


class DequeueHandlerBase(abc.ABC):
    """Dequeue handler base class with callback reporting."""

    _success_callback: Optional[Callable[[], None]] = None
    _requeue_callback: Optional[Callable[[], None]] = None
    _error_callback: Optional[Callable[[str, Optional[Dict[str, Any]]], None]] = None

    def set_callbacks(
        self,
        on_success: Callable[[], None],
        on_requeue: Callable[[], None],
        on_error: Callable[[str, Optional[Dict[str, Any]]], None],
    ) -> None:
        self._success_callback = on_success
        self._requeue_callback = on_requeue
        self._error_callback = on_error

    def report_success(self) -> None:
        if self._success_callback:
            self._success_callback()

    def report_requeue(self) -> None:
        if self._requeue_callback:
            self._requeue_callback()

    def report_error(self, error_msg: str, data: Optional[Dict[str, Any]] = None) -> None:
        if self._error_callback:
            self._error_callback(error_msg, data)

    async def on_cancelled(self, data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        self.report_success()
        return None

    @abc.abstractmethod
    async def on_dequeue(self, data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not data:
            return None
        return data
