# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Runtime configuration, memory templates, model connection probes, and restart routes."""

from __future__ import annotations

import asyncio
from typing import Any, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Path, Query, Request
from fastapi import Response as HTTPResponse
from pydantic import BaseModel, Field

from openviking.config.scope import ConfigScope
from openviking.config.validate import ConfigPatchError
from openviking.server.auth import (
    get_request_context,
    require_auth_root,
    require_auth_root_or_admin,
)
from openviking.server.config import validate_config_input
from openviking.server.dependencies import get_service
from openviking.server.identity import RequestContext, Role
from openviking.server.models import Response
from openviking.server.routers.admin_models import (
    ConfigPatchRequest,
    account_configuration_settings,
    authorize_account_config_patch,
    check_account_access,
    check_account_exists,
    check_user_exists,
    get_runtime_config_manager,
    reject_non_root_global_target,
    sync_account_acl_flag,
)
from openviking.server.user_config import read_user_config
from openviking.session.memory.account_templates import (
    EDITABLE_MEMORY_TEMPLATE_FIELDS,
    default_memory_template,
    memory_template_result,
    read_account_memory_template,
    update_account_memory_template,
)
from openviking.session.memory.memory_type_registry import get_default_registry
from openviking_cli.exceptions import FailedPreconditionError, InvalidArgumentError
from openviking_cli.session.user_id import UserIdentifier

router = APIRouter()


class ModelConnectionTestRequest(BaseModel):
    kind: Literal["vlm", "embedding"]
    config: dict[str, Any]
    fallback: dict[str, Any] = Field(default_factory=dict)
    thinking: bool | None = None
    mode: Literal["dense", "sparse", "hybrid"] = "dense"


class RestartRequest(BaseModel):
    revision: str = Field(min_length=1)


async def _memory_template_service(request: Request, ctx: RequestContext, account_id: str):
    check_account_access(ctx, account_id)
    await check_account_exists(request, account_id)
    service = get_service()
    if service.viking_fs is None:
        raise FailedPreconditionError("OpenViking service is not initialized.")
    return service


@router.get("/accounts/{account_id}/configuration")
@require_auth_root_or_admin
async def get_account_configuration(
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    path: Optional[str] = Query(None),
    ctx: RequestContext = Depends(get_request_context),
):
    """Return account settings with the effective Agent Evolution switch."""
    check_account_access(ctx, account_id)
    manager = await check_account_exists(request, account_id)
    result: dict[str, Any] = {
        "account_id": account_id,
        "settings": await account_configuration_settings(ctx, account_id),
    }
    if path is not None:
        from openviking.config.ttl import resolve_effective_ttl, validate_ttl_root
        from openviking.core.namespace import uri_parts

        try:
            validate_ttl_root(path, allow_peer_scope=True)
        except ValueError as exc:
            raise InvalidArgumentError(str(exc)) from exc
        user_id = uri_parts(path)[1]
        await reject_non_root_global_target(request, ctx, account_id, user_id)
        await check_user_exists(request, account_id, user_id, manager)
        user_ctx = RequestContext(user=UserIdentifier(account_id, user_id), role=Role.USER)
        config = await read_user_config(get_service().viking_fs, user_ctx)
        policy = await get_runtime_config_manager().resolve_account(
            account_id,
            lambda v: resolve_effective_ttl(v.cluster.ttl, v.account.ttl, path, config.ttl),
        )
        result["user_ttl"] = (
            config.ttl.model_dump(by_alias=True, exclude_none=True) if config.ttl else None
        )
        result["path"] = path
        result["effective_policy"] = policy.days if policy.enabled else "disabled"
    return Response(status="ok", result=result)


@router.patch("/accounts/{account_id}/configuration")
@require_auth_root_or_admin
async def patch_account_configuration(
    body: ConfigPatchRequest,
    request: Request,
    account_id: str = Path(..., description="Account ID"),
    ctx: RequestContext = Depends(get_request_context),
):
    """Apply a three-state PATCH to the account configuration layer."""
    check_account_access(ctx, account_id)
    await check_account_exists(request, account_id)
    authorize_account_config_patch(ctx, body.settings)
    validate_config_input(body.settings)
    try:
        if "ttl" in body.settings:
            from openviking.ttl.wiring import get_ttl_adapter

            await get_ttl_adapter().patch_configuration(body.settings, account_id)
        else:
            await get_runtime_config_manager().patch_account(account_id, body.settings)
    except (ConfigPatchError, ValueError) as exc:
        raise InvalidArgumentError(str(exc)) from exc
    if "acl" in body.settings and isinstance(body.settings["acl"], dict):
        if "enabled" in body.settings["acl"]:
            sync_account_acl_flag(get_service(), account_id, bool(body.settings["acl"]["enabled"]))
    return Response(
        status="ok",
        result={
            "account_id": account_id,
            "settings": await account_configuration_settings(ctx, account_id),
        },
    )


