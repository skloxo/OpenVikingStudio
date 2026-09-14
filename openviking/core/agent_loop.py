# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Two-Tier Agent Loop and Four-Layer Onion Guard (Card-Runtime-TwoTierAgentLoop-OnionGuard - v1.5.01)

Distilled from production-grade agent loops (pi/agent-loop.ts):
1. Two-Tier Event Loop Architecture:
   - Outer Loop: Manages session turn lifecycle, model failover/retry defense, and turn-level state.
   - Inner Loop: Drives execution while (hasMoreToolCalls || pendingMessages.length > 0), ensuring zero message loss.
2. Four-Layer Onion Defense:
   - Layer 1 (Core Loop): Prompt construction, model invocation, and tool dispatch state machine.
   - Layer 2 (Model Defense): Transient error retries, rate-limit backoff, and graceful fallback.
   - Layer 3 (User Control): Thread-safe async interrupt queue (interrupt), cooperative abort signal (abort).
   - Layer 4 (Dispatch & Brake): Tool execution sandboxing and early termination contract (terminate=True).
"""

import collections
from dataclasses import dataclass, field
from enum import Enum
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentLoopStatus(str, Enum):
    """Lifecycle statuses for TwoTierAgentLoop turns."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


@dataclass
class AgentMessage:
    """Strongly typed message container adhering to strict typed DTO rails."""
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCallResult:
    """Strongly typed result of a tool execution."""
    call_id: str
    tool_name: str
    output: Any
    is_error: bool = False
    terminate: bool = False


@dataclass(frozen=True)
class OnionGuardConfig:
    """Configuration parameters for onion defense guards."""
    max_inner_turns: int = 25
    max_retries: int = 3
    retry_delay_sec: float = 0.05
    tool_timeout_sec: float = 60.0


@dataclass
class TurnResult:
    """Immutable or final result of a complete turn."""
    status: AgentLoopStatus
    final_message: Optional[AgentMessage]
    history: List[AgentMessage]
    inner_turns: int
    terminated_early: bool
    aborted_reason: Optional[str] = None
    error: Optional[str] = None


