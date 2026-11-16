# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Admin endpoints for OpenViking multi-tenant HTTP Server."""

from __future__ import annotations

import asyncio
from contextlib import nullcontext

from fastapi import APIRouter, Depends, Path, Query, Request

from openviking.config.scope import ConfigScope
from openviking.config.validate import ConfigPatchError
from openviking.server.account_settings import (
    AccountAclSettings,
    AccountAgentEvolutionSettings,
    AccountSettingsPatch,
    read_account_settings,
    update_account_settings,
)
from openviking.server.auth import (
    get_request_context,
    require_auth_root,
    require_auth_root_or_admin,
    should_expose_user_key,
)
from openviking.server.config import validate_config_input
from openviking.server.dependencies import get_service
from openviking.server.identity import RequestContext, Role
from openviking.server.models import Response
from openviking.server.routers.admin_config import router as admin_config_router
from openviking.server.routers.admin_models import (
    CreateAccountRequest,
    LegacyAccountSettingsPatch,
    MigrateLegacyDataRequest,
    SetAgentEvolutionRequest,
    account_settings_result,
    agent_evolution_account_id,
    call_manager,
    check_account_access,
    check_account_exists,
    get_api_key_manager,
    get_runtime_config_manager,
    get_runtime_config_manager_optional,
    rollback_account_creation,
    run_legacy_migration_task,
    sync_account_acl_flag,
    validate_initial_user_config,
    write_initial_user_config,
)
from openviking.server.routers.admin_users import router as admin_users_router
from openviking.service.legacy_migration import LegacyDataMigration
from openviking.service.task_store import SYSTEM_TASK_ACCOUNT_ID, SYSTEM_TASK_USER_ID
from openviking.service.task_tracker import get_task_tracker
from openviking.storage.viking_fs import get_viking_fs
from openviking_cli.exceptions import FailedPreconditionError, InvalidArgumentError, NotFoundError
from openviking_cli.session.user_id import UserIdentifier
from openviking_cli.utils.config import get_openviking_config
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

# Re-exported for openviking.ttl.internal and compatibility tests
_check_account_exists = check_account_exists
_get_runtime_config_manager = get_runtime_config_manager


def _get_api_key_manager(request: Request, *, for_write: bool = False):
    return get_api_key_manager(request, for_write=for_write)


_get_api_key_manager._is_default_admin_hook = True  # type: ignore[attr-defined]

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
router.include_router(admin_config_router)
router.include_router(admin_users_router)


@router.get("/agent-evolution", deprecated=True)
@require_auth_root_or_admin
async def get_agent_evolution_status(
    request: Request,
    ctx: RequestContext = Depends(get_request_context),
):
    """Return the effective Agent Evolution switch for the caller's account."""
    account_id = agent_evolution_account_id(ctx)
    await check_account_exists(request, account_id)
    enabled = await get_service().sessions.get_agent_evolution_enabled(account_id)
    return Response(status="ok", result={"enabled": enabled, "account_id": account_id})


@router.put("/agent-evolution", deprecated=True)
@require_auth_root_or_admin
async def set_agent_evolution_status(
    body: SetAgentEvolutionRequest,
    request: Request,
    ctx: RequestContext = Depends(get_request_context),
):
    """Persist and hot-reload Agent Evolution for the caller's account."""
    account_id = agent_evolution_account_id(ctx)
    await check_account_exists(request, account_id)
    service = get_service()
    if service.viking_fs is None:
        raise FailedPreconditionError("OpenViking service is not initialized.")
    runtime_config = get_runtime_config_manager_optional()
    if runtime_config is not None:
        try:
            await runtime_config.patch_account(account_id, {"agent_evolution": {"enabled": body.enabled}})
        except (ConfigPatchError, ValueError) as exc:
            raise InvalidArgumentError(str(exc)) from exc
    else:
        await update_account_settings(
            service.viking_fs,
            account_id,
            AccountSettingsPatch(agent_evolution=AccountAgentEvolutionSettings(enabled=body.enabled)),
        )
    enabled = await service.sessions.get_agent_evolution_enabled(account_id)
    return Response(status="ok", result={"enabled": enabled, "account_id": account_id})


