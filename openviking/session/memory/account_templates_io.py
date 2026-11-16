# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Account-scoped template files with a restricted public editing contract."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable, Coroutine
from copy import deepcopy
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import yaml
from jinja2 import Environment, TemplateSyntaxError

from openviking.core.namespace_policy import SYSTEM_MEMORY_CUSTOM_ROOT
from openviking.pyagfs import AGFSAlreadyExistsError, AGFSNotFoundError, AsyncAGFSClient
from openviking.pyagfs.async_client import fs_ctx_from_agfs_path
from openviking.session.memory.dataclass import MemoryTypeSchema
from openviking.session.memory.memory_type_registry import MemoryTypeRegistry, get_default_registry
from openviking.session.memory.utils.content_template import (
    CONTENT_TEMPLATE_FIELDS,
    ContentTemplateError,
    validate_content_template,
)
from openviking.session.memory.utils.description_template import (
    MAX_DESCRIPTION_CHARS,
    DescriptionTemplateError,
    validate_description_template,
)
from openviking.storage.errors import LockAcquisitionError, ResourceBusyError
from openviking_cli.exceptions import FailedPreconditionError, InvalidArgumentError, NotFoundError
from openviking_cli.session.user_id import validate_account_id
from openviking_cli.utils.logger import get_logger

if TYPE_CHECKING:
    from openviking.storage.viking_fs import VikingFS

logger = get_logger(__name__)
_MAX_CONFIG_BYTES = 1024 * 1024
_TEMPLATE_LOCK_TIMEOUT_SECONDS = 10.0
_TEMPLATE_LOCK_RETRY_SECONDS = 0.05

from openviking.session.memory.account_templates_yaml import (
    EDITABLE_MEMORY_TEMPLATE_FIELDS,
    _EDITABLE_CONTENT_TEMPLATES,
    _ReadableTemplateDumper,
    _apply_editable_values,
    _complete_template,
    _parse_template,
    _read_raw,
    _read_unchecked_raw,
    _validate_memory_type,
    _validate_template,
    account_memory_template_path,
    account_memory_template_uri,
    default_memory_template,
    legacy_account_memory_template_path,
    memory_template_data,
)

async def _finish_storage_call(
    operation: Coroutine[Any, Any, Any],
    *,
    on_cancel: Callable[[Any], Awaitable[None]] | None = None,
):
    """Drain submitted native I/O before propagating cancellation.

    Cancelling an asyncio waiter cannot stop its worker thread. Keep the worker's
    result reachable, and (for acquisition) release a lease won during cancellation.
    Locked writes include their own release in a finally block.
    """
    task = asyncio.create_task(operation)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:

        async def finish():
            try:
                result = await task
            except Exception:
                logger.debug("Template storage call failed while cancelling", exc_info=True)
            else:
                if on_cancel is not None:
                    await on_cancel(result)

        cleanup = asyncio.create_task(finish())
        while not cleanup.done():
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                # Repeated cancellation must not interrupt lease cleanup either.
                continue
        cleanup.result()
        raise


async def _acquire_template_lock(client: AsyncAGFSClient, paths: list[str], uri: str):
    # Keep the cross-process lock, but never wait for contention in a worker:
    # the holder needs that same executor to finish its I/O and release the lease.
    loop = asyncio.get_running_loop()
    deadline = loop.time() + _TEMPLATE_LOCK_TIMEOUT_SECONDS
    primary_path = paths[0]

    async def release_cancelled_acquire(lease):
        await client.pathlock_release(lease, fs_ctx=fs_ctx_from_agfs_path(primary_path))

    while True:
        try:
            return await _finish_storage_call(
                client.pathlock_acquire_exact_batch(paths, timeout_secs=0.0),
                on_cancel=release_cancelled_acquire,
            )
        except LockAcquisitionError as exc:
            remaining = deadline - loop.time()
            if remaining > 0:
                await asyncio.sleep(min(_TEMPLATE_LOCK_RETRY_SECONDS, remaining))
                if loop.time() < deadline:
                    continue
            raise ResourceBusyError(
                "Another memory template operation is in progress. Please retry.",
                uri=uri,
                conflict_type="memory_templates_busy",
            ) from exc


def memory_template_result(
    registry: MemoryTypeRegistry, custom: dict | None, memory_type: str
) -> dict:
    defaults = default_memory_template(registry, memory_type)
    effective = dict(custom) if custom is not None else deepcopy(defaults)
    updated_at = effective.pop("_updated_at", None)
    return {
        "memory_type": memory_type,
        "status": "custom" if custom is not None else "system_default",
        "updated_at": updated_at,
        "defaults": defaults,
        "effective": effective,
    }


