# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Redis directory indexes and expiry-driven maintenance for the OV writer."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from bisect import bisect_right
from collections import OrderedDict
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from itertools import islice
from random import uniform
from typing import TYPE_CHECKING, Any, Sequence
from urllib.parse import quote
from uuid import uuid4
from zoneinfo import ZoneInfo

from openviking.config.ttl import (
    TTL_ROOT_DEPTH,
    TTLIndexType,
    classify_ttl_uri,
    resolve_effective_ttl,
    validate_ttl_root,
)
from openviking.core.namespace import uri_parts
from openviking.scheduling.expiry.api import (
    TTL_ITEM_TYPE,
    CallbackRequest,
    CallbackResult,
    CallbackStatus,
    ExpiryRegistration,
    ExpiryScheduler,
    HandlerOptions,
    ItemIdentity,
)
from openviking.scheduling.expiry.config import ExpiryRedisConfig
from openviking.scheduling.expiry.redis_store import create_redis_client
from openviking.server.error_mapping import is_not_found_error
from openviking.server.identity import RequestContext, Role
from openviking.service.task_tracker_concurrency import OwnerLoopDispatcher
from openviking.storage.abstract_overview import ABSTRACT_OVERVIEW_FILENAMES
from openviking.ttl.adapter import TTLBackfillRequest, TTLRecycleRequest, TTLRecycleResult
from openviking_cli.exceptions import (
    ConflictError,
    FailedPreconditionError,
    InvalidArgumentError,
    NotFoundError,
    UnavailableError,
)
from openviking_cli.session.user_id import UserIdentifier
from openviking_cli.utils.config.ttl_config import TTLConfig

if TYPE_CHECKING:
    from openviking.server.api_keys import APIKeyManager
    from openviking.service.core import OpenVikingService

TTLDirectory = tuple[TTLIndexType, str, str, list[str]]

logger = logging.getLogger(__name__)
DAY_MS = 86_400_000
from openviking.ttl.runtime_models import (
    DAY_MS,
    INITIAL,
    PATH_SAFE,
    READ_INITIAL,
    REMOVE,
    RESET,
    TTLDirectory,
    directory,
    next_check_ms,
)
from openviking.ttl.runtime_policy import _TTLPolicyMixin
from openviking.ttl.runtime_recycle import _TTLRecycleMixin
from openviking.ttl.runtime_worker import _TTLWorkerMixin


