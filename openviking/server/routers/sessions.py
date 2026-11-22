# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Sessions endpoints for OpenViking HTTP Server."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query

from openviking.core.path_variables import resolve_path_variables
from openviking.core.uri_validation import validate_request_viking_uri
from openviking.message.part import Part, TextPart, part_from_dict
from openviking.server.auth import get_session_request_context
from openviking.server.dependencies import get_service
from openviking.server.identity import RequestContext
from openviking.server.models import Response
from openviking.server.responses import error_response
from openviking.server.routers.sessions_models import (
    AddMessageRequest,
    AutoCommitPolicyRequest,
    BatchAddMessageRequest,
    CommitRequest,
    ContextPartRequest,
    CreateSessionRequest,
    EventExtractionConfigRequest,
    EventExtractionMetadataRequest,
    ExtractionMetadataRequest,
    MemoryExtractionConfigRequest,
    PartRequest,
    TextPartRequest,
    ToolPartRequest,
    UpdateSessionConfigRequest,
    UsedRequest,
)
from openviking.server.telemetry import run_operation
from openviking.utils.image_search import is_viking_uri
from openviking_cli.utils import get_logger

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])
logger = get_logger(__name__)

__all__ = [
    "router",
    "TextPartRequest",
    "ContextPartRequest",
    "ToolPartRequest",
    "PartRequest",
    "AutoCommitPolicyRequest",
    "EventExtractionConfigRequest",
    "MemoryExtractionConfigRequest",
    "AddMessageRequest",
    "BatchAddMessageRequest",
    "UsedRequest",
    "CreateSessionRequest",
    "UpdateSessionConfigRequest",
    "EventExtractionMetadataRequest",
    "ExtractionMetadataRequest",
    "CommitRequest",
]


def _event_tags_from_extraction_config(
    config: Optional[MemoryExtractionConfigRequest],
) -> Optional[List[str]]:
    """Extract event default tags from a memory extraction config.

    Returns ``None`` when the caller did not specify event tags (so the session
    default is left untouched), otherwise the provided list (possibly empty to
    clear the default). Normalization/validation happens in the service layer.
    """
    if config is None:
        return None
    events = config.events
    if events is None:
        return None
    return events.tags


def _commit_event_tags(
    metadata: "Optional[ExtractionMetadataRequest]",
) -> Optional[List[str]]:
    """Extract commit-time event tags from ``extraction_metadata``.

    Returns ``None`` when the caller did not specify event tags (so the session
    default applies), otherwise the provided list (possibly empty to disable
    default-tag injection for this commit). Normalization/validation happens in
    the service layer.
    """
    if metadata is None or metadata.event is None:
        return None
    return metadata.event.tags


def _resolve_message_parts(msg_request: AddMessageRequest, ctx: RequestContext) -> List[Part]:
    """Resolve parts from an AddMessageRequest, handling path variables."""
    if msg_request.parts is not None:
        return [_part_request_to_part(p, ctx) for p in msg_request.parts]
    return [TextPart(text=msg_request.content or "")]


def _session_pending_tokens(session: Any) -> int:
    """Read the post-write pending-token count from a session.

    Returns 0 when the session object does not expose ``meta`` so the response
    stays well-formed against lightweight or legacy session implementations.
    """
    meta = getattr(session, "meta", None)
    try:
        return max(0, int(getattr(meta, "pending_tokens", 0) or 0))
    except (TypeError, ValueError):
        return 0


def _part_request_to_part(raw_part: Dict[str, Any], ctx: RequestContext) -> Part:
    """Convert request part payload into an internal Part."""
    if not isinstance(raw_part, dict):
        return TextPart(text=str(raw_part))

    part_copy = dict(raw_part)
    if part_copy.get("type") == "context" and part_copy.get("uri"):
        part_copy["uri"] = validate_request_viking_uri(
            resolve_path_variables(part_copy["uri"]), ctx
        )
    if part_copy.get("type") == "tool":
        if part_copy.get("tool_uri"):
            part_copy["tool_uri"] = validate_request_viking_uri(
                resolve_path_variables(part_copy["tool_uri"]), ctx, field_name="tool_uri"
            )
        if part_copy.get("skill_uri"):
            part_copy["skill_uri"] = validate_request_viking_uri(
                resolve_path_variables(part_copy["skill_uri"]), ctx, field_name="skill_uri"
            )
        if part_copy.get("tool_output_storage_uri"):
            part_copy["tool_output_storage_uri"] = validate_request_viking_uri(
                resolve_path_variables(part_copy["tool_output_storage_uri"]),
                ctx,
                field_name="tool_output_storage_uri",
            )
    if part_copy.get("type") == "image_url":
        image_url = part_copy.get("image_url")
        if isinstance(image_url, dict) and "url" in image_url:
            image_url = dict(image_url)
            resolved_url = resolve_path_variables(image_url["url"])
            if is_viking_uri(resolved_url):
                resolved_url = validate_request_viking_uri(
                    resolved_url, ctx, field_name="image_url"
                )
            image_url["url"] = resolved_url
            part_copy["image_url"] = image_url
        elif isinstance(image_url, str):
            resolved_url = resolve_path_variables(image_url)
            part_copy["image_url"] = (
                validate_request_viking_uri(resolved_url, ctx, field_name="image_url")
                if is_viking_uri(resolved_url)
                else resolved_url
            )
    try:
        return part_from_dict(part_copy)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _to_jsonable(value: Any) -> Any:
    """Convert internal objects (e.g. Context) into JSON-serializable values."""
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    return value


