# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Shared request schemas and helper utilities for Admin routers."""

from __future__ import annotations

import inspect
import sys
from collections.abc import Mapping
from typing import Annotated, Any, Optional

from fastapi import Request
from pydantic import BaseModel, Field

from openviking.config.scope import ConfigScope
from openviking.server.account_settings import AccountSettings, effective_acl_enabled
from openviking.server.auth import get_api_key_manager_or_raise
from openviking.server.config import ServerConfig, UserConfig
from openviking.server.dependencies import get_service
from openviking.server.identity import RequestContext, Role
from openviking.server.user_config import (
    resolve_add_targets,
    resolve_user_add_targets,
    validate_resource_add_target,
    validate_skill_add_target,
    write_user_config,
)
from openviking.service.legacy_migration import LegacyDataMigration
from openviking.service.task_tracker import get_task_tracker
from openviking.session.memory.memory_type_registry import MemoryTypeRegistry, get_default_registry
from openviking.session.memory_policy import MemoryPolicy
from openviking_cli.exceptions import (
    FailedPreconditionError,
    InvalidArgumentError,
    NotFoundError,
    PermissionDeniedError,
)
from openviking_cli.utils.config import get_openviking_config
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

_ROOT_ONLY_ACCOUNT_CONFIG_SECTIONS = frozenset(
    {"vlm", "query_planner", "embedding", "vectordb", "parser_api"}
)


class CreateAccountRequest(BaseModel):
    account_id: str
    admin_user_id: str
    seed: str | None = None
    user_config: UserConfig | None = None
    settings: dict[str, Any] | None = None


class RegisterUserRequest(BaseModel):
    user_id: str
    role: str = "user"
    seed: str | None = None
    user_config: UserConfig | None = None


class SetRoleRequest(BaseModel):
    role: str


class RegenerateKeyRequest(BaseModel):
    seed: str | None = None


class CreateGroupRequest(BaseModel):
    model_config = {"extra": "forbid"}
    group_id: str


class GroupMembersRequest(BaseModel):
    model_config = {"extra": "forbid"}
    user_ids: list[Annotated[str, Field(min_length=1)]] = Field(min_length=1, max_length=1000)


class SetAgentEvolutionRequest(BaseModel):
    enabled: bool


class LegacyAccountAgentEvolutionSettings(BaseModel):
    enabled: bool
    model_config = {"extra": "forbid"}


class LegacyAccountAclSettings(BaseModel):
    enabled: bool = False
    model_config = {"extra": "forbid"}


class LegacyAccountSettingsPatch(BaseModel):
    agent_evolution: Optional[LegacyAccountAgentEvolutionSettings] = None
    acl: Optional[LegacyAccountAclSettings] = None
    model_config = {"extra": "forbid"}


class MigrateLegacyDataRequest(BaseModel):
    action: str = "migrate"
    model_config = {"extra": "forbid"}


class ConfigPatchRequest(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)
    revision: str | None = None
    content: str | None = None