async def _publish_template(
    client: AsyncAGFSClient, path: str, staging_path: str, encoded: bytes, fs_ctx: dict
) -> None:
    """Publish a complete file through same-mount AGFS rename/object replacement.

    The caller's lease covers BOTH paths. LocalFS renames the staged file; S3
    copies the whole staged object to the destination before deleting the source.
    Never overwrite/restore the active file in place, including on failure.
    """
    try:
        await client.write(staging_path, encoded, fs_ctx=fs_ctx)
        try:
            await client.mv(staging_path, path, fs_ctx=fs_ctx)
        except Exception:
            # An S3 move can publish successfully and then fail deleting its
            # source. Acknowledge only a verified published version; if state
            # cannot be verified, propagate the error without a destructive rollback.
            try:
                published = await _read_raw(client, path) == encoded
            except Exception:
                published = False
            if not published:
                raise
            logger.warning("Template move reported an error after publication: %s", path)
    finally:
        try:
            await client.rm(staging_path, fs_ctx=fs_ctx)
        except AGFSNotFoundError:
            pass
        except Exception:
            # Cleanup cannot undo a published version or mask the original error.
            logger.warning(
                "Failed to clean up staged memory template: %s", staging_path, exc_info=True
            )


async def _update_locked_template(
    client: AsyncAGFSClient,
    path: str,
    legacy_path: str,
    backup_path: str,
    staging_path: str | None,
    memory_type: str,
    complete: dict | None,
    encoded: bytes | None,
    lease,
):
    fs_ctx = fs_ctx_from_agfs_path(path)
    lease_ref = getattr(lease, "lease_ref", None) or getattr(lease, "id", None)
    if isinstance(lease, dict):
        lease_ref = lease.get("lease_ref", lease_ref)
    if lease_ref:
        fs_ctx["lease_ref"] = lease_ref
    try:
        raw = await _read_unchecked_raw(client, path)
        legacy_raw = await _read_unchecked_raw(client, legacy_path)
        active_raw = raw if raw is not None else legacy_raw
        current = None
        if active_raw is not None and len(active_raw) <= _MAX_CONFIG_BYTES:
            try:
                current = _parse_template(active_raw, memory_type)
            except FailedPreconditionError:
                # Explicit PUT/DELETE is the recovery path for damaged persisted
                # content, so allow the operation to replace or remove it.
                pass
        if complete is None and active_raw is None:
            await _remove_obsolete_backup(client, backup_path, fs_ctx)
            return None
        if complete is not None and raw is not None and current is not None:
            if {k: v for k, v in current.items() if k != "_updated_at"} == {
                k: v for k, v in complete.items() if k != "_updated_at"
            }:
                if legacy_raw is not None:
                    try:
                        await client.rm(legacy_path, fs_ctx=fs_ctx)
                    except AGFSNotFoundError:
                        pass
                    except Exception as exc:
                        raise FailedPreconditionError(
                            "Memory template is published, but legacy cleanup failed. "
                            "Retry the request.",
                            details={
                                "published": True,
                                "legacy_cleanup_pending": True,
                                "retryable": True,
                            },
                        ) from exc
                await _remove_obsolete_backup(client, backup_path, fs_ctx)
                return current
        try:
            await client.ensure_parent_dirs(path)
        except AGFSAlreadyExistsError:
            pass
        if complete is None:
            try:
                await client.rm(legacy_path, fs_ctx=fs_ctx)
            except AGFSNotFoundError:
                pass
            except Exception as exc:
                raise FailedPreconditionError(
                    "Failed to remove the legacy memory template. Retry the request.",
                    details={"legacy_cleanup_pending": True, "retryable": True},
                ) from exc
            try:
                await client.rm(path, fs_ctx=fs_ctx)
            except AGFSNotFoundError:
                pass
            except Exception as exc:
                raise FailedPreconditionError(
                    "Failed to remove the current memory template. Retry the request.",
                    details={"current_cleanup_pending": True, "retryable": True},
                ) from exc
        else:
            assert staging_path is not None and encoded is not None
            await _publish_template(client, path, staging_path, encoded, fs_ctx)
            try:
                await client.rm(legacy_path, fs_ctx=fs_ctx)
            except AGFSNotFoundError:
                pass
            except Exception as exc:
                raise FailedPreconditionError(
                    "Memory template is published, but legacy cleanup failed. Retry the request.",
                    details={
                        "published": True,
                        "legacy_cleanup_pending": True,
                        "retryable": True,
                    },
                ) from exc
        await _remove_obsolete_backup(client, backup_path, fs_ctx)
        logger.info("Updated account memory template: %s reset=%s", path, complete is None)
        return complete
    finally:
        await client.pathlock_release(lease, fs_ctx=fs_ctx_from_agfs_path(path))


async def _remove_obsolete_backup(client: AsyncAGFSClient, backup_path: str, fs_ctx: dict) -> None:
    try:
        await client.rm(backup_path, fs_ctx=fs_ctx)
    except AGFSNotFoundError:
        pass
    except Exception:
        logger.warning("Failed to remove obsolete memory template backup: %s", backup_path)


