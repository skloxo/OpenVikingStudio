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

import queue
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from openviking.core.hermes_experience_store import HermesExperienceStore


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class NudgeReviewRecord(BaseModel):
    """单次会话复盘记录。"""
    review_id: str = Field(default_factory=lambda: f"ndg-{uuid.uuid4().hex[:8]}")
    session_id: str
    reviewed_at: float = Field(default_factory=time.time)
    message_count: int = 0
    insights: List[str] = Field(default_factory=list)
    proposed_patch_needed: bool = False
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

            if not insights:
                insights.append(f"会话顺利完成，共 {len(messages)} 回合，执行路径平稳")

            duration = (time.monotonic() - t0) * 1000.0

            rec = NudgeReviewRecord(
                session_id=session_id,
                message_count=len(messages),
                insights=insights,
                proposed_patch_needed=has_error,
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

        return {
            "queue_depth": self._queue.qsize(),
            "completed_reviews": completed_count,
            "is_running": self._running,
            "latest_review": latest.model_dump() if latest else None,
        }

    def list_recent_reviews(self, limit: int = 20) -> List[NudgeReviewRecord]:
        """获取最近完成的复盘记录。"""
        with self._reviews_lock:
            return list(self._reviews[:limit])