async def maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def call_manager(fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Invoke manager method dropping unsupported optional kwargs cleanly."""
    try:
        sig = inspect.signature(fn)
        has_var_kw = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        if not has_var_kw:
            kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
    except (TypeError, ValueError):
        pass
    return await maybe_await(fn(*args, **kwargs))


def agent_evolution_account_id(ctx: RequestContext) -> str:
    if ctx.role == Role.ROOT:
        admin_mod = sys.modules.get("openviking.server.routers.admin")
        cfg_fn = getattr(admin_mod, "get_openviking_config", get_openviking_config)
        return cfg_fn().default_account
    return ctx.account_id


def get_api_key_manager(request: Request, *, for_write: bool = False):
    admin_mod = sys.modules.get("openviking.server.routers.admin")
    hook = getattr(admin_mod, "_get_api_key_manager", None) if admin_mod is not None else None
    if hook is not None and not getattr(hook, "_is_default_admin_hook", False):
        manager = hook(request)
    else:
        manager = get_api_key_manager_or_raise(request)
    if for_write and hasattr(manager, "require_writable"):
        manager.require_writable()
    return manager


def get_runtime_config_manager():
    service = get_service()
    manager = getattr(service, "runtime_config_manager", None)
    if manager is None:
        raise FailedPreconditionError("Runtime config manager is not initialized.")
    return manager


def get_runtime_config_manager_optional():
    service = get_service()
    return getattr(service, "runtime_config_manager", None)


def sync_account_acl_flag(service: Any, account_id: str, enabled: bool) -> None:
    vikingdb = getattr(service, "_vikingdb_manager", None)
    acl_manager = getattr(vikingdb, "acl_manager", None) if vikingdb is not None else None
    if acl_manager is not None and hasattr(acl_manager, "set_enabled"):
        acl_manager.set_enabled(account_id, bool(enabled))


def check_account_access(ctx: RequestContext, account_id: str) -> None:
    if ctx.role != Role.ROOT and ctx.account_id != account_id:
        raise PermissionDeniedError(f"{ctx.role} can only access account: {ctx.account_id}")


async def reject_non_root_global_target(
    request: Request, ctx: RequestContext, account_id: str, user_id: str
) -> None:
    if ctx.role == Role.ROOT:
        return
    manager = getattr(request.app.state, "api_key_manager", None)
    if manager is None:
        return
    user = await manager.get_user_membership(account_id, user_id)
    if user is not None and user["role"] == Role.GLOBAL:
        raise PermissionDeniedError("Only ROOT can manage GLOBAL identities")


async def reject_global_role_change_target(
    request: Request, account_id: str, user_id: str
) -> None:
    manager = getattr(request.app.state, "api_key_manager", None)
    if manager is None:
        return
    user = await manager.get_user_membership(account_id, user_id)
    if user is not None and user["role"] == Role.GLOBAL:
        raise InvalidArgumentError(
            "GLOBAL identities cannot change roles; delete and recreate instead."
        )


async def check_account_exists(request: Request, account_id: str):
    manager = getattr(request.app.state, "api_key_manager", None)
    if manager is None:
        return None
    account = await manager.get_account(account_id)
    if account is None:
        raise NotFoundError(account_id, "account")
    if account.get("status", "active") != "active":
        raise FailedPreconditionError(
            "Account is not active",
            details={"task_id": account.get("task_id")},
        )
    return manager


async def check_user_exists(
    request: Request, account_id: str, user_id: str, manager=None
) -> None:
    manager = manager or get_api_key_manager(request)
    if await manager.get_user_for_management(account_id, user_id) is None:
        raise NotFoundError(user_id, "user")


def authorize_account_config_patch(ctx: RequestContext, settings: Mapping[str, object]) -> None:
    restricted = _ROOT_ONLY_ACCOUNT_CONFIG_SECTIONS.intersection(settings)
    if restricted and ctx.role != Role.ROOT:
        fields = ", ".join(sorted(restricted))
        raise PermissionDeniedError(f"Only ROOT can modify account configuration fields: {fields}")


async def account_configuration_settings(ctx: RequestContext, account_id: str) -> dict[str, object]:
    settings = await get_runtime_config_manager().get_settings(ConfigScope.account(account_id))
    settings["agent_evolution"] = {
        "enabled": await get_service().sessions.get_agent_evolution_enabled(account_id)
    }
    if ctx.role == Role.ROOT:
        return settings
    return {
        key: value
        for key, value in settings.items()
        if key not in _ROOT_ONLY_ACCOUNT_CONFIG_SECTIONS
    }


async def account_settings_result(
    account_id: str,
    acl_or_settings: Any,
    overrides: Optional[dict] = None,
) -> dict:
    enabled = await get_service().sessions.get_agent_evolution_enabled(account_id)
    if isinstance(acl_or_settings, AccountSettings):
        acl_enabled = effective_acl_enabled(acl_or_settings)
        raw_overrides = acl_or_settings.model_dump(exclude_none=True)
    else:
        acl_enabled = bool(getattr(acl_or_settings, "enabled", False)) if acl_or_settings else False
        src = overrides or {}
        raw_overrides = {k: src[k] for k in ("agent_evolution", "acl") if k in src}
    return {
        "account_id": account_id,
        "settings": {
            "agent_evolution": {"enabled": enabled},
            "acl": {"enabled": acl_enabled},
        },
        "overrides": raw_overrides,
    }


def has_initial_user_config(user_config: UserConfig | None) -> bool:
    return bool(
        user_config
        and (
            user_config.add_targets.resource_uri
            or user_config.add_targets.skill_uri
            or user_config.memory_policy
            or getattr(user_config, "ttl", None) is not None
        )
    )


async def validate_initial_user_config(
    service: Any,
    user_ctx: RequestContext,
    user_config: UserConfig | None,
) -> None:
    if not has_initial_user_config(user_config) or user_config is None:
        return
    if service.viking_fs is None:
        raise FailedPreconditionError("OpenViking service is not initialized.")
    if user_config.add_targets.resource_uri:
        await validate_resource_add_target(
            user_config.add_targets.resource_uri, ctx=user_ctx, viking_fs=service.viking_fs
        )
    if user_config.add_targets.skill_uri:
        await validate_skill_add_target(
            user_config.add_targets.skill_uri, ctx=user_ctx, viking_fs=service.viking_fs
        )
    if user_config.memory_policy is not None:
        MemoryPolicy.from_dict(user_config.memory_policy)


async def write_initial_user_config(
    service: Any,
    user_ctx: RequestContext,
    user_config: UserConfig | None,
    *,
    lease_ref: object | None = None,
) -> None:
    if not has_initial_user_config(user_config):
        return
    await write_user_config(service.viking_fs, user_ctx, user_config, lease_ref=lease_ref)


async def rollback_account_creation(
    service: Any,
    manager: Any,
    account_id: str,
    runtime_config: Any,
    deletion_service: Any = None,
    actor: RequestContext | None = None,
) -> None:
    if deletion_service is not None and actor is not None and hasattr(deletion_service, "delete_now"):
        try:
            await deletion_service.delete_now(account_id, actor=actor)
            return
        except Exception:
            logger.exception("Synchronous account cleanup failed for %s", account_id)
            return
    try:
        if hasattr(service, "release_account_vector_resources"):
            await service.release_account_vector_resources(account_id)
    except Exception:
        logger.exception("Failed to release vector resources for account %s", account_id)
    if runtime_config is not None:
        try:
            await runtime_config.delete_account(account_id)
        except Exception:
            logger.exception("Failed to roll back runtime config for account %s", account_id)
    agfs = getattr(getattr(service, "viking_fs", None), "_async_agfs", None)
    if agfs is not None:
        try:
            await agfs.rm(f"/local/{account_id}", recursive=True)
        except Exception:
            logger.exception("Failed to roll back workspace for account %s", account_id)
    try:
        await manager.delete_account(account_id)
    except Exception:
        logger.exception("Failed to roll back account registry entry for %s", account_id)


def user_settings_result(
    ctx: RequestContext,
    user_config: UserConfig,
    server_config: ServerConfig,
) -> dict:
    defaults = getattr(server_config, "user_config_defaults", None)
    default_policy = getattr(defaults, "memory_policy", None)
    memory_policy_config = (
        user_config.memory_policy if user_config.memory_policy is not None else default_policy
    )
    memory_policy = MemoryPolicy.default().to_dict()
    memory_policy.update(memory_policy_config or {})
    if memory_policy.get("memory_types") is None:
        try:
            types = get_default_registry().list_names(include_disabled=False)
        except Exception:
            types = MemoryTypeRegistry().list_names(include_disabled=False)
        memory_policy["memory_types"] = sorted(types)
    add_targets = resolve_add_targets(resolve_user_add_targets(user_config, server_config), ctx=ctx)
    ttl_val = getattr(user_config, "ttl", None)
    return {
        "account_id": ctx.account_id,
        "user_id": ctx.user.user_id,
        "add_targets": {
            "resource_uri": add_targets.resource_uri,
            "skill_uri": add_targets.skill_uri,
        },
        "memory_policy": memory_policy,
        "ttl": ttl_val.model_dump(by_alias=True, exclude_none=True) if ttl_val is not None else None,
    }


async def run_legacy_migration_task(
    task_id: str,
    migration: LegacyDataMigration,
    *,
    action: str,
    account_id: str,
    user_id: str,
) -> None:
    tracker = get_task_tracker()
    await tracker.start(task_id, account_id=account_id, user_id=user_id, stage="running")
    try:
        result = await (migration.cleanup() if action == "cleanup" else migration.run())
    except Exception as exc:
        await tracker.fail(task_id, str(exc), account_id=account_id, user_id=user_id)
        logger.exception("Legacy %s task %s failed", action, task_id)
        return
    await tracker.complete(task_id, result, account_id=account_id, user_id=user_id)