@router.get("/accounts/{account_id}/memory-templates")
@require_auth_root_or_admin
async def list_memory_templates(
    request: Request,
    account_id: str,
    ctx: RequestContext = Depends(get_request_context),
):
    """List full defaults and account overrides for the six editable memory templates."""
    service = await _memory_template_service(request, ctx, account_id)
    registry = get_default_registry()
    names = list(EDITABLE_MEMORY_TEMPLATE_FIELDS)
    templates = await asyncio.gather(
        *(read_account_memory_template(service.viking_fs, account_id, name) for name in names)
    )
    return Response(
        status="ok",
        result={
            "account_id": account_id,
            "templates": [
                memory_template_result(registry, template, name)
                for name, template in zip(names, templates, strict=True)
            ],
        },
    )


@router.get("/accounts/{account_id}/memory-templates/{memory_type}")
@require_auth_root_or_admin
async def get_memory_template(
    request: Request,
    account_id: str,
    memory_type: str,
    ctx: RequestContext = Depends(get_request_context),
):
    """Read one template's full defaults and effective account configuration."""
    service = await _memory_template_service(request, ctx, account_id)
    registry = get_default_registry()
    default_memory_template(registry, memory_type)
    config = await read_account_memory_template(service.viking_fs, account_id, memory_type)
    return Response(
        status="ok",
        result={"account_id": account_id, **memory_template_result(registry, config, memory_type)},
    )


@router.put("/accounts/{account_id}/memory-templates/{memory_type}")
@require_auth_root_or_admin
async def put_memory_template(
    request: Request,
    account_id: str,
    memory_type: str,
    body: dict = Body(...),
    ctx: RequestContext = Depends(get_request_context),
):
    """Fill omitted values from deployment defaults and publish a complete YAML template."""
    service = await _memory_template_service(request, ctx, account_id)
    registry = get_default_registry()
    config = await update_account_memory_template(
        service.viking_fs, account_id, memory_type, body, registry
    )
    return Response(
        status="ok",
        result={"account_id": account_id, **memory_template_result(registry, config, memory_type)},
    )


@router.delete("/accounts/{account_id}/memory-templates/{memory_type}")
@require_auth_root_or_admin
async def reset_memory_template(
    request: Request,
    account_id: str,
    memory_type: str,
    ctx: RequestContext = Depends(get_request_context),
):
    """Remove one template override without rewriting existing memories."""
    service = await _memory_template_service(request, ctx, account_id)
    registry = get_default_registry()
    config = await update_account_memory_template(
        service.viking_fs, account_id, memory_type, None, registry
    )
    return Response(
        status="ok",
        result={"account_id": account_id, **memory_template_result(registry, config, memory_type)},
    )


@router.post("/configuration/test-model", include_in_schema=False)
@require_auth_root
async def test_model_configuration(
    body: ModelConnectionTestRequest,
    request: Request,
    response: HTTPResponse,
    ctx: RequestContext = Depends(get_request_context),
):
    """Private Studio operation; drafts are never saved or installed at runtime."""
    from openviking.server.model_connection_test import probe_model

    response.headers["Cache-Control"] = "no-store"
    result = await probe_model(body.kind, body.config, body.fallback, body.thinking, body.mode)
    return Response(status="ok", result=result)


