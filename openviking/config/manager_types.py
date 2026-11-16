# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Runtime config manager: merge, publish, invalidation.

The manager owns everything that is storage-independent: three-state PATCH
merge, per-scope copy-on-write publish, old/new diff, and consumer notification.
It depends only on the :class:`ConfigSource` abstraction and never imports a
concrete source implementation.

Two scopes are managed side by side, mirroring the two independent config models
(the cluster ``OpenVikingConfig`` and the per-account ``AccountConfig``):

- **cluster** — a single process-wide config object, bridged through the
  ``get_config`` / ``set_config`` / ``build_config`` hooks so the manager stays
  agnostic to the concrete cluster model.
- **account** — a per-account cache of the constructed Account configuration
  and its last-access time. Account and Cluster configurations remain distinct.
  ``get_account(account_id, field)`` returns the Account value, except for the
  deprecated whole-section fallback retained for existing fields.

Both models are built and validated by caller-supplied hooks, so the manager
imports neither ``OpenVikingConfig`` nor ``AccountConfig`` directly.
"""

from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import Future as ConcurrentFuture
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, Generic, Iterable, Optional, TypeVar

from openviking.config.merge import apply_three_state_patch, diff_sections
from openviking.config.scope import ConfigScope, ScopeKind
from openviking.config.source.base import ConfigSource
from openviking.service.task_tracker_concurrency import KeyedAsyncLockPool, run_to_completion
from openviking_cli.utils.config.runtime_field import fallback_of, resolve_fallback
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

# C = cluster config type; A = per-account config type.
C = TypeVar("C")
A = TypeVar("A")
T = TypeVar("T")
_NO_OLD_SETTINGS = object()


@dataclass(frozen=True)
class AccountConfigView(Generic[C, A]):
    """Expose one atomically captured Account/Cluster publication pair.

    Used only by synchronous selectors, never as a request context. Returned
    models are shared, read-only configuration values. Business resolvers should
    combine them explicitly instead of adding generic framework fallback rules.
    """

    _account: A
    _cluster: C

    @property
    def account(self) -> A:
        """Return the captured Account configuration."""
        return self._account

    @property
    def cluster(self) -> C:
        """Return the captured cluster configuration."""
        return self._cluster

    def get(self, field: str) -> Any:
        """Return an Account field with legacy whole-section fallback.

        This compatibility API never merges nested values. New business
        resolvers should read ``account`` and ``cluster`` explicitly.
        """
        fields = getattr(type(self._account), "model_fields", {})
        if field not in fields:
            raise AttributeError(field)
        value = getattr(self._account, field)
        if value is not None:
            return value
        target = fallback_of(fields[field])
        return resolve_fallback(self._cluster, target) if target is not None else None


@dataclass(frozen=True)
class AccountCandidateContext(Generic[C, A]):
    """Read-only inputs for synchronous, side-effect-free domain validation.

    ``old_view`` is supplied only for an update PATCH, built from the latest
    document passed to the source's mutation callback (including absent settings
    on an existing Account). Both views share one captured Cluster publication.
    Creation, initial loading and refresh validate only the candidate; loading a
    persisted document is not a local update request. ``changed_sections`` names
    PATCH keys, or is ``None`` when all validators must run.
    """

    new_view: AccountConfigView[C, A]
    old_view: Optional[AccountConfigView[C, A]]
    changed_sections: Optional[frozenset[str]]
    creating: bool


@dataclass(frozen=True)
class AccountCandidateValidator(Generic[C, A]):
    """Validate every candidate; sections describe the domain's dependencies.

    Validators may use context.changed_sections to scope PATCH transition
    rules, but must always validate the complete candidate's effective values.
    """

    sections: frozenset[str]
    validate: Callable[[AccountCandidateContext[C, A]], None]


REFRESH_INTERVAL_SECS = 30.0
# Accounts unused for this long are evicted and stop being polled.
ACCOUNT_IDLE_TTL_SECS = 24 * 60 * 60.0


@dataclass(frozen=True)
class ConfigChangeEvent:
    """Emitted after a new config is published.

    ``scope`` names the changed persisted settings document (cluster-wide or
    one account).
    ``old_config`` / ``new_config`` are the objects for that scope (the cluster
    config, or that account's :class:`AccountConfig`; ``None`` when the account
    scope was cleared or evicted). ``reason`` distinguishes ordinary config
    publication from manager-owned account lifecycle events.
    """

    scope: ConfigScope
    changed_sections: frozenset[str]
    old_config: Any
    new_config: Any
    reason: "ConfigChangeReason"


class ConfigChangeReason(str, Enum):
    UPDATE = "update"
    EVICT = "evict"


ConfigChangeConsumer = Callable[[ConfigChangeEvent], Awaitable[None]]


@dataclass(frozen=True)
class _ConsumerRegistration:
    scope: ScopeKind
    sections: frozenset[str]
    consumer: ConfigChangeConsumer


@dataclass
class _AccountEntry(Generic[A]):
    """One account's cached state protected by the publication lock.

    ``config`` is the constructed, already-validated account model;
    ``last_access`` drives idle eviction.
    """

    config: A
    last_access: float


@dataclass(frozen=True)
class _PreparedPatch:
    """Candidate and persisted document prepared for one scope mutation."""

    persisted_settings: dict
    candidate: Any


@dataclass(frozen=True)
class _PendingNotification:
    """One notification ordered after the previous event for its scope."""

    event: ConfigChangeEvent
    predecessor: Optional[ConcurrentFuture[None]]
    completion: ConcurrentFuture[None]

