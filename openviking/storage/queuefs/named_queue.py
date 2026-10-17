# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
import asyncio
import collections
import json
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4

from openviking.pyagfs import AGFSSyncClientProtocol, AsyncAGFSClient
from openviking.pyagfs.exceptions import (
    AGFSAlreadyExistsError,
    AGFSInvalidOperationError,
    AGFSNotFoundError,
)
from openviking.service.task_work_index import (
    TaskWorkIndex,
    TaskWorkRejected,
    bind_task_context,
    extract_task_metadata,
    prepare_task_payload,
)
from openviking_cli.utils.logger import get_logger

from .queue_types import (
    DequeueHandlerBase,
    DLQEntry,
    DLQStore,
    EnqueueHookBase,
    QueueError,
    QueueStatus,
    evaluate_queue_health,
)

logger = get_logger(__name__)

__all__ = [
    "NamedQueue",
    "QueueError",
    "QueueStatus",
    "DLQEntry",
    "DLQStore",
    "EnqueueHookBase",
    "DequeueHandlerBase",
]


class NamedQueue:
    """NamedQueue: Operation class for specific named queue, supports status tracking."""

    MAX_ERRORS = 100

    def __init__(
        self,
        agfs: AGFSSyncClientProtocol,
        mount_point: str,
        name: str,
        enqueue_hook: Optional[EnqueueHookBase] = None,
        dequeue_handler: Optional[DequeueHandlerBase] = None,
        task_work_index: Optional[TaskWorkIndex] = None,
    ):
        self.name = name
        self.path = f"{mount_point}/{name}"
        self._agfs = agfs
        self._async_agfs = AsyncAGFSClient(agfs)
        self._enqueue_hook = enqueue_hook
        self._dequeue_handler = dequeue_handler
        self._task_work_index = task_work_index
        self._initialized = False

        # Status tracking & health evaluation
        self._lock = threading.Lock()
        self._in_progress = 0
        self._processed = 0
        self._requeue_count = 0
        self._error_count = 0
        self._errors: List[QueueError] = []
        self._recent_outcomes: collections.deque[bool] = collections.deque(maxlen=100)
        self._dlq_store = DLQStore(queue_name=self.name, max_items=1000)

        # Inject callbacks to handler
        if self._dequeue_handler:
            self.set_dequeue_handler(self._dequeue_handler)

    def set_dequeue_handler(self, handler: DequeueHandlerBase) -> None:
        """Bind the consumer after its runtime dependencies are initialized."""
        self._dequeue_handler = handler
        handler.set_callbacks(
            on_success=self._on_process_success,
            on_requeue=self._on_process_requeue,
            on_error=self._on_process_error,
        )

    def _on_dequeue_start(self) -> None:
        """Called on dequeue."""
        with self._lock:
            self._in_progress += 1

    def _on_process_success(self) -> None:
        """Called on processing success."""
        with self._lock:
            self._in_progress = max(0, self._in_progress - 1)
            self._processed += 1
            self._recent_outcomes.append(True)

    def _on_process_requeue(self) -> None:
        """Called when a dequeued message is re-enqueued for later retry."""
        with self._lock:
            self._requeue_count += 1

    def _on_process_error(self, error_msg: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Called on processing failure."""
        if self._task_work_index is not None and data is not None:
            metadata = extract_task_metadata(data)
            if metadata is not None:
                self._task_work_index.record_failure(metadata.task_id, error_msg)
        with self._lock:
            self._in_progress = max(0, self._in_progress - 1)
            self._error_count += 1
            self._recent_outcomes.append(False)
            self._errors.append(
                QueueError(
                    timestamp=datetime.now(),
                    message=error_msg,
                    data=data,
                )
            )
            if len(self._errors) > self.MAX_ERRORS:
                self._errors = self._errors[-self.MAX_ERRORS :]
            self._dlq_store.record(error_msg, data)

    def has_errors(self) -> bool:
        """Check if queue currently has an active, unhealthy error condition."""
        with self._lock:
            _, active_errors, _ = evaluate_queue_health(
                in_progress=self._in_progress,
                processed=self._processed,
                error_count=self._error_count,
                recent_outcomes=self._recent_outcomes,
                pending=0,
            )
            return active_errors

    def is_healthy(self) -> bool:
        """Queue is healthy if it does not suffer from active or critical error condition."""
        return not self.has_errors()

    async def get_status(self) -> QueueStatus:
        """Get queue status with active health determination."""
        pending = await self.size()
        with self._lock:
            is_healthy, active_errors, recent_rate = evaluate_queue_health(
                in_progress=self._in_progress,
                processed=self._processed,
                error_count=self._error_count,
                recent_outcomes=self._recent_outcomes,
                pending=pending,
            )
            return QueueStatus(
                pending=pending,
                in_progress=self._in_progress,
                processed=self._processed,
                requeue_count=self._requeue_count,
                error_count=self._error_count,
                errors=list(self._errors),
                recent_error_rate=recent_rate,
                is_healthy=is_healthy,
                has_active_errors=active_errors,
            )

    def reset_status(self) -> None:
        """Reset status counters."""
        with self._lock:
            self._in_progress = 0
            self._processed = 0
            self._requeue_count = 0
            self._error_count = 0
            self._errors = []
            self._recent_outcomes.clear()

    def get_dlq(
        self,
        include_retried: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get DLQ entries for this queue."""
        with self._lock:
            return self._dlq_store.get_entries(include_retried=include_retried, limit=limit)

    async def retry_failed(
        self,
        entry_ids: Optional[List[str]] = None,
        max_items: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Re-enqueue failed items from Dead Letter Queue (DLQ) for self-healing."""
        with self._lock:
            candidates = self._dlq_store.get_retry_candidates(
                entry_ids=entry_ids, max_items=max_items
            )

        retried_entries = []
        for entry in candidates:
            payload = entry.get("data")
            if payload is None:
                continue
            try:
                new_msg_id = await self.enqueue(payload)
                with self._lock:
                    self._dlq_store.mark_retried(entry["id"], new_msg_id)
                    # Self-heal: decrements error count so that retrying resolves the failure
                    self._error_count = max(0, self._error_count - 1)
                retried_entries.append({
                    "id": entry["id"],
                    "queue": self.name,
                    "new_msg_id": new_msg_id,
                })
            except Exception as e:
                logger.error(f"[NamedQueue] Failed to retry DLQ entry {entry.get('id')}: {e}")

        return retried_entries

    def clear_dlq(self) -> int:
        """Clear DLQ entries and reset error count."""
        with self._lock:
            count = self._dlq_store.clear()
            self._errors.clear()
            self._error_count = 0
            self._recent_outcomes.clear()
            return count

    def has_dequeue_handler(self) -> bool:
        """Check if dequeue handler exists."""
        return self._dequeue_handler is not None

    async def _ensure_initialized(self):
        """Ensure queue directory is created in AGFS."""
        if not self._initialized:
            try:
                await self._async_agfs.mkdir(self.path)
            except (AGFSAlreadyExistsError, FileExistsError):
                pass
            self._initialized = True

    async def enqueue(self, data: Union[str, Dict[str, Any]]) -> str:
        """Send message to queue (enqueue)."""
        await self._ensure_initialized()
        enqueue_file = f"{self.path}/enqueue"

        # Execute enqueue hook
        if self._enqueue_hook:
            data = await self._enqueue_hook.on_enqueue(data)

        if isinstance(data, dict):
            data, task_metadata = prepare_task_payload(data)
        else:
            task_metadata = None

        if self._task_work_index is not None and not self._task_work_index.register(
            self.name, task_metadata
        ):
            task_id = task_metadata.task_id if task_metadata is not None else "unknown"
            logger.info(
                "[NamedQueue] Skip enqueue for cancelling task %s on %s",
                task_id,
                self.name,
            )
            raise TaskWorkRejected(
                f"Task {task_id} is cancelling; rejected work for {self.name}"
            )

        try:
            if isinstance(data, dict):
                data = json.dumps(data)

            msg_id = await self._async_agfs.write(enqueue_file, data.encode("utf-8"))
        except BaseException:
            if self._task_work_index is not None and task_metadata is not None:
                await self._task_work_index.discard(self.name, task_metadata)
            raise
        return msg_id if isinstance(msg_id, str) else str(msg_id)

    async def ack(self, msg_id: str, message: Optional[Dict[str, Any]] = None) -> None:
        """Acknowledge successful processing of a message (deletes it from persistent storage).

        Must be called after the dequeue handler finishes processing a message.
        Task-owned work is provisionally removed from the runtime index first so
        the last message can persist its task's terminal state before deletion.
        If not called (e.g. process crashes), the message will be automatically
        re-queued on the next startup via RecoverStale.
        """
        if not msg_id:
            return
        ack_file = f"{self.path}/ack"
        prepared = None
        try:
            if self._task_work_index is not None and message is not None:
                prepared = await self._task_work_index.prepare_ack(self.name, message)
            await self._async_agfs.write(ack_file, msg_id.encode("utf-8"))
        except asyncio.CancelledError:
            if self._task_work_index is not None and prepared is not None:
                self._task_work_index.rollback_ack(self.name, prepared)
            raise
        except Exception as e:
            if self._task_work_index is not None and prepared is not None:
                self._task_work_index.rollback_ack(self.name, prepared)
            logger.warning(f"[NamedQueue] Ack failed for {self.name} msg_id={msg_id}: {e}")

    async def _read_queue_message(self) -> Optional[Dict[str, Any]]:
        """Read and remove one message from the AGFS queue; return parsed dict or None.

        Normalises the various return types AGFSClient.read() may produce.
        """
        content = await self._async_agfs.read(f"{self.path}/dequeue")
        if not content or content == b"{}":
            return None
        if isinstance(content, bytes):
            raw = content
        elif isinstance(content, str):
            raw = content.encode("utf-8")
        elif hasattr(content, "content") and content.content is not None:
            raw = content.content
        else:
            raw = str(content).encode("utf-8")
        return json.loads(raw.decode("utf-8"))

    async def dequeue(self) -> Optional[Dict[str, Any]]:
        """Dequeue a message, process it, then ack to confirm deletion.

        Flow (at-least-once delivery):
          1. Read from /dequeue  → backend marks message as 'processing' (not deleted yet)
          2. Call on_dequeue()   → actual processing
          3. Call ack()          → backend deletes the message permanently

        If the process crashes between steps 1 and 3, the backend's RecoverStale
        on the next startup resets the message back to 'pending' for retry.
        """
        await self._ensure_initialized()
        try:
            data = await self._read_queue_message()
            if data is None:
                return None
            # Capture message ID before passing data to handler (handler may modify it)
            msg_id = data.get("id", "") if isinstance(data, dict) else ""
            raw_data = data
            if self._dequeue_handler:
                self._on_dequeue_start()
                data = await self.process_dequeued(data)
            # Ack unconditionally after handler returns (success or handled error).
            # If on_dequeue raises, the exception propagates and ack is skipped —
            # the message will be recovered on next startup.
            await self.ack(msg_id, raw_data)
            return data
        except Exception as e:
            logger.debug(f"[NamedQueue] Dequeue failed for {self.name}: {e}")
            return None

    async def dequeue_raw(self) -> Optional[Dict[str, Any]]:
        """Get and remove message from queue without invoking the handler."""
        await self._ensure_initialized()
        try:
            return await self._read_queue_message()
        except Exception as e:
            logger.debug(f"[NamedQueue] Dequeue raw failed for {self.name}: {e}")
            return None

    async def process_dequeued(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Invoke the dequeue handler on already-fetched raw data.

        NOTE: caller must call _on_dequeue_start() before invoking this method
        so that in_progress is incremented atomically with the dequeue.
        """
        if self._dequeue_handler is None:
            return data

        metadata = extract_task_metadata(data)
        if metadata is None or self._task_work_index is None:
            return await self._dequeue_handler.on_dequeue(data)

        active_task = asyncio.current_task()
        with bind_task_context(metadata.task_id, metadata.account_id, metadata.user_id):
            if self._task_work_index.cancellation_requested(metadata.task_id):
                return await self._dequeue_handler.on_cancelled(data)
            if active_task is not None:
                self._task_work_index.register_active(metadata.task_id, active_task)
            try:
                return await self._dequeue_handler.on_dequeue(data)
            except asyncio.CancelledError:
                if self._task_work_index.cancellation_requested(metadata.task_id):
                    self._on_process_success()
                    return None
                raise
            finally:
                if active_task is not None:
                    self._task_work_index.unregister_active(metadata.task_id, active_task)

    async def peek(self) -> Optional[Dict[str, Any]]:
        """Peek at head message without removing."""
        await self._ensure_initialized()
        peek_file = f"{self.path}/peek"

        try:
            content = await self._async_agfs.read(peek_file)
            if not content or content == b"{}":
                return None
            if isinstance(content, bytes):
                return json.loads(content.decode("utf-8"))
            elif isinstance(content, str):
                return json.loads(content)
            else:
                return None
        except Exception as e:
            logger.debug(f"[NamedQueue] Peek failed for {self.name}: {e}")
            return None

    async def size(self) -> int:
        """Get queue size."""
        await self._ensure_initialized()
        size_file = f"{self.path}/size"

        try:
            content = await self._async_agfs.read(size_file)
            if content is None:
                return 0
            if isinstance(content, bytes):
                text = content.decode("utf-8")
            elif isinstance(content, str):
                text = content
            else:
                raise TypeError(f"Unexpected queue size response: {type(content).__name__}")
            text = text.strip()
            return int(text) if text else 0
        except (AGFSNotFoundError, FileNotFoundError, AGFSInvalidOperationError):
            return 0

    async def snapshot(self) -> List[Dict[str, Any]]:
        """Return all unacknowledged messages without changing queue state."""
        await self._ensure_initialized()
        try:
            content = await self._async_agfs.read(f"{self.path}/messages")
        except (AGFSNotFoundError, FileNotFoundError, AGFSInvalidOperationError):
            return []
        if not content:
            return []
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        elif hasattr(content, "content") and content.content is not None:
            content = content.content.decode("utf-8")
        parsed = json.loads(content)
        return parsed if isinstance(parsed, list) else []

    async def clear(self) -> bool:
        """Clear queue."""
        await self._ensure_initialized()
        clear_file = f"{self.path}/clear"

        messages = await self.snapshot() if self._task_work_index is not None else []
        prepared = []
        try:
            if self._task_work_index is not None:
                for message in messages:
                    metadata = await self._task_work_index.prepare_ack(self.name, message)
                    if metadata is not None:
                        prepared.append(metadata)
            await self._async_agfs.write(clear_file, b"")
            return True
        except asyncio.CancelledError:
            if self._task_work_index is not None:
                for metadata in prepared:
                    self._task_work_index.rollback_ack(self.name, metadata)
            raise
        except Exception as e:
            if self._task_work_index is not None:
                for metadata in prepared:
                    self._task_work_index.rollback_ack(self.name, metadata)
            logger.error(f"[NamedQueue] Clear failed for {self.name}: {e}")
            return False