@router.post("")
async def create_session(
    request: CreateSessionRequest = Body(default_factory=CreateSessionRequest),
    _ctx: RequestContext = Depends(get_session_request_context),
):
    """Create a new session.

    If session_id is provided, creates a session with the given ID.
    If session_id is None, creates a new session with auto-generated ID.
    """
    service = get_service()

    update_auto_commit_policy = "auto_commit_policy" in request.model_fields_set
    auto_commit_policy_payload: Optional[Dict[str, Any]] = None
    if request.auto_commit_policy is not None:
        auto_commit_policy_payload = request.auto_commit_policy.model_dump(exclude_none=True)

    event_tags = _event_tags_from_extraction_config(request.memory_extraction_config)

    async def _create() -> dict[str, Any]:
        await service.initialize_user_directories(_ctx)
        session = await service.sessions.create(
            _ctx,
            request.session_id,
            memory_policy=request.memory_policy,
            auto_commit_policy=auto_commit_policy_payload,
            update_auto_commit_policy=update_auto_commit_policy,
            event_tags=event_tags,
        )
        return {
            "session_id": session.session_id,
            "uri": session.uri,
            "user": session.user.to_dict(),
            "auto_commit_policy": service.sessions.effective_auto_commit_policy(session),
            "memory_extraction_config": service.sessions.effective_memory_extraction_config(
                session
            ),
        }

    execution = await run_operation(
        operation="session.create",
        telemetry=request.telemetry,
        fn=_create,
    )
    return Response(status="ok", result=execution.result, telemetry=execution.telemetry)


@router.get("")
async def list_sessions(
    category: Optional[str] = Query(None, description="Filter sessions: interactive, heartbeat, or all"),
    _ctx: RequestContext = Depends(get_session_request_context),
):
    """List all sessions."""
    service = get_service()
    result = await service.sessions.sessions(_ctx, category=category)
    return Response(status="ok", result=result)


@router.get("/{session_id}")
async def get_session(
    session_id: str = Path(..., description="Session ID"),
    auto_create: bool = Query(False, description="Create the session if it does not exist"),
    _ctx: RequestContext = Depends(get_session_request_context),
):
    """Get session details."""
    from openviking_cli.exceptions import NotFoundError

    service = get_service()
    try:
        session = await service.sessions.get(session_id, _ctx, auto_create=auto_create)
    except NotFoundError:
        return error_response("NOT_FOUND", f"Session {session_id} not found")
    result = session.meta.to_dict()
    result["uri"] = session.uri
    result["user"] = session.user.to_dict()
    result["pending_tokens"] = int(session.meta.pending_tokens or 0)
    result["auto_commit_policy"] = service.sessions.effective_auto_commit_policy(session)
    result.pop("event_search_tags", None)
    result["memory_extraction_config"] = (
        service.sessions.effective_memory_extraction_config(session)
    )
    return Response(status="ok", result=result)