@router.get("/configuration")
@require_auth_root
async def get_cluster_configuration(
    request: Request,
    response: HTTPResponse,
    source: str = Query("runtime", pattern="^(runtime|file)$"),
    account_id: str | None = Query(None),
    ctx: RequestContext = Depends(get_request_context),
):
    """Return the cluster layer's explicit runtime configuration or file draft."""
    runtime_config = get_runtime_config_manager()
    if source == "file":
        from openviking.config.config_file import read_config_file

        response.headers["Cache-Control"] = "no-store"
        try:
            result = await asyncio.to_thread(
                read_config_file, getattr(request.app.state, "server_config_overrides", None)
            )
        except (ValueError, OSError) as exc:
            raise FailedPreconditionError(
                "Cannot read the server startup configuration file"
            ) from exc
        cluster = await runtime_config.get_settings(ConfigScope.cluster())
        account = (
            await runtime_config.get_settings(ConfigScope.account(account_id)) if account_id else {}
        )
        model_kinds = ("vlm", "embedding", "query_planner", "rerank")
        result["overrides"] = {
            "cluster": [key for key in model_kinds if (cluster or {}).get(key) is not None],
            "account": [key for key in model_kinds if (account or {}).get(key) is not None],
        }
        result["restart"] = request.app.state.restart_controller.status()
        return Response(status="ok", result=result)
    settings = await runtime_config.get_settings(ConfigScope.cluster())
    return Response(status="ok", result={"settings": settings})


@router.post("/restart", status_code=202)
@require_auth_root
async def restart_server(
    body: RestartRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    response: HTTPResponse,
    ctx: RequestContext = Depends(get_request_context),
):
    from openviking.config.config_file import preview_config_file, read_config_file

    controller = request.app.state.restart_controller
    server_overrides = getattr(request.app.state, "server_config_overrides", None)
    if controller.shutdown is None:
        raise FailedPreconditionError(
            "Remote restart requires the single-worker openviking-server CLI"
        )
    async with controller.lock:
        try:
            config = await asyncio.to_thread(read_config_file, server_overrides)
            if config["revision"] != body.revision:
                raise ValueError("ov.conf changed; reload before restarting")
            await asyncio.to_thread(preview_config_file, config["content"], {}, server_overrides)
            if controller.recovery is not None and not controller.requested:
                await asyncio.to_thread(controller.recovery.prepare, body.revision)
        except ValueError as exc:
            raise InvalidArgumentError(str(exc)) from exc
        except OSError as exc:
            raise FailedPreconditionError(
                "Cannot read the server startup configuration file"
            ) from exc
        result = controller.request()
        background_tasks.add_task(controller.stop)
        response.headers["Cache-Control"] = "no-store"
        return Response(status="ok", result=result)


@router.patch("/configuration")
@require_auth_root
async def patch_cluster_configuration(
    body: ConfigPatchRequest,
    request: Request,
    response: HTTPResponse,
    source: str = Query("runtime", pattern="^(runtime|file)$"),
    dry_run: bool = Query(False),
    ctx: RequestContext = Depends(get_request_context),
):
    """Apply a three-state PATCH to the cluster configuration layer."""
    validate_config_input(body.settings, body.content)
    if dry_run and (source != "file" or body.content is None):
        raise InvalidArgumentError("dry_run requires source=file and full file content")
    if source == "file":
        from openviking.config.config_file import preview_config_file, save_config_file

        server_overrides = getattr(request.app.state, "server_config_overrides", None)
        async with request.app.state.restart_controller.lock:
            if request.app.state.restart_controller.requested:
                raise FailedPreconditionError("Server restart is already in progress")
            response.headers["Cache-Control"] = "no-store"
            try:
                if dry_run:
                    result = await asyncio.to_thread(
                        preview_config_file, body.content, body.settings, server_overrides
                    )
                else:
                    if body.content is None or body.settings:
                        raise ValueError("File saves require full content and no model settings")
                    result = await asyncio.to_thread(
                        save_config_file, body.content, body.revision or "", server_overrides
                    )
            except ValueError as exc:
                raise InvalidArgumentError(str(exc)) from exc
            except OSError as exc:
                raise FailedPreconditionError(
                    "Cannot write ov.conf; check file and directory permissions"
                ) from exc
            return Response(status="ok", result=result)
    if body.content is not None:
        raise InvalidArgumentError("Full file content requires source=file")
    runtime_config = get_runtime_config_manager()
    try:
        if "ttl" in body.settings:
            from openviking.ttl.wiring import get_ttl_adapter

            await get_ttl_adapter().patch_configuration(body.settings)
        else:
            await runtime_config.patch_cluster(body.settings)
    except (ConfigPatchError, ValueError) as exc:
        raise InvalidArgumentError(str(exc)) from exc
    settings = await runtime_config.get_settings(ConfigScope.cluster())
    return Response(status="ok", result={"settings": settings})
