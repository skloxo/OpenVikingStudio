# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Agent-scope skill management endpoints for OpenViking HTTP Server."""

import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request
from fastapi import Path as ApiPath

from openviking.core.namespace import canonical_user_root
from openviking.core.path_variables import resolve_path_variables
from openviking.core.skill_loader import validate_skill_format
from openviking.core.uri_validation import validate_request_viking_uri
from openviking.server.auth import get_request_context
from openviking.server.dependencies import get_service
from openviking.server.identity import RequestContext
from openviking.server.models import Response
from openviking.server.routers.skills_helpers import (
    _agent_skills_root,
    _entry_looks_like_skill,
    _list_skills_from_root,
    _parse_abstract_meta,
    _relative_skill_path,
    _require_skill,
    _skill_file_kind,
    _skill_md_uri,
    _skill_name_from_uri,
    _skill_root_from_hit_uri,
    _skill_root_uri,
    _skill_summary_from_entry,
    _skill_summary_from_hit,
    _skill_summary_from_meta,
    _validate_skill_name,
)
from openviking.server.routers.skills_models import (
    FindSkillsRequest,
    UpdateSkillRequest,
    ValidateSkillRequest,
)
from openviking.server.skill_source_metadata import (
    SOURCE_METADATA_FILENAME,
    persist_skill_source_metadata,
    read_skill_source_metadata,
)
from openviking.server.telemetry import run_operation
from openviking.service.skill_integrity import (
    _list_skill_files,
    _read_skill_detail,
    _restore_skill_privacy,
    _skill_manifest_with_integrity,
    _skill_snapshot_lock,
)
from openviking.service.skill_retina_cron import SkillRetinaAuditor
from openviking.service.skill_updater import execute_skill_update
from openviking_cli.exceptions import InvalidArgumentError

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])

__all__ = [
    "router",
    "UpdateSkillRequest",
    "FindSkillsRequest",
    "ValidateSkillRequest",
    "persist_skill_source_metadata",
    "read_skill_source_metadata",
    "_entry_looks_like_skill",
    "_require_skill",
    "_skill_root_uri",
    "_skill_md_uri",
    "_skill_name_from_uri",
    "_agent_skills_root",
    "_validate_skill_name",
    "_list_skills_from_root",
    "_read_skill_detail",
]


@router.get("")
async def list_skills(
    node_limit: int = 1000,
    target_uri: Optional[str] = None,
    _ctx: RequestContext = Depends(get_request_context),
):
    """List installed agent skills."""
    del node_limit
    service = get_service()
    if target_uri:
        resolved_uri = validate_request_viking_uri(
            resolve_path_variables(target_uri), _ctx, field_name="target_uri"
        )
        skills = await _list_skills_from_root(service, _ctx, resolved_uri)
        return Response(
            status="ok", result={"root_uri": resolved_uri, "skills": skills, "total": len(skills)}
        )
    user_skills = await _list_skills_from_root(
        service, _ctx, f"{canonical_user_root(_ctx)}/skills"
    )
    agent_skills = await _list_skills_from_root(service, _ctx, "viking://agent/skills")
    merged_skills = [*user_skills, *agent_skills]
    return Response(
        status="ok",
        result={
            "root_uris": [f"{canonical_user_root(_ctx)}/skills", "viking://agent/skills"],
            "skills": merged_skills,
            "total": len(merged_skills),
        },
    )