@router.patch("/{session_id}/config")
async def update_session_config(
    session_id: str = Path(..., description="Session ID"),
    request: UpdateSessionConfigRequest = Body(default_factory=UpdateSessionConfigRequest),
    _ctx: RequestContext = Depends(get_session_request_context),
):
    """Update mutable session config (event-memory default tags).

    Takes effect on subsequent message writes, idle scans, and commits.
    ``auto_commit_policy=null`` disables automatic commits.
    """
    from openviking_cli.exceptions import NotFoundError

    service = get_service()
    event_tags = _event_tags_from_extraction_config(
        request.memory_extraction_config
    )
    update_auto_commit_policy = "auto_commit_policy" in request.model_fields_set
    auto_commit_policy = (
        request.auto_commit_policy.model_dump(exclude_none=True)
        if request.auto_commit_policy is not None
        else None
    )

    async def _update() -> dict[str, Any]:
        session = await service.sessions.update_config(
            session_id,
            _ctx,
            event_tags=event_tags,
            auto_commit_policy=auto_commit_policy,
            update_auto_commit_policy=update_auto_commit_policy,
        )
        return {
            "session_id": session.session_id,
            "auto_commit_policy": service.sessions.effective_auto_commit_policy(session),
            "memory_extraction_config": service.sessions.effective_memory_extraction_config(
                session
            ),
        }

    try:
        execution = await run_operation(
            operation="session.update_config",
            telemetry=request.telemetry,
            fn=_update,
        )
    except NotFoundError:
        return error_response("NOT_FOUND", f"Session {session_id} not found")
    return Response(
        status="ok", result=execution.result, telemetry=execution.telemetry
    ).model_dump(exclude_none=True)


@router.get("/{session_id}/tool-results")
async def list_tool_results(
    session_id: str = Path(..., description="Session ID"),
    tool_name: Optional[str] = Query(None, description="Filter by tool name"),
    limit: int = Query(50, ge=1, description="Maximum number of tool results"),
    _ctx: RequestContext = Depends(get_session_request_context),
):
    """List externalized tool results for a session."""
    service = get_service()
    session = await service.sessions.open(session_id, _ctx, auto_create=False)
    result = await session.list_tool_results(tool_name=tool_name, limit=limit)
    return Response(status="ok", result=_to_jsonable(result))


@router.get("/{session_id}/tool-results/{tool_result_id}")
async def read_tool_result(
    session_id: str = Path(..., description="Session ID"),
    tool_result_id: str = Path(..., description="Tool result ID"),
    offset: int = Query(0, ge=0, description="Unicode character offset"),
    limit: int = Query(20_000, description="Maximum Unicode characters to return"),
    include_metadata: bool = Query(True, description="Include metadata in response"),
    _ctx: RequestContext = Depends(get_session_request_context),
):
    """Read an externalized tool result by Unicode character range."""
    if limit < -1:
        return error_response(
            "INVALID_ARGUMENT",
            "limit must be -1 or greater than or equal to 0",
            details={"field": "limit", "value": limit},
        )
    service = get_service()
    session = await service.sessions.open(session_id, _ctx, auto_create=False)
    result = await session.read_tool_result(
        tool_result_id,
        offset=offset,
        limit=limit,
        include_metadata=include_metadata,
    )
    return Response(status="ok", result=_to_jsonable(result))


@router.get("/{session_id}/tool-results/{tool_result_id}/search")
async def search_tool_result(
    session_id: str = Path(..., description="Session ID"),
    tool_result_id: str = Path(..., description="Tool result ID"),
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, description="Maximum matches"),
    context_chars: int = Query(300, ge=0, description="Context characters around each hit"),
    _ctx: RequestContext = Depends(get_session_request_context),
):
    """Search within an externalized tool result."""
    service = get_service()
    session = await service.sessions.open(session_id, _ctx, auto_create=False)
    result = await session.search_tool_result(
        tool_result_id,
        query=q,
        limit=limit,
        context_chars=context_chars,
    )
    return Response(status="ok", result=_to_jsonable(result))


@router.get("/{session_id}/context")
async def get_session_context(
    session_id: str = Path(..., description="Session ID"),
    token_budget: int = Query(128_000, description="Token budget for session context"),
    _ctx: RequestContext = Depends(get_session_request_context),
):
    """Get assembled session context."""
    if token_budget < 0:
        return error_response(
            "INVALID_ARGUMENT",
            "token_budget must be greater than or equal to 0",
            details={"field": "token_budget", "value": token_budget},
        )

    from openviking_cli.exceptions import NotFoundError

    service = get_service()
    try:
        session = await service.sessions.get(session_id, _ctx, auto_create=False)
        result = await session.get_session_context(token_budget=token_budget)
        return Response(status="ok", result=_to_jsonable(result))
    except NotFoundError:
        # Postel's Law: Non-existent or uninitialized session context gracefully resolves to empty working memory
        empty_context = {
            "latest_archive_overview": "",
            "pre_archive_abstracts": [],
            "messages": [],
            "estimatedTokens": 0,
            "stats": {
                "totalArchives": 0,
                "includedArchives": 0,
                "droppedArchives": 0,
                "failedArchives": 0,
                "activeTokens": 0,
                "archiveTokens": 0,
            },
        }
        return Response(status="ok", result=empty_context)


