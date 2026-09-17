# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Agent Loop Telemetry & Observability Probe (Card-Observability-AgentLoop-Telemetry - v1.5.09)

Provides real-time, thread-safe observability metrics for TwoTierAgentLoop & PiDualLoop:
1. Interjection Queue Metrics: current queue depth, total queued, total drained.
2. Active Brake & Flow Metrics: terminate: true trigger count, completed, aborted, failed turns.
3. Model Defense Metrics: transient error retries triggered, exhausted retries count, recovery rate.
4. Merkle Diff Latency: millisecond stat comparison latency (<2ms baseline), monitored files, version.
5. Inner Tool Iteration Steps: total inner steps, last turn steps.
"""

from dataclasses import asdict, dataclass, field
import threading
import time
from typing import Any, Dict, Optional


@dataclass
class AgentLoopTelemetrySnapshot:
    """Strongly typed telemetry snapshot for Agent Loop observability."""
    # 1. 插话队列指标 (Interjection Queue)
    interjection_queue_depth: int = 0
    interjection_total_queued: int = 0
    interjection_total_drained: int = 0
    interjection_lossless_rate: float = 100.0

    # 2. 主动刹车与完工流转 (Active Brake & Termination)
    active_brake_count: int = 0
    turns_completed: int = 0
    turns_aborted: int = 0
    turns_failed: int = 0
    total_turns: int = 0

    # 3. 模型防御与自愈 (Model Defense)
    model_defense_retries_total: int = 0
    model_defense_exhausted_total: int = 0
    model_recovery_rate: float = 100.0

    # 4. 内层工具迭代步数 (Inner Tool Steps)
    total_inner_steps: int = 0
    last_turn_inner_steps: int = 0

    # 5. Merkle 增量状态树巡检 (Merkle State Diff Latency)
    merkle_last_diff_ms: Optional[float] = None
    merkle_tree_file_count: int = 0
    merkle_version: int = 0
    merkle_last_scan_ts: Optional[float] = None

    # 6. 元数据
    timestamp: float = field(default_factory=time.time)
    status: str = "healthy"


class AgentLoopTelemetryCollector:
    """Thread-safe singleton collector for TwoTierAgentLoop runtime metrics."""

    _instance: Optional["AgentLoopTelemetryCollector"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "AgentLoopTelemetryCollector":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._data_lock = threading.Lock()
        self._current_queue_depth = 0
        self._total_queued = 0
        self._total_drained = 0

        self._active_brake_count = 0
        self._turns_completed = 0
        self._turns_aborted = 0
        self._turns_failed = 0

        self._model_retries_total = 0
        self._model_exhausted_total = 0

        self._merkle_last_diff_ms: Optional[float] = None
        self._merkle_file_count = 0
        self._merkle_version = 0
        self._merkle_last_scan_ts: Optional[float] = None

        self._initialized = True

    @classmethod
    def get_instance(cls) -> "AgentLoopTelemetryCollector":
        return cls()

    def record_interjection_queued(self, count: int = 1) -> None:
        with self._data_lock:
            self._current_queue_depth += count
            self._total_queued += count

    def record_interjection_drained(self, count: int) -> None:
        with self._data_lock:
            self._current_queue_depth = max(0, self._current_queue_depth - count)
            self._total_drained += count

    def record_active_brake(self, tool_name: str = "") -> None:
        with self._data_lock:
            self._active_brake_count += 1

    def record_model_retry(self, exhausted: bool = False) -> None:
        with self._data_lock:
            self._model_retries_total += 1
            if exhausted:
                self._model_exhausted_total += 1

    def record_turn_finished(
        self,
        status: str,
        inner_steps: int,
        terminated_early: bool = False,
    ) -> None:
        with self._data_lock:
            self._total_inner_steps += inner_steps
            self._last_turn_inner_steps = inner_steps
            if status == "completed":
                self._turns_completed += 1
            elif status == "aborted":
                self._turns_aborted += 1
            elif status == "failed":
                self._turns_failed += 1

            if terminated_early:
                self._active_brake_count += 1

    def record_merkle_diff(self, diff_ms: float, file_count: int, version: int) -> None:
        with self._data_lock:
            self._merkle_last_diff_ms = max(0.01, round(diff_ms, 3))
            self._merkle_file_count = file_count
            self._merkle_version = version
            self._merkle_last_scan_ts = time.time()

    def get_snapshot(self) -> AgentLoopTelemetrySnapshot:
        with self._data_lock:
            total_turns = self._turns_completed + self._turns_aborted + self._turns_failed
            recovery_rate = 100.0
            if self._model_retries_total > 0:
                recovered = self._model_retries_total - self._model_exhausted_total
                recovery_rate = round((recovered / self._model_retries_total) * 100.0, 1)

            lossless_rate = 100.0
            if self._total_queued > 0 and self._total_queued < self._total_drained:
                lossless_rate = round((self._total_drained / self._total_queued) * 100.0, 1)

            return AgentLoopTelemetrySnapshot(
                interjection_queue_depth=self._current_queue_depth,
                interjection_total_queued=self._total_queued,
                interjection_total_drained=self._total_drained,
                interjection_lossless_rate=lossless_rate,
                active_brake_count=self._active_brake_count,
                turns_completed=self._turns_completed,
                turns_aborted=self._turns_aborted,
                turns_failed=self._turns_failed,
                total_turns=total_turns,
                model_defense_retries_total=self._model_retries_total,
                model_defense_exhausted_total=self._model_exhausted_total,
                model_recovery_rate=recovery_rate,
                total_inner_steps=self._total_inner_steps,
                last_turn_inner_steps=self._last_turn_inner_steps,
                merkle_last_diff_ms=self._merkle_last_diff_ms,
                merkle_tree_file_count=self._merkle_file_count,
                merkle_version=self._merkle_version,
                merkle_last_scan_ts=self._merkle_last_scan_ts,
                timestamp=time.time(),
                status="healthy",
            )

    def simulate_probe(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute simulation probe for testing and UI live demonstration."""
        if action == "inject_interjection":
            count = kwargs.get("count", 1)
            self.record_interjection_queued(count)
            if kwargs.get("auto_drain", True):
                self.record_interjection_drained(count)
            return {"action": action, "injected_count": count, "success": True}

        elif action == "simulate_brake":
            tool_name = kwargs.get("tool_name", "multi_metric_gate")
            self.record_active_brake(tool_name)
            self.record_turn_finished("completed", inner_steps=kwargs.get("steps", 3), terminated_early=True)
            return {"action": action, "tool_name": tool_name, "terminated_early": True, "success": True}

        elif action == "probe_merkle":
            start = time.perf_counter()
            _ = [i * i for i in range(10000)]
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            version = self._merkle_version + 1
            file_count = kwargs.get("file_count", self._merkle_file_count + 1)
            self.record_merkle_diff(elapsed_ms, file_count, version)
            return {"action": action, "diff_ms": round(elapsed_ms, 3), "version": version, "file_count": file_count, "success": True}

        elif action == "simulate_retry":
            exhausted = kwargs.get("exhausted", False)
            self.record_model_retry(exhausted=exhausted)
            return {"action": action, "exhausted": exhausted, "success": True}

        return {"action": action, "error": f"Unknown action: {action}", "success": False}

    def reset(self) -> None:
        """Reset metrics for test isolation."""
        with self._data_lock:
            self._current_queue_depth = 0
            self._total_queued = 0
            self._total_drained = 0
            self._active_brake_count = 0
            self._turns_completed = 0
            self._turns_aborted = 0
            self._turns_failed = 0
            self._model_retries_total = 0
            self._model_exhausted_total = 0
            self._total_inner_steps = 0
            self._last_turn_inner_steps = 0
            self._merkle_last_diff_ms = None
            self._merkle_file_count = 0
            self._merkle_version = 0
            self._merkle_last_scan_ts = None


def get_agent_loop_telemetry_collector() -> AgentLoopTelemetryCollector:
    """Convenience getter for AgentLoopTelemetryCollector singleton."""
    return AgentLoopTelemetryCollector.get_instance()
