# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Hook Aspect System (Card-Harness-ReadWriteOffload-HookGuard - v1.5.05)

Decouples cross-cutting concerns (logging, sandboxing, offload, permission checks)
from core inference and agent loops.
Provides pre-tool and post-tool interceptor chains with strict typed DTOs.
"""

from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AspectDecisionType(str, Enum):
    """Outcome of a pre-tool aspect inspection."""
    ALLOW = "allow"
    BLOCK = "block"
    REWRITE = "rewrite"


@dataclass
class AspectContext:
    """Runtime metadata passed across hook aspects."""
    session_id: str = "default"
    peer_id: str = "default"
    turn_id: int = 0
    phase: str = "execution"
    auth_tokens: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AspectDecision:
    """Decision returned by before_tool_call interceptors."""
    decision: AspectDecisionType = AspectDecisionType.ALLOW
    modified_args: Optional[Dict[str, Any]] = None
    override_output: Optional[Any] = None
    block_reason: Optional[str] = None
    terminate_turn: bool = False

    @classmethod
    def allow(cls, modified_args: Optional[Dict[str, Any]] = None) -> "AspectDecision":
        if modified_args is not None:
            return cls(decision=AspectDecisionType.REWRITE, modified_args=modified_args)
        return cls(decision=AspectDecisionType.ALLOW)

    @classmethod
    def block(cls, reason: str, override_output: Optional[Any] = None, terminate: bool = False) -> "AspectDecision":
        return cls(
            decision=AspectDecisionType.BLOCK,
            override_output=override_output or f"Blocked by guard: {reason}",
            block_reason=reason,
            terminate_turn=terminate,
        )


class HookAspect:
    """Base interface for all decoupled hook aspects."""

    name: str = "base_aspect"
    priority: int = 100  # Lower number executes first

    def before_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        ctx: AspectContext,
    ) -> AspectDecision:
        """Invoked before tool dispatch. Can allow, rewrite args, or block execution."""
        return AspectDecision.allow()

    def after_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        output: Any,
        ctx: AspectContext,
    ) -> Any:
        """Invoked after tool dispatch. Can mutate, redact, or wrap outputs."""
        return output


class HookAspectRegistry:
    """
    Priority-ordered registry managing active hook aspects.
    Executes pre-tool aspects in priority order (stopping immediately on BLOCK)
    and post-tool aspects in reverse priority order.
    """

    def __init__(self, aspects: Optional[List[HookAspect]] = None) -> None:
        self._aspects: List[HookAspect] = []
        if aspects:
            for aspect in aspects:
                self.register(aspect)

    def register(self, aspect: HookAspect) -> None:
        """Register an aspect and keep registry sorted by priority ascending."""
        self._aspects.append(aspect)
        self._aspects.sort(key=lambda a: a.priority)
        logger.debug(f"[HookAspectRegistry] Registered aspect '{aspect.name}' (priority={aspect.priority})")

    def unregister(self, name: str) -> bool:
        """Unregister an aspect by name."""
        initial_len = len(self._aspects)
        self._aspects = [a for a in self._aspects if a.name != name]
        return len(self._aspects) < initial_len

    @property
    def aspects(self) -> List[HookAspect]:
        return list(self._aspects)

    def execute_before_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        ctx: AspectContext,
    ) -> AspectDecision:
        """Run all registered before_tool_call aspects in order."""
        current_args = dict(args)
        for aspect in self._aspects:
            try:
                decision = aspect.before_tool_call(tool_name, current_args, ctx)
                if decision.decision == AspectDecisionType.BLOCK:
                    logger.warning(
                        f"[HookAspectRegistry] Aspect '{aspect.name}' blocked tool '{tool_name}': {decision.block_reason}"
                    )
                    return decision
                elif decision.decision == AspectDecisionType.REWRITE and decision.modified_args:
                    current_args = decision.modified_args
            except Exception as e:
                logger.exception(f"[HookAspectRegistry] Aspect '{aspect.name}' before_tool_call crashed: {e}")
                return AspectDecision.block(f"Aspect crash in {aspect.name}: {e}")

        if current_args != args:
            return AspectDecision.allow(modified_args=current_args)
        return AspectDecision.allow()

    def execute_after_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        output: Any,
        ctx: AspectContext,
    ) -> Any:
        """Run all registered after_tool_call aspects in reverse order."""
        current_output = output
        for aspect in reversed(self._aspects):
            try:
                current_output = aspect.after_tool_call(tool_name, args, current_output, ctx)
            except Exception as e:
                logger.exception(f"[HookAspectRegistry] Aspect '{aspect.name}' after_tool_call crashed: {e}")
        return current_output