@router.get("/{session_id}/archives/{archive_id}")
async def get_session_archive(
    session_id: str = Path(..., description="Session ID"),
    archive_id: str = Path(..., description="Archive ID"),
    _ctx: RequestContext = Depends(get_session_request_context),
):
    """Get one completed archive for a session."""
    from openviking_cli.exceptions import NotFoundError

    service = get_service()
    session = await service.sessions.open(session_id, _ctx, auto_create=False)
    try:
        result = await session.get_session_archive(archive_id)
    except NotFoundError:
        return error_response(
            code="NOT_FOUND", message=f"Archive {archive_id} not found"
        )
    return Response(status="ok", result=_to_jsonable(result))


@router.delete("/{session_id}")
async def delete_session(
    session_id: str = Path(..., description="Session ID"),
    _ctx: RequestContext = Depends(get_session_request_context),
):
    """Delete a session."""
    service = get_service()
    await service.sessions.delete(session_id, _ctx)
    return Response(status="ok", result={"session_id": session_id})


@router.post("/{session_id}/commit")
async def commit_session(
    session_id: str = Path(..., description="Session ID"),
    body: CommitRequest = Body(default_factory=CommitRequest),
    _ctx: RequestContext = Depends(get_session_request_context),
):
    """Commit a session (archive and extract memories).

    Archive (Phase 1) completes before returning.  Memory extraction
    (Phase 2) runs in the background.  A ``task_id`` is returned for
    polling progress via ``GET /tasks/{task_id}``.
    """
    service = get_service()
    commit_kwargs: Dict[str, Any] = {"keep_recent_count": body.keep_recent_count}
    optional_retention = {
        "enable_working_memory": body.enable_working_memory,
        "retention_mode": body.retention_mode,
        "keep_recent_turn_count": body.keep_recent_turn_count,
        "retained_message_token_budget": body.retained_message_token_budget,
        "min_raw_tail_steps": body.min_raw_tail_steps,
        "session_window_context": body.session_window_context,
        "summary_token_ratio": body.summary_token_ratio,
        "retained_token_ratio": body.retained_token_ratio,
        "reasoning_effort": body.reasoning_effort,
    }
    commit_kwargs.update(
        {key: value for key, value in optional_retention.items() if value is not None}
    )
    event_tags = _commit_event_tags(body.extraction_metadata)
    if event_tags is not None:
        commit_kwargs["event_tags"] = event_tags
    execution = await run_operation(
        operation="session.commit",
        telemetry=body.telemetry,
        fn=lambda: service.sessions.commit_async(
            session_id,
            _ctx,
            **commit_kwargs,
        ),
    )
    return Response(
        status="ok",
        result=execution.result,
        telemetry=execution.telemetry,
    ).model_dump(exclude_none=True)


