# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Redis persistence for distributed expiry scheduling."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from importlib import resources
from typing import Any, Literal, Sequence, cast
from urllib.parse import urlsplit

from .api import ExpiryRegistration, ExpiryRegistrationResult, ItemIdentity
from .config import ExpiryRedisConfig
from .keys import ExpiryKeys
from .metrics import ExpiryMetrics
from .models import (
    MAX_EXACT_INTEGER,
    SCORE_TIME_BASE,
    AsyncExecutor,
    BucketItem,
    BucketPage,
    BucketRef,
    Claim,
    ItemMetadata,
    NamespaceSpec,
    OwnerRole,
    OwnerToken,
    PublishResult,
    RegistryCursor,
    RegistryPage,
    ShardWindow,
    SourceCursor,
    SourceItem,
    SourcePage,
    StoreOperationError,
    claim_layer_bounds,
    decode_claim_score,
    encode_claim_score,
    encode_ready_claim_score,
    metadata_ttl_ms,
)

RetryPolicy = Literal["read", "idempotent", "resolve_by_caller"]


def create_redis_client(config: ExpiryRedisConfig, *, retry=None):
    """Build without connecting; callers retain their own startup/retry lifecycle."""
    import redis.asyncio as redis_async

    endpoint = config.endpoints[0]
    if "://" not in endpoint:
        endpoint = ("rediss" if config.tls else "redis") + "://" + endpoint
    password = config.resolve_password()
    kwargs: dict[str, Any] = {
        "username": config.username or None,
        "password": password,
        "decode_responses": True,
        "socket_connect_timeout": config.connect_timeout_seconds,
        "socket_timeout": config.socket_timeout_seconds,
        "max_connections": config.max_connections,
    }
    if retry is not None:
        kwargs["retry"] = retry
    if config.mode == "standalone":
        return redis_async.Redis.from_url(endpoint, **kwargs)
    else:
        from redis.asyncio.cluster import ClusterNode, RedisCluster
        from redis.backoff import NoBackoff
        from redis.retry import Retry

        nodes = []
        use_tls = config.tls
        for raw in config.endpoints:
            normalized = (
                raw if "://" in raw else (("rediss" if config.tls else "redis") + f"://{raw}")
            )
            parsed = urlsplit(normalized)
            use_tls = parsed.scheme == "rediss"
            nodes.append(ClusterNode(parsed.hostname or "", parsed.port or 6379))
        # Store retry policies must be the only authority for replaying
        # commands: a lost CAS/SET NX response cannot safely be replayed.
        # These instance-local flags leave MOVED/ASK routing intact.
        kwargs.setdefault("retry", Retry(NoBackoff(), 0))
        return RedisCluster(
            startup_nodes=nodes,
            ssl=use_tls,
            cluster_error_retry_attempts=0,
            **kwargs,
        )



from .redis_store_ops import _RedisExpiryOpsMixin


