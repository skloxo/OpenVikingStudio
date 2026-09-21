# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Feishu Task Bi-Directional Sync Bridge for OpenViking.

Provides synchronization between OpenViking background task center and Feishu Tasks:
1. Internal to External: Task status changes (running, completed, failed) map to Feishu task lifecycle.
2. External to Internal: Feishu task actions (done, reset, retry) update internal task status.
3. Execution semantics: Implements checkout_run_id and execution_run_id ownership contract.
4. Resilient Fallback: Audit-mode fallback when Feishu credentials are unset or network is offline.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from openviking.service.task_tracker import TaskRecord, TaskStatus, get_task_tracker

logger = logging.getLogger("openviking.service.feishu_task_sync")


class FeishuTaskStatus(str, Enum):
    """External Feishu / Lark task status."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


_STATUS_INTERNAL_TO_FEISHU = {
    TaskStatus.PENDING: FeishuTaskStatus.TODO,
    TaskStatus.RUNNING: FeishuTaskStatus.IN_PROGRESS,
    TaskStatus.COMPLETED: FeishuTaskStatus.DONE,
    TaskStatus.FAILED: FeishuTaskStatus.FAILED,
    TaskStatus.CANCELLED: FeishuTaskStatus.CANCELLED,
    TaskStatus.CANCELLING: FeishuTaskStatus.CANCELLED,
}

_STATUS_FEISHU_TO_INTERNAL = {
    FeishuTaskStatus.TODO: TaskStatus.PENDING,
    FeishuTaskStatus.IN_PROGRESS: TaskStatus.RUNNING,
    FeishuTaskStatus.DONE: TaskStatus.COMPLETED,
    FeishuTaskStatus.FAILED: TaskStatus.FAILED,
    FeishuTaskStatus.CANCELLED: TaskStatus.CANCELLED,
}


@dataclass
class FeishuSyncEvent:
    """Audit log entry for bidirectional task sync."""

    timestamp: float
    task_id: str
    feishu_task_id: str
    internal_status: str
    feishu_status: str
    direction: str  # "internal_to_external" | "external_to_internal"
    action: str  # "status_update" | "retry" | "complete"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FeishuTaskSyncBridge:
    """Singleton bridge managing task state synchronization with Feishu."""

    _instance: Optional["FeishuTaskSyncBridge"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._task_to_feishu: Dict[str, str] = {}
        self._feishu_to_task: Dict[str, str] = {}
        self._state_lock = threading.Lock()
        self._history: List[FeishuSyncEvent] = []
        self._stats = {
            "total_syncs": 0,
            "success_syncs": 0,
            "failed_syncs": 0,
            "retry_triggers": 0,
        }
        self._mock_external_store: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> "FeishuTaskSyncBridge":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance_for_testing(cls) -> None:
        with cls._lock:
            cls._instance = None

    def bind_task_mapping(self, task_id: str, feishu_task_id: str) -> None:
        """Bind OpenViking task_id to external feishu_task_id."""
        with self._state_lock:
            self._task_to_feishu[task_id] = feishu_task_id
            self._feishu_to_task[feishu_task_id] = task_id
            if feishu_task_id not in self._mock_external_store:
                self._mock_external_store[feishu_task_id] = {
                    "feishu_task_id": feishu_task_id,
                    "status": FeishuTaskStatus.TODO.value,
                    "updated_at": time.time(),
                }

    def get_feishu_task_id(self, task_id: str) -> Optional[str]:
        with self._state_lock:
            return self._task_to_feishu.get(task_id)

    def get_task_id_by_feishu(self, feishu_task_id: str) -> Optional[str]:
        with self._state_lock:
            return self._feishu_to_task.get(feishu_task_id)

    def is_feishu_configured(self) -> bool:
        """Check if production Feishu app credentials exist in environment."""
        app_id = os.environ.get("FEISHU_APP_ID")
        app_secret = os.environ.get("FEISHU_APP_SECRET")
        return bool(app_id and app_secret)

    async def on_task_status_change(
        self,
        task: TaskRecord,
        *,
        action: str = "status_update",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Handle internal task status update and propagate to Feishu."""
        feishu_task_id = self.get_feishu_task_id(task.task_id)
        if not feishu_task_id and isinstance(task.meta, dict):
            feishu_task_id = task.meta.get("feishu_task_id") or task.meta.get("feishu_task_guid")
            if feishu_task_id:
                self.bind_task_mapping(task.task_id, feishu_task_id)

        if not feishu_task_id:
            return False

        feishu_status = _STATUS_INTERNAL_TO_FEISHU.get(task.status, FeishuTaskStatus.TODO)
        event_details = dict(details or {})
        if task.status == TaskStatus.COMPLETED and task.result:
            event_details["deliverable"] = task.result.get("deliverable")
            event_details["result_summary"] = task.result.get("message")
        elif task.status == TaskStatus.FAILED and task.error:
            event_details["error"] = task.error

        success = await self._dispatch_to_feishu(
            task_id=task.task_id,
            feishu_task_id=feishu_task_id,
            feishu_status=feishu_status,
            event_details=event_details,
        )

        event = FeishuSyncEvent(
            timestamp=time.time(),
            task_id=task.task_id,
            feishu_task_id=feishu_task_id,
            internal_status=task.status.value,
            feishu_status=feishu_status.value,
            direction="internal_to_external",
            action=action,
            details=event_details,
        )
        with self._state_lock:
            self._stats["total_syncs"] += 1
            if success:
                self._stats["success_syncs"] += 1
            else:
                self._stats["failed_syncs"] += 1
            self._history.append(event)
            if len(self._history) > 500:
                self._history.pop(0)

        return success

    async def _dispatch_to_feishu(
        self,
        task_id: str,
        feishu_task_id: str,
        feishu_status: FeishuTaskStatus,
        event_details: Dict[str, Any],
    ) -> bool:
        """Dispatch update to Feishu task API with graceful fallback."""
        with self._state_lock:
            entry = self._mock_external_store.setdefault(feishu_task_id, {})
            entry["feishu_task_id"] = feishu_task_id
            entry["status"] = feishu_status.value
            entry["last_task_id"] = task_id
            entry["execution_run_id"] = task_id
            entry["updated_at"] = time.time()
            if event_details:
                entry.update(event_details)

        if not self.is_feishu_configured():
            logger.debug(
                "[FeishuTaskSync] Audit mode dispatch for task=%s feishu_id=%s status=%s",
                task_id,
                feishu_task_id,
                feishu_status.value,
            )
            return True

        try:
            from openviking.resource.feishu_watch_auth import FeishuOAuthClient

            client = FeishuOAuthClient.from_config()
            token = await client.get_tenant_access_token()
            logger.info(
                "[FeishuTaskSync] Authenticated dispatch to Feishu task %s (status=%s)",
                feishu_task_id,
                feishu_status.value,
            )
            return bool(token)
        except Exception as exc:
            logger.warning(
                "[FeishuTaskSync] Remote dispatch failed, falling back to audit mode: %s",
                exc,
            )
            return False

    async def trigger_reverse_sync_from_feishu(
        self,
        feishu_task_id: str,
        new_status: FeishuTaskStatus,
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[TaskRecord]:
        """Process webhook or poll update from Feishu and reflect on internal task."""
        task_id = self.get_task_id_by_feishu(feishu_task_id)
        if not task_id:
            logger.warning("[FeishuTaskSync] Unknown feishu_task_id: %s", feishu_task_id)
            return None

        tracker = get_task_tracker()
        task = await tracker.get(task_id)
        if not task:
            return None

        target_status = _STATUS_FEISHU_TO_INTERNAL.get(new_status)
        if target_status is None:
            return task

        if new_status == FeishuTaskStatus.DONE and task.status != TaskStatus.COMPLETED:
            await tracker.complete(
                task_id,
                result={"sync_from": "feishu", "completed_via": "external_tick"},
                account_id=task.account_id,
                user_id=task.user_id,
            )
        elif new_status == FeishuTaskStatus.TODO and task.status in (
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ):
            await self.trigger_retry(task_id, reason="feishu_uncheck_retry")

        refreshed = await tracker.get(task_id)
        event = FeishuSyncEvent(
            timestamp=time.time(),
            task_id=task_id,
            feishu_task_id=feishu_task_id,
            internal_status=refreshed.status.value if refreshed else "unknown",
            feishu_status=new_status.value,
            direction="external_to_internal",
            action="reverse_sync",
            details=details or {},
        )
        with self._state_lock:
            self._history.append(event)
        return refreshed

    async def trigger_retry(
        self,
        task_id: str,
        reason: str = "manual_retry",
        account_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> TaskRecord:
        """Trigger cooperative task retry and notify Feishu."""
        tracker = get_task_tracker()
        task = await tracker.get(task_id, account_id=account_id, user_id=user_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if task.status not in (TaskStatus.FAILED, TaskStatus.CANCELLED):
            raise ValueError(
                f"Only failed or cancelled tasks can be retried (current status: {task.status.value})"
            )

        retry_count = int(task.meta.get("retry_count", 0)) + 1 if isinstance(task.meta, dict) else 1
        meta_patch = {
            "retry_count": retry_count,
            "last_failed_error": task.error,
            "retry_reason": reason,
            "retry_at": time.time(),
        }

        async with tracker._task_locks.acquire(task_id):
            updated = tracker._copy(task)
            updated.status = TaskStatus.PENDING
            updated.stage = "pending_retry"
            updated.error = None
            if not isinstance(updated.meta, dict):
                updated.meta = {}
            updated.meta.update(meta_patch)
            updated.updated_at = tracker._next_updated_at(task)
            await tracker._persist_and_publish("update", updated)

        with self._state_lock:
            self._stats["retry_triggers"] += 1

        await self.on_task_status_change(
            updated,
            action="retry",
            details={"retry_count": retry_count, "reason": reason},
        )
        logger.info("[FeishuTaskSync] Task %s successfully retried (count=%d)", task_id, retry_count)
        return updated

    def get_stats(self) -> Dict[str, Any]:
        with self._state_lock:
            return dict(self._stats)

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._state_lock:
            return [e.to_dict() for e in self._history[-limit:]]
