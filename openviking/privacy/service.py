# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""User-scoped privacy config service backed by VikingFS."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

from openviking.core.namespace import canonical_user_root
from openviking.privacy.global_policy import UserGlobalPolicyService
from openviking.privacy.helpers import (
    canonicalize_values,
    config_root_uri,
    current_uri,
    history_dir_uri,
    meta_uri,
    parse_version_filename,
    read_privacy_json,
    version_uri,
    write_privacy_json,
)
from openviking.privacy.models import (
    UserPrivacyConfigMeta,
    UserPrivacyConfigVersion,
    UserPrivacyFieldDeleteResult,
)
from openviking.privacy.validation import (
    validate_privacy_field_name,
    validate_privacy_identifier,
    validate_privacy_metadata,
    validate_privacy_values,
)
from openviking.server.identity import RequestContext
from openviking.storage.viking_fs import VikingFS
from openviking.utils.time_utils import get_current_timestamp
from openviking_cli.exceptions import AlreadyExistsError, NotFoundError


class UserPrivacyConfigService:
    """Manage user-scoped privacy configs with version history."""

    def __init__(self, viking_fs: VikingFS):
        self._viking_fs = viking_fs
        self._global_policies = UserGlobalPolicyService(viking_fs)
        self._catalog_revisions: dict[tuple[str, str], int] = {}

    @property
    def global_policies(self) -> UserGlobalPolicyService:
        """Owner-scoped GLOBAL access policy cache with TTL and FIFO eviction."""
        return self._global_policies

    def catalog_revision(self, ctx: RequestContext) -> int:
        """Return the process-local revision of the caller's active value catalog."""
        return self._catalog_revisions.get((ctx.account_id, ctx.user.user_id), 0)

    def _bump_catalog_revision(self, ctx: RequestContext) -> None:
        key = (ctx.account_id, ctx.user.user_id)
        self._catalog_revisions[key] = self._catalog_revisions.get(key, 0) + 1

    def _user_root(self, ctx: RequestContext) -> str:
        return canonical_user_root(ctx)

    def _user_space(self, ctx: RequestContext) -> str:
        return self._user_root(ctx)[len("viking://user/") :]

    def get_config_root(self, ctx: RequestContext, category: str, target_key: str) -> str:
        return config_root_uri(self._user_space(ctx), category, target_key)

    async def exists(self, ctx: RequestContext, category: str, target_key: str) -> bool:
        uri = current_uri(self._user_space(ctx), category, target_key)
        stat_fn = getattr(self._viking_fs, "stat", None)
        try:
            if callable(stat_fn):
                await stat_fn(uri, ctx=ctx, skip_count=True)
            else:
                await self._viking_fs.read_file(uri, ctx=ctx)
            return True
        except (NotFoundError, FileNotFoundError):
            return False

    async def delete(
        self,
        ctx: RequestContext,
        category: str,
        target_key: str,
        *,
        owner_lease_ref: Optional[dict[str, Any]] = None,
    ) -> bool:
        root_uri = self.get_config_root(ctx, category, target_key)
        async with self._config_lock(
            ctx, category, target_key, owner_lease_ref=owner_lease_ref
        ) as lease:
            if not await self.exists(ctx, category, target_key):
                return False
            if owner_lease_ref is not None:
                await self._clear_contents(ctx, category, target_key, lease)
            else:
                await self._viking_fs.rm(root_uri, recursive=True, ctx=ctx, lease_ref=lease)
            self._bump_catalog_revision(ctx)
            return True

    async def _clear_contents(
        self,
        ctx: RequestContext,
        category: str,
        target_key: str,
        lease_ref: Optional[dict[str, Any]],
    ) -> None:
        """Clear config data under an existing lock, preserving the locked root."""
        root = self.get_config_root(ctx, category, target_key)
        for name in (".meta.json", "current.json", "history"):
            uri = f"{root}/{name}"
            if await self._viking_fs.exists(uri, ctx=ctx):
                await self._viking_fs.rm(
                    uri, recursive=name == "history", ctx=ctx, lease_ref=lease_ref
                )

    async def _ensure_root(
        self,
        ctx: RequestContext,
        category: str,
        target_key: str,
        lease_ref: Optional[dict[str, Any]] = None,
    ) -> None:
        root_uri = self.get_config_root(ctx, category, target_key)
        await self._viking_fs.mkdir(root_uri, exist_ok=True, ctx=ctx, lease_ref=lease_ref)
        await self._viking_fs.mkdir(
            history_dir_uri(self._user_space(ctx), category, target_key),
            exist_ok=True,
            ctx=ctx,
            lease_ref=lease_ref,
        )

    @asynccontextmanager
    async def _config_lock(
        self,
        ctx: RequestContext,
        category: str,
        target_key: str,
        *,
        owner_lease_ref: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[Optional[dict[str, Any]]]:
        uri_to_path = getattr(self._viking_fs, "_uri_to_path", None)
        agfs = getattr(self._viking_fs, "_async_agfs", None)
        acquire = getattr(agfs, "pathlock_acquire_tree", None)
        release = getattr(agfs, "pathlock_release", None)
        if not callable(uri_to_path) or not callable(acquire) or not callable(release):
            yield None
            return
        kwargs: dict[str, Any] = {"timeout_secs": 30.0}
        if owner_lease_ref is not None:
            kwargs["owner_lease_ref"] = owner_lease_ref
        lease = await acquire(uri_to_path(self.get_config_root(ctx, category, target_key), ctx=ctx), **kwargs)
        try:
            yield lease
        finally:
            await release(lease)

    async def get_meta(
        self, ctx: RequestContext, category: str, target_key: str
    ) -> Optional[UserPrivacyConfigMeta]:
        data = await read_privacy_json(
            self._viking_fs, meta_uri(self._user_space(ctx), category, target_key), ctx
        )
        return None if data is None else UserPrivacyConfigMeta.from_dict(data)

    async def _save_meta(
        self,
        ctx: RequestContext,
        category: str,
        target_key: str,
        meta: UserPrivacyConfigMeta,
        lease_ref: Optional[dict[str, Any]] = None,
    ) -> None:
        meta.updated_at = get_current_timestamp()
        await write_privacy_json(
            self._viking_fs,
            meta_uri(self._user_space(ctx), category, target_key),
            meta.to_dict(),
            ctx,
            lease_ref,
        )

    async def get_current(
        self, ctx: RequestContext, category: str, target_key: str
    ) -> Optional[UserPrivacyConfigVersion]:
        data = await read_privacy_json(
            self._viking_fs, current_uri(self._user_space(ctx), category, target_key), ctx
        )
        return None if data is None else UserPrivacyConfigVersion.from_dict(data)

    async def get_version(
        self, ctx: RequestContext, category: str, target_key: str, version: int
    ) -> Optional[UserPrivacyConfigVersion]:
        data = await read_privacy_json(
            self._viking_fs, version_uri(self._user_space(ctx), category, target_key, version), ctx
        )
        return None if data is None else UserPrivacyConfigVersion.from_dict(data)

    async def list_categories(self, ctx: RequestContext) -> list[str]:
        uri = f"{self._user_root(ctx)}/privacy"
        try:
            entries = await self._viking_fs.ls(uri, ctx=ctx)
        except (NotFoundError, FileNotFoundError):
            return []
        return sorted(entry["name"] for entry in entries if entry.get("name"))

    async def list_targets(self, ctx: RequestContext, category: str) -> list[str]:
        validate_privacy_identifier(category, "category")
        uri = f"{self._user_root(ctx)}/privacy/{category}"
        try:
            entries = await self._viking_fs.ls(uri, ctx=ctx)
        except (NotFoundError, FileNotFoundError):
            return []
        return sorted(entry["name"] for entry in entries if entry.get("name"))

    async def list_versions(self, ctx: RequestContext, category: str, target_key: str) -> list[int]:
        try:
            entries = await self._viking_fs.ls(
                history_dir_uri(self._user_space(ctx), category, target_key), ctx=ctx
            )
        except (NotFoundError, FileNotFoundError):
            return []
        versions = [
            v
            for entry in entries
            if (v := parse_version_filename(entry.get("name", ""))) is not None
        ]
        return sorted(versions)

    async def upsert(
        self,
        ctx: RequestContext,
        category: str,
        target_key: str,
        values: dict[str, Any],
        updated_by: str = "",
        change_reason: str = "",
        labels: Optional[dict[str, Any]] = None,
        *,
        owner_lease_ref: Optional[dict[str, Any]] = None,
        preserve_fields: Optional[set[str]] = None,
    ) -> UserPrivacyConfigVersion:
        async with self._config_lock(
            ctx, category, target_key, owner_lease_ref=owner_lease_ref
        ) as lease:
            current = await self.get_current(ctx, category, target_key)
            if preserve_fields:
                retained = (
                    {key: value for key, value in current.values.items() if key in preserve_fields}
                    if current is not None
                    else {}
                )
                values = {**retained, **values}
            return await self._upsert_locked(
                ctx=ctx,
                category=category,
                target_key=target_key,
                values=values,
                updated_by=updated_by,
                change_reason=change_reason,
                labels=labels,
                lease_ref=lease,
                current=current,
            )

    async def patch_values(
        self,
        ctx: RequestContext,
        category: str,
        target_key: str,
        updates: dict[str, Any],
        updated_by: str = "",
        change_reason: str = "",
        labels: Optional[dict[str, Any]] = None,
    ) -> UserPrivacyConfigVersion:
        """Atomically update named fields, preserving independent fields with equal values."""
        async with self._config_lock(ctx, category, target_key) as lease:
            current = await self.get_current(ctx, category, target_key)
            values = dict(current.values) if current is not None else {}
            values.update(updates)
            return await self._upsert_locked(
                ctx=ctx,
                category=category,
                target_key=target_key,
                values=values,
                updated_by=updated_by,
                change_reason=change_reason,
                labels=labels,
                lease_ref=lease,
                current=current,
            )

    async def insert_values(
        self,
        ctx: RequestContext,
        category: str,
        target_key: str,
        updates: dict[str, Any],
        updated_by: str = "",
        change_reason: str = "",
        labels: Optional[dict[str, Any]] = None,
    ) -> UserPrivacyConfigVersion:
        """Atomically add new fields; labels apply only when creating the target."""
        async with self._config_lock(ctx, category, target_key) as lease:
            current = await self.get_current(ctx, category, target_key)
            values = dict(current.values) if current is not None else {}
            if not values.keys().isdisjoint(updates):
                raise AlreadyExistsError(f"{category}/{target_key}", "privacy field")
            values.update(updates)
            return await self._upsert_locked(
                ctx=ctx,
                category=category,
                target_key=target_key,
                values=values,
                updated_by=updated_by,
                change_reason=change_reason,
                labels=labels if current is None else None,
                lease_ref=lease,
                current=current,
            )

    async def _publish_snapshot(
        self,
        *,
        ctx: RequestContext,
        category: str,
        target_key: str,
        version_number: int,
        values: dict[str, Any],
        updated_by: str,
        change_reason: str,
        meta: Optional[UserPrivacyConfigMeta],
        labels: Optional[dict[str, Any]],
        lease_ref: Optional[dict[str, Any]],
    ) -> UserPrivacyConfigVersion:
        now = get_current_timestamp()
        snapshot = UserPrivacyConfigVersion(
            version=version_number,
            category=category,
            target_key=target_key,
            values=dict(values),
            created_at=now,
            created_by=updated_by,
            change_reason=change_reason,
        )
        payload = snapshot.to_dict()
        user_space = self._user_space(ctx)
        await write_privacy_json(
            self._viking_fs, version_uri(user_space, category, target_key, version_number), payload, ctx, lease_ref
        )
        await write_privacy_json(
            self._viking_fs, current_uri(user_space, category, target_key), payload, ctx, lease_ref
        )
        if meta is None:
            meta = UserPrivacyConfigMeta(category=category, target_key=target_key, created_at=now)
        meta.active_version = version_number
        meta.latest_version = version_number
        meta.updated_by = updated_by
        meta.last_accessed_at = now
        if labels is not None:
            meta.labels = dict(labels)
        await self._save_meta(ctx, category, target_key, meta, lease_ref)
        self._bump_catalog_revision(ctx)
        return snapshot

    async def _upsert_locked(
        self,
        *,
        ctx: RequestContext,
        category: str,
        target_key: str,
        values: dict[str, Any],
        updated_by: str,
        change_reason: str,
        labels: Optional[dict[str, Any]],
        lease_ref: Optional[dict[str, Any]],
        current: Optional[UserPrivacyConfigVersion],
    ) -> UserPrivacyConfigVersion:
        """Persist a complete snapshot while the caller holds the target lock."""
        validate_privacy_values(values, category=category)
        validate_privacy_metadata(change_reason=change_reason, labels=labels)
        await self._ensure_root(ctx, category, target_key, lease_ref)
        now = get_current_timestamp()
        meta = await self.get_meta(ctx, category, target_key)
        if current and canonicalize_values(current.values) == canonicalize_values(values):
            if meta is None:
                meta = UserPrivacyConfigMeta(
                    category=category,
                    target_key=target_key,
                    active_version=current.version,
                    latest_version=current.version,
                    created_at=now,
                )
            meta.updated_by = updated_by
            meta.last_accessed_at = now
            if labels is not None:
                meta.labels = dict(labels)
            await self._save_meta(ctx, category, target_key, meta, lease_ref)
            return current
        version_number = 1 if meta is None else meta.latest_version + 1
        return await self._publish_snapshot(
            ctx=ctx,
            category=category,
            target_key=target_key,
            version_number=version_number,
            values=values,
            updated_by=updated_by,
            change_reason=change_reason,
            meta=meta,
            labels=labels,
            lease_ref=lease_ref,
        )

    async def activate_version(
        self,
        ctx: RequestContext,
        category: str,
        target_key: str,
        version: int,
        updated_by: str = "",
        *,
        owner_lease_ref: Optional[dict[str, Any]] = None,
    ) -> UserPrivacyConfigVersion:
        async with self._config_lock(
            ctx, category, target_key, owner_lease_ref=owner_lease_ref
        ) as lease:
            meta = await self.get_meta(ctx, category, target_key)
            snapshot = await self.get_version(ctx, category, target_key, version)
            if meta is None or snapshot is None:
                raise NotFoundError(f"{category}/{target_key}/versions/{version}", "privacy config")
            await write_privacy_json(
                self._viking_fs,
                current_uri(self._user_space(ctx), category, target_key),
                snapshot.to_dict(),
                ctx,
                lease,
            )
            meta.active_version = version
            meta.updated_by = updated_by
            meta.last_accessed_at = get_current_timestamp()
            await self._save_meta(ctx, category, target_key, meta, lease)
            self._bump_catalog_revision(ctx)
            return snapshot

    async def delete_field(
        self,
        ctx: RequestContext,
        category: str,
        target_key: str,
        field: str,
        updated_by: str = "",
    ) -> Optional[UserPrivacyFieldDeleteResult]:
        """Remove one field from the active values by publishing a new snapshot."""
        validate_privacy_field_name(field, location="field")
        async with self._config_lock(ctx, category, target_key) as lease:
            meta = await self.get_meta(ctx, category, target_key)
            current = await self.get_current(ctx, category, target_key)
            if meta is None or current is None or field not in current.values:
                return None
            values = dict(current.values)
            values.pop(field)
            if not values:
                await self._viking_fs.rm(
                    self.get_config_root(ctx, category, target_key),
                    recursive=True,
                    ctx=ctx,
                    lease_ref=lease,
                )
                self._bump_catalog_revision(ctx)
                return UserPrivacyFieldDeleteResult(
                    category=category, target_key=target_key, field=field, target_deleted=True
                )
            snapshot = await self._publish_snapshot(
                ctx=ctx,
                category=category,
                target_key=target_key,
                version_number=meta.latest_version + 1,
                values=values,
                updated_by=updated_by,
                change_reason=f"delete field: {field}",
                meta=meta,
                labels=None,
                lease_ref=lease,
            )
            return UserPrivacyFieldDeleteResult(
                category=category,
                target_key=target_key,
                field=field,
                target_deleted=False,
                active_version=snapshot.version,
            )
