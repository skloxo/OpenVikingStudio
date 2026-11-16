# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Resource endpoints for OpenViking HTTP Server."""

from typing import Any, Literal, Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile

from openviking.core.path_variables import resolve_path_variables
from openviking.core.uri_validation import validate_content_target_uri, validate_request_viking_uri
from openviking.server.auth import get_request_context, get_upload_request_context
from openviking.server.dependencies import get_service
from openviking.server.identity import RequestContext
from openviking.server.local_input_guard import require_remote_resource_source
from openviking.server.resource_ingest import ingest_temp_upload
from openviking.server.responses import response_from_result
from openviking.server.routers.filesystem import CpRequest, MvRequest
from openviking.server.routers.filesystem import cp as copy_filesystem_entry
from openviking.server.routers.filesystem import mv as move_filesystem_entry
from openviking.server.routers.filesystem import rm as remove_filesystem_entry
from openviking.server.routers.resources_models import AddResourceRequest, AddSkillRequest
from openviking.server.skill_source_metadata import persist_skill_source_metadata
from openviking.server.telemetry import run_operation
from openviking.server.temp_upload_store import TempUploadStore
from openviking_cli.exceptions import InvalidArgumentError

router = APIRouter(prefix="/api/v1", tags=["resources"])

__all__ = ["router", "AddResourceRequest", "AddSkillRequest"]

_SHARED_RESOURCES_ROOT = "viking://resources"


def _validate_shared_resource_uri(
    uri: str,
    ctx: RequestContext,
    *,
    field_name: str = "uri",
) -> str:
    resolved = validate_request_viking_uri(
        resolve_path_variables(uri), ctx, field_name=field_name
    ).rstrip("/")
    decoded_segments = unquote(resolved).replace("\\", "/").split("/")
    if not resolved.startswith(f"{_SHARED_RESOURCES_ROOT}/") or any(
        segment in {".", ".."} for segment in decoded_segments
    ):
        raise InvalidArgumentError(
            "Only children of viking://resources/ are allowed for this operation"
        )
    return resolved


