# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""User and group management endpoints under /api/v1/admin."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Path, Query, Request

from openviking.server.api_keys.models import validate_account_user_creation_role
from openviking.server.auth import (
    get_request_context,
    is_personal_api_key_auth,
    require_auth_role,
    require_auth_root_or_admin,
    should_expose_user_key,
)
from openviking.server.config import ServerConfig, validate_config_input
from openviking.server.dependencies import get_service
from openviking.server.identity import ACCOUNT_USER_ASSIGNABLE_ROLES, RequestContext, Role
from openviking.server.models import Response
from openviking.server.routers.admin_models import (
    CreateGroupRequest,
    GroupMembersRequest,
    RegenerateKeyRequest,
    RegisterUserRequest,
    SetRoleRequest,
    call_manager,
    check_account_access,
    check_account_exists,
    check_user_exists,
    get_api_key_manager,
    maybe_await,
    reject_global_role_change_target,
    reject_non_root_global_target,
    user_settings_result,
    validate_initial_user_config,
    write_initial_user_config,
)
from openviking.server.user_config import patch_user_config, read_user_config
from openviking_cli.exceptions import (
    FailedPreconditionError,
    InvalidArgumentError,
    NotFoundError,
    PermissionDeniedError,
)
from openviking_cli.session.user_id import UserIdentifier

router = APIRouter()