@router.post("/accounts")
@require_auth_root
async def create_account(
    body: CreateAccountRequest,
    request: Request,
    ctx: RequestContext = Depends(get_request_context),
):
    """Create a new account (workspace) with its first admin user."""
    validate_config_input(body.settings)
    service = get_service()
    account_ctx = RequestContext(user=UserIdentifier(body.account_id, body.admin_user_id), role=Role.ADMIN)
    validate_config_input(body.user_config)
    await validate_initial_user_config(service, account_ctx, body.user_config)

    runtime_config = get_runtime_config_manager_optional()
    if runtime_config is not None:
        try:
            runtime_config.validate_initial_settings(body.account_id, body.settings or {})
        except (ConfigPatchError, ValueError) as exc:
            raise InvalidArgumentError(str(exc)) from exc
    elif body.settings:
        raise FailedPreconditionError("Runtime config manager is not initialized.")

    manager = get_api_key_manager(request, for_write=True)
    user_key = None
    account_created = False
    lock_cm = (
        service.account_workspace_lock(account_ctx)
        if hasattr(service, "account_workspace_lock") and getattr(service, "viking_fs", None) is not None
        else nullcontext(None)
    )
    try:
        async with lock_cm as lease:
            user_key = await call_manager(
                manager.create_account,
                body.account_id,
                body.admin_user_id,
                seed=body.seed,
                lease_ref=lease,
            )
            account_created = True
            if body.settings and runtime_config is not None:
                await runtime_config.patch_account(
                    body.account_id, body.settings, creating=True, lease_ref=lease
                )
                if "acl" in body.settings and isinstance(body.settings["acl"], dict):
                    if "enabled" in body.settings["acl"]:
                        sync_account_acl_flag(
                            service, body.account_id, bool(body.settings["acl"]["enabled"])
                        )
            if hasattr(service, "initialize_account_workspace"):
                await service.initialize_account_workspace(account_ctx, lease_ref=lease)
            else:
                await service.initialize_account_directories(account_ctx)
                await service.initialize_user_directories(account_ctx)
            await write_initial_user_config(service, account_ctx, body.user_config, lease_ref=lease)
    except BaseException:
        if account_created:
            await rollback_account_creation(
                service,
                manager,
                body.account_id,
                runtime_config,
                deletion_service=getattr(request.app.state, "deletion_service", None),
                actor=ctx,
            )
        raise
    result = {"account_id": body.account_id, "admin_user_id": body.admin_user_id}
    if should_expose_user_key(request):
        result["user_key"] = user_key
    return Response(status="ok", result=result)


@router.get("/accounts")
@require_auth_root
async def list_accounts(
    request: Request,
    name: str | None = None,
    limit: int | None = Query(None, ge=1, description="Page size; omit to return all"),
    page: int = Query(1, ge=1, description="1-based page number (requires limit)"),
    query: str | None = Query(None, description="Case-insensitive account id substring"),
    ctx: RequestContext = Depends(get_request_context),
):
    """List accounts in creation order. `name` supports wildcard (* and ?) matching."""
    accounts = await get_api_key_manager(request).list_accounts(
        name_filter=name, limit=limit, page=page, query_filter=query
    )
    return Response(status="ok", result=accounts)


@router.get("/metric-inventory")
@require_auth_root
async def metric_inventory(
    request: Request,
    account_id: str | None = None,
    page_size: int = Query(500, ge=1, le=1000),
    ctx: RequestContext = Depends(get_request_context),
):
    """Stream metadata only for an offline scan."""
    from fastapi.responses import StreamingResponse
    from openviking.observability.reporting.inventory import inventory_lines

    manager = get_api_key_manager(request)
    return StreamingResponse(
        inventory_lines(get_service(), manager, account_id=account_id, page_size=page_size),
        media_type="application/x-ndjson",
    )


@router.get("/accounts/{account_id}")
@require_auth_root
async def get_account(
    request: Request,
    account_id: str,
    ctx: RequestContext = Depends(get_request_context),
):
    """Return credential-free metadata for one account, or 404 if absent."""
    account = await get_api_key_manager(request).get_account(account_id)
    if account is None:
        raise NotFoundError(account_id, "account")
    return Response(status="ok", result=account)


