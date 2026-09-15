# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Failure Classification & Anti-Loop Barrier with Multi-Tenant Runtime Context.
(Card-Harness-DeepSeek-AgentScope-SpecDriven - v1.5.03)

Derived from AgentScope Java 2.0 & deepseek-harness:
1. Three-tier failure classification:
   - Transient: Network jitter / 429 rate limit -> exponential backoff retry.
   - Deterministic: 400 / 404 / schema error -> anti-loop barrier & reflection prompt.
   - Fatal: Sandbox escape / auth revocation / memory limit -> immediate halt.
2. Anti-loop barrier: Physically blocks identical failing tool calls from repeating endlessly.
3. MultiTenantRuntimeContext: Explicit enterprise multi-tenancy and role context.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class FailureCategory(str, Enum):
    """Categorization of tool or system failure."""
    TRANSIENT = "transient"
    DETERMINISTIC = "deterministic"
    FATAL = "fatal"


@dataclass(frozen=True)
class FailureFingerprint:
    """Unique signature of a failure occurrence."""
    tool_name: str
    normalized_args_hash: str
    error_type: str


@dataclass
class ClassificationDecision:
    """Decision produced by the failure classifier."""
    category: FailureCategory
    can_retry: bool
    backoff_sec: float
    reflection_prompt: Optional[str]
    reason: str


class FailureClassifier:
    """
    Guarantees Anti-Loop Barrier & Failure Classification.
    Prevents models from endlessly repeating failing tool calls with identical arguments.
    """

    TRANSIENT_KEYWORDS: tuple[str, ...] = (
        "timeout",
        "rate limit",
        "429",
        "503",
        "connection reset",
        "temporarily unavailable",
        "service unavailable",
    )

    FATAL_KEYWORDS: tuple[str, ...] = (
        "sandbox escape",
        "out of memory",
        "oom",
        "permission denied",
        "unauthorized",
        "auth revocation",
        "security violation",
    )

    def __init__(
        self,
        max_transient_retries: int = 3,
        base_backoff_sec: float = 0.1,
    ) -> None:
        self.max_transient_retries = max_transient_retries
        self.base_backoff_sec = base_backoff_sec
        self._failure_history: Dict[FailureFingerprint, int] = {}
        self._blocked_fingerprints: Set[FailureFingerprint] = set()

    def _hash_args(self, args: Any) -> str:
        """Create a deterministic hash from tool arguments."""
        try:
            serialized = json.dumps(args, sort_keys=True, default=str)
        except Exception:
            serialized = str(args)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    def classify_error(self, error: Exception | str) -> FailureCategory:
        """Classify an exception or error string into one of three categories."""
        err_msg = str(error).lower()
        err_type = type(error).__name__.lower() if isinstance(error, Exception) else ""

        for fatal_kw in self.FATAL_KEYWORDS:
            if fatal_kw in err_msg or fatal_kw in err_type:
                return FailureCategory.FATAL

        for trans_kw in self.TRANSIENT_KEYWORDS:
            if trans_kw in err_msg or trans_kw in err_type:
                return FailureCategory.TRANSIENT

        return FailureCategory.DETERMINISTIC

    def evaluate(
        self,
        tool_name: str,
        args: Any,
        error: Exception | str,
    ) -> ClassificationDecision:
        """
        Evaluate a failed tool execution and produce an actionable decision.
        Enforces the Anti-Loop Barrier when deterministic calls repeat.
        """
        args_hash = self._hash_args(args)
        err_type = type(error).__name__ if isinstance(error, Exception) else "Error"
        fingerprint = FailureFingerprint(
            tool_name=tool_name,
            normalized_args_hash=args_hash,
            error_type=err_type,
        )

        category = self.classify_error(error)
        attempt_count = self._failure_history.get(fingerprint, 0) + 1
        self._failure_history[fingerprint] = attempt_count

        if category == FailureCategory.FATAL:
            self._blocked_fingerprints.add(fingerprint)
            return ClassificationDecision(
                category=FailureCategory.FATAL,
                can_retry=False,
                backoff_sec=0.0,
                reflection_prompt=None,
                reason=f"Fatal error detected ({error}). Halting execution immediately.",
            )

        if category == FailureCategory.TRANSIENT:
            if attempt_count <= self.max_transient_retries:
                backoff = self.base_backoff_sec * (2 ** (attempt_count - 1))
                return ClassificationDecision(
                    category=FailureCategory.TRANSIENT,
                    can_retry=True,
                    backoff_sec=backoff,
                    reflection_prompt=None,
                    reason=f"Transient failure (attempt {attempt_count}/{self.max_transient_retries}). Retrying with backoff {backoff:.2f}s.",
                )
            else:
                self._blocked_fingerprints.add(fingerprint)
                return ClassificationDecision(
                    category=FailureCategory.TRANSIENT,
                    can_retry=False,
                    backoff_sec=0.0,
                    reflection_prompt=f"[Harness Guard] Tool '{tool_name}' exhausted all {self.max_transient_retries} transient retries.",
                    reason=f"Exhausted transient retries for tool {tool_name}.",
                )

        # Deterministic Failure: Enforce Anti-Loop Barrier!
        self._blocked_fingerprints.add(fingerprint)
        reflection = (
            f"[Anti-Loop Barrier] Tool '{tool_name}' failed deterministically with error: '{error}'. "
            f"Repeating the identical call is blocked. "
            f"Please diagnose the parameter requirements, adjust your inputs, or choose an alternative tool."
        )
        return ClassificationDecision(
            category=FailureCategory.DETERMINISTIC,
            can_retry=False,
            backoff_sec=0.0,
            reflection_prompt=reflection,
            reason=f"Deterministic failure detected. Anti-Loop Barrier engaged to block duplicate call.",
        )

    def is_blocked(self, tool_name: str, args: Any) -> bool:
        """Check if an exact tool call is actively blocked by the Anti-Loop Barrier."""
        args_hash = self._hash_args(args)
        for fp in self._blocked_fingerprints:
            if fp.tool_name == tool_name and fp.normalized_args_hash == args_hash:
                return True
        return False

    def reset(self) -> None:
        """Clear failure history and barrier state."""
        self._failure_history.clear()
        self._blocked_fingerprints.clear()


@dataclass
class MultiTenantRuntimeContext:
    """Explicit multi-tenant runtime context for enterprise isolation."""
    tenant_id: str = "default"
    user_id: str = "default"
    session_id: str = "default"
    roles: List[str] = field(default_factory=lambda: ["user"])
    attributes: Dict[str, Any] = field(default_factory=dict)
    is_admin: bool = False

    def has_role(self, role: str) -> bool:
        """Check if user or tenant holds specified role."""
        if self.is_admin:
            return True
        return role in self.roles

    def get_attr(self, key: str, default: Any = None) -> Any:
        """Retrieve contextual attribute safely."""
        return self.attributes.get(key, default)