@router.post("/find")
async def find_skills(
    request: FindSkillsRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Find agent skills by semantic search."""
    service = get_service()
    target_uri = request.target_uri
    if target_uri:
        resolved_uri = validate_request_viking_uri(
            resolve_path_variables(target_uri), _ctx, field_name="target_uri"
        )
        execution = await run_operation(
            operation="skills.find",
            telemetry=request.telemetry,
            fn=lambda: service.search.find(
                query=request.query,
                ctx=_ctx,
                target_uri=resolved_uri,
                limit=request.limit,
                score_threshold=request.score_threshold,
                level=request.level,
            ),
        )
        result = execution.result
        result_dict = result.to_dict() if hasattr(result, "to_dict") else dict(result or {})
        hits = [_skill_summary_from_hit(hit) for hit in result_dict.get("skills", [])]
        return Response(
            status="ok",
            result={"root_uri": resolved_uri, "skills": hits, "total": len(hits)},
            telemetry=execution.telemetry,
        ).model_dump(exclude_none=True)

    user_root = f"{canonical_user_root(_ctx)}/skills"
    agent_root = "viking://agent/skills"

    user_execution, agent_execution = await asyncio.gather(
        run_operation(
            operation="skills.find",
            telemetry=request.telemetry,
            fn=lambda: service.search.find(
                query=request.query,
                ctx=_ctx,
                target_uri=user_root,
                limit=request.limit,
                score_threshold=request.score_threshold,
                level=request.level,
            ),
        ),
        run_operation(
            operation="skills.find",
            telemetry=request.telemetry,
            fn=lambda: service.search.find(
                query=request.query,
                ctx=_ctx,
                target_uri=agent_root,
                limit=request.limit,
                score_threshold=request.score_threshold,
                level=request.level,
            ),
        ),
    )

    user_result = user_execution.result
    user_result_dict = (
        user_result.to_dict() if hasattr(user_result, "to_dict") else dict(user_result or {})
    )
    user_hits = [_skill_summary_from_hit(hit) for hit in user_result_dict.get("skills", [])]

    agent_result = agent_execution.result
    agent_result_dict = (
        agent_result.to_dict() if hasattr(agent_result, "to_dict") else dict(agent_result or {})
    )
    agent_hits = [_skill_summary_from_hit(hit) for hit in agent_result_dict.get("skills", [])]

    merged_hits = [*user_hits, *agent_hits]
    if merged_hits and "score" in merged_hits[0]:
        merged_hits.sort(key=lambda x: x.get("score", 0), reverse=True)

    return Response(
        status="ok",
        result={
            "root_uris": [user_root, agent_root],
            "skills": merged_hits,
            "total": len(merged_hits),
        },
        telemetry=user_execution.telemetry,
    ).model_dump(exclude_none=True)


@router.post("/validate")
async def validate_skill(
    request: ValidateSkillRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Validate a SKILL.md payload using Agent Skills formatting rules."""
    del _ctx
    result = validate_skill_format(
        request.data,
        strict=request.strict,
        skill_dir_name=request.skill_dir_name,
        source_path=request.source_path,
    )
    return Response(status="ok", result=result)


@router.get("/retina/status")
async def get_skill_retina_status(
    _ctx: RequestContext = Depends(get_request_context),
):
    """Get audit and physical identity status for skills roots."""
    service = get_service()
    user_root = f"{canonical_user_root(_ctx)}/skills"
    agent_root = "viking://agent/skills"
    user_report = await SkillRetinaAuditor.audit_skills(service, _ctx, user_root)
    agent_report = await SkillRetinaAuditor.audit_skills(service, _ctx, agent_root)
    return Response(
        status="ok",
        result={
            "user": user_report.to_dict(),
            "agent": agent_report.to_dict(),
            "is_identical": user_report.is_identical and agent_report.is_identical,
        },
    )


@router.post("/retina/audit")
async def audit_skills_retina(
    _ctx: RequestContext = Depends(get_request_context),
):
    """Trigger physical retina audit on skills roots."""
    service = get_service()
    user_root = f"{canonical_user_root(_ctx)}/skills"
    agent_root = "viking://agent/skills"
    user_report = await SkillRetinaAuditor.audit_skills(service, _ctx, user_root)
    agent_report = await SkillRetinaAuditor.audit_skills(service, _ctx, agent_root)
    return Response(
        status="ok",
        result={
            "user": user_report.to_dict(),
            "agent": agent_report.to_dict(),
            "is_identical": user_report.is_identical and agent_report.is_identical,
        },
    )


@router.post("/retina/heal")
async def heal_skills_retina(
    _ctx: RequestContext = Depends(get_request_context),
):
    """Trigger physical retina self-healing on skills roots."""
    service = get_service()
    user_root = f"{canonical_user_root(_ctx)}/skills"
    agent_root = "viking://agent/skills"
    user_report = await SkillRetinaAuditor.heal_skills(service, _ctx, user_root)
    agent_report = await SkillRetinaAuditor.heal_skills(service, _ctx, agent_root)
    return Response(
        status="ok",
        result={
            "user": user_report.to_dict(),
            "agent": agent_report.to_dict(),
            "is_identical": user_report.is_identical and agent_report.is_identical,
            "total_healed": user_report.healed_count + agent_report.healed_count,
        },
    )


@router.get("/{skill_name}")
async def get_skill(
    skill_name: str = ApiPath(..., description="Skill name"),
    target_uri: Optional[str] = None,
    include_content: Optional[bool] = None,
    include_files: bool = True,
    include_integrity: bool = False,
    include_source: bool = False,
    level: Optional[int] = None,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Show one installed agent skill."""
    if level is not None and level not in {0, 1, 2}:
        raise InvalidArgumentError(
            "Skill show level must be 0, 1, or 2",
            details={"field": "level", "allowed": [0, 1, 2]},
        )
    service = get_service()
    root_uri = await _require_skill(service, _ctx, skill_name, target_uri)
    result = await _read_skill_detail(
        service,
        _ctx,
        skill_name=skill_name,
        root_uri=root_uri,
        include_content=include_content,
        include_files=include_files,
        include_integrity=include_integrity,
        include_source=include_source,
        level=level,
    )
    return Response(status="ok", result=result)


@router.put("/{skill_name}")
async def update_skill(
    http_request: Request,
    request: UpdateSkillRequest,
    skill_name: str = ApiPath(..., description="Skill name"),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Replace an existing agent skill with new content."""
    service = get_service()
    root_uri = await _require_skill(service, _ctx, skill_name, request.target_uri)
    execution = await execute_skill_update(
        http_request=http_request,
        request=request,
        skill_name=skill_name,
        root_uri=root_uri,
        ctx=_ctx,
        service=service,
        persist_metadata_fn=persist_skill_source_metadata,
    )
    return Response(
        status="ok",
        result=execution.result,
        telemetry=execution.telemetry,
    ).model_dump(exclude_none=True)


@router.delete("/{skill_name}")
async def delete_skill(
    skill_name: str = ApiPath(..., description="Skill name"),
    target_uri: Optional[str] = None,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Remove one installed agent skill."""
    service = get_service()
    root_uri = await _require_skill(service, _ctx, skill_name, target_uri)
    result = await service.fs.rm(root_uri, ctx=_ctx, recursive=True)
    privacy_deleted = False
    privacy = service.privacy_configs
    if privacy is not None:
        privacy_deleted = await privacy.delete(_ctx, "skill", skill_name)
    response_result: Dict[str, Any] = {"name": skill_name, "uri": root_uri, "root_uri": root_uri}
    if isinstance(result, dict) and "estimated_deleted_count" in result:
        response_result["estimated_deleted_count"] = result["estimated_deleted_count"]
    response_result["privacy_deleted"] = privacy_deleted
    return Response(status="ok", result=response_result)