@router.post("/resources/cp")
async def copy_resource(
    request: CpRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Copy a shared resource to another location in the shared subtree."""
    from_uri = _validate_shared_resource_uri(request.from_uri, _ctx, field_name="from_uri")
    to_uri = _validate_shared_resource_uri(request.to_uri, _ctx, field_name="to_uri")
    return await copy_filesystem_entry(
        CpRequest(from_uri=from_uri, to_uri=to_uri, recursive=request.recursive),
        _ctx=_ctx,
    )


@router.post("/resources/mv")
async def move_resource(
    request: MvRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Rename or move a shared resource within the shared subtree."""
    from_uri = _validate_shared_resource_uri(request.from_uri, _ctx, field_name="from_uri")
    to_uri = _validate_shared_resource_uri(request.to_uri, _ctx, field_name="to_uri")
    return await move_filesystem_entry(
        MvRequest(from_uri=from_uri, to_uri=to_uri),
        _ctx=_ctx,
    )


@router.delete("/resources")
async def delete_resource(
    uri: str = Query(..., description="URI below viking://resources/"),
    recursive: bool = Query(False, description="Remove a directory recursively"),
    wait: bool = Query(True, description="Wait for semantic index cleanup"),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Delete one shared resource without exposing general filesystem deletion."""
    resolved = _validate_shared_resource_uri(uri, _ctx)
    return await remove_filesystem_entry(
        uri=resolved,
        recursive=recursive,
        wait=wait,
        _ctx=_ctx,
    )


@router.post("/resources/temp_upload")
async def temp_upload(
    request: Request,
    file: UploadFile = File(...),
    telemetry: bool = Form(False),
    upload_mode: Optional[Literal["local", "shared"]] = Form(None),
    _ctx: RequestContext = Depends(get_upload_request_context),
):
    """Upload a temporary file for add_resource or import_ovpack.

    Two auth layers (see :func:`get_upload_request_context`): with an API key the file is
    stored and its ``temp_file_id`` returned (used by the CLI and ``import_ovpack``). With a
    signed ``?token=`` — minted by the MCP ``add_resource`` tool for local-file paths — the
    server additionally finishes ingestion in-request: it resolves the upload, calls
    ``add_resource`` with the token-bound ``to``/``reason``, and returns the final result, so
    the agent never needs a second call. The ``?token=`` query param is consumed by the auth
    dependency.
    """
    signed = getattr(request.state, "signed_upload", None)
    effective_upload_mode = upload_mode or request.app.state.config.temp_upload.default_mode

    async def _upload() -> dict[str, Any]:
        store = TempUploadStore.build(request.app.state.config)
        temp_file_id = await store.save_upload(file, effective_upload_mode, _ctx)
        if signed is None:
            return {"temp_file_id": temp_file_id}
        return await ingest_temp_upload(
            store,
            temp_file_id,
            _ctx,
            to=signed.to,
            reason=signed.reason,
            processing_mode=signed.processing_mode,
            tags=signed.tags,
            tag_mode=signed.tag_mode,
            parse_mode=signed.parse_mode,
        )

    try:
        execution = await run_operation(
            operation="resources.temp_upload",
            telemetry=telemetry,
            fn=_upload,
        )
    except InvalidArgumentError as exc:
        if signed is None:
            raise
        # save_upload raises InvalidArgumentError for both bad mode and oversize. The signed
        # route mapped oversize to 413 and the rest to 400 before the routes merged; preserve
        # that contract for the token path.
        msg = str(exc)
        status = 413 if "exceeds size limit" in msg else 400
        raise HTTPException(status_code=status, detail=msg) from exc
    return response_from_result(execution.result, telemetry=execution.telemetry)


@router.post("/resources")
async def add_resource(
    http_request: Request,
    request: AddResourceRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Add resource to OpenViking."""
    service = get_service()
    to_uri = resolve_path_variables(request.to).strip() if request.to else ""
    if to_uri:
        to_uri = validate_content_target_uri(to_uri, _ctx, kind="resource", field_name="to")
    parent_uri = resolve_path_variables(request.parent).strip() if request.parent else ""
    if parent_uri:
        parent_uri = validate_content_target_uri(
            parent_uri,
            _ctx,
            kind="resource",
            field_name="parent",
        )

    path = request.path
    allow_local_path_resolution = False
    original_filename = None
    resolved = None
    if request.temp_file_id:
        if request.watch_interval > 0:
            raise InvalidArgumentError(
                "watch_interval > 0 is not supported for uploaded content: an "
                "upload is a static snapshot, so the watch would re-process "
                "stale content forever. Watch a URL / "
                "sitemap / RSS source instead, or re-add the resource when the "
                "source changes."
            )
        resolved = await TempUploadStore.build(http_request.app.state.config).resolve_for_consume(
            request.temp_file_id, _ctx
        )
        path = resolved.local_path
        original_filename = resolved.original_filename
        allow_local_path_resolution = True
    elif path is not None:
        path = require_remote_resource_source(path, declared_connector_add_type=request.add_type)
    if path is None:
        raise InvalidArgumentError("Either 'path' or 'temp_file_id' must be provided.")

    # Use original_filename from upload if source_name not explicitly provided
    source_name = request.source_name
    if source_name is None and original_filename is not None:
        source_name = original_filename

    kwargs = {
        "strict": request.strict,
        "source_name": source_name,
        "ignore_dirs": request.ignore_dirs,
        "include": request.include,
        "exclude": request.exclude,
        "directly_upload_media": request.directly_upload_media,
        "watch_interval": request.watch_interval,
        "processing_mode": request.processing_mode,
    }
    # Connector routing needs to distinguish an omitted create_parent from an
    # explicit false.  Standard imports still observe false when the field is
    # omitted because ResourceService reads it with kwargs.get(..., False).
    if "create_parent" in request.model_fields_set:
        kwargs["create_parent"] = request.create_parent
    if request.temp_file_id and request.watch_interval <= 0:
        kwargs["temp_file_id"] = request.temp_file_id
    if request.preserve_structure is not None:
        kwargs["preserve_structure"] = request.preserve_structure

    async def _add() -> dict[str, Any]:
        try:
            result = await service.resources.add_resource(
                path=path,
                ctx=_ctx,
                add_type=request.add_type,
                to=to_uri,
                parent=parent_uri,
                reason=request.reason,
                instruction=request.instruction,
                wait=request.wait,
                timeout=request.timeout,
                tags=request.tags,
                tag_mode=request.tag_mode,
                allow_local_path_resolution=allow_local_path_resolution,
                enforce_public_remote_targets=True,
                args=request.args,
                **kwargs,
            )
        except Exception:
            raise
        else:
            return result
        finally:
            if resolved:
                await resolved.cleanup()

    execution = await run_operation(
        operation="resources.add_resource",
        telemetry=request.telemetry,
        fn=_add,
    )
    return response_from_result(execution.result, telemetry=execution.telemetry)


@router.post("/skills")
async def add_skill(
    http_request: Request,
    request: AddSkillRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Add skill to OpenViking."""
    service = get_service()
    target_uri = resolve_path_variables(request.target_uri).strip() if request.target_uri else ""
    if target_uri:
        target_uri = validate_content_target_uri(
            target_uri,
            _ctx,
            kind="skill",
            field_name="target_uri",
        )
    data = request.data
    allow_local_path_resolution = False
    resolved = None
    source_path_hint = None
    source_metadata = request.source_metadata or {
        "type": "api",
        "source": "inline_content",
        "operation": "add",
    }
    if request.temp_file_id:
        store = TempUploadStore.build(http_request.app.state.config)
        resolved = await store.resolve_for_consume(request.temp_file_id, _ctx)
        data = resolved.local_path
        source_path_hint = resolved.original_filename
        allow_local_path_resolution = True
        if request.source_metadata is None:
            source_metadata = {
                "type": "api",
                "source": "temp_upload",
                "operation": "add",
                "upload_mode": resolved.mode,
            }
        if resolved.original_filename and request.source_metadata is None:
            source_metadata["original_filename"] = resolved.original_filename

    # 场景归并与大包纯化防线：如果技能已被母包 scenarios 吸收，自动合流至母包而非散落顶层
    try:
        from openviking.core.skill_loader import SkillLoader
        from openviking.service.skill_aliasing_router import SkillAliasingRouter
        if isinstance(data, str) and ("name:" in data or "---" in data):
            meta, _ = SkillLoader._split_frontmatter(data)
            parsed_name = meta.get("name")
            if parsed_name:
                router = SkillAliasingRouter()
                resolved_sc = router.resolve(str(parsed_name).strip())
                if resolved_sc and resolved_sc.get("is_virtual"):
                    parent_bundle = resolved_sc.get("bundle_name")
                    sc_filename = f"{str(parsed_name).strip()}.md"
                    from openviking.service.skill_path_resolver import resolve_skills_root
                    target_file = resolve_skills_root("default") / parent_bundle / "scenarios" / sc_filename
                    if target_file.parent.exists():
                        target_file.write_text(data, encoding="utf-8")
                        return Response(status="ok", result={
                            "name": parsed_name,
                            "uri": f"viking://agent/skills/{parent_bundle}/scenarios/{sc_filename}",
                            "parent_bundle": parent_bundle,
                            "is_absorbed": True,
                        }).model_dump(exclude_none=True)
    except Exception:
        pass

    async def _add() -> dict[str, Any]:
        try:
            result = await service.resources.add_skill(
                data=data,
                ctx=_ctx,
                wait=request.wait,
                timeout=request.timeout,
                allow_local_path_resolution=allow_local_path_resolution,
                source_path_hint=source_path_hint,
                target_uri=target_uri,
            )
            await persist_skill_source_metadata(service, _ctx, result, source_metadata)
        except HTTPException:
            raise
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception:
            raise
        else:
            return result
        finally:
            if resolved:
                await resolved.cleanup()

    execution = await run_operation(
        operation="resources.add_skill",
        telemetry=request.telemetry,
        fn=_add,
    )
    return response_from_result(execution.result, telemetry=execution.telemetry)