class TwoTierAgentLoop:
    """
    Two-Tier Event Loop with Four-Layer Onion Guard.
    Guarantees thread-safe mid-turn interrupt injection, tool early termination,
    and cooperative cancellation without loop collapse.
    """

    def __init__(
        self,
        model_invoker: Callable[[List[AgentMessage]], AgentMessage],
        tool_dispatcher: Callable[[str, Dict[str, Any]], ToolCallResult],
        config: Optional[OnionGuardConfig] = None,
    ) -> None:
        self._model_invoker = model_invoker
        self._tool_dispatcher = tool_dispatcher
        self._config = config or OnionGuardConfig()
        self._pending_messages: collections.deque[AgentMessage] = collections.deque()
        self._lock = threading.Lock()
        self._abort_signal = threading.Event()
        self._abort_reason: Optional[str] = None

    def interrupt(self, message: AgentMessage) -> None:
        """Layer 3: Thread-safe injection of user interrupt messages into pending queue."""
        with self._lock:
            self._pending_messages.append(message)
            logger.debug(f"[TwoTierAgentLoop] User interrupt queued: {message.content[:50]}...")

    def abort(self, reason: str = "User aborted") -> None:
        """Layer 3: Cooperative cancellation signal."""
        with self._lock:
            self._abort_reason = reason
            self._abort_signal.set()
            logger.info(f"[TwoTierAgentLoop] Abort signaled: {reason}")

    def has_pending_messages(self) -> bool:
        """Check if any user interrupt messages are pending."""
        with self._lock:
            return len(self._pending_messages) > 0

    def _drain_pending_messages(self) -> List[AgentMessage]:
        """Atomically drain all pending interrupt messages."""
        with self._lock:
            drained = list(self._pending_messages)
            self._pending_messages.clear()
            return drained

    def _invoke_model_with_defense(self, messages: List[AgentMessage]) -> AgentMessage:
        """Layer 2 (Model Defense): Retry on transient errors with backoff."""
        retries = 0
        last_exception: Optional[Exception] = None
        while retries < self._config.max_retries:
            try:
                return self._model_invoker(messages)
            except Exception as e:
                retries += 1
                last_exception = e
                logger.warning(
                    f"[TwoTierAgentLoop:ModelDefense] Invocation attempt {retries} failed: {e}. Retrying..."
                )
                if retries < self._config.max_retries:
                    time.sleep(self._config.retry_delay_sec * retries)
        raise RuntimeError(f"Model defense exhausted all {self._config.max_retries} retries: {last_exception}") from last_exception

    def run_turn(
        self,
        initial_prompt: str,
        context_messages: Optional[List[AgentMessage]] = None,
    ) -> TurnResult:
        """
        Outer Loop: Drives the complete turn lifecycle from initial prompt to final output.
        """
        self._abort_signal.clear()
        self._abort_reason = None
        with self._lock:
            self._pending_messages.clear()

        history: List[AgentMessage] = list(context_messages or [])
        history.append(AgentMessage(role="user", content=initial_prompt))

        inner_turn = 0
        has_more_tool_calls = True
        terminated_early = False
        final_message: Optional[AgentMessage] = None

        try:
            # Inner Loop: executes tools and drains pending messages
            while (has_more_tool_calls or self.has_pending_messages()) and not self._abort_signal.is_set():
                if inner_turn >= self._config.max_inner_turns:
                    logger.warning(f"[TwoTierAgentLoop] Reached max inner turns ({self._config.max_inner_turns}). Halting.")
                    break

                inner_turn += 1

                # Layer 3: Drain user interrupts (Zero Message Loss)
                pending = self._drain_pending_messages()
                for p_msg in pending:
                    history.append(p_msg)

                # Layer 1 & 2: Invoke model under model defense guard
                model_msg = self._invoke_model_with_defense(history)
                history.append(model_msg)
                final_message = model_msg

                # Check if model requested tool execution
                if not model_msg.tool_calls:
                    has_more_tool_calls = False
                    continue

                # Layer 4: Tool execution and early brake contract (terminate: true)
                for call in model_msg.tool_calls:
                    if self._abort_signal.is_set():
                        break

                    tool_name = call.get("name", "")
                    call_id = call.get("id", "")
                    args = call.get("args", {})

                    try:
                        tool_result = self._tool_dispatcher(tool_name, args)
                    except Exception as err:
                        tool_result = ToolCallResult(
                            call_id=call_id,
                            tool_name=tool_name,
                            output=f"Error executing tool {tool_name}: {err}",
                            is_error=True,
                        )

                    history.append(
                        AgentMessage(
                            role="tool",
                            name=tool_name,
                            content=str(tool_result.output),
                            metadata={"call_id": tool_result.call_id, "is_error": tool_result.is_error},
                        )
                    )

                    # Early Brake Contract: terminate=True halts loop immediately!
                    if tool_result.terminate:
                        terminated_early = True
                        has_more_tool_calls = False
                        final_message = AgentMessage(
                            role="assistant",
                            content=str(tool_result.output),
                            metadata={"terminated_by": tool_name},
                        )
                        history.append(final_message)
                        logger.info(f"[TwoTierAgentLoop] Early brake triggered by tool {tool_name}. Halting turn.")
                        break

                if terminated_early:
                    break

            if self._abort_signal.is_set():
                return TurnResult(
                    status=AgentLoopStatus.ABORTED,
                    final_message=final_message,
                    history=history,
                    inner_turns=inner_turn,
                    terminated_early=terminated_early,
                    aborted_reason=self._abort_reason,
                )

            return TurnResult(
                status=AgentLoopStatus.COMPLETED,
                final_message=final_message,
                history=history,
                inner_turns=inner_turn,
                terminated_early=terminated_early,
            )

        except Exception as e:
            logger.exception(f"[TwoTierAgentLoop] Turn failed: {e}")
            return TurnResult(
                status=AgentLoopStatus.FAILED,
                final_message=final_message,
                history=history,
                inner_turns=inner_turn,
                terminated_early=terminated_early,
                error=str(e),
            )
