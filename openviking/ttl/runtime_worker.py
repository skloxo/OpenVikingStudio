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
from openviking.ttl.runtime_models import DAY_MS, INITIAL, PATH_SAFE, READ_INITIAL, REMOVE, RESET, TTLDirectory, directory, next_check_ms


class _TTLWorkerMixin:
    async def on_post_write(self, uri: str, ctx: RequestContext | None, written_at_ms: int) -> None:
        if not self.writer or ctx is None:
            return
        item = directory(uri)
        if item is None or (item[0] == "sessions" and uri != item[2] + "/messages.jsonl"):
            return
        if item[0] != "sessions" and uri.rsplit("/", 1)[-1] in ABSTRACT_OVERVIEW_FILENAMES:
            return
        base = written_at_ms if item[0] == "sessions" else self.base(item)
        await self._dispatcher.run(
            lambda: self._enqueue_registration((ctx.account_id, item[0], item[2]), base)
        )

    async def _enqueue_registration(self, key: tuple[str, TTLIndexType, str], base: int) -> None:
        # Only an in-memory merge on the write path. The worker owns Redis I/O.
        old = self._retry.get(key)
        if old is None and len(self._retry) >= self.retry_limit:
            self.registration_dropped_total += 1
            logger.error(
                "TTL event=registration_dropped scope=%s uri=%s pending=%s dropped_total=%s",
                key[0],
                key[2],
                len(self._retry),
                self.registration_dropped_total,
            )
            return
        was_empty = not self._retry
        self._retry[key] = max(base, old) if old is not None else base
        # Updates to a failed batch must not defeat the worker's retry backoff.
        if was_empty:
            self._wake_registrations()

    async def _register(self, key, base):
        account, kind, uri = key
        redis = await self.client()
        await redis.zadd(
            self.prefix(account) + kind,
            {uri: base},
            **({"gt": True} if kind == "sessions" else {"nx": True}),
        )

    async def _retry_writes(self, *, closing=False):
        groups = {}
        for (account, kind, uri), base in islice(self._retry.items(), min(self.batch_size, 256)):
            groups.setdefault((account, kind), {})[uri] = base
        error = None
        for (account, kind), entries in groups.items():
            if self._closed and not closing:
                return
            try:
                async with self._registration_lock:
                    pair = await self.policies(account)
                    active = {
                        uri: base
                        for uri, base in entries.items()
                        if self._retry.get((account, kind, uri)) == base
                        and (await self.policy(account, uri, pair)).enabled
                    }
                    if active:
                        redis = await self.client()
                        await redis.zadd(
                            self.prefix(account) + kind,
                            active,
                            **({"gt": True} if kind == "sessions" else {"nx": True}),
                        )
                if active:
                    await self._schedule(account)
                # Also discard disabled entries; do not remove a concurrent update.
                for uri, base in entries.items():
                    key = (account, kind, uri)
                    if self._retry.get(key) == base:
                        self._retry.pop(key, None)
            except Exception as exc:
                error = exc
                # Do not let one failed account monopolize the bounded head batch.
                for uri in entries:
                    key = (account, kind, uri)
                    if key in self._retry:
                        current = self._retry.pop(key)
                        self._retry[key] = current
                logger.exception("TTL batch registration failed scope=%s kind=%s", account, kind)
        if error is not None:
            raise error

    async def register_initial_backfill(self, request: TTLBackfillRequest) -> None:
        if not self.writer or request.resource_id != self.resource_id:
            raise FailedPreconditionError("TTL request must target this writer")
        account = request.account_id
        pair = await self.policies(account)
        state = await self.read_initial(account)
        if not await self._initial_enabled(account, pair, state):
            raise FailedPreconditionError("TTL is disabled")
        await self._register_initial(request, pair, state, discover=False)

    async def _register_initial(
        self, request: TTLBackfillRequest, pair, state, *, discover=True
    ) -> None:
        account = request.account_id
        if not await self._schedule(account):
            raise FailedPreconditionError("TTL Account is unavailable")
        intents = request.reset_intents or {
            root: token
            for root, token in state["reset_required"].items()
            if (await self.policy(account, root, pair)).enabled
        }
        reset = request.reset or bool(intents)
        roots = request.roots
        if not reset and not state["roots"] and (state["pending"] or state["done"]):
            raise FailedPreconditionError("initial state is missing roots")
        needs_discovery = roots is None and (reset or state["discover"] or not state["roots"])
        if roots is None:
            if needs_discovery and discover:
                roots = await self._initial_roots(account, pair)
                needs_discovery = False
            elif state["roots"]:
                try:
                    roots = json.loads(state["roots"])
                except ValueError as exc:
                    raise FailedPreconditionError("invalid saved initial roots") from exc
                if not isinstance(roots, list):
                    raise FailedPreconditionError("invalid saved initial roots")
            else:
                roots = []
        roots = sorted(set(roots))
        try:
            for root in roots:
                validate_ttl_root(root)
        except ValueError as exc:
            raise InvalidArgumentError(
                "initial roots must be canonical Events or Sessions roots"
            ) from exc
        if request.reset_intents and not request.reset:
            raise InvalidArgumentError("reset intents require reset")
        # Configuration can change while discovery yields. Leave
        # these intents pending rather than acknowledge a scan of closed roots.
        active_intents = {
            root: token
            for root, token in intents.items()
            if (await self.policy(account, root, pair)).enabled
        }
        if intents and not active_intents:
            return
        if not reset and state["done"]:
            return
        if reset:
            self._stop_scan.add(account)
        try:
            async with self._locks.setdefault(account, asyncio.Lock()):
                async with self._recycle_lock if reset else nullcontext():
                    prefix = self.prefix(account) + "backfill:"
                    redis = await self.client()
                    checkpoint = json.dumps({"root": 0, "stack": []}, separators=(",", ":"))
                    try:
                        result = await redis.eval(
                            RESET if reset else INITIAL,
                            4,
                            prefix + "initial",
                            prefix + "initial:done",
                            prefix + "pending",
                            prefix + "reset_required",
                            json.dumps(roots, separators=(",", ":")),
                            checkpoint,
                            json.dumps(active_intents, separators=(",", ":")),
                            "1" if needs_discovery else "0",
                        )
                    except Exception as exc:
                        raise UnavailableError(
                            "TTL initial registration failed; query state before retry"
                        ) from exc
                    if not result:
                        raise ConflictError("initial roots changed; reset is required")
                    if result == 2:
                        return
                    self._pending.add(account)
        finally:
            self._stop_scan.discard(account)
        logger.info(
            "TTL initial registered scope=%s/%s event=%s",
            self.resource_id,
            account,
            "reset" if reset else "resume",
        )

    async def _resume_initial(self, account: str, *, discover=True) -> None:
        state = await self.read_initial(account)
        if state["done"] and not state["reset_required"]:
            return
        pair = await self.policies(account)
        if not await self._initial_enabled(account, pair, state):
            self._pending.discard(account)
            return
        await self._register_initial(
            TTLBackfillRequest(self.resource_id, account), pair, state, discover=discover
        )

    async def _run(self):
        delay = 1
        while not self._closed:
            self._wake.clear()
            failed = False
            # Only expiry callbacks admit Accounts to a maintenance round.
            for account in self._recycle.copy():
                if self._closed:
                    break
                try:
                    await self._resume_initial(account)
                    if account in self._pending and not self._closed:
                        async with self._locks.setdefault(account, asyncio.Lock()):
                            await self._scan(account)
                    elif not self._closed:
                        result = await self._recycle_registered(
                            TTLRecycleRequest(self.resource_id, account)
                        )
                        logger.info(
                            "TTL recycle resource=%s account=%s result=%s",
                            self.resource_id,
                            account,
                            result,
                        )
                    self._recycle.discard(account)
                except Exception:
                    failed = True
                    logger.exception("TTL worker retry scope=%s delay=%s", account, delay)
            delay = min(delay * 2, 60) if failed else 1
            if not self._recycle:
                return
            try:
                await asyncio.wait_for(self._wake.wait(), uniform(delay / 2, delay))
            except TimeoutError:
                pass

    async def _children(self, uri, ctx):
        await asyncio.sleep(self.batch_interval)
        try:
            entries = await self.fs.ls(
                uri,
                ctx=ctx,
                node_limit=None,
                include_abstract=False,
                show_all_hidden=True,
            )
        except Exception as exc:
            if is_not_found_error(exc):
                return []
            raise
        return sorted(e["uri"].rstrip("/") for e in entries if e.get("isDir"))