@router.post("/accounts/{account_id}/users")
@require_auth_root_or_admin
async def register_user(
    body: RegisterUserRequest,
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    """Register a new user in an account."""
    check_account_access(ctx, account_id)
    resolved_role = validate_account_user_creation_role(body.role)
    if resolved_role == Role.GLOBAL and ctx.role != Role.ROOT:
        raise PermissionDeniedError("Only ROOT can create GLOBAL identities")
    service = get_service()
    user_ctx = RequestContext(user=UserIdentifier(account_id, body.user_id), role=resolved_role)
    validate_config_input(body.user_config)
    await validate_initial_user_config(service, user_ctx, body.user_config)
    manager = get_api_key_manager(request, for_write=True)
    user_key = await manager.register_user(
        account_id,
        body.user_id,
        str(resolved_role),
        seed=body.seed,
    )
    await service.initialize_user_directories(user_ctx)
    await write_initial_user_config(service, user_ctx, body.user_config)
    result = {"account_id": account_id, "user_id": body.user_id}
    if should_expose_user_key(request):
        result["user_key"] = user_key
    return Response(status="ok", result=result)


@router.get("/accounts/{account_id}/users")
@require_auth_role(Role.ROOT, Role.ADMIN, Role.USER)
async def list_users(
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    limit: int | None = Query(None, ge=1, description="Page size; omit to return all"),
    include_credentials: bool = Query(True),
    name: str | None = None,
    role: str | None = None,
    page: int = Query(1, ge=1, description="1-based page number (requires limit)"),
    query: str | None = Query(None, description="Case-insensitive username substring"),
    include_summary: bool = Query(False),
    ctx: RequestContext = Depends(get_request_context),
):
    """List users in an account, in creation order."""
    check_account_access(ctx, account_id)
    manager = get_api_key_manager(request)
    expose_key = should_expose_user_key(request) or not include_credentials
    if ctx.role == Role.USER:
        expose_key = expose_key and is_personal_api_key_auth(request, ctx)
    users = await manager.list_users_page(
        account_id,
        limit=limit,
        name_filter=name,
        role_filter=role,
        expose_key=expose_key,
        mask_keys=include_credentials and ctx.role != Role.ROOT,
        hide_other_keys=ctx.role == Role.USER,
        viewer_account_id=ctx.account_id,
        viewer_user_id=ctx.user.user_id,
        page=page,
        query_filter=query,
    )
    if not include_credentials:
        users["users"] = [
            {
                "user_id": user["user_id"],
                "role": user["role"],
                **(
                    {"api_key_available": bool(user.get("api_key"))}
                    if ctx.role != Role.USER or user["user_id"] == ctx.user.user_id
                    else {}
                ),
            }
            for user in users["users"]
        ]
    if ctx.role == Role.USER:
        users.pop("key_count", None)
    return Response(status="ok", result=users if include_summary else users["users"])


@router.get("/accounts/{account_id}/users/{user_id}")
@require_auth_root_or_admin
async def get_user(
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    user_id: str = Path(..., description="User ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    """Return one user's credential-free membership info, or 404 if absent."""
    check_account_access(ctx, account_id)
    user = await get_api_key_manager(request).get_user_membership(account_id, user_id)
    if user is None:
        raise NotFoundError(user_id, "user")
    return Response(status="ok", result={"user_id": user_id, "role": user["role"]})


@router.get("/accounts/{account_id}/users/{user_id}/settings")
@require_auth_role(Role.ROOT, Role.ADMIN, Role.USER)
async def get_user_settings(
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    user_id: str = Path(..., description="User ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    """Return effective add targets, memory policy, and explicit User TTL."""
    check_account_access(ctx, account_id)
    if ctx.role == Role.USER and user_id != ctx.user.user_id:
        raise PermissionDeniedError("USER can only access their own settings")
    await reject_non_root_global_target(request, ctx, account_id, user_id)
    manager = await check_account_exists(request, account_id)
    await check_user_exists(request, account_id, user_id, manager)
    service = get_service()
    if service.viking_fs is None:
        raise FailedPreconditionError("OpenViking service is not initialized.")
    user_ctx = RequestContext(user=UserIdentifier(account_id, user_id), role=Role.USER)
    user_config = await read_user_config(service.viking_fs, user_ctx)
    server_config = getattr(request.app.state, "config", None) or ServerConfig()
    return Response(status="ok", result=user_settings_result(user_ctx, user_config, server_config))


@router.patch("/accounts/{account_id}/users/{user_id}/settings")
@require_auth_role(Role.ROOT, Role.ADMIN, Role.USER)
async def patch_user_settings(
    body: Any = Body(...),
    request: Request = None,  # type: ignore[assignment]
    account_id: str = Path(..., description="Account ID"),
    user_id: str = Path(..., description="User ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    """Patch User add targets, memory policy and TTL without restarting."""
    from openviking.server.config import UserSettingsPatch

    patch_body = body if isinstance(body, UserSettingsPatch) else UserSettingsPatch.model_validate(body)
    check_account_access(ctx, account_id)
    if ctx.role == Role.USER and user_id != ctx.user.user_id:
        raise PermissionDeniedError("USER can only access their own settings")
    await reject_non_root_global_target(request, ctx, account_id, user_id)
    manager = await check_account_exists(request, account_id)
    await check_user_exists(request, account_id, user_id, manager)
    service = get_service()
    if service.viking_fs is None:
        raise FailedPreconditionError("OpenViking service is not initialized.")
    user_ctx = RequestContext(user=UserIdentifier(account_id, user_id), role=Role.USER)
    validate_config_input(patch_body)
    user_config = await patch_user_config(service.viking_fs, user_ctx, patch_body)
    server_config = getattr(request.app.state, "config", None) or ServerConfig()
    return Response(status="ok", result=user_settings_result(user_ctx, user_config, server_config))


@router.delete("/accounts/{account_id}/users/{user_id}", status_code=202)
@require_auth_root_or_admin
async def remove_user(
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    user_id: str = Path(..., description="User ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    """Revoke a user and start durable cleanup of their owned data."""
    check_account_access(ctx, account_id)
    await reject_non_root_global_target(request, ctx, account_id, user_id)
    get_api_key_manager(request, for_write=True)
    deletion_service = getattr(request.app.state, "deletion_service", None)
    if deletion_service is not None:
        result = await deletion_service.delete(account_id, user_id, actor=ctx)
        return Response(status="ok", result=result)
    user_deletion_service = getattr(request.app.state, "user_deletion_service", None)
    if user_deletion_service is None:
        raise FailedPreconditionError("User deletion service is not initialized.")
    result = await user_deletion_service.delete_user(account_id, user_id, actor=ctx)
    return Response(status="ok", result=result)


@router.put("/accounts/{account_id}/users/{user_id}/role")
@require_auth_root_or_admin
async def set_user_role(
    body: SetRoleRequest,
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    user_id: str = Path(..., description="User ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    """Change an account user's role (USER <-> ADMIN)."""
    check_account_access(ctx, account_id)
    await reject_non_root_global_target(request, ctx, account_id, user_id)
    await reject_global_role_change_target(request, account_id, user_id)
    role = body.role.lower()
    if role not in ACCOUNT_USER_ASSIGNABLE_ROLES:
        raise InvalidArgumentError("set_user_role only supports user and admin roles.")
    await get_api_key_manager(request, for_write=True).set_role(account_id, user_id, role)
    return Response(
        status="ok",
        result={"account_id": account_id, "user_id": user_id, "role": role},
    )


@router.post("/accounts/{account_id}/users/{user_id}/key")
@require_auth_role(Role.ROOT, Role.ADMIN, Role.USER)
async def regenerate_key(
    request: Request,
    body: RegenerateKeyRequest | None = Body(default=None),
    account_id: str = Path(..., description="Account ID"),
    user_id: str = Path(..., description="User ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    """Regenerate a user's API key. Old key is immediately invalidated."""
    check_account_access(ctx, account_id)
    await reject_non_root_global_target(request, ctx, account_id, user_id)
    if ctx.role == Role.USER:
        if user_id != ctx.user.user_id:
            raise PermissionDeniedError("USER can only regenerate their own API key")
        if not is_personal_api_key_auth(request, ctx):
            raise PermissionDeniedError("Self-service key rotation requires a personal API key")
    manager = get_api_key_manager(request, for_write=True)
    new_key = await call_manager(
        manager.regenerate_key,
        account_id,
        user_id,
        seed=body.seed if body is not None else None,
        expected_api_key=ctx.api_key if ctx.role == Role.USER else None,
    )
    return Response(status="ok", result={"user_key": new_key})


# ---- Group endpoints ----


@router.post("/accounts/{account_id}/groups")
@require_auth_root_or_admin
async def create_group(
    body: CreateGroupRequest,
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    check_account_access(ctx, account_id)
    result = await get_api_key_manager(request, for_write=True).create_group(
        account_id, body.group_id
    )
    return Response(status="ok", result=result)


@router.get("/accounts/{account_id}/groups")
@require_auth_root_or_admin
async def list_groups(
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    check_account_access(ctx, account_id)
    result = await maybe_await(get_api_key_manager(request).get_groups(account_id))
    return Response(status="ok", result=result)


@router.delete("/accounts/{account_id}/groups/{group_id}")
@require_auth_root_or_admin
async def delete_group(
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    group_id: str = Path(..., description="Group ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    check_account_access(ctx, account_id)
    manager = get_api_key_manager(request, for_write=True)
    for member_id in await maybe_await(manager.get_group_members(account_id, group_id)):
        await reject_non_root_global_target(request, ctx, account_id, member_id)
    await manager.delete_group(account_id, group_id)
    return Response(status="ok", result={"deleted": True})


@router.get("/accounts/{account_id}/groups/{group_id}/members")
@require_auth_root_or_admin
async def list_group_members(
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    group_id: str = Path(..., description="Group ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    check_account_access(ctx, account_id)
    members = await maybe_await(
        get_api_key_manager(request).get_group_members(account_id, group_id)
    )
    return Response(status="ok", result={"group_id": group_id, "members": members})


@router.put("/accounts/{account_id}/groups/{group_id}/members")
@require_auth_root_or_admin
async def add_group_members(
    body: GroupMembersRequest,
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    group_id: str = Path(..., description="Group ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    check_account_access(ctx, account_id)
    for member_id in body.user_ids:
        await reject_non_root_global_target(request, ctx, account_id, member_id)
    added = await get_api_key_manager(request, for_write=True).add_group_members(
        account_id, group_id, body.user_ids
    )
    return Response(status="ok", result={"added": added})


@router.delete("/accounts/{account_id}/groups/{group_id}/members")
@require_auth_root_or_admin
async def remove_group_members(
    body: GroupMembersRequest,
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    group_id: str = Path(..., description="Group ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    check_account_access(ctx, account_id)
    for member_id in body.user_ids:
        await reject_non_root_global_target(request, ctx, account_id, member_id)
    removed = await get_api_key_manager(request, for_write=True).remove_group_members(
        account_id, group_id, body.user_ids
    )
    return Response(status="ok", result={"removed": removed})


@router.put("/accounts/{account_id}/groups/{group_id}/members/{user_id}")
@require_auth_root_or_admin
async def add_group_member(
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    group_id: str = Path(..., description="Group ID"),
    user_id: str = Path(..., description="User ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    check_account_access(ctx, account_id)
    await reject_non_root_global_target(request, ctx, account_id, user_id)
    added = await get_api_key_manager(request, for_write=True).add_group_member(
        account_id, group_id, user_id
    )
    return Response(status="ok", result={"added": added})


@router.delete("/accounts/{account_id}/groups/{group_id}/members/{user_id}")
@require_auth_root_or_admin
async def remove_group_member(
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    group_id: str = Path(..., description="Group ID"),
    user_id: str = Path(..., description="User ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    check_account_access(ctx, account_id)
    await reject_non_root_global_target(request, ctx, account_id, user_id)
    removed = await get_api_key_manager(request, for_write=True).remove_group_member(
        account_id, group_id, user_id
    )
    return Response(status="ok", result={"removed": removed})