class DirectoryTTL(_TTLPolicyMixin, _TTLWorkerMixin, _TTLRecycleMixin):
    def __init__(
        self,
        *,
        resource_id: str,
        redis: dict[str, Any] | None = None,
        writer: bool = True,
        timezone_name: str | None = None,
        batch_size: int = 256,
        batch_interval: float = 0.05,
        stat_rate: int = 200,
        delete_interval: float = 0.05,
        read_timeout: float = 0.2,
        retry_limit: int = 10000,
    ) -> None:
        if not resource_id or not 1 <= batch_size <= 512 or stat_rate <= 0 or batch_interval < 0:
            raise ValueError("invalid TTL resource or rate limits")
        self.resource_id = resource_id
        self.redis_config = ExpiryRedisConfig.model_validate(redis or {})
        self.writer = writer
        # With no override, naive date timestamps use the writer's existing
        # local timezone, just like its date-directory generation fallback.
        self.zone = ZoneInfo(timezone_name) if timezone_name else None
        self.batch_size, self.stat_rate = batch_size, stat_rate
        self.batch_interval = batch_interval
        self.delete_interval, self.read_timeout = delete_interval, read_timeout
        self.retry_limit = retry_limit
        self.redis = None
        self._task = None
        self._registration_task = None
        self._started = False
        self._closed = False
        self._wake = asyncio.Event()
        self._registration_wake = asyncio.Event()
        self._pending = set()
        self._locks = {}
        self._stop_scan = set()
        self._retry = {}
        self.registration_dropped_total = 0
        self._recycle_lock = asyncio.Lock()
        self._registration_lock = asyncio.Lock()
        self._scheduler: ExpiryScheduler | None = None
        self._scheduled: set[str] = set()
        self._recycle: set[str] = set()
        self._recycle_after_ms = 0
        self._dispatcher = OwnerLoopDispatcher()
        self._user_policies = OrderedDict()
        self._user_loads = {}

    def bind_runtime(self, service: OpenVikingService, account_manager: APIKeyManager) -> None:
        # Bind before queue workers can invoke the write hooks.
        self._dispatcher.bind_current_loop()
        self.fs = service.viking_fs
        self.manager = service.runtime_config_manager
        self.account_manager = account_manager

    def supports_config(self) -> bool:
        return self.writer

    def install_expiry(self, scheduler: ExpiryScheduler) -> None:
        self._scheduler = scheduler
        scheduler.register_handler(
            TTL_ITEM_TYPE,
            self,
            options=HandlerOptions(
                concurrency=1, max_attempts=None, metadata_enabled=False, lazy_start=True
            ),
        )

    @staticmethod
    def _identity(account: str) -> ItemIdentity:
        return ItemIdentity(TTL_ITEM_TYPE, account, "_system", "maintenance")

    async def _schedule(self, account: str, *, force: bool = False) -> bool:
        if self._scheduler is None or (account in self._scheduled and not force):
            return True
        async with self._registration_lock:
            manager = getattr(self, "account_manager", None)
            info = await manager.get_account(account) if manager is not None else {}
            if info is not None and info.get("status") != "deleting":
                await self._scheduler.report(
                    ExpiryRegistration(
                        self._identity(account),
                        due_at_ms=next_check_ms(self.resource_id, time.time_ns() // 1_000_000),
                        timeout_seconds=3600,
                    )
                )
                self._scheduled.add(account)
                return True
        await self.delete_account(account)
        return False

    async def delete_account(self, account: str) -> None:
        """Retire TTL state through the existing durable Account deletion task."""
        self._stop_scan.add(account)
        try:
            async with (
                self._locks.setdefault(account, asyncio.Lock()),
                self._recycle_lock,
                self._registration_lock,
            ):
                self._scheduled.discard(account)
                self._pending.discard(account)
                self._recycle.discard(account)
                for key in list(self._retry):
                    if key[0] == account:
                        self._retry.pop(key, None)
                for key in list(self._user_policies):
                    if key[0] == account:
                        self._user_policies.pop(key, None)
                if self._scheduler is not None:
                    await self._scheduler.unregister(self._identity(account))
                redis = await self.client()
                prefix = self.prefix(account)
                await redis.unlink(
                    *(prefix + kind for kind in TTLIndexType),
                    *(
                        prefix + "backfill:" + name
                        for name in ("initial", "initial:done", "pending", "reset_required")
                    ),
                )
        finally:
            self._stop_scan.discard(account)
        logger.info("TTL account state removed resource=%s account=%s", self.resource_id, account)

    async def handle(self, request: CallbackRequest) -> CallbackResult:
        if self._closed:
            return CallbackResult(CallbackStatus.RETRY, "stopping")
        account = request.identity.account_id
        # Confirm the next durable wake-up before acknowledging this one.
        # Long-running filesystem work stays outside the short expiry callback.
        if not await self._schedule(account, force=True):
            return CallbackResult(CallbackStatus.COMPLETED, "account_deleted")
        if time.time_ns() // 1_000_000 >= self._recycle_after_ms:
            self._recycle.add(account)
            self._wake_worker()
        return CallbackResult(CallbackStatus.COMPLETED, "maintenance_scheduled")

    def _wake_worker(self) -> None:
        self._wake.set()
        if self.writer and self._started and not self._closed and self._recycle:
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._run(), name="ttl-maintenance")

    def _wake_registrations(self) -> None:
        self._registration_wake.set()
        if self.writer and self._started and not self._closed:
            if self._registration_task is None or self._registration_task.done():
                self._registration_task = asyncio.create_task(
                    self._flush_registrations(), name="ttl-registration"
                )

    async def _flush_registrations(self) -> None:
        # Coalesce a commit's writes without delaying the business request.
        await asyncio.sleep(min(self.batch_interval, 0.05))
        delay = 1
        while self._retry and not self._closed:
            self._registration_wake.clear()
            try:
                await self._retry_writes()
            except Exception:
                logger.exception("TTL registration retry delay=%s", delay)
                try:
                    await asyncio.wait_for(
                        self._registration_wake.wait(), uniform(delay / 2, delay)
                    )
                except TimeoutError:
                    pass
                delay = min(delay * 2, 60)
            else:
                delay = 1
                if self._retry:
                    await asyncio.sleep(self.batch_interval)

