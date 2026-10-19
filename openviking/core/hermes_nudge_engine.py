# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Periodic Nudges 异步副进程复盘引擎 (Asynchronous Trajectory Reflection Engine).

核心价值:
  1. 零阻塞用户交互: 主交互链路结束后，以异步副进程/守护线程形式派发复盘；
  2. 经验提纯: 分析会话中出现的重试、工具错误与关键成功路径，提纯为 Evolution Lesson；
  3. 候选微补丁自提议: 当识别到代码/技能特定规则缺陷时，生成建议补丁交由 PatchEngine 治理。

(Card-Evolve-HermesEvolveLoop-Patch v1.5.39)
"""

from __future__ import annotations

import logging
import queue
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from openviking.core.hermes_experience_store import HermesExperienceStore

logger = logging.getLogger("openviking.core.hermes_nudge_engine")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class StructuredAttribution(BaseModel):
    """Hermes 经历提纯结构化归因结果。"""
    attribution_id: str = Field(default_factory=lambda: f"attr-{uuid.uuid4().hex[:8]}")
    session_id: str
    failure_category: str = "NONE"  # DETERMINISTIC | TRANSIENT | SYNTAX | CONTRACT | NONE
    root_cause_summary: str = ""
    error_frames: List[str] = Field(default_factory=list)
    affected_entity: Optional[str] = None
    suggested_patch: Optional[Dict[str, Any]] = None
    patch_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)


class NudgeReviewRecord(BaseModel):
    """单次会话复盘记录。"""
    review_id: str = Field(default_factory=lambda: f"ndg-{uuid.uuid4().hex[:8]}")
    session_id: str
    reviewed_at: float = Field(default_factory=time.time)
    message_count: int = 0
    insights: List[str] = Field(default_factory=list)
    proposed_patch_needed: bool = False
    attribution: Optional[StructuredAttribution] = None
    duration_ms: float = 0.0
    status: str = "completed"  # "completed" | "failed" | "skipped"


# ---------------------------------------------------------------------------
# Nudge 调度引擎 (单例 Worker)
# ---------------------------------------------------------------------------

class HermesNudgeEngine:
    """异步轨迹复盘引擎。单例模式。"""

    _instance: Optional["HermesNudgeEngine"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._store = HermesExperienceStore.get_instance()
        self._queue: queue.Queue[str] = queue.Queue()
        self._reviews: List[NudgeReviewRecord] = []
        self._attributions: List[StructuredAttribution] = []
        self._reviews_lock = threading.Lock()
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="hermes-nudge-worker",
        )
        self._worker_thread.start()

    @classmethod
    def get_instance(cls) -> "HermesNudgeEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            if cls._instance is not None:
                cls._instance._running = False
                cls._instance = None

    def trigger_nudge(self, session_id: str) -> Dict[str, Any]:
        """将指定会话排入异步复盘队列（零阻塞直接返回）。"""
        self._queue.put(session_id)
        return {
            "session_id": session_id,
            "status": "queued",
            "queue_depth": self._queue.qsize(),
            "queued_at": time.time(),
        }

    def attribute_session(self, session_id: str, auto_propose_patch: bool = False) -> StructuredAttribution:
        """从会话消息中提取错误堆栈、执行物理归因并可选提议微手术补丁。"""
        messages = self._store.get_messages_by_session(session_id)
        if not messages:
            return StructuredAttribution(session_id=session_id, failure_category="NONE", root_cause_summary="No messages found in session")

        category = "NONE"
        root_cause = ""
        frames: List[str] = []
        affected_file: Optional[str] = None
        suggested_patch_data: Optional[Dict[str, Any]] = None
        created_patch_id: Optional[str] = None

        tb_pattern = re.compile(
            r'File "([^"]+)", line (\d+)(?:, in (\w+))?\n\s*(.*?)\n(?:([A-Za-z0-9_]+Error|[A-Za-z0-9_]+Exception):\s*(.*))?',
            re.MULTILINE,
        )

        for m in reversed(messages):
            content = m.content
            # Check for Python traceback
            match = tb_pattern.search(content)
            if match:
                fpath, line_no, func_name, code_line, exc_type, exc_msg = match.groups()
                affected_file = fpath
                frames.append(f"{fpath}:{line_no} in {func_name or 'unknown'}")
                exc_full = f"{exc_type}: {exc_msg}" if exc_type else "Exception detected"
                root_cause = f"[{exc_full}] at line {line_no}: {code_line}"

                if "SyntaxError" in (exc_type or "") or "IndentationError" in (exc_type or ""):
                    category = "SYNTAX"
                else:
                    category = "DETERMINISTIC"
                break

            # Check for contract / AHE violation
            if "ahe" in content.lower() and "violation" in content.lower():
                category = "CONTRACT"
                root_cause = "AHE Contract Assumption Violation detected"
                frames.append("AHEContractVerifier")
                break

            # Check for transient errors
            transient_signals = ["timeout", "429", "rate limit", "connection reset", "502 bad gateway", "503 service unavailable"]
            if any(sig in content.lower() for sig in transient_signals):
                category = "TRANSIENT"
                root_cause = f"Transient network/gateway error identified: {content[:120]}"
                break

            # Generic error signal
            if "error" in content.lower() or "exception" in content.lower() or "failed" in content.lower():
                err_lines = [l.strip() for l in content.splitlines() if any(w in l.lower() for w in ["error", "exception", "failed"])]
                if err_lines:
                    root_cause = err_lines[0][:150]
                    category = "DETERMINISTIC"
                    break

        if category != "NONE" and affected_file and auto_propose_patch:
            suggested_patch_data = {
                "skill_name": "hermes-attribution",
                "file_path": affected_file,
                "target_content": "# target line causing error",
                "replacement_content": "# patched line with guardrail",
                "reason": f"Automated micro-patch suggested for {root_cause[:80]}",
            }
            try:
                from openviking.core.hermes_patch_engine import HermesPatchEngine
                p = HermesPatchEngine.get_instance().propose_patch(
                    skill_name="hermes-attribution",
                    file_path=affected_file,
                    target_content=suggested_patch_data["target_content"],
                    replacement_content=suggested_patch_data["replacement_content"],
                    reason=suggested_patch_data["reason"],
                )
                created_patch_id = p.patch_id
            except Exception as p_exc:
                logger.debug(f"[HermesNudgeEngine] Propose patch skipped: {p_exc}")

        attribution = StructuredAttribution(
            session_id=session_id,
            failure_category=category,
            root_cause_summary=root_cause or "No errors detected; execution successful.",
            error_frames=frames,
            affected_entity=affected_file,
            suggested_patch=suggested_patch_data,
            patch_id=created_patch_id,
        )

        with self._reviews_lock:
            self._attributions.insert(0, attribution)
            if len(self._attributions) > 100:
                self._attributions.pop()

        # Bridge to UniversalAuditLedger
        try:
            from openviking.service.universal_audit_ledger import UniversalAuditLedger
            UniversalAuditLedger.get_instance().record_event(
                entity_type="HERMES_SESSION",
                entity_id=session_id,
                action="HERMES_STRUCTURED_ATTRIBUTION",
                operator="hermes_nudge_engine",
                status="SUCCESS" if category in ("NONE", "TRANSIENT") else "FLAGGED",
                details={
                    "attribution_id": attribution.attribution_id,
                    "category": category,
                    "root_cause": attribution.root_cause_summary,
                    "patch_id": created_patch_id,
                },
            )
        except Exception:
            pass

        return attribution

    def _worker_loop(self) -> None:
        """后台复盘消费者循环。"""
        while self._running:
            try:
                session_id = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            t0 = time.monotonic()
            messages = self._store.get_messages_by_session(session_id)
            if not messages:
                self._queue.task_done()
                continue

            insights: List[str] = []
            has_error = False

            for m in messages:
                text = m.content.lower()
                if "error" in text or "traceback" in text or "exception" in text or "failed" in text:
                    has_error = True
                    insights.append(f"[{m.role}] 识别到潜在异常/重试信号")

            attr = None
            if has_error:
                try:
                    attr = self.attribute_session(session_id, auto_propose_patch=False)
                    insights.append(f"[归因] 分类={attr.failure_category}: {attr.root_cause_summary[:80]}")
                except Exception as a_exc:
                    logger.debug(f"[HermesNudgeEngine] Attribution failure: {a_exc}")

            if not insights:
                insights.append(f"会话顺利完成，共 {len(messages)} 回合，执行路径平稳")

            duration = (time.monotonic() - t0) * 1000.0

            rec = NudgeReviewRecord(
                session_id=session_id,
                message_count=len(messages),
                insights=insights,
                proposed_patch_needed=has_error,
                attribution=attr,
                duration_ms=round(duration, 2),
                status="completed",
            )

            with self._reviews_lock:
                self._reviews.insert(0, rec)
                if len(self._reviews) > 200:
                    self._reviews.pop()

            self._queue.task_done()

    def get_status(self) -> Dict[str, Any]:
        """查询复盘引擎当前运行状态。"""
        with self._reviews_lock:
            completed_count = len(self._reviews)
            latest = self._reviews[0] if self._reviews else None
            attr_count = len(self._attributions)

        return {
            "queue_depth": self._queue.qsize(),
            "completed_reviews": completed_count,
            "attributions_count": attr_count,
            "is_running": self._running,
            "latest_review": latest.model_dump() if latest else None,
        }

    def list_recent_reviews(self, limit: int = 20) -> List[NudgeReviewRecord]:
        """获取最近完成的复盘记录。"""
        with self._reviews_lock:
            return list(self._reviews[:limit])

    def list_attributions(self, limit: int = 50) -> List[StructuredAttribution]:
        """获取结构化归因记录。"""
        with self._reviews_lock:
            return list(self._attributions[:limit])

    def get_attribution(self, session_id: str) -> Optional[StructuredAttribution]:
        """获取指定会话的归因记录。"""
        with self._reviews_lock:
            for a in self._attributions:
                if a.session_id == session_id:
                    return a
        return None
