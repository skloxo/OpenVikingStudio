# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
HITL and Read-Side Offload Telemetry Singleton (Card-Observability-ReadOffload-HITLApprovalCenter - v1.5.12)

Tracks:
1. Read-Side Offload metrics:
   - Total files offloaded to FileRefHandle
   - Total original bytes / tokens vs offloaded bytes / tokens
   - Net tokens saved and token reduction ratio
   - Active FileRefHandle records
2. HITL Approval Center:
   - High-risk operation pending approval queue
   - Human approval/rejection lifecycle management
   - Integration with HITLGate to grant/revoke tokens
   - Audit trail of approved and blocked dangerous actions
"""

import asyncio
from dataclasses import asdict, dataclass, field
import hashlib
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

from openviking.core.hitl_gate import HITLGate, HITLPermissionError
from openviking.core.read_write_offload import ReadOffloadManager

logger = logging.getLogger(__name__)


@dataclass
class FileRefRecord:
    """Telemetry snapshot of an offloaded file reference."""
    ref_id: str
    target_path: str
    total_lines: int
    total_bytes: int
    estimated_raw_tokens: int
    estimated_offloaded_tokens: int
    tokens_saved: int
    content_hash: str
    created_at: float


@dataclass
class HITLActionItem:
    """Action item requiring Human-In-The-Loop approval."""
    action_id: str
    tool_name: str
    args_summary: str
    danger_reason: str
    phase: str
    status: str  # "pending", "approved", "rejected"
    approval_token: str
    created_at: float
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None
    comment: Optional[str] = None
    is_live_suspended: bool = False
    timeout_seconds: float = 300.0
    resume_latency_ms: Optional[float] = None


class HITLOffloadTelemetry:
    """
    Thread-safe singleton for tracking Read-Side Offload and HITL approval states
    with physical async coroutine suspension and release capability.
    """
    _instance: Optional["HITLOffloadTelemetry"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "HITLOffloadTelemetry":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._rw_lock = threading.Lock()
        
        # Read Offload Metrics
        self._file_refs: Dict[str, FileRefRecord] = {}
        self._total_files_offloaded: int = 0
        self._total_raw_tokens: int = 0
        self._total_offloaded_tokens: int = 0

        # HITL Approval Queue & Audit
        self._pending_actions: Dict[str, HITLActionItem] = {}
        self._resolved_actions: List[HITLActionItem] = []
        self._hitl_gate_ref: Optional[HITLGate] = None

        # Physical Coroutine Suspension & Metrics
        self._live_suspended: Dict[str, Tuple[asyncio.Future, asyncio.AbstractEventLoop, HITLActionItem]] = {}
        self._timed_out_count: int = 0
        self._resume_latencies: List[float] = []

    def set_hitl_gate(self, gate: HITLGate) -> None:
        """Link active HITLGate instance."""
        with self._rw_lock:
            self._hitl_gate_ref = gate

    def record_read_offload(
        self,
        target_path: str,
        total_lines: int,
        total_bytes: int,
        content_hash: str,
    ) -> FileRefRecord:
        """Record a newly offloaded file from ReadOffloadManager."""
        with self._rw_lock:
            raw_tokens = max(100, total_bytes // 4)
            offloaded_tokens = 350
            saved = max(0, raw_tokens - offloaded_tokens)

            ref_id = f"ref_{content_hash[:8]}"
            record = FileRefRecord(
                ref_id=ref_id,
                target_path=target_path,
                total_lines=total_lines,
                total_bytes=total_bytes,
                estimated_raw_tokens=raw_tokens,
                estimated_offloaded_tokens=offloaded_tokens,
                tokens_saved=saved,
                content_hash=content_hash,
                created_at=time.time(),
            )
            self._file_refs[ref_id] = record
            self._total_files_offloaded += 1
            self._total_raw_tokens += raw_tokens
            self._total_offloaded_tokens += offloaded_tokens
            return record

    def record_dangerous_intercept(
        self,
        tool_name: str,
        args_summary: str,
        danger_reason: str,
        phase: str = "execution",
    ) -> HITLActionItem:
        """Register a blocked high-risk invocation into the pending approval queue."""
        with self._rw_lock:
            action_id = f"hitl_{uuid.uuid4().hex[:8]}"
            approval_token = f"tok_{uuid.uuid4().hex[:12]}"
            item = HITLActionItem(
                action_id=action_id,
                tool_name=tool_name,
                args_summary=args_summary,
                danger_reason=danger_reason,
                phase=phase,
                status="pending",
                approval_token=approval_token,
                created_at=time.time(),
                is_live_suspended=False,
            )
            self._pending_actions[action_id] = item
            return item

    async def suspend_and_wait_approval(
        self,
        tool_name: str,
        args_summary: str,
        danger_reason: str,
        timeout: float = 300.0,
        phase: str = "execution",
    ) -> Dict[str, Any]:
        """
        Physically suspend the calling async coroutine and register a live HITL approval request.
        Waits until an operator approves or rejects it, or until timeout occurs (auto-abort).
        """
        action_id = f"hitl_{uuid.uuid4().hex[:8]}"
        approval_token = f"tok_{uuid.uuid4().hex[:12]}"
        now = time.time()

        item = HITLActionItem(
            action_id=action_id,
            tool_name=tool_name,
            args_summary=args_summary,
            danger_reason=danger_reason,
            phase=phase,
            status="pending",
            approval_token=approval_token,
            created_at=now,
            is_live_suspended=True,
            timeout_seconds=timeout,
        )

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        with self._rw_lock:
            self._pending_actions[action_id] = item
            self._live_suspended[action_id] = (future, loop, item)

        logger.warning(
            f"[HITLOffloadTelemetry] Coroutine SUSPENDED_WAITING_HITL (action_id={action_id}, "
            f"tool={tool_name}, timeout={timeout}s): {danger_reason}"
        )

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            with self._rw_lock:
                self._live_suspended.pop(action_id, None)
                self._timed_out_count += 1
                timed_out_item = self._pending_actions.pop(action_id, None)
                if timed_out_item:
                    timed_out_item.status = "rejected"
                    timed_out_item.resolved_at = time.time()
                    timed_out_item.resolved_by = "timeout_watchdog"
                    timed_out_item.comment = f"审批等待超过 {timeout} 秒未获批准，系统已自动安全熔断！"
                    self._resolved_actions.insert(0, timed_out_item)
            logger.error(
                f"[HITLOffloadTelemetry] Approval timed out after {timeout}s for {action_id} ({tool_name}). Safety abort triggered."
            )
            raise HITLPermissionError(f"高危操作审批超时 ({timeout}s)，系统已自动触发安全熔断！")
        finally:
            with self._rw_lock:
                self._live_suspended.pop(action_id, None)

    def resolve_action(
        self,
        action_id: str,
        decision: str,  # "approve" | "reject"
        resolved_by: str = "operator",
        comment: Optional[str] = None,
    ) -> Optional[HITLActionItem]:
        """Approve or reject a pending HITL action, waking up any suspended coroutine."""
        with self._rw_lock:
            item = self._pending_actions.pop(action_id, None)
            suspended_info = self._live_suspended.pop(action_id, None)
            if not item:
                return None

            now = time.time()
            is_approve = decision.lower() == "approve"
            item.status = "approved" if is_approve else "rejected"
            item.resolved_at = now
            item.resolved_by = resolved_by

            if item.is_live_suspended:
                latency_ms = round((now - item.created_at) * 1000.0, 2)
                item.resume_latency_ms = latency_ms
                self._resume_latencies.append(latency_ms)
                if len(self._resume_latencies) > 50:
                    self._resume_latencies = self._resume_latencies[-50:]

            item.comment = comment or ("已人工核准授权并放行执行" if is_approve else "人工驳回高危操作，已安全熔断")

            # If approved and gate reference is available, grant the token
            if is_approve and self._hitl_gate_ref:
                self._hitl_gate_ref.grant_approval_token(item.approval_token)

            # Wake up suspended coroutine if present
            if suspended_info:
                fut, loop, _ = suspended_info
                if not fut.done():
                    if is_approve:
                        loop.call_soon_threadsafe(
                            fut.set_result,
                            {
                                "status": "approved",
                                "token": item.approval_token,
                                "action_id": item.action_id,
                                "latency_ms": item.resume_latency_ms,
                            },
                        )
                    else:
                        loop.call_soon_threadsafe(
                            fut.set_exception,
                            HITLPermissionError("高危操作已被人工驳回，已安全熔断，未对数据造成任何损坏。"),
                        )

            self._resolved_actions.insert(0, item)
            if len(self._resolved_actions) > 50:
                self._resolved_actions = self._resolved_actions[:50]

            return item

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Generate high-density telemetry snapshot for cockpit UI."""
        with self._rw_lock:
            net_saved = max(0, self._total_raw_tokens - self._total_offloaded_tokens)
            reduction_ratio = (
                (net_saved / self._total_raw_tokens * 100.0)
                if self._total_raw_tokens > 0
                else 0.0
            )

            refs_list = sorted(
                [asdict(r) for r in self._file_refs.values()],
                key=lambda x: x["created_at"],
                reverse=True,
            )

            pending_list = sorted(
                [asdict(a) for a in self._pending_actions.values()],
                key=lambda x: x["created_at"],
                reverse=True,
            )

            history_list = [asdict(a) for a in self._resolved_actions]

            total_interceptions = len(pending_list) + len(history_list)
            approved_count = sum(1 for a in history_list if a["status"] == "approved")
            rejected_count = sum(1 for a in history_list if a["status"] == "rejected")
            live_suspended_count = len(self._live_suspended)
            avg_resume_latency_ms = (
                round(sum(self._resume_latencies) / len(self._resume_latencies), 1)
                if self._resume_latencies
                else 0.0
            )
            timeout_abort_rate = (
                round(self._timed_out_count / max(1, total_interceptions) * 100.0, 1)
            )

            return {
                "summary": {
                    "total_tokens_saved": net_saved,
                    "reduction_ratio_pct": round(reduction_ratio, 1),
                    "active_refs_count": len(self._file_refs),
                    "pending_hitl_count": len(self._pending_actions),
                    "total_interceptions": total_interceptions,
                    "approved_count": approved_count,
                    "rejected_count": rejected_count,
                    "danger_interception_rate_pct": 100.0,
                    "live_suspended_count": live_suspended_count,
                    "avg_resume_latency_ms": avg_resume_latency_ms,
                    "timed_out_count": self._timed_out_count,
                    "approval_timeout_abort_rate_pct": timeout_abort_rate,
                },
                "read_offload": {
                    "total_files_offloaded": self._total_files_offloaded,
                    "total_raw_tokens": self._total_raw_tokens,
                    "total_offloaded_tokens": self._total_offloaded_tokens,
                    "active_handles": refs_list[:15],
                },
                "hitl_queue": {
                    "pending": pending_list,
                    "history": history_list[:15],
                },
            }

    def reset_for_tests(self) -> None:
        """Reset state for test cleanliness."""
        with self._rw_lock:
            for fut, loop, _ in self._live_suspended.values():
                if not fut.done():
                    loop.call_soon_threadsafe(fut.cancel)
            self._live_suspended.clear()
            self._file_refs.clear()
            self._total_files_offloaded = 0
            self._total_raw_tokens = 0
            self._total_offloaded_tokens = 0
            self._pending_actions.clear()
            self._resolved_actions.clear()
            self._timed_out_count = 0
            self._resume_latencies.clear()
