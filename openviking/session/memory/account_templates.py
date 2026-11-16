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
    _validate_memory_type,
    _validate_template,
    account_memory_template_path,
    account_memory_template_uri,
    default_memory_template,
    legacy_account_memory_template_path,
    memory_template_data,
)
from openviking.session.memory.account_templates_io import (
    _acquire_template_lock,
    _finish_storage_call,
    _publish_template,
    _remove_obsolete_backup,
    _update_locked_template,
    memory_template_result,
)
from openviking.session.memory.account_templates_yaml import (
    _managed_memory_type_for_uri,
    _read_raw,
    _read_unchecked_raw,
    normalize_account_memory_template_write,
    validate_account_memory_template_transfer,
)

async def read_account_memory_template(
    viking_fs: VikingFS, account_id: str, memory_type: str
) -> dict | None:
    path = account_memory_template_path(account_id, memory_type)
    legacy_path = legacy_account_memory_template_path(account_id, memory_type)
    client = AsyncAGFSClient(viking_fs.agfs)
    # Publication switches a fully-written staging file into place. Readers may
    # see either complete version (or no override after DELETE), without a lock.
    raw = await _read_raw(client, path)
    if raw is not None:
        return _parse_template(raw, memory_type)
    return _parse_template(await _read_raw(client, legacy_path), memory_type)


async def update_account_memory_template(
    viking_fs: VikingFS,
    account_id: str,
    memory_type: str,
    template: dict | None,
    registry: MemoryTypeRegistry,
) -> dict | None:
    """Publish a full template, or delete its override to restore deployment defaults."""
    defaults = default_memory_template(registry, memory_type)
    complete = None
    encoded = None
    if template is not None:
        try:
            complete = _complete_template(defaults, template, memory_type)
        except DescriptionTemplateError as exc:
            raise InvalidArgumentError(
                str(exc),
                details={"field": exc.field, "reason": exc.reason, "line": exc.line},
            ) from exc
        except ContentTemplateError as exc:
            raise InvalidArgumentError(
                str(exc),
                details={"field": "content_template", "reason": exc.reason, "line": exc.line},
            ) from exc
        except (ValueError, TypeError, KeyError, AttributeError, TemplateSyntaxError) as exc:
            raise InvalidArgumentError(f"Invalid memory template: {exc}") from exc
        # Saving an unchanged default form (including per-field resets) removes
        # the override through the same locked path as DELETE. Compare before
        # adding publication metadata; any remaining edit keeps it custom.
        if complete == defaults:
            complete = None
        else:
            complete["_updated_at"] = datetime.now(timezone.utc).isoformat()
            encoded = yaml.dump(
                complete,
                Dumper=_ReadableTemplateDumper,
                allow_unicode=True,
                sort_keys=False,
            ).encode("utf-8")
            if len(encoded) > _MAX_CONFIG_BYTES:
                raise InvalidArgumentError("A memory template must not exceed 1 MiB")

    path = account_memory_template_path(account_id, memory_type)
    legacy_path = legacy_account_memory_template_path(account_id, memory_type)
    backup_path = f"{path}.backup"
    staging_path = f"{path}.{uuid.uuid4().hex}.tmp" if complete is not None else None
    client = AsyncAGFSClient(viking_fs.agfs)
    lock_paths = [path, legacy_path, backup_path]
    if staging_path is not None:
        lock_paths.append(staging_path)
    lease = await _acquire_template_lock(
        client, lock_paths, account_memory_template_uri(memory_type)
    )
    return await _finish_storage_call(
        _update_locked_template(
            client,
            path,
            legacy_path,
            backup_path,
            staging_path,
            memory_type,
            complete,
            encoded,
            lease,
        )
    )


async def resolve_account_memory_registry(
    viking_fs: VikingFS, account_id: str, registry: MemoryTypeRegistry
) -> MemoryTypeRegistry:
    """Snapshot account types over server-owned deployment defaults, without mutating them."""
    schemas = registry.list_all(include_disabled=True)
    templates = await asyncio.gather(
        *(read_account_memory_template(viking_fs, account_id, s.memory_type) for s in schemas)
    )
    resolved = MemoryTypeRegistry(load_schemas=False)
    for schema, template in zip(schemas, templates, strict=True):
        try:
            resolved.register(
                _validate_template(
                    template,
                    schema.memory_type,
                    deployment_defaults=memory_template_data(schema),
                )
                if template is not None
                else schema.model_copy(deep=True)
            )
        except (ContentTemplateError, DescriptionTemplateError) as exc:
            raise FailedPreconditionError(
                f"Invalid account {getattr(exc, 'field', 'content_template')} "
                f"for {schema.memory_type}; republish or reset it"
            ) from exc
    return resolved