@router.post("/migrate")
@require_auth_root
async def migrate_legacy_data(
    request: Request,
    body: MigrateLegacyDataRequest | None = None,
    ctx: RequestContext = Depends(get_request_context),
):
    """Preflight and enqueue legacy agent/session data migration or cleanup."""
    manager = get_api_key_manager(request)
    service = get_service()
    if service.viking_fs is None:
        raise FailedPreconditionError("OpenViking service is not initialized.")
    action = (body.action if body else "migrate").strip().lower()
    if action not in {"migrate", "cleanup"}:
        raise InvalidArgumentError("Migration action must be 'migrate' or 'cleanup'.")
    migration = LegacyDataMigration(viking_fs=service.viking_fs, api_key_manager=manager, service=service)
    if action == "migrate":
        plan = await migration.preflight()
        if plan.errors:
            raise FailedPreconditionError(
                "Legacy migration preflight failed.", details=plan.to_preflight_result()
            )
    tracker = get_task_tracker()
    task_type = "legacy_cleanup" if action == "cleanup" else "legacy_migration"
    resource_id = "legacy-data-cleanup" if action == "cleanup" else "legacy-data"
    task = await tracker.create(
        task_type,
        resource_id=resource_id,
        account_id=SYSTEM_TASK_ACCOUNT_ID,
        user_id=SYSTEM_TASK_USER_ID,
    )
    asyncio.create_task(
        run_legacy_migration_task(
            task.task_id,
            migration,
            action=action,
            account_id=SYSTEM_TASK_ACCOUNT_ID,
            user_id=SYSTEM_TASK_USER_ID,
        )
    )
    return Response(status="ok", result={"task_id": task.task_id})


@router.delete("/accounts/{account_id}")
@require_auth_root
async def delete_account(
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    """Delete an account and cascade-clean its storage (AGFS + VectorDB)."""
    deletion_service = getattr(request.app.state, "deletion_service", None)
    if deletion_service is not None:
        get_api_key_manager(request, for_write=True)
        result = await deletion_service.delete(account_id, actor=ctx)
        return Response(status="ok", result=result)
    manager = get_api_key_manager(request, for_write=True)
    viking_fs = get_viking_fs()
    try:
        await viking_fs._async_agfs.rm(f"/local/{account_id}", recursive=True)
    except Exception as e:
        logger.warning(f"AGFS cleanup for account {account_id}: {e}")
    try:
        storage = viking_fs._get_vector_store()
        if storage:
            deleted = await storage.delete_account_data(account_id, ctx=ctx)
            logger.info(f"VectorDB cascade delete for account {account_id}: {deleted} records")
    except Exception as e:
        logger.warning(f"VectorDB cleanup for account {account_id}: {e}")
    await manager.delete_account(account_id)
    return Response(status="ok", result={"deleted": True})


@router.get("/accounts/{account_id}/settings", deprecated=True)
@require_auth_root_or_admin
async def get_account_settings(
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    """Return effective and explicitly overridden settings for one account."""
    check_account_access(ctx, account_id)
    await check_account_exists(request, account_id)
    runtime_config = get_runtime_config_manager_optional()
    if runtime_config is not None:
        acl_setting = await runtime_config.get_account(account_id, "acl")
        overrides = await runtime_config.get_settings(ConfigScope.account(account_id))
        return Response(
            status="ok", result=await account_settings_result(account_id, acl_setting, overrides)
        )
    service = get_service()
    if service.viking_fs is None:
        raise FailedPreconditionError("OpenViking service is not initialized.")
    settings = await read_account_settings(service.viking_fs, account_id)
    return Response(status="ok", result=await account_settings_result(account_id, settings))


@router.patch("/accounts/{account_id}/settings", deprecated=True)
@require_auth_root_or_admin
async def patch_account_settings(
    request: Request,
    body: LegacyAccountSettingsPatch,
    account_id: str = Path(..., description="Account ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    """Update allowlisted hot-reloadable settings for one account."""
    check_account_access(ctx, account_id)
    await check_account_exists(request, account_id)
    service = get_service()
    if service.viking_fs is None:
        raise FailedPreconditionError("OpenViking service is not initialized.")
    runtime_config = get_runtime_config_manager_optional()
    if runtime_config is not None:
        patch = body.model_dump(exclude_none=True)
        try:
            if patch:
                await runtime_config.patch_account(account_id, patch)
        except (ConfigPatchError, ValueError) as exc:
            raise InvalidArgumentError(str(exc)) from exc
        if body.acl is not None:
            sync_account_acl_flag(service, account_id, body.acl.enabled)
        acl_setting = await runtime_config.get_account(account_id, "acl")
        overrides = await runtime_config.get_settings(ConfigScope.account(account_id))
        return Response(
            status="ok", result=await account_settings_result(account_id, acl_setting, overrides)
        )
    legacy_patch = AccountSettingsPatch(
        agent_evolution=(
            AccountAgentEvolutionSettings(enabled=body.agent_evolution.enabled)
            if body.agent_evolution is not None
            else None
        ),
        acl=AccountAclSettings(enabled=body.acl.enabled) if body.acl is not None else None,
    )
    settings = await update_account_settings(service.viking_fs, account_id, legacy_patch)
    return Response(status="ok", result=await account_settings_result(account_id, settings))
