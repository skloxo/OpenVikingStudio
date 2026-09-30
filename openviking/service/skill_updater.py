# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Atomic skill update executor with rollback and privacy restoration."""

from pathlib import Path
import shutil
from typing import Any, Dict, Optional
import uuid

from fastapi import Request

from openviking.server.identity import RequestContext
from openviking.server.routers.skills_helpers import _validate_skill_name
from openviking.server.routers.skills_models import UpdateSkillRequest
from openviking.server.skill_source_metadata import persist_skill_source_metadata
from openviking.server.telemetry import run_operation
from openviking.server.temp_upload_store import TempUploadStore
from openviking.service.skill_integrity import _restore_skill_privacy
from openviking_cli.exceptions import InvalidArgumentError


async def execute_skill_update(
    http_request: Request,
    request: UpdateSkillRequest,
    skill_name: str,
    root_uri: str,
    ctx: RequestContext,
    service: Any,
    persist_metadata_fn: Optional[Any] = None,
) -> Dict[str, Any]:
    """Execute atomic skill replacement with automatic snapshot backup, rollback, and cleanup."""
    persist_fn = persist_metadata_fn or persist_skill_source_metadata
    data = request.data
    allow_local_path_resolution = False
    resolved = None
    source_metadata = request.source_metadata or {
        "type": "api",
        "source": "inline_content",
        "operation": "update",
    }
    if request.temp_file_id:
        resolved = await TempUploadStore.build(http_request.app.state.config).resolve_for_consume(
            request.temp_file_id, ctx
        )
        data = Path(resolved.local_path)
        allow_local_path_resolution = True
        if request.source_metadata is None:
            source_metadata = {
                "type": "api",
                "source": "temp_upload",
                "operation": "update",
                "upload_mode": resolved.mode,
            }
        if resolved.original_filename and request.source_metadata is None:
            source_metadata["original_filename"] = resolved.original_filename

    source_path_hint = resolved.original_filename if resolved else None

    async def _update() -> Dict[str, Any]:
        skill_root_parent = root_uri.rsplit("/", 1)[0]
        backup_uri = f"{skill_root_parent}/.{skill_name}.update-backup-{uuid.uuid4().hex}"
        backup_created = False
        privacy_update_attempted = False
        previous_privacy = None
        preparation = None
        privacy = service.privacy_configs
        try:
            if privacy is not None:
                previous_privacy = await privacy.get_current(ctx, "skill", skill_name)
            preparation = await service.resources._skill_processor.prepare_skill_processing(  # noqa: SLF001
                data,
                ctx=ctx,
                allow_local_path_resolution=allow_local_path_resolution,
                source_path_hint=source_path_hint,
            )
            expected_name = _validate_skill_name(skill_name)
            if preparation.skill_dict.get("name") != expected_name:
                raise InvalidArgumentError(
                    f"Skill name mismatch: path name is '{expected_name}', content name is '{preparation.skill_dict.get('name')}'",
                    details={
                        "expected": expected_name,
                        "actual": preparation.skill_dict.get("name"),
                    },
                )
            await service.fs.mv(root_uri, backup_uri, ctx=ctx)
            backup_created = True
            result = await service.resources.add_skill(
                data=preparation,
                ctx=ctx,
                wait=request.wait,
                timeout=request.timeout,
                allow_local_path_resolution=False,
                source_path_hint=source_path_hint,
                apply_privacy=False,
                privacy_change_reason="auto-extracted from update_skill",
                target_uri=skill_root_parent,
            )
            await persist_fn(service, ctx, result, source_metadata)
            privacy_update_attempted = True
            await service.resources._skill_processor.apply_skill_privacy(  # noqa: SLF001
                preparation.skill_dict,
                preparation.privacy_values,
                ctx,
                change_reason="auto-extracted from update_skill",
                delete_if_empty=True,
            )
        except Exception:
            if backup_created:
                try:
                    await service.fs.rm(root_uri, ctx=ctx, recursive=True)
                except Exception:
                    pass
                try:
                    await service.fs.mv(backup_uri, root_uri, ctx=ctx)
                except Exception:
                    pass
            if privacy_update_attempted:
                try:
                    await _restore_skill_privacy(service, ctx, skill_name, previous_privacy)
                except Exception:
                    pass
            raise
        else:
            if backup_created:
                await service.fs.rm(backup_uri, ctx=ctx, recursive=True)
            result["action"] = "update"
            return result
        finally:
            if preparation and preparation.cleanup_path:
                shutil.rmtree(preparation.cleanup_path, ignore_errors=True)
            if resolved:
                await resolved.cleanup()

    return await run_operation(
        operation="skills.update",
        telemetry=request.telemetry,
        fn=_update,
    )
