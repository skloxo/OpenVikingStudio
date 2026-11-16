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
from openviking.ttl.runtime_models import DAY_MS, PATH_SAFE, REMOVE, TTLDirectory, directory, next_check_ms


class _TTLRecycleMixin:
    async def _scan(self, account):
        redis = await self.client()
        prefix = self.prefix(account) + "backfill:"
        if not await redis.sismember(prefix + "pending", "initial"):
            self._pending.discard(account)
            return
        if await redis.get(prefix + "initial:done") == "1":
            await redis.srem(prefix + "pending", "initial")
            self._pending.discard(account)
            return
        state = await redis.hgetall(prefix + "initial")
        if state.get("discover") == "1":
            return  # Scope discovery belongs to the scheduled maintenance round.
        if not state.get("roots") or not state.get("checkpoint"):
            raise FailedPreconditionError("pending initial has incomplete state")
        roots = json.loads(state["roots"])
        checkpoint = json.loads(state["checkpoint"])
        ctx = self.context(account)
        listings = {}
        while checkpoint["root"] < len(roots):
            if self._closed or account in self._stop_scan:
                return
            root = roots[checkpoint["root"]]
            pair = await self.policies(account)
            if not (await self.policy(account, root, pair)).enabled:
                # A disabled root does not block other enabled roots in the account.
                # Reopening this root requires the persisted initial reset.
                checkpoint["root"] += 1
                checkpoint["stack"] = []
                listings.clear()
                await redis.hset(
                    prefix + "initial",
                    "checkpoint",
                    json.dumps(checkpoint, separators=(",", ":")),
                )
                continue
            stack = checkpoint["stack"]
            if not stack:
                stack.append({"uri": root, "last": ""})
            frame = stack[-1]
            if frame["uri"] not in listings:
                listings[frame["uri"]] = await self._children(frame["uri"], ctx)
            cached = listings[frame["uri"]]
            start = bisect_right(cached, frame["last"])
            if start == len(cached):
                listings.pop(frame["uri"])
                stack.pop()
                if not stack:
                    checkpoint["root"] += 1
                await redis.hset(
                    prefix + "initial",
                    "checkpoint",
                    json.dumps(checkpoint, separators=(",", ":")),
                )
                continue
            # Stop at Session or valid date directories. Never list their contents.
            leaf = root.endswith("/sessions") or len(stack) == 3
            if not leaf:
                child = cached[start]
                frame["last"] = child
                stack.append({"uri": child, "last": ""})
                continue
            batch = cached[start : start + self.batch_size]
            items = [(u, directory(u)) for u in batch]
            items = [(u, item) for u, item in items if item is not None]
            if items:
                await asyncio.sleep(self.batch_interval)
                index = self.prefix(account) + items[0][1][0]
                scores = await redis.zmscore(index, [u for u, _ in items])
                additions = {}
                for (uri, item), score in zip(items, scores, strict=True):
                    if score is not None:
                        continue
                    if item[0] == "sessions":
                        await asyncio.sleep(1 / self.stat_rate)
                        try:
                            stat = await self.fs.stat(uri + "/messages.jsonl", ctx=ctx)
                        except Exception as exc:
                            if is_not_found_error(exc):
                                continue
                            raise
                        additions[uri] = self.modtime(stat)
                    else:
                        additions[uri] = self.base(item)
                if additions:
                    await redis.zadd(index, additions, nx=True)
            # A failed/unknown ZADD must never advance the persisted checkpoint.
            frame["last"] = batch[-1]
            await redis.hset(
                prefix + "initial",
                "checkpoint",
                json.dumps(checkpoint, separators=(",", ":")),
            )
        if self._closed or account in self._stop_scan:
            return
        await redis.set(prefix + "initial:done", "1")
        await redis.srem(prefix + "pending", "initial")
        self._pending.discard(account)
        logger.info("TTL initial scope=%s event=done", account)

    @staticmethod
    def modtime(stat):
        value = stat.get("modTime") or stat.get("ModTime")
        if not isinstance(value, str):
            raise ValueError("messages.jsonl has no valid ModTime")
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)

    async def resolve_expires_at(
        self, uris: Sequence[str], ctx: RequestContext | None
    ) -> dict[str, str | None]:
        result = dict.fromkeys(uris)
        if ctx is None:
            return result
        pair = await self.policies(ctx.account_id)
        sessions = {}
        now = {}
        for uri in uris:
            item = directory(uri)
            if item is None:
                continue
            policy = await self.policy(ctx.account_id, item[1], pair)
            if not policy.enabled:
                continue
            if item[0] == "sessions":
                sessions.setdefault(item[2], []).append((uri, item, policy.days))
            else:
                now[uri] = self.expiry(item, self.base(item), policy.days)
        if sessions:
            try:
                async with asyncio.timeout(self.read_timeout):
                    redis = await self.client()
                    scores = await redis.zmscore(
                        self.prefix(ctx.account_id) + "sessions", list(sessions)
                    )
                for entries, score in zip(sessions.values(), scores, strict=True):
                    if score is not None:
                        for uri, item, days in entries:
                            now[uri] = self.expiry(item, score, days)
            except Exception:
                logger.warning(
                    "TTL expiry read unavailable scope=%s",
                    ctx.account_id,
                    exc_info=True,
                )
        for uri, ms in now.items():
            result[uri] = (
                datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")
            )
        return result

    async def recycle_due(self, request: TTLRecycleRequest) -> TTLRecycleResult:
        if not self.writer or request.resource_id != self.resource_id:
            raise FailedPreconditionError("TTL request must target this writer")
        if request.max_base_time_ms is None:
            await self._resume_initial(request.account_id, discover=False)
        return await self._recycle_registered(request)

    async def _recycle_registered(self, request: TTLRecycleRequest) -> TTLRecycleResult:
        if self._recycle_lock.locked():
            raise ConflictError("TTL recycle round is already running")
        counts = {"scanned": 0, "deleted": 0, "skipped": 0, "failed": 0}
        account = request.account_id
        async with self._recycle_lock:
            redis = await self.client()
            prefix = self.prefix(account)
            if await redis.get(prefix + "backfill:initial:done") != "1":
                return TTLRecycleResult()
            cutoff = request.max_base_time_ms
            if cutoff is None:
                if not await redis.exists(*(prefix + kind for kind in TTLIndexType)):
                    return TTLRecycleResult()
                cutoff = await self._recycle_cutoff(account)
                if cutoff is None:
                    return TTLRecycleResult()
            ctx = self.context(account)
            for kind in ("user_events", "peer_events", "sessions"):
                offset = 0
                while not self._closed:
                    await asyncio.sleep(self.batch_interval)
                    candidates = await redis.zrangebyscore(
                        prefix + kind,
                        "-inf",
                        cutoff,
                        start=offset,
                        num=min(request.limit, self.batch_size),
                        withscores=True,
                    )
                    if not candidates:
                        break
                    if await redis.get(prefix + "backfill:initial:done") != "1":
                        return TTLRecycleResult(**counts)
                    removed = 0
                    for uri, score in candidates:
                        if self._closed or account in self._stop_scan:
                            return TTLRecycleResult(**counts)
                        counts["scanned"] += 1
                        try:
                            did_delete, did_remove = await self._delete(account, uri, score, ctx)
                            counts["deleted" if did_delete else "skipped"] += 1
                            removed += did_remove
                        except Exception:
                            counts["failed"] += 1
                            logger.exception("TTL recycle failed scope=%s uri=%s", account, uri)
                    offset += len(candidates) - removed
        return TTLRecycleResult(**counts)

    async def _recycle_cutoff(self, account: str) -> int | None:
        # Use the current user registry, not initial roots or an incomplete cache.
        # Changes after this snapshot enter the next hourly round.
        pair = await self.policies(account)
        roots = self.policy_roots()

        def minimum(config, days=None):
            for root in roots:
                value = resolve_effective_ttl(*pair, root, config).days
                if value is not None and (days is None or value < days):
                    days = value
            return days

        days = minimum(None)
        if days != 1:
            manager = getattr(self, "account_manager", None)
            if manager is None:
                # Local dev mode has no user registry; use the safe lower bound.
                return time.time_ns() // 1_000_000
            users = await manager.list_users_page(account, limit=None, expose_key=False)
            for i, user in enumerate(users["users"]):
                if i % self.batch_size == 0:
                    await asyncio.sleep(self.batch_interval)
                days = minimum(await self.user_policy(account, user["user_id"]), days)
                if days == 1:
                    break
        if days is None:
            return None
        return time.time_ns() // 1_000_000 - (days - 1) * DAY_MS

    async def _delete(self, account, uri, score, ctx):
        item = directory(uri)
        if item is None or item[2] != uri:
            return False, 0
        # Every valid TTL is at least one day. Skip young entries without loading
        # user configuration; Events retain their existing calendar-day semantics.
        if self.expiry(item, score, 1) > time.time_ns() // 1_000_000:
            return False, 0
        policy = await self.policy(account, item[1])
        if (
            not policy.enabled
            or self.expiry(item, score, policy.days) > time.time_ns() // 1_000_000
        ):
            return False, 0
        await asyncio.sleep(self.delete_interval)
        path = self.fs._uri_to_path(uri, ctx=ctx)
        agfs = self.fs._async_agfs
        lease = await agfs.pathlock_acquire_tree(path)
        try:
            redis = await self.client()
            if await redis.get(self.prefix(account) + "backfill:initial:done") != "1":
                return False, 0
            policy = await self.policy(account, item[1])
            if not policy.enabled:
                return False, 0
            base = score
            if item[0] == "sessions":
                try:
                    base = self.modtime(await self.fs.stat(uri + "/messages.jsonl", ctx=ctx))
                except Exception as exc:
                    if not is_not_found_error(exc):
                        raise
            if self.expiry(item, base, policy.days) > time.time_ns() // 1_000_000:
                await self._register((account, item[0], uri), base)
                return False, int(base > score)
            try:
                await self.fs.rm(uri, recursive=True, ctx=ctx, lease_ref=lease)
            except Exception as exc:
                if not is_not_found_error(exc):
                    raise
            removed = await redis.eval(REMOVE, 1, self.prefix(account) + item[0], uri, str(score))
            return True, int(removed)
        finally:
            await agfs.pathlock_release(lease)