class RedisExpiryStore(_RedisExpiryOpsMixin):
    def __init__(
        self,
        config: ExpiryRedisConfig,
        keys: ExpiryKeys,
        io: AsyncExecutor,
        metrics: ExpiryMetrics,
    ) -> None:
        self._config = config
        self._keys = keys
        self._io = io
        self._metrics = metrics
        self._client: Any = None
        self._scripts: dict[str, str] = {}
        self._script_shas: dict[str, str] = {}
        self._ready = False
        self._enabled_consumers: set[str] = set()

    async def open(self) -> None:
        await self._io.run(self._open_on_loop)

    async def close(self) -> None:
        self._ready = False
        if self._client is not None:
            await self._io.run(self._close_on_loop)

    async def ensure_namespace(self, spec: NamespaceSpec) -> None:
        key = self._keys.namespace()
        expected = {
            "shard_count": str(spec.shard_count),
            "hash_name": spec.hash_name,
            "hash_seed": str(spec.hash_seed),
            "identity_encoding": spec.identity_encoding,
        }
        current = await self._command("hgetall", key)
        self._enabled_consumers = {
            field.removeprefix("consumer_enabled:")
            for field, value in current.items()
            if field.startswith("consumer_enabled:") and value == "1"
        }
        initializing = True
        if current:
            normalized = {str(k): str(v) for k, v in current.items()}
            for field, value in expected.items():
                if normalized.get(field) != value:
                    raise StoreOperationError(
                        "namespace_mismatch", f"Timer namespace mismatch: {field}"
                    )
            state = normalized.get("state")
            if state not in {"INITIALIZING", "READY"}:
                raise StoreOperationError("namespace_corrupt", "Invalid timer namespace state")
            initializing = state == "INITIALIZING"
        else:
            created = dict(expected)
            created["state"] = "INITIALIZING"
            await self._command("hset", key, mapping=created, retry="idempotent")
        for shard_id in range(spec.shard_count):
            progress_key = self._keys.progress(shard_id)
            if initializing:
                await self._command("set", progress_key, "0", nx=True, retry="idempotent")
            elif await self._command("get", progress_key) is None:
                raise StoreOperationError(
                    "namespace_corrupt", f"Timer progress is missing for shard {shard_id}"
                )
        if initializing:
            await self._command("hset", key, "state", "READY", retry="idempotent")
        self._ready = True

    def consumer_enabled(self, item_type: str) -> bool:
        return item_type in self._enabled_consumers

    async def enable_consumer(self, item_type: str) -> None:
        if not self.consumer_enabled(item_type):
            await self._command(
                "hset",
                self._keys.namespace(),
                f"consumer_enabled:{item_type}",
                "1",
                retry="idempotent",
            )
            self._enabled_consumers.add(item_type)

    async def ensure_metadata(self, item_id: str, task: ExpiryRegistration) -> None:
        identity = task.identity
        await self._eval(
            "ensure_metadata",
            [self._keys.metadata(item_id)],
            [
                identity.item_type,
                identity.local_id,
                identity.account_id,
                identity.user_id,
                metadata_ttl_ms(task.timeout_seconds),
            ],
            retry="idempotent",
        )

    async def read_metadata(self, item_id: str) -> ItemMetadata | None:
        raw = await self._command("hgetall", self._keys.metadata(item_id))
        if not raw:
            return None
        required = ("item_type", "account_id", "user_id", "local_id")
        if any(name not in raw for name in required):
            raise StoreOperationError("metadata_corrupt", "Timer metadata is incomplete")
        return ItemMetadata(ItemIdentity(*(str(raw[name]) for name in required)))

    async def upsert_resource(
        self, shard_id: int, item_id: str, task: ExpiryRegistration
    ) -> ExpiryRegistrationResult:
        raw = await self._eval(
            "upsert_resource",
            [self._keys.source(shard_id)],
            [item_id, task.due_at_ms],
            retry="resolve_by_caller",
        )
        return ExpiryRegistrationResult(int(raw))

    async def unregister_resource(
        self,
        shard_id: int,
        item_id: str,
        *,
        delete_metadata: bool = True,
    ) -> None:
        await self._command("zrem", self._keys.source(shard_id), item_id, retry="idempotent")
        if delete_metadata:
            await self._single_key_command(
                "DEL",
                self._keys.metadata(item_id),
                retry="idempotent",
            )

    async def read_progress(self, shard_id: int) -> int:
        raw = await self._command("get", self._keys.progress(shard_id))
        if raw is None:
            raise StoreOperationError("namespace_corrupt", "Timer progress is missing")
        try:
            return int(raw)
        except (TypeError, ValueError) as exc:
            raise StoreOperationError("namespace_corrupt", "Timer progress is invalid") from exc

    async def read_scan_window(self, shard_id: int) -> ShardWindow:
        progress = await self.read_progress(shard_id)
        source_now_ms = await self._read_time_ms_for_key(self._keys.source(shard_id))
        upper = source_now_ms // 60_000 * 60_000
        if upper < progress:
            raise StoreOperationError(
                "clock_regression", "Source time is behind published progress"
            )
        return ShardWindow(progress, upper, source_now_ms)

    async def read_source_page(
        self,
        shard_id: int,
        *,
        lower_exclusive_ms: int,
        upper_inclusive_ms: int,
        after: SourceCursor | None,
        limit: int,
    ) -> SourcePage:
        items, next_raw = await self._read_zset_page(
            self._keys.source(shard_id),
            lower_exclusive=lower_exclusive_ms,
            upper_inclusive=upper_inclusive_ms,
            after_score=None if after is None else after.due_at_ms,
            after_member=None if after is None else after.item_id,
            limit=limit,
        )
        page_items = tuple(SourceItem(item, score) for item, score in items)
        cursor = SourceCursor(*next_raw) if next_raw else None
        return SourcePage(page_items, cursor)

    async def reset_unpublished_minute(
        self,
        owner: OwnerToken,
        *,
        minute_ms: int,
        expected_progress_ms: int,
        item_types: Sequence[str],
    ) -> None:
        await self.assert_owner(owner)
        current = await self.read_progress(owner.shard_id)
        if current != expected_progress_ms or minute_ms <= current:
            raise StoreOperationError("progress_conflict", "Timer progress changed")
        keys = [
            self._keys.bucket(BucketRef(item_type, owner.shard_id, minute_ms))
            for item_type in item_types
        ]
        # Bucket keys deliberately have no shared cluster hash tag. Delete them
        # one at a time, bypassing redis-py's cross-slot pipeline helper.
        for key in keys:
            await self._single_key_command("UNLINK", key, retry="idempotent")

    async def stage_items(
        self, owner: OwnerToken, bucket: BucketRef, item_ids: Sequence[str]
    ) -> None:
        if not item_ids:
            return
        await self.assert_owner(owner)
        mapping = dict.fromkeys(item_ids, 0)
        await self._command("zadd", self._keys.bucket(bucket), mapping, retry="resolve_by_caller")

    async def publish_minute(
        self,
        owner: OwnerToken,
        *,
        expected_progress_ms: int,
        minute_ms: int,
        buckets: Sequence[BucketRef],
    ) -> PublishResult:
        members = [self._keys.registry_member(ref) for ref in buckets]
        raw = await self._eval(
            "publish_minute",
            [
                self._keys.registry(owner.shard_id),
                self._keys.progress(owner.shard_id),
                self._keys.owner(OwnerRole.SCHEDULER, owner.shard_id),
            ],
            [owner.token, expected_progress_ms, minute_ms, len(members), *members],
            retry="resolve_by_caller",
        )
        status = str(raw[0])
        if status not in {"published", "already_published"}:
            raise StoreOperationError("namespace_corrupt", "Invalid timer publish result")
        return PublishResult(
            cast(Literal["published", "already_published"], status),
            int(raw[1]),
        )

    async def cleanup_source_page(self, shard_id: int, through_ms: int, *, limit: int) -> int:
        return int(
            await self._eval(
                "cleanup_source_page",
                [self._keys.source(shard_id)],
                [through_ms, limit],
                retry="idempotent",
            )
        )

    async def read_registry_page(
        self, shard_id: int, *, after: RegistryCursor | None, limit: int
    ) -> RegistryPage:
        items, next_raw = await self._read_zset_page(
            self._keys.registry(shard_id),
            lower_exclusive=-1,
            upper_inclusive=None,
            after_score=None if after is None else after.score_ms,
            after_member=None if after is None else after.member,
            limit=limit,
        )
        buckets = tuple(
            self._keys.parse_registry_member(str(member), expected_shard=shard_id)
            for member, _score in items
        )
        cursor = RegistryCursor(*next_raw) if next_raw else None
        return RegistryPage(buckets, cursor)

    async def read_time_ms(self) -> int:
        return self._decode_redis_time(await self._command("time"))

    @staticmethod
    def _decode_redis_time(raw: Any) -> int:
        try:
            seconds, microseconds = (int(value) for value in raw)
        except (TypeError, ValueError) as exc:
            raise StoreOperationError("namespace_corrupt", "Invalid Redis time") from exc
        if not 0 < seconds < SCORE_TIME_BASE or not 0 <= microseconds < 1_000_000:
            raise StoreOperationError("namespace_corrupt", "Redis time is outside supported range")
        return seconds * 1000 + microseconds // 1000

    async def _read_time_ms_for_key(self, key: str) -> int:
        """Read TIME from the primary owning key so source cutoffs share its clock."""

        async def operation() -> Any:
            if self._client is None:
                raise StoreOperationError("not_started", "Redis timer store is closed")
            kwargs: dict[str, object] = {}
            if self._config.mode == "cluster":
                node = self._client.get_node_from_key(key)
                if node is None:
                    raise RuntimeError("Redis Cluster has no primary for the timer key")
                kwargs["target_nodes"] = node
            return await self._client.time(**kwargs)

        raw = await self._io.run(lambda: self._run_with_retry(operation, retry="read"))
        return self._decode_redis_time(raw)

    async def _read_zset_page(
        self,
        key: str,
        *,
        lower_exclusive: int,
        upper_inclusive: int | None,
        after_score: int | None,
        after_member: str | None,
        limit: int,
    ) -> tuple[tuple[tuple[str, int], ...], tuple[int, str] | None]:
        if after_score is None:
            upper = (
                await self._read_time_ms_for_key(key)
                if upper_inclusive is None
                else upper_inclusive
            )
            raw_items = await self._command(
                "zrangebyscore",
                key,
                f"({lower_exclusive}",
                upper,
                start=0,
                num=limit + 1,
                withscores=True,
            )
            items = self._decode_zset_items(
                raw_items,
                lower_exclusive=lower_exclusive,
                upper_inclusive=upper,
            )
            has_more = len(items) > limit
            items = items[:limit]
            next_cursor = (items[-1][1], items[-1][0]) if has_more else None
            return items, next_cursor

        raw = await self._eval(
            "read_zset_page",
            [key],
            [
                lower_exclusive,
                "" if upper_inclusive is None else upper_inclusive,
                after_score,
                after_member or "",
                limit,
            ],
            retry="read",
        )
        data = json.loads(raw)
        items = tuple((str(member), int(score)) for member, score in data["items"])
        next_raw = data.get("next")
        next_cursor = (int(next_raw[0]), str(next_raw[1])) if next_raw else None
        return items, next_cursor

    @staticmethod
    def _decode_zset_items(
        raw_items: Any,
        *,
        lower_exclusive: int,
        upper_inclusive: int,
    ) -> tuple[tuple[str, int], ...]:
        items: list[tuple[str, int]] = []
        try:
            for member, raw_score in raw_items:
                numeric_score = float(raw_score)
                score = int(numeric_score)
                if numeric_score != score or score <= lower_exclusive or score > upper_inclusive:
                    raise ValueError
                items.append((str(member), score))
        except (TypeError, ValueError) as exc:
            raise StoreOperationError(
                "namespace_corrupt", "Timer sorted set contains an invalid score"
            ) from exc
        return tuple(items)