@router.post("/{session_id}/messages")
async def add_message(
    request: AddMessageRequest,
    session_id: str = Path(..., description="Session ID"),
    _ctx: RequestContext = Depends(get_session_request_context),
):
    """Add a message to a session.

    Supports two modes:
    1. Simple mode: provide `content` string (backward compatible)
       Example: {"role": "user", "content": "Hello"}

    2. Parts mode: provide `parts` array for full Part support
       Example: {"role": "assistant", "parts": [
           {"type": "text", "text": "Here's the answer"},
           {"type": "context", "uri": "viking://resources/doc.md", "abstract": "..."}
       ]}

    If both `content` and `parts` are provided, `parts` takes precedence.
    Missing sessions are auto-created on first add.
    """
    service = get_service()

    async def _add() -> dict[str, Any]:
        session = await service.sessions.open(session_id, _ctx, auto_create=True)
        parts = _resolve_message_parts(request, _ctx)

        specs = [
            {
                "role": request.role,
                "parts": parts,
                "peer_id": request.peer_id,
                "created_at": request.created_at,
                "turn_id": request.turn_id,
                "message_kind": request.message_kind,
                "source_message_ids": request.source_message_ids,
            }
        ]
        add_many_async = getattr(session, "add_messages_async", None)
        if callable(add_many_async):
            await add_many_async(specs)
        else:
            session.add_messages(specs)
        # Anti-Entropy Ingestion Gate: Auto-register routine cron / heartbeat probes / internal extractors
        is_hb = False
        hb_keywords = (
            "[openclaw heartbeat poll]",
            "heartbeat poll",
            "cron probe",
            "internal commitment extractor",
            "memory search agent",
            "dream diary entry",
            "dream diary from these memory fragments",
        )
        if request.content and any(k in request.content.lower() for k in hb_keywords):
            is_hb = True
        elif request.parts:
            for p in request.parts:
                txt = getattr(p, "text", "") or ""
                if any(k in txt.lower() for k in hb_keywords):
                    is_hb = True
                    break
        if is_hb:
            service.sessions.register_heartbeat_session(session_id)
            if hasattr(session, "_meta"):
                session._meta.is_heartbeat = True
                session._meta.category = "heartbeat"
                if hasattr(session, "_save_meta"):
                    try:
                        await session._save_meta()
                    except Exception as exc:
                        logger.warning(
                            "Failed to save session metadata for %s: %s",
                            getattr(session, "session_id", ""),
                            exc,
                        )

        await service.sessions.maybe_schedule_auto_commit(
            session_id,
            _ctx,
            reason_hint="message_write",
            session=session,
        )
        return {
            "session_id": session_id,
            "message_count": len(session.messages),
            # Post-write value so a commit policy can decide without a
            # follow-up get_session round trip.
            "pending_tokens": _session_pending_tokens(session),
        }

    execution = await run_operation(
        operation="session.add_message",
        telemetry=request.telemetry,
        fn=_add,
    )
    return Response(status="ok", result=execution.result, telemetry=execution.telemetry)


@router.post("/{session_id}/messages/batch")
async def batch_add_messages(
    request: BatchAddMessageRequest,
    session_id: str = Path(..., description="Session ID"),
    _ctx: RequestContext = Depends(get_session_request_context),
):
    """Add multiple messages to a session in a single request.

    Accepts a list of messages, each following the same format as AddMessageRequest.
    Missing sessions are auto-created on first add.
    """
    service = get_service()

    async def _batch_add() -> dict[str, Any]:
        session = await service.sessions.open(session_id, _ctx, auto_create=True)
        specs = []
        for msg_request in request.messages:
            parts = _resolve_message_parts(msg_request, _ctx)
            specs.append(
                {
                    "role": msg_request.role,
                    "parts": parts,
                    "peer_id": msg_request.peer_id,
                    "created_at": msg_request.created_at,
                    "turn_id": msg_request.turn_id,
                    "message_kind": msg_request.message_kind,
                    "source_message_ids": msg_request.source_message_ids,
                }
            )
        add_many_async = getattr(session, "add_messages_async", None)
        if callable(add_many_async):
            msgs = await add_many_async(specs)
        else:
            msgs = session.add_messages(specs)
        await service.sessions.maybe_schedule_auto_commit(
            session_id,
            _ctx,
            reason_hint="message_write",
            session=session,
        )
        return {
            "session_id": session_id,
            "message_count": len(session.messages),
            "added": len(msgs),
            # Post-write value so a commit policy can decide without a
            # follow-up get_session round trip.
            "pending_tokens": _session_pending_tokens(session),
        }

    execution = await run_operation(
        operation="session.batch_add_messages",
        telemetry=request.telemetry,
        fn=_batch_add,
    )
    return Response(status="ok", result=execution.result, telemetry=execution.telemetry)


@router.post("/{session_id}/used")
async def record_used(
    request: UsedRequest,
    session_id: str = Path(..., description="Session ID"),
    _ctx: RequestContext = Depends(get_session_request_context),
):
    """Record actually used contexts and skills in a session."""
    service = get_service()
    session = await service.sessions.open(session_id, _ctx, auto_create=False)

    # Resolve path variables in contexts
    resolved_contexts = None
    if request.contexts is not None:
        resolved_contexts = [
            validate_request_viking_uri(resolve_path_variables(uri), _ctx)
            for uri in request.contexts
        ]

    # Resolve path variables in skill URI if present
    resolved_skill = request.skill
    if resolved_skill is not None and "uri" in resolved_skill:
        resolved_skill = dict(resolved_skill)
        resolved_skill["uri"] = validate_request_viking_uri(
            resolve_path_variables(resolved_skill["uri"]), _ctx
        )

    session.used(contexts=resolved_contexts, skill=resolved_skill)
    return Response(
        status="ok",
        result={
            "session_id": session_id,
            "contexts_used": session.stats.contexts_used,
            "skills_used": session.stats.skills_used,
        },
    )
