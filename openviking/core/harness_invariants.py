# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Harness Four Invariants: Terminability, Recoverability, Observability, and Telemetry.
(Card-Harness-DeepSeek-AgentScope-SpecDriven - v1.5.03)

Enterprise harness invariants derived from deepseek-harness & AgentScope Java 2.0:
1. Terminability: Wall-clock time, token count, cost, and tool call budget enforcement.
2. Recoverability: Lightweight checkpoints for state machine snapshotting & rollbacks.
3. Observability: White-box execution traces, defensive events, and invariant telemetry.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional
import uuid


class BudgetExceededError(RuntimeError):
    """Raised when an execution budget limit is exceeded."""
    pass


@dataclass(frozen=True)
class ExecutionBudget:
    """Immutable budget constraints for agent turns and workflows."""
    max_wall_time_sec: float = 120.0
    max_total_tokens: int = 100_000
    max_cost_usd: float = 1.00
    max_tool_invocations: int = 50


@dataclass
class BudgetSnapshot:
    """Current consumption state against allocated budget."""
    elapsed_time_sec: float
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    tool_invocations: int
    is_exhausted: bool
    exhaustion_reason: Optional[str] = None


class BudgetEnforcer:
    """
    Guarantees Terminability invariant.
    Tracks wall-clock time, token usage, cost, and tool calls.
    Raises BudgetExceededError when limits are breached.
    """

    def __init__(self, budget: Optional[ExecutionBudget] = None) -> None:
        self._budget = budget or ExecutionBudget()
        self._start_time: float = time.monotonic()
        self._prompt_tokens: int = 0
        self._completion_tokens: int = 0
        self._cost_usd: float = 0.0
        self._tool_invocations: int = 0

    @property
    def budget(self) -> ExecutionBudget:
        return self._budget

    def start(self) -> None:
        """Reset the start timer."""
        self._start_time = time.monotonic()

    def record_tokens(self, prompt_tokens: int = 0, completion_tokens: int = 0, cost_usd: float = 0.0) -> None:
        """Record model token and cost consumption."""
        self._prompt_tokens += max(0, prompt_tokens)
        self._completion_tokens += max(0, completion_tokens)
        self._cost_usd += max(0.0, cost_usd)

    def record_tool_invocation(self, count: int = 1) -> None:
        """Record one or more tool executions."""
        self._tool_invocations += max(0, count)

    def check_budget(self) -> None:
        """
        Verify budget bounds. Raises BudgetExceededError if any constraint is violated.
        """
        snapshot = self.get_snapshot()
        if snapshot.is_exhausted:
            raise BudgetExceededError(snapshot.exhaustion_reason)

    def get_snapshot(self) -> BudgetSnapshot:
        """Generate current budget utilization snapshot."""
        elapsed = time.monotonic() - self._start_time
        total_tokens = self._prompt_tokens + self._completion_tokens
        exhaustion_reason: Optional[str] = None

        if elapsed > self._budget.max_wall_time_sec:
            exhaustion_reason = (
                f"Wall-clock timeout exceeded: {elapsed:.2f}s > {self._budget.max_wall_time_sec}s"
            )
        elif total_tokens > self._budget.max_total_tokens:
            exhaustion_reason = (
                f"Token budget exceeded: {total_tokens} > {self._budget.max_total_tokens}"
            )
        elif self._cost_usd > self._budget.max_cost_usd:
            exhaustion_reason = (
                f"Cost budget exceeded: ${self._cost_usd:.4f} > ${self._budget.max_cost_usd:.4f}"
            )
        elif self._tool_invocations > self._budget.max_tool_invocations:
            exhaustion_reason = (
                f"Tool invocation budget exceeded: {self._tool_invocations} > {self._budget.max_tool_invocations}"
            )

        return BudgetSnapshot(
            elapsed_time_sec=elapsed,
            total_tokens=total_tokens,
            prompt_tokens=self._prompt_tokens,
            completion_tokens=self._completion_tokens,
            cost_usd=self._cost_usd,
            tool_invocations=self._tool_invocations,
            is_exhausted=exhaustion_reason is not None,
            exhaustion_reason=exhaustion_reason,
        )


@dataclass
class Checkpoint:
    """Point-in-time snapshot of session execution state for Recoverability."""
    checkpoint_id: str
    session_id: str
    turn_index: int
    state_data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    description: str = ""


