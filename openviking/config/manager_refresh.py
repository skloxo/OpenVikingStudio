# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Publication, notification, and refresh helpers for RuntimeConfigManager."""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import Future as ConcurrentFuture
from typing import Any, Optional

from openviking.config.manager_types import (
    _NO_OLD_SETTINGS,
    ACCOUNT_IDLE_TTL_SECS,
    REFRESH_INTERVAL_SECS,
    AccountCandidateContext,
    AccountConfigView,
    ConfigChangeEvent,
    ConfigChangeReason,
    _AccountEntry,
    _PendingNotification,
)
from openviking.config.merge import diff_sections
from openviking.config.scope import ConfigScope, ScopeKind
from openviking.service.task_tracker_concurrency import run_to_completion
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)


class _RuntimeConfigRefreshMixin:
    def _build_account_candidate(
        self,
        settings: Optional[dict],
        *,
        changed_sections: Optional[frozenset[str]] = None,
        old_settings: Any = _NO_OLD_SETTINGS,
        creating: bool = False,
    ) -> A:
        """Build an Account model and run injected cross-publication checks."""
        account = self._build_account(settings)
        # The source may contain changes rejected by a previous refresh.
        # Validate the complete candidate; changed_sections only scopes
        # transition checks inside validators, never candidate validity.
        validators = self._account_candidate_validators
        if not validators:
            return account
        cluster = self._get_config()
        context = AccountCandidateContext(
            new_view=AccountConfigView(account, cluster),
            old_view=(
                AccountConfigView(self._build_account(old_settings), cluster)
                if not creating and old_settings is not _NO_OLD_SETTINGS
                else None
            ),
            changed_sections=changed_sections,
            creating=creating,
        )
        for validator in validators:
            validator.validate(context)
        return account

    def _publish(
        self,
        scope: ConfigScope,
        persisted_settings: Optional[dict],
        candidate: Any,
        *,
        reason: ConfigChangeReason,
    ) -> ConfigChangeEvent:
        """Swap an already-built candidate into publication state."""
        if scope.kind is ScopeKind.CLUSTER:
            if candidate is None:
                raise ValueError("cluster publication requires a candidate")
            old = self._get_config()
            self._set_config(candidate)
            self._persisted_settings[scope] = persisted_settings
            return ConfigChangeEvent(
                scope=scope,
                changed_sections=diff_sections(old, candidate),
                old_config=old,
                new_config=candidate,
                reason=reason,
            )
        assert scope.key is not None
        account_id = scope.key
        old_entry = self._accounts.get(account_id)
        old_config = old_entry.config if old_entry is not None else None
        if candidate is None:
            self._accounts.pop(account_id, None)
            self._persisted_settings.pop(scope, None)
        else:
            self._accounts[account_id] = _AccountEntry(
                config=candidate,
                last_access=(old_entry.last_access if old_entry else time.monotonic()),
            )
            self._persisted_settings[scope] = persisted_settings
        return self._account_event(account_id, old_config, candidate, reason=reason)

    def _account_event(
        self,
        account_id: str,
        old_config: Any,
        new_config: Any,
        *,
        reason: ConfigChangeReason,
    ) -> ConfigChangeEvent:
        return ConfigChangeEvent(
            scope=ConfigScope.account(account_id),
            changed_sections=diff_sections(old_config, new_config),
            old_config=old_config,
            new_config=new_config,
            reason=reason,
        )

    def _chain_notification(
        self, event: ConfigChangeEvent
    ) -> Optional[_PendingNotification]:
        """Link an event to the preceding notification for the same scope."""
        is_evict = event.reason is ConfigChangeReason.EVICT
        if not event.changed_sections and not is_evict:
            return None
        completion: ConcurrentFuture[None] = ConcurrentFuture()
        pending = _PendingNotification(
            event=event,
            predecessor=self._notification_tails.get(event.scope),
            completion=completion,
        )
        self._notification_tails[event.scope] = completion
        return pending

    async def _notify_in_order(
        self, pending: Optional[_PendingNotification]
    ) -> None:
        """Deliver one event after its scope predecessor, without write locks."""
        if pending is None:
            return
        if pending.predecessor is not None:
            await asyncio.wrap_future(pending.predecessor)
        try:
            await self._notify(pending.event)
        finally:
            pending.completion.set_result(None)
            with self._publication_lock:
                if self._notification_tails.get(pending.event.scope) is pending.completion:
                    self._notification_tails.pop(pending.event.scope, None)

    async def _notify(self, event: ConfigChangeEvent) -> None:
        """Await matching consumers in registration order for one scope."""
        is_evict = event.reason is ConfigChangeReason.EVICT
        if not event.changed_sections and not is_evict:
            return
        for registration in self._consumers:
            if registration.scope is not event.scope.kind:
                continue
            if not is_evict and registration.sections.isdisjoint(event.changed_sections):
                continue
            try:
                await registration.consumer(event)
            except Exception:
                logger.exception("Config change consumer failed")

    def _lock_for(self, scope: ConfigScope):
        key = (scope.kind.value, scope.key)
        return self._scope_locks.acquire(key)

    # -- periodic refresh ----------------------------------------------------

    def start_refresh_loop(self, interval_secs: float = REFRESH_INTERVAL_SECS) -> None:
        loop = asyncio.get_running_loop()
        with self._refresh_task_lock:
            if self._refresh_task is None or self._refresh_task.done():
                self._refresh_task = loop.create_task(self._refresh_loop(interval_secs))
                self._refresh_task_loop = loop

    async def stop_refresh_loop(self) -> None:
        with self._refresh_task_lock:
            task = self._refresh_task
            owner_loop = self._refresh_task_loop
        if task is None or owner_loop is None:
            return

        async def cancel_and_wait() -> None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        if asyncio.get_running_loop() is owner_loop:
            await cancel_and_wait()
        else:
            future = asyncio.run_coroutine_threadsafe(cancel_and_wait(), owner_loop)
            await asyncio.wrap_future(future)
        with self._refresh_task_lock:
            if self._refresh_task is task:
                self._refresh_task = None
                self._refresh_task_loop = None

    async def _refresh_loop(self, interval_secs: float) -> None:
        while True:
            try:
                await asyncio.sleep(interval_secs)
                await self.refresh_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Runtime config refresh iteration failed")

    async def refresh_once(self) -> None:
        """Reload all active configuration scopes once."""
        await run_to_completion(self._refresh_once)

    async def _refresh_once(self) -> None:
        """Reload cluster + hot accounts once, publishing any observed change.

        Every active scope is reloaded and diffed against the last published
        settings document (``_refresh_scope``); the manager owns change detection, so the
        source stays stateless. Cold accounts (idle > TTL) are evicted and stop
        being reloaded. On load or publish failure the last effective value is
        kept, and the next refresh retries the active scope.
        """
        with self._publication_lock:
            account_ids = list(self._accounts)
        for account_id in account_ids:
            await self._evict_account_if_cold(account_id)
        with self._publication_lock:
            scopes = [ConfigScope.cluster()] + [
                ConfigScope.account(account_id) for account_id in self._accounts
            ]
        for scope in scopes:
            try:
                await self._refresh_scope(scope, reason=ConfigChangeReason.UPDATE)
            except Exception:
                logger.warning(
                    "Runtime config refresh for %s failed; keeping last value",
                    scope,
                    exc_info=True,
                )

    async def _refresh_scope(
        self,
        scope: ConfigScope,
        *,
        reason: ConfigChangeReason,
    ) -> None:
        async with self._lock_for(scope):
            persisted_settings = await self._source.load(scope)
            with self._publication_lock:
                if (
                    scope in self._persisted_settings
                    and self._persisted_settings[scope] == persisted_settings
                ):
                    return
                candidate = self._build_candidate(
                    scope,
                    persisted_settings,
                    changed_sections=None,
                    old_settings=_NO_OLD_SETTINGS,
                    creating=False,
                )
                if scope.kind is ScopeKind.ACCOUNT:
                    assert scope.key is not None
                    if scope.key not in self._accounts:
                        # A refresh must not resurrect an evicted/never-loaded account.
                        return
                event = self._publish(scope, persisted_settings, candidate, reason=reason)
                notification = self._chain_notification(event)
        await self._notify_in_order(notification)

    async def _evict_account_if_cold(self, account_id: str) -> None:
        scope = ConfigScope.account(account_id)
        async with self._lock_for(scope):
            with self._publication_lock:
                entry = self._accounts.get(account_id)
                if (
                    entry is None
                    or time.monotonic() - entry.last_access <= ACCOUNT_IDLE_TTL_SECS
                ):
                    return
                self._accounts.pop(account_id)
                self._persisted_settings.pop(scope, None)
                event = self._account_event(
                    account_id,
                    entry.config,
                    None,
                    reason=ConfigChangeReason.EVICT,
                )
                notification = self._chain_notification(event)
        await self._notify_in_order(notification)
