# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Defensive Code Annotation & Telemetry Registry (Card-Harness-DefensiveAndPurge).

Provides explicit `@defensive` decorator and runtime telemetry to safeguard critical
defensive fallbacks (FRP reconnect, SQLite retry, gatekeeper fail-open, timeout recovery)
while exposing observability into whether defensive mechanisms are active or dormant.
"""

import asyncio
import functools
import inspect
import logging
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

logger = logging.getLogger("openviking.defensive")


@dataclass
class DefensiveRecord:
    domain: str
    name: str
    func_name: str
    module: str
    doc: str = ""
    executions: int = 0
    fallbacks: int = 0
    last_trigger_ts: float = 0.0
    last_error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DefensiveTriggerEvent:
    domain: str
    name: str
    exception_type: str
    error_message: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DefensiveRegistry:
    """Thread-safe registry of all explicit defensive mechanisms in OpenViking."""

    _instance: Optional["DefensiveRegistry"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._records: Dict[str, DefensiveRecord] = {}
        self._recent_triggers: deque[DefensiveTriggerEvent] = deque(maxlen=100)
        self._state_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "DefensiveRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def register(
        self,
        domain: str,
        name: str,
        func: Callable,
    ) -> str:
        key = f"{domain}:{name}"
        with self._state_lock:
            if key not in self._records:
                self._records[key] = DefensiveRecord(
                    domain=domain,
                    name=name,
                    func_name=getattr(func, "__name__", str(func)),
                    module=getattr(func, "__module__", ""),
                    doc=(inspect.getdoc(func) or "")[:150],
                )
        return key

    def record_execution(self, key: str) -> None:
        with self._state_lock:
            rec = self._records.get(key)
            if rec:
                rec.executions += 1

    def record_fallback(self, key: str, exc: Exception) -> None:
        with self._state_lock:
            rec = self._records.get(key)
            err_msg = f"{type(exc).__name__}: {str(exc)}"
            ts = time.time()
            if rec:
                rec.fallbacks += 1
                rec.last_trigger_ts = ts
                rec.last_error = err_msg
            domain, name = key.split(":", 1) if ":" in key else ("general", key)
            self._recent_triggers.append(
                DefensiveTriggerEvent(
                    domain=domain,
                    name=name,
                    exception_type=type(exc).__name__,
                    error_message=err_msg[:250],
                    timestamp=ts,
                )
            )

    def get_telemetry(self) -> Dict[str, Any]:
        with self._state_lock:
            total_execs = sum(r.executions for r in self._records.values())
            total_fallbacks = sum(r.fallbacks for r in self._records.values())
            fallback_rate = (
                round(total_fallbacks / total_execs, 4) if total_execs > 0 else 0.0
            )
            return {
                "total_registered": len(self._records),
                "total_executions": total_execs,
                "total_fallbacks": total_fallbacks,
                "overall_fallback_rate": fallback_rate,
                "sites": [r.to_dict() for r in self._records.values()],
                "recent_triggers": [t.to_dict() for t in list(self._recent_triggers)[-20:]],
            }

    def reset_for_testing(self) -> None:
        with self._state_lock:
            for rec in self._records.values():
                rec.executions = 0
                rec.fallbacks = 0
                rec.last_trigger_ts = 0.0
                rec.last_error = ""
            self._recent_triggers.clear()


def defensive(
    domain: str = "general",
    name: str = "",
    fallback: Any = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    retry_count: int = 0,
    retry_backoff: float = 0.05,
    log_level: str = "warning",
) -> Callable:
    """Decorator explicitly annotating intentional defensive safety nets.

    Args:
        domain: Functional domain (e.g. 'gatekeeper', 'sqlite', 'frp', 'gpu', 'memory')
        name: Name of defensive safeguard
        fallback: Value or callable to return when all retries are exhausted
        exceptions: Tuple of exceptions to intercept
        retry_count: Number of retries before falling back
        retry_backoff: Exponential backoff factor in seconds
        log_level: Logging level ('debug', 'info', 'warning', 'error')
    """

    def decorator(fn: Callable) -> Callable:
        safeguard_name = name or fn.__name__
        registry = DefensiveRegistry.get_instance()
        key = registry.register(domain, safeguard_name, fn)

        def _resolve_fallback(exc: Exception) -> Any:
            registry.record_fallback(key, exc)
            log_fn = getattr(logger, log_level.lower(), logger.warning)
            log_fn(
                "[DEFENSIVE:%s:%s] Safeguard triggered on %s: %s, executing fallback.",
                domain,
                safeguard_name,
                type(exc).__name__,
                exc,
            )
            if callable(fallback) and not isinstance(fallback, (type, type(None))):
                try:
                    return fallback()
                except Exception:
                    pass
            return fallback

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                if key not in registry._records:
                    registry.register(domain, safeguard_name, fn)
                registry.record_execution(key)
                attempts = 0
                while True:
                    try:
                        return await fn(*args, **kwargs)
                    except exceptions as exc:
                        attempts += 1
                        if attempts <= retry_count:
                            await asyncio.sleep(retry_backoff * (2 ** (attempts - 1)))
                            continue
                        return _resolve_fallback(exc)

            return async_wrapper

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if key not in registry._records:
                registry.register(domain, safeguard_name, fn)
            registry.record_execution(key)
            attempts = 0
            while True:
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    attempts += 1
                    if attempts <= retry_count:
                        time.sleep(retry_backoff * (2 ** (attempts - 1)))
                        continue
                    return _resolve_fallback(exc)

        return sync_wrapper

    return decorator


def get_defensive_telemetry() -> Dict[str, Any]:
    """Retrieve full defensive telemetry snapshot for monitoring and Studio UI."""
    return DefensiveRegistry.get_instance().get_telemetry()