class CheckpointRegistry:
    """
    Guarantees Recoverability invariant.
    Maintains ordered checkpoint history for session rollback & resume.
    """

    def __init__(self) -> None:
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._session_index: Dict[str, List[str]] = {}

    def save(
        self,
        session_id: str,
        turn_index: int,
        state_data: Dict[str, Any],
        description: str = "",
    ) -> Checkpoint:
        """Create and register a new checkpoint."""
        cp_id = f"cp_{uuid.uuid4().hex[:12]}"
        cp = Checkpoint(
            checkpoint_id=cp_id,
            session_id=session_id,
            turn_index=turn_index,
            state_data=dict(state_data),
            description=description,
        )
        self._checkpoints[cp_id] = cp
        if session_id not in self._session_index:
            self._session_index[session_id] = []
        self._session_index[session_id].append(cp_id)
        return cp

    def get(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Retrieve a checkpoint by unique identifier."""
        return self._checkpoints.get(checkpoint_id)

    def list_by_session(self, session_id: str) -> List[Checkpoint]:
        """List all checkpoints belonging to a session in chronological order."""
        cp_ids = self._session_index.get(session_id, [])
        return [self._checkpoints[cid] for cid in cp_ids if cid in self._checkpoints]

    def latest(self, session_id: str) -> Optional[Checkpoint]:
        """Retrieve the latest checkpoint for a session."""
        cps = self.list_by_session(session_id)
        return cps[-1] if cps else None

    def restore(self, checkpoint_id: str) -> Dict[str, Any]:
        """Restore session state data from a checkpoint."""
        cp = self.get(checkpoint_id)
        if not cp:
            raise KeyError(f"Checkpoint not found: {checkpoint_id}")
        return dict(cp.state_data)

    def prune(self, session_id: str, keep_latest: int = 5) -> int:
        """Prune older checkpoints, retaining only the latest N checkpoints."""
        cp_ids = self._session_index.get(session_id, [])
        if len(cp_ids) <= keep_latest:
            return 0
        to_prune = cp_ids[:-keep_latest]
        self._session_index[session_id] = cp_ids[-keep_latest:]
        pruned_count = 0
        for cid in to_prune:
            if cid in self._checkpoints:
                del self._checkpoints[cid]
                pruned_count += 1
        return pruned_count


@dataclass
class TraceEvent:
    """Granular execution event for Harness Observability."""
    event_type: str
    timestamp: float
    payload: Dict[str, Any] = field(default_factory=dict)


class HarnessTrace:
    """
    Guarantees Observability invariant.
    Captures execution events, milestones, and telemetry metrics in a structured timeline.
    """

    def __init__(self, session_id: str, trace_id: Optional[str] = None) -> None:
        self.trace_id: str = trace_id or f"tr_{uuid.uuid4().hex[:12]}"
        self.session_id: str = session_id
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.status: str = "running"
        self._events: List[TraceEvent] = []
        self._metrics: Dict[str, Any] = {}

    @property
    def events(self) -> List[TraceEvent]:
        return list(self._events)

    @property
    def metrics(self) -> Dict[str, Any]:
        return dict(self._metrics)

    def record_event(self, event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Record an execution milestone or lifecycle event."""
        self._events.append(
            TraceEvent(
                event_type=event_type,
                timestamp=time.time(),
                payload=dict(payload or {}),
            )
        )

    def set_metric(self, key: str, value: Any) -> None:
        """Set a telemetry metric value."""
        self._metrics[key] = value

    def finish(self, status: str = "completed") -> None:
        """Mark trace completed and record duration."""
        self.end_time = time.time()
        self.status = status
        self.record_event("trace_finish", {"duration_sec": self.end_time - self.start_time, "status": status})


class InvariantTelemetry:
    """Aggregate telemetry counters and gauges across all four harness invariants."""

    def __init__(self) -> None:
        self.total_budget_checks: int = 0
        self.total_budget_exceeded: int = 0
        self.total_checkpoints_saved: int = 0
        self.total_checkpoints_restored: int = 0
        self.total_traces_recorded: int = 0

    def record_budget_check(self, exceeded: bool = False) -> None:
        self.total_budget_checks += 1
        if exceeded:
            self.total_budget_exceeded += 1

    def record_checkpoint_saved(self) -> None:
        self.total_checkpoints_saved += 1

    def record_checkpoint_restored(self) -> None:
        self.total_checkpoints_restored += 1

    def record_trace_completed(self) -> None:
        self.total_traces_recorded += 1
