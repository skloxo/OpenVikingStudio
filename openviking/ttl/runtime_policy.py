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
from openviking.ttl.runtime_models import DAY_MS, INITIAL, PATH_SAFE, READ_INITIAL, REMOVE, RESET, TTLDirectory, next_check_ms


class _TTLPolicyMixin:
    async def patch_configuration(self, settings: dict, account_id: str | None = None) -> None:
        patch = settings["ttl"]

        def may_enable(value):
            if value is None:
                return True
            if isinstance(value, dict):
                return any(may_enable(node) for node in value.values())
            return value != "disabled"

        accounts = []
        if may_enable(patch):
            accounts = (
                [{"account_id": account_id}]
                if account_id is not None
                else await self.account_manager.list_accounts()
            )
            for account in accounts:
                account = account["account_id"]
                pair = await self.policies(account)
                roots = set(self.policy_roots())
                scopes = [root for root in roots if not resolve_effective_ttl(*pair, root).enabled]
                await self._register_reset_intent(account, scopes)
        if account_id is None:
            await self.manager.patch_cluster(settings)
        else:
            await self.manager.patch_account(account_id, settings)

    async def _register_reset_intent(self, account: str, scopes: Sequence[str]) -> None:
        try:
            if scopes:
                redis = await self.client()
                pipe = redis.pipeline(transaction=False)
                token = uuid4().hex
                for scope in scopes:
                    pipe.hsetnx(self.prefix(account) + "backfill:reset_required", scope, token)
                await pipe.execute()
            if not await self._schedule(account):
                raise NotFoundError(account, "account")
        except Exception as exc:
            raise UnavailableError("TTL reset intent registration unavailable") from exc

    async def read_initial(self, account_id: str) -> dict:
        prefix = self.prefix(account_id) + "backfill:"
        try:
            redis = await self.client()
            values = await redis.eval(
                READ_INITIAL,
                4,
                prefix + "initial",
                prefix + "initial:done",
                prefix + "pending",
                prefix + "reset_required",
            )
            return {
                "roots": values[0],
                "checkpoint": values[1],
                "done": values[2] == "1",
                "pending": values[3] == "1",
                "reset_required": json.loads(values[4]),
                "discover": values[5] == "1",
            }
        except Exception as exc:
            raise UnavailableError("TTL initial state query unavailable") from exc

    async def _initial_roots(self, account: str, pair) -> list[str]:
        ctx = self.context(account)
        roots = set()
        for i, user in enumerate(await self._children("viking://user", ctx)):
            if i % self.batch_size == 0:
                await asyncio.sleep(self.batch_interval)
            config = await self.user_policy(account, uri_parts(user)[1])
            for root in (user + "/memories/events", user + "/sessions"):
                if resolve_effective_ttl(*pair, root, config).enabled:
                    roots.add(root)
            probe = user + "/peers"
            if resolve_effective_ttl(*pair, probe, config).enabled:
                for peer in await self._children(user + "/peers", ctx):
                    roots.add(peer + "/memories/events")
        return sorted(roots)

    def prefix(self, account_id: str) -> str:
        scope = quote(self.resource_id, safe=PATH_SAFE) + "|" + quote(account_id, safe=PATH_SAFE)
        return "ttl:{" + scope + "}:"

    def context(self, account_id: str) -> RequestContext:
        return RequestContext(user=UserIdentifier(account_id, "ttl-internal"), role=Role.ROOT)

    @staticmethod
    def user_roots(user: str) -> list[str]:
        base = f"viking://user/{user}"
        return [
            base + "/sessions",
            base + "/memories/events",
            base + "/peers",
        ]

    def _cache_user_policy(self, key, config) -> None:
        self._user_policies[key] = (time.monotonic(), config)
        self._user_policies.move_to_end(key)
        while len(self._user_policies) > 1024:
            self._user_policies.popitem(last=False)

    async def user_policy(self, account: str, user: str) -> TTLConfig | None:
        """Share one snapshot per user; refresh on demand, not once per directory."""
        key = (account, user)
        cached = self._user_policies.get(key)
        if cached is not None and time.monotonic() - cached[0] < 30:
            return cached[1]

        async def load():
            cached = self._user_policies.get(key)
            if cached is not None and time.monotonic() - cached[0] < 30:
                return cached[1]
            task = self._user_loads.get(key)
            if task is None:
                from openviking.server.user_config import read_user_config

                async def read():
                    try:
                        ctx = RequestContext(user=UserIdentifier(account, user), role=Role.ROOT)
                        value = (await read_user_config(self.fs, ctx)).ttl
                        if self._user_loads.get(key) is not asyncio.current_task():
                            return await self.user_policy(account, user)
                        # A PATCH published while this read was in flight wins.
                        if self._user_policies.get(key) is cached:
                            self._cache_user_policy(key, value)
                        return self._user_policies.get(key, (0, value))[1]
                    finally:
                        if self._user_loads.get(key) is asyncio.current_task():
                            self._user_loads.pop(key, None)

                task = asyncio.create_task(read())
                self._user_loads[key] = task
            return await asyncio.shield(task)

        return await self._dispatcher.run(load)

    async def policy(self, account: str, uri: str, pair=None):
        pair = pair if pair is not None else await self.policies(account)
        parts = uri_parts(uri)
        user = (
            await self.user_policy(account, parts[1]) if classify_ttl_uri(uri) is not None else None
        )
        return resolve_effective_ttl(*pair, uri, user)

    async def _initial_enabled(self, account: str, pair, state) -> bool:
        if self.enabled(pair):
            return True
        roots = set(json.loads(state["roots"]) if state["roots"] else [])
        roots.update(state["reset_required"])
        for (scope, user), (_, config) in list(self._user_policies.items()):
            if scope == account and config is not None:
                roots.update(self.user_roots(user))
        for root in sorted(roots):
            if (await self.policy(account, root, pair)).enabled:
                return True
        return False

    async def prepare_user_configuration(self, ctx, before, after) -> None:
        pair = await self.policies(ctx.account_id)
        opening = [
            root
            for root in self.user_roots(ctx.user.user_id)
            if resolve_effective_ttl(*pair, root, after).enabled
            and not resolve_effective_ttl(*pair, root, before).enabled
        ]
        if not opening:
            return
        await self._register_reset_intent(ctx.account_id, opening)

    async def publish_user_configuration(self, ctx, config) -> None:
        async def publish():
            key = (ctx.account_id, ctx.user.user_id)
            self._user_loads.pop(key, None)
            self._cache_user_policy(key, config)

        await self._dispatcher.run(publish)

    async def policies(self, account_id: str) -> tuple[TTLConfig | None, TTLConfig | None]:
        return await self.manager.resolve_account(
            account_id, lambda v: (v.cluster.ttl, v.account.ttl)
        )

    @classmethod
    def policy_roots(cls) -> list[str]:
        return cls.user_roots("_ttl_")

    @classmethod
    def enabled(cls, pair: tuple[TTLConfig | None, TTLConfig | None]) -> bool:
        return any(resolve_effective_ttl(*pair, uri).enabled for uri in cls.policy_roots())

    def expiry(self, item: TTLDirectory, base: float, days: int) -> float:
        if item[0] == "sessions":
            return base + days * DAY_MS
        dt = datetime(*map(int, item[3]), tzinfo=self.zone) + timedelta(days=days)
        return int(dt.timestamp() * 1000)

    def base(self, item: TTLDirectory) -> int:
        return int(datetime(*map(int, item[3]), tzinfo=self.zone).timestamp() * 1000)

    async def client(self):
        # No connection or ping at startup or on a disabled-account path.
        if self.redis is None:
            from redis.backoff import NoBackoff
            from redis.retry import Retry

            if not self.redis_config.endpoints:
                raise UnavailableError("TTL Redis is not configured")
            self.redis = create_redis_client(self.redis_config, retry=Retry(NoBackoff(), 0))
        return self.redis

    async def start(self) -> None:
        self._dispatcher.bind_current_loop()
        self._closed = False
        self._started = True
        self._recycle_after_ms = next_check_ms(self.resource_id, time.time_ns() // 1_000_000)
        if self._retry:
            self._wake_registrations()

    async def aclose(self) -> None:
        self._closed = True
        self._started = False
        self._wake.set()
        self._registration_wake.set()
        if self._registration_task:
            await self._registration_task
            self._registration_task = None
        if self._task:
            await self._task  # Finish in-flight I/O; never cancel a Redis checkpoint write.
            self._task = None
        if self._retry:
            try:
                async with asyncio.timeout(2):
                    while self._retry:
                        await self._retry_writes(closing=True)
            except Exception:
                logger.warning(
                    "TTL shutdown left volatile registrations pending=%s",
                    len(self._retry),
                    exc_info=True,
                )
        async with self._recycle_lock:
            if self.redis:
                await self.redis.aclose()
                self.redis = None

