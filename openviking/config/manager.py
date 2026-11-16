# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Runtime config manager: merge, publish, invalidation."""

from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import Future as ConcurrentFuture
from typing import Any, Callable, Generic, Iterable, Optional

from openviking.config.manager_refresh import _RuntimeConfigRefreshMixin
from openviking.config.manager_types import (
    _NO_OLD_SETTINGS,
    ACCOUNT_IDLE_TTL_SECS,
    REFRESH_INTERVAL_SECS,
    A,
    AccountCandidateContext,
    AccountCandidateValidator,
    AccountConfigView,
    C,
    ConfigChangeConsumer,
    ConfigChangeEvent,
    ConfigChangeReason,
    T,
    _AccountEntry,
    _ConsumerRegistration,
    _PendingNotification,
    _PreparedPatch,
)
from openviking.config.merge import apply_three_state_patch, diff_sections
from openviking.config.scope import ConfigScope, ScopeKind
from openviking.config.source.base import ConfigSource
from openviking.service.task_tracker_concurrency import KeyedAsyncLockPool, run_to_completion
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

class RuntimeConfigManager(_RuntimeConfigRefreshMixin, Generic[C, A]):
    """Coordinate scoped config patching/publication over a :class:`ConfigSource`.

    ``base_config`` is the caller-owned immutable startup baseline.
    ``get_config`` / ``set_config`` bridge to the process-wide cluster singleton;
    ``build_config`` rebuilds the cluster model from the baseline plus a complete
    Cluster settings document; ``build_account`` constructs an Account model from
    its own settings document. Supplying these as hooks keeps the manager free of
    concrete config-model imports and business-specific defaulting rules.
    """

    def __init__(
        self,
        source: ConfigSource,
        *,
        base_config: C,
        get_config: Callable[[], C],
        set_config: Callable[[C], None],
        build_config: Callable[[C, dict], C],
        build_account: Callable[[Optional[dict]], A],
        validate_request: Optional[Callable[[dict, bool, bool], None]] = None,
        account_candidate_validators: Iterable[AccountCandidateValidator[C, A]] = (),
    ) -> None:
        self._source = source
        # Immutable startup baseline. Cluster overrides are always rebuilt from
        # this object, never from the previously published effective config.
        self._base_config = base_config
        self._get_config = get_config
        self._set_config = set_config
        # build_config(old_cluster, cluster_override) -> new validated cluster config.
        self._build_config = build_config
        # build_account(account_settings) -> validated Account configuration.
        # Account/Cluster composition belongs to business resolvers. Existing
        # RuntimeField fallback remains a whole-section compatibility read only.
        self._build_account = build_account
        # validate_request(patch, is_account_scope, creating) -> None (structural gate).
        self._validate_request = validate_request
        # Domain validators run before persistence and never mutate publications.
        self._account_candidate_validators = tuple(account_candidate_validators)
        # Per-account cache; publication_lock protects cross-loop snapshots.
        self._accounts: dict[str, _AccountEntry[A]] = {}
        self._persisted_settings: dict[ConfigScope, Optional[dict]] = {}
        self._consumers: list[_ConsumerRegistration] = []
        # Per-scope local locks serialize same-node concurrent PATCHes so two
        # requests mutating the same scope can't interleave read-merge-write.
        self._scope_locks = KeyedAsyncLockPool[tuple]()
        self._publication_lock = threading.RLock()
        self._notification_tails: dict[ConfigScope, ConcurrentFuture[None]] = {}
        self._refresh_task_lock = threading.Lock()
        self._refresh_task: Optional[asyncio.Task] = None
        self._refresh_task_loop: Optional[asyncio.AbstractEventLoop] = None

    # -- consumers ------------------------------------------------------------

    def add_update_consumer(
        self,
        *,
        scope: ScopeKind,
        sections: set[str] | frozenset[str],
        consumer: ConfigChangeConsumer,
    ) -> None:
        """Register a consumer for one scope kind and one or more sections."""
        if not sections:
            raise ValueError("config consumer must register at least one section")
        self._consumers.append(
            _ConsumerRegistration(
                scope=scope,
                sections=frozenset(sections),
                consumer=consumer,
            )
        )

    # -- cluster loading -----------------------------------------------------

    async def initialize(self) -> None:
        """Load cluster defaults before serving requests."""
        await self._refresh_scope(ConfigScope.cluster(), reason=ConfigChangeReason.UPDATE)

    async def replace_base_config(self, base_config: C) -> ConfigChangeEvent:
        """Replace the startup baseline without persisting runtime settings."""
        return await run_to_completion(lambda: self._replace_base_config(base_config))

    async def _replace_base_config(self, base_config: C) -> ConfigChangeEvent:
        scope = ConfigScope.cluster()
        async with self._lock_for(scope):
            with self._publication_lock:
                self._base_config = base_config
                persisted_settings = self._persisted_settings.get(scope)
                candidate = self._build_candidate(scope, persisted_settings)
                event = self._publish(
                    scope,
                    persisted_settings,
                    candidate,
                    reason=ConfigChangeReason.UPDATE,
                )
                notification = self._chain_notification(event)
        await self._notify_in_order(notification)
        return event

    # -- account loading -----------------------------------------------------

    async def _ensure_loaded(self, account_id: str) -> None:
        """Load and validate one Account configuration, once.

        Idempotent and concurrency-safe per Account. Absence of a file records
        "loaded, no settings"; a read/decrypt/validate failure raises and does
        not fall back to another Account's configuration.
        """
        with self._publication_lock:
            entry = self._accounts.get(account_id)
            if entry is not None:
                entry.last_access = time.monotonic()
                return
        scope = ConfigScope.account(account_id)
        async with self._lock_for(scope):
            with self._publication_lock:
                if account_id in self._accounts:
                    self._accounts[account_id].last_access = time.monotonic()
                    return
            persisted_settings = await self._source.load(scope)
            with self._publication_lock:
                self._accounts[account_id] = _AccountEntry(
                    config=self._build_account_candidate(persisted_settings),
                    last_access=time.monotonic(),
                )
                self._persisted_settings[scope] = persisted_settings

    async def get_account(self, account_id: str, field: str) -> Any:
        """Load an Account field, retaining deprecated whole-section fallback."""
        return await self.resolve_account(account_id, lambda view: view.get(field))

    async def resolve_account(
        self, account_id: str, resolver: Callable[[AccountConfigView[C, A]], T]
    ) -> T:
        """Select a domain value from one publication pair.

        Selectors must be synchronous and perform no I/O or configuration
        mutations. Loading and cancellation have the same contract as get_account.
        """
        return await run_to_completion(lambda: self._resolve_account(account_id, resolver))

    async def _resolve_account(
        self, account_id: str, resolver: Callable[[AccountConfigView[C, A]], T]
    ) -> T:
        while True:
            await self._ensure_loaded(account_id)
            with self._publication_lock:
                entry = self._accounts.get(account_id)
                if entry is not None:
                    view = AccountConfigView(entry.config, self._get_config())
                    break
        result = resolver(view)
        import inspect

        if inspect.isawaitable(result):
            if inspect.iscoroutine(result):
                result.close()
            raise TypeError("account configuration resolver must be synchronous")
        return result

    async def get_settings(self, scope: ConfigScope) -> dict:
        """Read the settings stored for exactly one scope."""
        import copy

        return copy.deepcopy(await self._source.load(scope) or {})

    def validate_initial_settings(self, account_id: str, settings: dict) -> None:
        """Validate creation-time settings without persisting them."""
        ConfigScope.account(account_id)
        if self._validate_request is not None:
            self._validate_request(settings, True, True)
        self._build_account_candidate(settings, creating=True)

    # -- PATCH ---------------------------------------------------------------

    async def patch_cluster(self, patch: dict) -> ConfigChangeEvent:
        """Apply a three-state PATCH to the Cluster settings and publish."""
        scope = ConfigScope.cluster()
        return await run_to_completion(lambda: self._patch(scope, patch))

    async def patch_account(
        self,
        account_id: str,
        patch: dict,
        *,
        creating: bool = False,
        lease_ref: object | None = None,
    ) -> ConfigChangeEvent:
        """Apply a three-state PATCH to one Account configuration and publish."""
        scope = ConfigScope.account(account_id)
        return await run_to_completion(
            lambda: self._patch(
                scope,
                patch,
                creating=creating,
                lease_ref=lease_ref,
            )
        )

    async def delete_account(self, account_id: str) -> ConfigChangeEvent:
        """Delete one Account configuration and evict all manager-owned state."""
        scope = ConfigScope.account(account_id)
        return await run_to_completion(lambda: self._delete_account(scope))

    async def _delete_account(self, scope: ConfigScope) -> ConfigChangeEvent:
        assert scope.key is not None
        async with self._lock_for(scope):
            await self._source.delete(scope)
            with self._publication_lock:
                event = self._publish(
                    scope,
                    None,
                    None,
                    reason=ConfigChangeReason.EVICT,
                )
                notification = self._chain_notification(event)
        await self._notify_in_order(notification)
        return event

    async def _patch(
        self,
        scope: ConfigScope,
        patch: dict,
        *,
        creating: bool = False,
        lease_ref: object | None = None,
    ) -> ConfigChangeEvent:
        # Phase 1: validate only the request boundary. Candidate validation
        # happens after the current document has been merged.
        self._validate_patch_request(scope, patch, creating)

        # Phase 2: serialize the scope's read/merge/validate/write operation.
        async with self._lock_for(scope):
            prepared = await self._persist_validated_patch(
                scope,
                patch,
                creating=creating,
                lease_ref=lease_ref,
            )

            # Phase 3: publish only the already-built candidate. Account and
            # Cluster publications are independent; a Cluster pointer change
            # never rebuilds the AccountConfig candidate.
            with self._publication_lock:
                event = self._publish(
                    scope,
                    prepared.persisted_settings,
                    prepared.candidate,
                    reason=ConfigChangeReason.UPDATE,
                )
                notification = self._chain_notification(event)

        # Phase 4: consumers run outside write locks, in publication order.
        await self._notify_in_order(notification)
        return event

    def _validate_patch_request(
        self,
        scope: ConfigScope,
        patch: dict,
        creating: bool,
    ) -> None:
        """Validate the request boundary before entering scope serialization."""
        if self._validate_request is not None:
            self._validate_request(patch, scope.kind is ScopeKind.ACCOUNT, creating)

    async def _persist_validated_patch(
        self,
        scope: ConfigScope,
        patch: dict,
        *,
        creating: bool,
        lease_ref: object | None = None,
    ) -> _PreparedPatch:
        """Prepare one candidate and persist its explicit scope document."""
        prepared: Optional[_PreparedPatch] = None

        def mutate(current: Optional[dict]) -> dict:
            nonlocal prepared
            prepared = self._prepare_patch(scope, current, patch, creating=creating)
            return prepared.persisted_settings

        update_with_lease = getattr(self._source, "update_with_lease", None)
        if lease_ref is not None and callable(update_with_lease):
            persisted_settings = await update_with_lease(scope, mutate, lease_ref)
        else:
            persisted_settings = await self._source.update(scope, mutate)
        if prepared is None:
            raise RuntimeError("config source update did not invoke its mutate callback")
        if prepared.persisted_settings is not persisted_settings:
            prepared = _PreparedPatch(
                persisted_settings=persisted_settings,
                candidate=prepared.candidate,
            )
        return prepared

    def _prepare_patch(
        self,
        scope: ConfigScope,
        current: Optional[dict],
        patch: dict,
        *,
        creating: bool,
    ) -> _PreparedPatch:
        """Merge, transition-check, construct and validate one PATCH candidate."""
        persisted_settings = apply_three_state_patch(current, patch)
        if self._validate_request is not None and not creating:
            self._validate_resets(
                current or {},
                patch,
                scope.kind is ScopeKind.ACCOUNT,
            )
        candidate = self._build_candidate(
            scope,
            persisted_settings,
            changed_sections=frozenset(patch),
            old_settings=current,
            creating=creating,
        )
        return _PreparedPatch(persisted_settings=persisted_settings, candidate=candidate)

    def _validate_resets(self, current: dict, patch: dict, is_account: bool) -> None:
        """A parent reset must not erase creation-only overrides beneath it."""

        def removed(node: dict, changes: dict) -> dict:
            result = {}
            for key, value in changes.items():
                if value is None and key in node:
                    result[key] = node[key]
                elif isinstance(value, dict) and isinstance(node.get(key), dict):
                    nested = removed(node[key], value)
                    if nested:
                        result[key] = nested
            return result

        assert self._validate_request is not None
        self._validate_request(removed(current, patch), is_account, False)

    # -- copy-on-write publish -----------------------------------------------

    def _build_candidate(
        self,
        scope: ConfigScope,
        persisted_settings: Optional[dict],
        *,
        changed_sections: Optional[frozenset[str]] = None,
        old_settings: Any = _NO_OLD_SETTINGS,
        creating: bool = False,
    ) -> Any:
        """Build and validate the candidate publication for one scope."""
        if scope.kind is ScopeKind.CLUSTER:
            return self._build_config(self._base_config, persisted_settings or {})
        return self._build_account_candidate(
            persisted_settings,
            changed_sections=changed_sections,
            old_settings=old_settings,
            creating=creating,
        )

