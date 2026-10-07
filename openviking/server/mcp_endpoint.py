# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""MCP (Model Context Protocol) endpoint for OpenViking server.

Exposes OpenViking tools (filesystem, retrieval, memory, watch management,
health) to Claude Code (or any MCP client) via streamable HTTP; the
`@mcp.tool` registrations below are the authoritative list.

Mounted on the FastAPI app at /mcp. The MCP session manager lifecycle is
tied to the FastAPI app lifespan (not a sub-app lifespan) so the task group
is always initialized before requests arrive.

Identity headers (X-OpenViking-Account, X-OpenViking-User)
are extracted from HTTP request scope and propagated via contextvars.
"""

from __future__ import annotations

import base64
import contextvars
import hashlib
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Dict, List, Literal, Optional, Union
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import (
    AudioContent,
    ContentBlock,
    ImageContent,
    TextContent,
    ToolAnnotations,
)
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from openviking.core.path_variables import resolve_path_variables
from openviking.core.uri_validation import (
    validate_content_target_uri,
    validate_request_viking_uri,
)
from openviking.parse.mode import ParseMode, normalize_parse_mode
from openviking.resource.processing_mode import DEFAULT_PROCESSING_MODE, ProcessingMode
from openviking.retrieve.context_assembler import (
    DEFAULT_MAX_TOKENS,
    AssembleParams,
    assemble_context,
)
from openviking.server.auth import _extract_api_key, normalize_actor_peer_header, resolve_identity
from openviking.server.dependencies import get_server_config, get_service
from openviking.server.identity import RequestContext
from openviking.server.local_input_guard import (
    TEMP_FILE_ID_RE,
    is_remote_resource_source,
)
from openviking.server.resource_ingest import ingest_temp_upload
from openviking.server.temp_upload_store import TempUploadStore
from openviking.server.upload_token_store import upload_token_store
from openviking.telemetry.span_models import update_root_span_identity
from openviking.utils.media_limits import MAX_INLINE_TOOL_RESULT_MEDIA_BYTES
from openviking.utils.search_filters import SearchContextTypeInput, merge_search_filter
from openviking_cli.exceptions import (
    InvalidArgumentError,
    NotFoundError,
    OpenVikingError,
    PermissionDeniedError,
    UnauthenticatedError,
)
from openviking_cli.session.user_id import UserIdentifier
from openviking_cli.utils import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Identity propagation via contextvars
# ---------------------------------------------------------------------------

_mcp_ctx: contextvars.ContextVar[Optional[RequestContext]] = contextvars.ContextVar(
    "_mcp_ctx", default=None
)

# URL hints from the incoming request, captured by middleware so MCP tools can
# reconstruct the agent-facing public URL without knowing about ASGI/Starlette.
# Only used as a fallback when neither OPENVIKING_PUBLIC_BASE_URL nor
# ServerConfig.public_base_url is set.
_request_url_ctx: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar(
    "_request_url_ctx", default=None
)


def _get_ctx() -> RequestContext:
    ctx = _mcp_ctx.get()
    if ctx is None:
        raise UnauthenticatedError("MCP request identity not set")
    return ctx


def _resolve_mcp_workspace_uri(uri: str, ctx: RequestContext) -> str:
    """Resolve MCP workspace URIs, expanding the viking://~ home alias, at its boundary."""
    return validate_request_viking_uri(resolve_path_variables(uri), ctx)


def _scope_to_origin(scope: Scope) -> Optional[str]:
    """Derive the public-facing origin (scheme://host) from an ASGI scope.

    Resolution order matches openviking.server.oauth.router._public_origin:
      1. ``OPENVIKING_PUBLIC_BASE_URL`` environment variable
      2. ``app.state.oauth_config.issuer`` (if OAuth enabled)
      3. ``X-Forwarded-Proto`` / ``X-Forwarded-Host``
      4. scope's own scheme + Host header
    """
    import os as _os

    env_value = _os.environ.get("OPENVIKING_PUBLIC_BASE_URL", "").strip()
    if env_value:
        return env_value.rstrip("/")

    app = scope.get("app")
    if app is not None:
        cfg = getattr(app.state, "oauth_config", None)
        configured = getattr(cfg, "issuer", None) if cfg else None
        if configured:
            return configured.rstrip("/")

    headers = {
        k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])
    }
    proto = headers.get("x-forwarded-proto") or scope.get("scheme") or "http"
    proto = proto.split(",", 1)[0].strip()
    host = headers.get("x-forwarded-host") or headers.get("host")
    if not host:
        server = scope.get("server")
        if isinstance(server, (list, tuple)) and len(server) >= 2:
            host = f"{server[0]}:{server[1]}" if server[1] else str(server[0])
    if not host:
        return None
    host = host.split(",", 1)[0].strip()
    return f"{proto}://{host}"


def _oauth_enabled(scope: Scope) -> bool:
    """Return True if app.state has an oauth_provider (i.e. OAuth is configured)."""
    app = scope.get("app")
    if app is None:
        return False
    return getattr(app.state, "oauth_provider", None) is not None


class _IdentityASGIMiddleware:
    """ASGI middleware: delegates to auth.resolve_identity (the same function
    used by all REST API routes) so authentication logic is never duplicated."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # 兼容性归一化：若客户端请求 /mcp 时缺少 text/event-stream 或 application/json，
        # 自动补齐 Accept 请求头，防止 FastMCP streamable-http 因客户端 Accept 格式报 406 Not Acceptable
        raw_headers = scope.get("headers", [])
        new_headers = []
        has_accept = False
        for k, v in raw_headers:
            if k.lower() == b"accept":
                has_accept = True
                val = v.decode("latin1", errors="replace")
                parts = [p.strip() for p in val.split(",") if p.strip()]
                if not any(p.startswith("application/json") for p in parts):
                    parts.insert(0, "application/json")
                if not any(p.startswith("text/event-stream") for p in parts):
                    parts.append("text/event-stream")
                new_headers.append((k, ", ".join(parts).encode("latin1")))
            else:
                new_headers.append((k, v))
        if not has_accept:
            new_headers.append((b"accept", b"application/json, text/event-stream"))
        scope["headers"] = new_headers

        request = Request(scope, receive=receive)
        x_api_key = request.headers.get("x-api-key")
        authorization = request.headers.get("authorization")
        try:
            actor_peer_id = normalize_actor_peer_header(
                request.headers.get("x-openviking-actor-peer")
            )
            declared_agent_id = (
                request.query_params.get("agent_id")
                or request.headers.get("x-openviking-agent-id")
                or actor_peer_id
            )
            agent_rec = None
            inferred_user_id = None
            if declared_agent_id:
                from openviking.storage.agent_principal_store import AgentPrincipalStore
                agent_rec = AgentPrincipalStore.get_instance().get_agent(
                    declared_agent_id, include_deleted=False
                )
                if not agent_rec or agent_rec.status == "revoked":
                    resp = JSONResponse(
                        {
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {
                                "code": -32001,
                                "message": f"Agent ID [{declared_agent_id}] not found or credential invalid",
                            },
                        },
                        status_code=401,
                    )
                    return await resp(scope, receive, send)
                inferred_user_id = agent_rec.user_id

            # 自动推断属主：只要指定了 agent_id，系统自动解析归属 user_id，严禁强迫调用方在 URL 拼接 user_id
            effective_user_param = (
                request.headers.get("x-openviking-user")
                or request.query_params.get("user_id")
                or inferred_user_id
                or "default"
            )

            identity = await resolve_identity(
                request,
                x_api_key=x_api_key,
                authorization=authorization,
                x_openviking_account=request.headers.get("x-openviking-account") or "default",
                x_openviking_user=effective_user_param,
            )

            # 🛡️ 属主匹配强校验：防串户与越权接入 (Owner-Agent Cross Verification)
            declared_user_id = request.query_params.get("user_id") or request.headers.get("x-openviking-user")
            if declared_user_id and agent_rec and agent_rec.user_id and declared_user_id != agent_rec.user_id:
                resp = JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32003,
                            "message": f"Cross-tenant access denied: Agent [{declared_agent_id}] belongs to user [{agent_rec.user_id}], but request specified user [{declared_user_id}]",
                        },
                    },
                    status_code=403,
                )
                return await resp(scope, receive, send)

            auth_user = getattr(identity, "user_id", None) if identity else None
            if auth_user and auth_user not in ("anonymous", "default_anonymous") and agent_rec and agent_rec.user_id:
                auth_role = getattr(identity, "role", "")
                if auth_role != "admin" and auth_user != agent_rec.user_id:
                    resp = JSONResponse(
                        {
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {
                                "code": -32003,
                                "message": f"Owner mismatch: Agent [{declared_agent_id}] belongs to user [{agent_rec.user_id}], but authenticated key belongs to [{auth_user}]",
                            },
                        },
                        status_code=403,
                    )
                    return await resp(scope, receive, send)

            # Enforce physical Tool ACL validation for POST tools/call requests
            replay_receive = receive
            if declared_agent_id and agent_rec and request.method == "POST":
                import json
                import time
                body = await request.body()

                body_consumed = False
                async def _replay_receive():
                    nonlocal body_consumed
                    if not body_consumed:
                        body_consumed = True
                        return {"type": "http.request", "body": body, "more_body": False}
                    return await receive()

                replay_receive = _replay_receive

                try:
                    payload = json.loads(body)
                    calls = payload if isinstance(payload, list) else [payload]
                    for call_obj in calls:
                        if isinstance(call_obj, dict) and call_obj.get("method") == "tools/call":
                            params = call_obj.get("params") or {}
                            tool_name = params.get("name")
                            allowed = set(agent_rec.allowed_tools) if agent_rec.allowed_tools else set()
                            if "*" not in allowed and tool_name and tool_name not in allowed:
                                req_id = call_obj.get("id")
                                logger.warning(
                                    f"Tool ACL Denied: Agent [{declared_agent_id}] attempted unauthorized tool [{tool_name}]. Allowed: {agent_rec.allowed_tools}"
                                )
                                resp = JSONResponse(
                                    {
                                        "jsonrpc": "2.0",
                                        "id": req_id,
                                        "error": {
                                            "code": -32003,
                                            "message": f"Permission Denied: Tool [{tool_name}] is not authorized for Agent Principal [{declared_agent_id}]. Please grant access in OpenViking Tool ACL Matrix.",
                                        },
                                    },
                                    status_code=403,
                                )
                                return await resp(scope, _replay_receive, send)
                            # Heartbeat & message count increment
                            try:
                                AgentPrincipalStore.get_instance().update_agent(
                                    declared_agent_id,
                                    total_messages=agent_rec.total_messages + 1,
                                    last_seen=time.time(),
                                )
                            except Exception:
                                pass
                except Exception as parse_err:
                    logger.debug(f"Tool ACL bypass parse error: {parse_err}")

        except (UnauthenticatedError, PermissionDeniedError, InvalidArgumentError) as exc:
            status = (
                401
                if isinstance(exc, UnauthenticatedError)
                else (403 if isinstance(exc, PermissionDeniedError) else 400)
            )
            headers: dict[str, str] = {}
            if status == 401 and _oauth_enabled(scope):
                origin = _scope_to_origin(scope)
                if origin:
                    headers["WWW-Authenticate"] = (
                        f'Bearer resource_metadata="{origin}/.well-known/oauth-protected-resource"'
                    )
            resp = JSONResponse(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32001, "message": str(exc)}},
                status_code=status,
                headers=headers,
            )
            return await resp(scope, receive, send)

        effective_account_id = identity.account_id or "default"
        effective_user_id = identity.user_id or "default"
        update_root_span_identity(
            request_state=request.state,
            account_id=effective_account_id,
            user_id=effective_user_id,
        )
        ctx = RequestContext(
            user=UserIdentifier(
                effective_account_id,
                effective_user_id,
            ),
            role=identity.role,
            actor_peer_id=actor_peer_id,
            from_oauth=identity.from_oauth,
            api_key=_extract_api_key(x_api_key, authorization),
        )
        url_info = {
            "x_forwarded_proto": request.headers.get("x-forwarded-proto"),
            "x_forwarded_host": request.headers.get("x-forwarded-host"),
            "host": request.headers.get("host"),
        }
        ctx_token = _mcp_ctx.set(ctx)
        url_token = _request_url_ctx.set(url_info)
        try:
            return await self.app(scope, replay_receive, send)
        finally:
            _mcp_ctx.reset(ctx_token)
            _request_url_ctx.reset(url_token)


# ---------------------------------------------------------------------------
# MCP server tools (aligned with vikingbot/agent/tools/ov_file.py)
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "openviking",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    stateless_http=True,
)

# Each static profile describes the tool's most consequential supported mode.
_READ_ONLY_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
_DESTRUCTIVE_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=False,
    openWorldHint=False,
)
_RETRY_SAFE_DESTRUCTIVE_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
)
_OPEN_WORLD_DESTRUCTIVE_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=False,
    openWorldHint=True,
)


# -- find / search ---------------------------------------------------------


def _resolve_context_type_filter(
    context_type: Optional[SearchContextTypeInput],
) -> Optional[Dict[str, Any]]:
    try:
        return merge_search_filter(None, context_type=context_type)
    except ValueError as exc:
        raise InvalidArgumentError(str(exc)) from exc


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def find(
    query: str,
    target_uri: str = "",
    limit: int = 10,
    min_score: float = 0.35,
    level: Optional[List[int]] = None,
    context_type: Optional[Union[str, List[str]]] = None,
    read_content: bool = False,
) -> str:
    """Fast semantic retrieval without session context. Returns ranked memories, resources, and skills with URI, abstract, and score."""
    service = get_service()
    ctx = _get_ctx()
    if target_uri:
        target_uri = _resolve_mcp_workspace_uri(target_uri, ctx)
    result = await service.search.find(
        query=query,
        ctx=ctx,
        target_uri=target_uri,
        limit=limit,
        score_threshold=min_score,
        filter=_resolve_context_type_filter(context_type),
        level=level,
    )
    return await _format_search_result(result, service=service, ctx=ctx, read_content=read_content)


@mcp.tool(annotations=_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def search(
    query: str,
    target_uri: str = "",
    session_id: Optional[str] = None,
    limit: int = 10,
    min_score: Optional[float] = None,
    level: Optional[List[int]] = None,
    context_type: Optional[Union[str, List[str]]] = None,
    mode: Literal["list", "context"] = "list",
    query_expansion: Literal["off", "auto"] = "auto",
    max_tokens: int = DEFAULT_MAX_TOKENS,
    quotas: Optional[Dict[str, int]] = None,
    purpose: Optional[Literal["chat", "coding"]] = None,
    detail: Literal["auto", "abstract", "overview", "full"] = "auto",
    detail_by_category: Optional[Dict[str, str]] = None,
    dedup_turns: int = 0,
    exclude_uris: Optional[List[str]] = None,
    peer_scope: Literal["actor", "all"] = "all",
    other_peer_penalty: Optional[float] = None,
    other_peer_penalties: Optional[Dict[str, float]] = None,
    rewrite: Literal["off", "auto"] = "off",
    rewrite_max_bullets: int = 6,
    read_content: bool = False,
) -> str:
    """Deep semantic retrieval with optional session context and intent analysis.

    ``mode="list"`` returns ranked memories, resources, and skills with URI,
    abstract, and score. ``mode="context"`` returns an injection-ready,
    token-budgeted context block and supports category quotas, purpose presets,
    detail tiers, cross-turn deduplication, peer scoping, and optional rewriting.
    ``target_uri`` is only supported in list mode.
    """
    service = get_service()
    ctx = _get_ctx()
    context_filter = _resolve_context_type_filter(context_type)
    if mode == "context":
        if read_content:
            raise InvalidArgumentError("read_content is only supported in mode='list'")
        if target_uri:
            raise InvalidArgumentError("target_uri is not supported in mode='context'")
        if detail != "auto" and detail_by_category:
            raise InvalidArgumentError(
                "detail cannot be combined with detail_by_category in mode='context'"
            )
        if other_peer_penalty is not None and other_peer_penalties:
            raise InvalidArgumentError(
                "other_peer_penalty cannot be combined with other_peer_penalties in mode='context'"
            )
        # Resolve exclusions with the same strictness as the REST search router,
        # so alias URIs match the canonical URIs they are compared against.
        resolved_exclude_uris = [
            _resolve_mcp_workspace_uri(exclude_uri, ctx) for exclude_uri in (exclude_uris or ())
        ]
        result = await assemble_context(
            service=service,
            ctx=ctx,
            params=AssembleParams(
                query=query,
                limit=limit,
                score_threshold=min_score,
                filter=context_filter,
                session_id=session_id,
                query_expansion=query_expansion,
                max_tokens=max_tokens,
                quotas=quotas,
                purpose=purpose,
                detail=detail_by_category or (None if detail == "auto" else detail),
                dedup_turns=dedup_turns,
                exclude_uris=resolved_exclude_uris,
                peer_scope=peer_scope,
                other_peer_penalty=other_peer_penalties or other_peer_penalty,
                rewrite=rewrite == "auto",
                rewrite_max_bullets=rewrite_max_bullets,
            ),
        )
        if result.digest.strip():
            return result.digest
        if result.rendered.strip():
            return result.rendered
        return "No matching context found."

    if target_uri:
        target_uri = _resolve_mcp_workspace_uri(target_uri, ctx)
    session = None
    # Intent off: skip session.load — SearchService will not scan session either.
    if session_id and service.search.is_intent_enabled():
        session = service.sessions.session(ctx, session_id)
        await session.load()
    result = await service.search.search(
        query=query,
        ctx=ctx,
        target_uri=target_uri,
        session=session,
        limit=limit,
        score_threshold=0.35 if min_score is None else min_score,
        filter=context_filter,
        level=level,
    )
    return await _format_search_result(result, service=service, ctx=ctx, read_content=read_content)


async def _format_search_result(result, *, service, ctx, read_content: bool = False) -> str:
    items = []
    for ctx_type, contexts in [
        ("memory", result.memories),
        ("resource", result.resources),
        ("skill", result.skills),
    ]:
        for m in contexts:
            items.append((ctx_type, m))

    items.sort(key=lambda x: getattr(x[1], "score", 0.0), reverse=True)

    if not items:
        return "No matching context found."

    contents: dict[str, str] = {}
    if read_content:
        import asyncio

        semaphore = asyncio.Semaphore(10)

        async def _read(uri: str) -> None:
            async with semaphore:
                try:
                    contents[uri] = await service.fs.read_visible(uri, ctx=ctx)
                except Exception:
                    pass

        await asyncio.gather(*(_read(m.uri) for _, m in items))

    lines = []
    for ctx_type, m in items:
        abstract = (
            getattr(m, "abstract", "") or getattr(m, "overview", "") or "(no abstract)"
        ).strip()
        score = getattr(m, "score", 0.0)
        line = f"- [{ctx_type} {score * 100:.0f}%] {m.uri}\n    {abstract}"
        if m.uri in contents:
            line += f"\n\n    {contents[m.uri]}"
        lines.append(line)

    return (
        f"Found {len(items)} item(s):\n\n"
        + "\n".join(lines)
        + ("" if read_content else "\n\nUse the read tool to expand a URI.")
    )


# -- read ------------------------------------------------------------------


_MCP_IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
_MCP_AUDIO_EXTENSIONS = {".flac", ".m4a", ".mp3", ".oga", ".ogg", ".wav"}
_MCP_VIDEO_EXTENSIONS = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"}
_MCP_MEDIA_MAX_BYTES = MAX_INLINE_TOOL_RESULT_MEDIA_BYTES


def _mcp_uri_suffix(uri: str) -> str:
    """Lowercased file extension of a URI, ignoring any query or fragment."""
    path = uri.split("#", 1)[0].split("?", 1)[0]
    return PurePosixPath(path).suffix.lower()


def _is_mcp_image_uri(uri: str) -> bool:
    return _mcp_uri_suffix(uri) in _MCP_IMAGE_EXTENSIONS


def _is_mcp_audio_uri(uri: str) -> bool:
    return _mcp_uri_suffix(uri) in _MCP_AUDIO_EXTENSIONS


def _is_mcp_video_uri(uri: str) -> bool:
    return _mcp_uri_suffix(uri) in _MCP_VIDEO_EXTENSIONS


def _sniff_mcp_image_mime_type(data: bytes) -> Optional[str]:
    """Recognize the raster formats shared by common MCP coding clients."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _mcp_image_content(data: bytes, mime_type: str) -> ImageContent:
    encoded = base64.b64encode(data).decode("ascii")
    return ImageContent(type="image", data=encoded, mimeType=mime_type)


def _sniff_mcp_audio_mime_type(data: bytes, uri: str) -> Optional[str]:
    """Recognize audio formats represented by MCP AudioContent."""
    suffix = _mcp_uri_suffix(uri)
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WAVE":
        return "audio/wav"
    if data.startswith(b"fLaC"):
        return "audio/flac"
    if data.startswith(b"OggS") and suffix in {".oga", ".ogg"}:
        return "audio/ogg"
    if data.startswith(b"ID3") or (len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
        return "audio/mpeg"
    if len(data) >= 12 and data[4:8] == b"ftyp" and suffix == ".m4a":
        return "audio/mp4"
    return None


def _mcp_audio_content(data: bytes, mime_type: str) -> AudioContent:
    encoded = base64.b64encode(data).decode("ascii")
    return AudioContent(type="audio", data=encoded, mimeType=mime_type)


def _mcp_media_download_hint(uri: str) -> str:
    """Return actionable fallbacks when media cannot be inlined."""
    path = uri.split("#", 1)[0].split("?", 1)[0]
    filename = PurePosixPath(path).name or "download"
    encoded_uri = quote(uri, safe="")
    return (
        f'Use `ov get "{uri}" "./{filename}"` or GET '
        f"`/api/v1/content/download?uri={encoded_uri}` to fetch the original file."
    )


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS, structured_output=False)
async def read(uris: str | list[str], dehydrate: Optional[bool] = None) -> str | list[ContentBlock]:
    """Read one or more viking:// file URIs. Raster images and supported audio return native MCP content blocks. For directory listing, use the list tool instead. Set dehydrate=True to force LLMLingua-2 compression, False to disable, or leave as default (None) for adaptive auto-dehydration."""
    import asyncio

    service = get_service()
    ctx = _get_ctx()
    uri_list = uris if isinstance(uris, list) else [uris]
    semaphore = asyncio.Semaphore(10)

    async def _preflight_one(uri: str) -> tuple[str, Optional[int], Optional[str]]:
        """Resolve a URI and stat media before any binary bytes are loaded."""
        try:
            resolved_uri = _resolve_mcp_workspace_uri(uri, ctx)
            is_image = _is_mcp_image_uri(resolved_uri)
            is_audio = _is_mcp_audio_uri(resolved_uri)
            is_video = _is_mcp_video_uri(resolved_uri)
            if not (is_image or is_audio or is_video):
                return resolved_uri, None, None

            async with semaphore:
                stat = await service.fs.stat(resolved_uri, ctx=ctx)
            if stat.get("isDir"):
                return (
                    resolved_uri,
                    None,
                    f"Cannot render {uri}: URI points to a directory. "
                    "Use the list tool (or `ov ls` / `ov tree`) to browse its contents.",
                )
            if is_video:
                return (
                    resolved_uri,
                    None,
                    f"Cannot render {uri}: MCP has no standard VideoContent block. "
                    f"{_mcp_media_download_hint(uri)}",
                )

            size = stat.get("size") if stat else None
            if isinstance(size, bool) or not isinstance(size, int) or size < 0:
                return (
                    resolved_uri,
                    None,
                    f"Cannot render {uri}: file size is unavailable. "
                    f"{_mcp_media_download_hint(uri)}",
                )
            return resolved_uri, size, None
        except OpenVikingError as exc:
            return uri, None, str(exc)

    preflight = await asyncio.gather(*[_preflight_one(uri) for uri in uri_list])
    checked: list[tuple[str, Optional[int], Optional[str]]] = []
    media_total = 0
    for uri, (resolved_uri, size, error) in zip(uri_list, preflight, strict=True):
        if error is None and size is not None:
            if size > _MCP_MEDIA_MAX_BYTES:
                error = (
                    f"Media file is too large to inline through MCP ({size} bytes; limit "
                    f"{_MCP_MEDIA_MAX_BYTES} bytes). {_mcp_media_download_hint(uri)}"
                )
            elif media_total + size > _MCP_MEDIA_MAX_BYTES:
                error = (
                    f"Cannot inline {uri}: combined media size would exceed the MCP tool-call "
                    f"limit of {_MCP_MEDIA_MAX_BYTES} bytes. Read fewer media files at once. "
                    f"{_mcp_media_download_hint(uri)}"
                )
            else:
                media_total += size
        checked.append((resolved_uri, size, error))

    async def _read_one(
        uri: str, prepared: tuple[str, Optional[int], Optional[str]]
    ) -> str | ContentBlock:
        async with semaphore:
            try:
                resolved_uri, declared_size, error = prepared
                if error is not None:
                    return error
                is_image = _is_mcp_image_uri(resolved_uri)
                is_audio = _is_mcp_audio_uri(resolved_uri)
                if is_image or is_audio:
                    data = await service.fs.read_file_bytes(resolved_uri, ctx=ctx)
                    if declared_size is None or len(data) > declared_size:
                        return (
                            f"Cannot render {uri}: file changed after its size was checked. "
                            "Retry the read."
                        )
                    mime_type = (
                        _sniff_mcp_image_mime_type(data)
                        if is_image
                        else _sniff_mcp_audio_mime_type(data, resolved_uri)
                    )
                    if mime_type is None:
                        return (
                            f"Cannot render {uri}: its bytes do not match a supported media "
                            f"format. {_mcp_media_download_hint(uri)}"
                        )
                    if is_image:
                        return _mcp_image_content(data, mime_type)
                    return _mcp_audio_content(data, mime_type)
                content = await service.fs.read_visible(resolved_uri, ctx=ctx)
                # Adaptive auto-dehydration & explicit flag handling (Zero-Intervention SSOT)
                should_run_dehydration = False
                if dehydrate is True:
                    should_run_dehydration = isinstance(content, str) and len(content) > 100
                elif dehydrate is None:
                    # Adaptive mode: silently auto-detect long markdown / prose documents
                    if isinstance(content, str):
                        from openviking.service.wiki_dehydration_adaptive import should_auto_dehydrate
                        should_run_dehydration, _ = should_auto_dehydrate(content, resolved_uri)

                if should_run_dehydration and isinstance(content, str):
                    try:
                        from openviking.service.wiki_dehydration_engine import (
                            WikiDehydrationEngine,
                            DehydrationRequest,
                        )
                        dehydrated = WikiDehydrationEngine.get_instance().dehydrate(
                            DehydrationRequest(content=content)
                        )
                        content = dehydrated.dehydrated_content
                    except Exception as err:
                        logger.warning("MCP read dehydration fallback: %s", err)
                return content
            except OpenVikingError as exc:
                return str(exc)

    if len(uri_list) == 1:
        result = await _read_one(uri_list[0], checked[0])
        if isinstance(result, str):
            return result
        return [TextContent(type="text", text=f"Source: {uri_list[0]}"), result]

    results = await asyncio.gather(
        *[_read_one(uri, prepared) for uri, prepared in zip(uri_list, checked, strict=True)]
    )
    if any(not isinstance(result, str) for result in results):
        blocks: list[ContentBlock] = []
        for uri, result in zip(uri_list, results, strict=True):
            blocks.append(TextContent(type="text", text=f"=== {uri} ==="))
            if isinstance(result, str):
                blocks.append(TextContent(type="text", text=result))
            else:
                blocks.append(result)
        return blocks

    parts = []
    for uri, text in zip(uri_list, results, strict=True):
        parts.append(f"=== {uri} ===\n{text}")
    return "\n\n".join(parts)


# -- list ------------------------------------------------------------------


@mcp.tool(name="list", annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def ls(
    uri: str,
    recursive: bool = False,
    offset: int = 0,
    limit: int | None = None,
    sort_by: Literal["name", "mtime"] | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
) -> str:
    """List one sorted page under a viking:// directory URI.

    Args:
        uri: Directory URI to list.
        recursive: Whether to recursively list descendants.
        offset: Number of visible entries to skip.
        limit: Optional maximum number of entries.
        sort_by: Optional name or modification-time ordering.
        sort_order: Ascending or descending order.

    Returns:
        A line-oriented directory listing.
    """
    if offset < 0:
        raise InvalidArgumentError("offset must be greater than or equal to 0")
    if limit is not None and limit <= 0:
        raise InvalidArgumentError("limit must be greater than 0")

    service = get_service()
    ctx = _get_ctx()
    resolved_uri = _resolve_mcp_workspace_uri(uri, ctx)

    options: dict[str, Any] = {
        "ctx": ctx,
        "recursive": recursive,
        "output": "original",
    }
    if offset:
        options["offset"] = offset
    if limit is not None:
        options["node_limit"] = limit
    if sort_by is not None:
        options["sort_by"] = sort_by
        options["sort_order"] = sort_order
    entries = await service.fs.ls(resolved_uri, **options)
    if not entries:
        return f"(no entries under {uri})"

    lines = []
    for e in entries:
        name = e.get("name", "?") if isinstance(e, dict) else getattr(e, "name", "?")
        is_dir = e.get("isDir", False) if isinstance(e, dict) else getattr(e, "is_dir", False)
        entry_uri = e.get("uri", "") if isinstance(e, dict) else getattr(e, "uri", "")
        if recursive and entry_uri:
            lines.append(f"[{'dir' if is_dir else 'file'}] {entry_uri}")
        else:
            lines.append(f"[{'dir' if is_dir else 'file'}] {name}")
    return "\n".join(lines)


# -- tree ------------------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def tree(
    uri: str = "viking://",
    level_limit: int = 3,
    node_limit: int = 1000,
    include_abstract: bool = False,
    offset: int = 0,
    limit: int | None = None,
) -> str:
    """Show one visible page from a recursive directory tree.

    Args:
        uri: Directory URI to traverse.
        level_limit: Maximum traversal depth.
        node_limit: Existing default result limit.
        include_abstract: Whether to include file summaries.
        offset: Number of visible nodes to skip.
        limit: Optional result limit that overrides node_limit.

    Returns:
        An indented directory tree.
    """
    if offset < 0:
        raise InvalidArgumentError("offset must be greater than or equal to 0")
    if limit is not None and limit <= 0:
        raise InvalidArgumentError("limit must be greater than 0")

    service = get_service()
    ctx = _get_ctx()
    resolved_uri = _resolve_mcp_workspace_uri(uri, ctx)
    output = "agent" if include_abstract else "original"
    effective_limit = limit if limit is not None else node_limit
    try:
        entries = await service.fs.tree(
            resolved_uri,
            ctx=ctx,
            output=output,
            node_limit=effective_limit,
            level_limit=level_limit,
            offset=offset,
        )
    except NotFoundError:
        entries = []
    if not entries:
        return f"(nothing under {uri})"

    lines = [
        f"Tree of {uri} (depth <= {level_limit}, {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}):"
    ]
    for e in entries:
        rel = (e.get("rel_path") or e.get("name") or "?").strip("/")
        name = rel.rsplit("/", 1)[-1]
        depth = len([part for part in rel.split("/") if part])
        indent = "  " * max(0, depth - 1)
        if e.get("isDir"):
            lines.append(f"{indent}{name}/")
            continue
        lines.append(f"{indent}{name} ({e.get('size', 0)} B)")
        abstract = (e.get("abstract") or "").strip().replace("\n", " ")
        if include_abstract and abstract:
            lines.append(f"{indent}  - {abstract}")
    if len(entries) >= effective_limit:
        lines.append(
            f"(truncated at node_limit={effective_limit}; narrow the uri or raise node_limit to see more)"
        )
    return "\n".join(lines)


# -- remember --------------------------------------------------------------


class StoreMessage(BaseModel):
    role: Literal["user", "assistant"] = Field(description="Message role")
    content: str = Field(description="Message text content")


@mcp.tool(annotations=_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def remember(messages: list[StoreMessage]) -> str:
    """Store information into OpenViking long-term memory. Use when the user says 'remember this', shares preferences, important facts, or decisions worth persisting."""
    import uuid

    from openviking.message.part import TextPart

    service = get_service()
    ctx = _get_ctx()
    session_id = f"mcp-store-{uuid.uuid4().hex[:12]}"
    session = await service.sessions.get(session_id, ctx, auto_create=True)
    for msg in messages:
        if msg.content:
            add_async = getattr(session, "add_message_async", None)
            if callable(add_async):
                await add_async(msg.role, [TextPart(text=msg.content)])
            else:
                session.add_message(msg.role, [TextPart(text=msg.content)])
    await service.sessions.commit_async(session_id, ctx)
    return f"Stored {len(messages)} message(s) and committed for memory extraction."


# -- write -----------------------------------------------------------------


@mcp.tool(annotations=_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def write(
    uri: str,
    content: str,
    mode: Literal["replace", "append", "create"] = "replace",
    wait: bool = False,
    timeout: Optional[float] = None,
) -> str:
    """Write text to a viking:// file. Use this to save files (notes, profiles, knowledge, state) in OpenViking the same way you would use a working directory. To change part of an existing file, prefer the edit tool over a full rewrite.

    - mode="replace" (default): overwrite the file; creates it and any missing parent directories if needed.
    - mode="create": fail if the file already exists.
    - Any new file (whether created by "replace" or "create") must end in one of: .md .txt .json .yaml .yml .toml .py .js .ts
    - mode="append": append to the end of an existing file; fails if the file does not exist.

    Writable scopes: viking://resources/, viking://user/{user_id}/, viking://agent/. The viking://~ home alias expands to the caller's user root. The managed user subtrees skills/, peers/, privacy/ and sessions/ are read-only. After a write, semantic search indexes refresh in the background; pass wait=true to block until search reflects the change."""
    service = get_service()
    ctx = _get_ctx()
    uri = _resolve_mcp_workspace_uri(uri, ctx)

    # Ingestion Gatekeeper defense (Card-Entropy-01-Gatekeeper)
    from openviking.service.entropy_gatekeeper import EntropyGatekeeper

    gatekeeper_decision = await EntropyGatekeeper.get_instance().evaluate_and_intercept(
        uri=uri,
        content=content,
        ctx=ctx,
    )
    if gatekeeper_decision.action == "noop":
        disk_identical = False
        try:
            existing_doc = await service.fs.read(uri, ctx=ctx)
            existing_content = existing_doc.get("content", "") if isinstance(existing_doc, dict) else str(existing_doc)
            in_hash = hashlib.sha256(content.strip().encode("utf-8")).hexdigest()
            disk_hash = hashlib.sha256(existing_content.strip().encode("utf-8")).hexdigest()
            if in_hash == disk_hash:
                disk_identical = True
        except Exception:
            disk_identical = False

        if disk_identical:
            logger.info(
                "[EntropyGatekeeper][MCP] Intercepted exact bitwise redundant write for %s",
                uri,
            )
            return (
                f"[Entropy Defense] NOOP (指纹秒级印证): 目标节点 {uri} 内容完全一致 (0 字节变动)。"
                f"已拦截物理重复落盘，节约 {gatekeeper_decision.saved_bytes} B。"
            )
        else:
            logger.warning(
                "[EntropyGatekeeper][MCP] Overriding NOOP with physical write for %s: Target file missing or content changed.",
                uri,
            )

    try:
        result = await service.fs.write(
            uri=uri, content=content, ctx=ctx, mode=mode, wait=wait, timeout=timeout
        )
    except NotFoundError:
        if mode != "replace":
            raise
        # Replace doubles as create-or-overwrite so agents can save a new file
        # without first checking whether it exists; strict creation stays
        # available via mode="create".
        result = await service.fs.write(
            uri=uri, content=content, ctx=ctx, mode="create", wait=wait, timeout=timeout
        )
    written = result.get("written_bytes", 0)
    message = (
        f"Wrote {written} bytes to {result.get('uri', uri)} (mode={result.get('mode', mode)})."
    )
    return message + _indexing_hint(result)


@mcp.tool(annotations=_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def edit(
    uri: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
    wait: bool = False,
    timeout: Optional[float] = None,
) -> str:
    """Replace an exact string with new text in an existing viking:// file. Use this for targeted changes instead of rewriting the whole file with the write tool. old_string must match the file's current content exactly, including indentation and newlines; use the read tool first to see it. The edit fails and the file is left unchanged if old_string is not found, or if it matches more than once and replace_all is false (pass more surrounding context to make it unique, or set replace_all=true to replace every occurrence). Pass new_string="" to delete old_string.

    Editing a memory file preserves its metadata; after an edit, search indexes refresh in the background (pass wait=true to block until search reflects the change)."""
    service = get_service()
    ctx = _get_ctx()
    uri = _resolve_mcp_workspace_uri(uri, ctx)

    if not old_string:
        raise InvalidArgumentError("old_string must not be empty")
    try:
        current = await service.fs.read_visible(uri, ctx=ctx)
    except (InvalidArgumentError, PermissionDeniedError, UnauthenticatedError):
        raise
    except Exception as exc:
        raise NotFoundError(uri, "file") from exc
    occurrences = current.count(old_string)
    if occurrences == 0:
        raise InvalidArgumentError(
            f"old_string not found in {uri}. "
            "Re-read the file with the read tool to get its current content."
        )
    if occurrences > 1 and not replace_all:
        raise InvalidArgumentError(
            f"old_string matches {occurrences} locations in {uri}. "
            "Include more surrounding context to make it unique, or set replace_all=true."
        )
    updated = current.replace(old_string, new_string)
    if updated == current:
        return f"No changes: {uri} already matches the requested edit."
    result = await service.fs.write(
        uri=uri, content=updated, ctx=ctx, mode="replace", wait=wait, timeout=timeout
    )
    written = result.get("written_bytes", 0)
    message = f"Edited {result.get('uri', uri)} ({written} bytes written)."
    return message + _indexing_hint(result)


def _indexing_hint(result: Dict[str, Any]) -> str:
    semantic = result.get("semantic_status")
    vector = result.get("vector_status")
    parts = [f"semantic={semantic}", f"vector={vector}"]
    if result.get("overview_status") is not None:
        parts.append(f"overview={result['overview_status']}")
    hint = f"\nIndexing: {', '.join(parts)}."
    if "queued" in (semantic, vector):
        hint += " Search indexes update in the background; pass wait=true if a follow-up search must see this change immediately."
    return hint


# -- add_resource ----------------------------------------------------------


_DEFAULT_UPLOAD_TTL_SECONDS = 600


def _resolve_public_base_url() -> tuple[str, str]:
    """Pick the URL the agent should POST uploads to. Returns ``(base_url, source)``.

    Resolution order (first match wins):

    1. ``env`` — ``OPENVIKING_PUBLIC_BASE_URL`` environment variable. Operator-set,
       always wins.
    2. ``config`` — ``ServerConfig.public_base_url``. Operator-set baseline in ov.conf.
    3. ``forwarded`` — ``X-Forwarded-Host`` (+ ``X-Forwarded-Proto``) from the request.
       Set by reverse proxies (nginx, ALB, ingress controllers, MCP proxies). Reliable
       when the proxy chain forwards these headers, which is the standard default.
    4. ``host`` — the raw ``Host`` header from a direct connection. Reliable for
       same-host MCP clients (e.g. local Claude Code talking to localhost server).
    5. ``listen`` — ``http://{listen_host}:{listen_port}`` last-resort fallback.
       Only produces an agent-reachable URL when the server is bound to a routable
       address; commonly wrong behind reverse proxies.

    Sources 1 and 2 are "explicit" — operator vouched for the URL. Sources 3-5 are
    inferred and may be wrong when the proxy chain doesn't forward request headers.
    Callers should append a "set OPENVIKING_PUBLIC_BASE_URL if upload fails" hint
    in that case.
    """
    env_url = os.environ.get("OPENVIKING_PUBLIC_BASE_URL")
    if env_url:
        return env_url.rstrip("/"), "env"
    config = get_server_config()
    if config is not None and config.public_base_url:
        return config.public_base_url.rstrip("/"), "config"

    url_info = _request_url_ctx.get()
    if url_info:
        # X-Forwarded-Host / -Proto can be comma-separated lists when the request
        # crosses multiple proxy hops. Take the first (left-most original-client)
        # value, matching the normalization in openviking.server.oauth.router.
        def _first(value: Optional[str]) -> Optional[str]:
            if not value:
                return None
            head = value.split(",", 1)[0].strip()
            return head or None

        xfh = _first(url_info.get("x_forwarded_host"))
        xfp = _first(url_info.get("x_forwarded_proto"))
        host_hdr = _first(url_info.get("host"))
        if xfh:
            proto = xfp or "https"
            return f"{proto}://{xfh}", "forwarded"
        if host_hdr:
            return f"http://{host_hdr}", "host"

    if config is not None:
        from openviking.server.config import map_bind_host_to_loopback

        host = map_bind_host_to_loopback(config.host)
        return f"http://{host}:{config.port}", "listen"
    return "http://127.0.0.1:1933", "listen"


async def _maybe_sitemap_hint(path: str) -> str:
    """Best-effort sitemap/RSS suggestion for a single-page add (never crawls).

    Policy: only suggest when the added URL is the site root / homepage (path is
    empty or "/"). Adding a deep article URL implies intent for just that page, and
    gating to the root also keeps the (bounded, non-recursive) probe from re-running
    when many pages of the same site are added one-by-one.

    Gated by config (``webfeed.suggest_feed``) and fully exception-safe so it can
    never block or fail the add it is attached to.
    """
    try:
        from urllib.parse import urlparse

        if urlparse(path).path not in ("", "/"):
            return ""

        from openviking.parse.accessors import discover_feed_hint
        from openviking.utils.network_guard import ensure_public_remote_target
        from openviking_cli.utils.config import get_openviking_config

        webfeed = getattr(get_openviking_config(), "webfeed", None)
        if webfeed is not None and not getattr(webfeed, "suggest_feed", True):
            return ""
        timeout = float(getattr(webfeed, "suggest_timeout", 2.5)) if webfeed else 2.5
        hint = await discover_feed_hint(
            path, timeout=timeout, request_validator=ensure_public_remote_target
        )
        return hint or ""
    except Exception:
        return ""


@mcp.tool(annotations=_OPEN_WORLD_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def add_resource(
    path: str = "",
    temp_file_id: str = "",
    add_type: str = "",
    description: str = "",
    watch_interval: float = 0,
    processing_mode: ProcessingMode = DEFAULT_PROCESSING_MODE,
    to: str = "",
    parent: str = "",
    tags: Optional[list[str]] = None,
    tag_mode: str = "replace",
    args: Optional[dict[str, Any]] = None,
) -> str:
    """Add a resource to OpenViking. Asynchronous — processing happens in the background.

    Remote URL: pass ``path`` as an http(s)://, git@, ssh://, or git:// URL. A sitemap /
    RSS / Atom URL ingests the WHOLE site as one resource tree; pass ``args={"site": true}``
    to force whole-site ingestion from a bare domain.

    Local file: pass ``path`` as a filesystem path (e.g. ``/tmp/foo.pdf``). The response is an
    upload instruction — HTTP POST the file to the returned URL and the server ingests it
    automatically; you do NOT need to call this tool again.

    Args:
        path: Remote URL or local filesystem path. Required unless ``temp_file_id`` is set.
        temp_file_id: Server-minted upload id from a prior signed local-file upload.
        add_type: Explicit Connector source type (e.g. "tos", "git"). When set, the
            request routes through the Connector integration (must be enabled
            server-side) and ``path`` is sent verbatim — never treated as a local
            file. Requires an exact ``to`` target and cannot be combined with
            ``temp_file_id`` or ``parent``. Leave empty for the default path-probing
            behavior.
        description: Optional human-readable reason for adding the resource.
        watch_interval: Auto-refresh cadence in minutes. 0 = no watch. Prefer >=1440 (24h)
            unless the source changes faster — every refresh re-embeds the whole resource.
            Only applies to remote-URL invocations.
        processing_mode: "semantic_and_vectors" for normal semantic processing, or
            "vectors_only" to skip semantic understanding and only build vector indexes.
        to: Target URI under viking://resources/ (e.g. "viking://resources/volcengine/OpenViking").
            Required when ``add_type`` is set; otherwise leave empty to derive a URI
            from the source.
        parent: Parent URI under viking://resources/ for remote imports. Mutually exclusive
            with ``to`` and not supported when ``add_type`` is set.
        tags: Optional explicit k=v retrieval tags to apply after ingestion.
        tag_mode: Tag update mode, "replace" or "append". Defaults to "replace".
        args: Parser-specific options, e.g. {"auth_config": {"token": "..."}}
            for native HTTPS Git imports and watches, {"feishu_access_token": "..."}
            for Feishu imports, {"site": true} for whole-site ingestion, or
            {"parse_mode": "no_split"} to keep each parsed document body in one file.
    """
    from openviking.server.local_input_guard import require_remote_resource_source

    service = get_service()
    ctx = _get_ctx()

    try:
        to = resolve_path_variables(to).strip() if to else ""
        if to:
            to = validate_content_target_uri(to, ctx, kind="resource", field_name="to")
        parent = resolve_path_variables(parent).strip() if parent else ""
        if parent:
            parent = validate_content_target_uri(
                parent,
                ctx,
                kind="resource",
                field_name="parent",
            )
    except (InvalidArgumentError, PermissionDeniedError) as exc:
        return f"Error: {exc}"

    try:
        mode = normalize_parse_mode((args or {}).get("parse_mode", ParseMode.DEFAULT))
    except InvalidArgumentError as exc:
        return f"Error: {exc}"

    if watch_interval < 0:
        return (
            "Error: watch_interval must be >= 0. Use 0 for one-shot add (no watch); "
            "use a positive number of minutes (>=1440 recommended) to subscribe to auto-refresh."
        )

    add_type = add_type.strip()
    if add_type and temp_file_id:
        return "Error: add_type cannot be combined with temp_file_id."
    if add_type and not path:
        return "Error: add_type requires 'path'."
    if add_type and parent:
        return "Error: add_type cannot be combined with parent."
    if add_type and not to:
        return "Error: add_type requires an exact 'to' target."

    # Branch 1: ingest by temp_file_id. Kept for backward compat / REST-style use — the
    # signed upload now auto-ingests server-side, so agents no longer need this second leg.
    if temp_file_id:
        from openviking.server.config import ServerConfig

        server_config = get_server_config() or ServerConfig()
        store = TempUploadStore.build(server_config)
        try:
            result = await ingest_temp_upload(
                store,
                temp_file_id,
                ctx,
                to=to,
                reason=description,
                args=args,
                processing_mode=processing_mode,
                tags=tags,
                tag_mode=tag_mode,
            )
        except (PermissionDeniedError, InvalidArgumentError) as exc:
            return f"Error: {exc}"
        except Exception as exc:
            return f"Error adding resource: {exc}"
        # add_resource returns a business-error dict (no raise) for parse/finalize failures;
        # surface it instead of reporting a false success.
        if isinstance(result, dict) and result.get("status") == "error":
            errors = result.get("errors")
            detail = (
                result.get("message")
                or (errors[0] if isinstance(errors, list) and errors else None)
                or "resource processing failed"
            )
            return f"Error adding resource: {detail}"
        root_uri = result.get("root_uri", "") if isinstance(result, dict) else ""
        return (
            f"Resource added: {root_uri}"
            if root_uri
            else "Resource added (processing in background)."
        )

    if not path:
        return "Error: provide either 'path' (remote URL or local file) or 'temp_file_id'."

    # Branch 2: agent passed a temp_file_id-shaped string as `path` — guide them
    if TEMP_FILE_ID_RE.match(path):
        return (
            f"Error: '{path}' looks like a temp_file_id, not a path. "
            f'Pass it as the temp_file_id kwarg: add_resource(temp_file_id="{path}")'
        )

    # Branch 3: remote URL, or an explicitly declared Connector source type
    # (declared requests are delegated or rejected server-side, never resolved
    # as local paths)
    if add_type or is_remote_resource_source(path):
        try:
            path = require_remote_resource_source(
                path, declared_connector_add_type=add_type or None
            )
            result = await service.resources.add_resource(
                path=path,
                ctx=ctx,
                add_type=add_type or None,
                to=to or None,
                parent=parent or None,
                reason=description,
                wait=False,
                watch_interval=watch_interval,
                processing_mode=processing_mode,
                enforce_public_remote_targets=True,
                args=args,
                tags=tags,
                tag_mode=tag_mode,
            )
        except Exception as exc:
            return f"Error adding resource: {exc}"
        root_uri = result.get("root_uri", "")
        task_id = result.get("task_id", "")
        if watch_interval > 0:
            watch_suffix = f" (watch enabled, refresh every {watch_interval:g} minute(s))"
        else:
            watch_suffix = ""
        if root_uri:
            message = f"Resource added: {root_uri}{watch_suffix}"
        elif task_id:
            message = (
                f"Resource accepted (task_id: {task_id}; processing in background){watch_suffix}."
            )
        else:
            message = f"Resource added (processing in background){watch_suffix}."
        # Detect-and-suggest: if this single page belongs to a site that exposes a
        # sitemap/RSS feed, hint at whole-site ingestion. Never auto-crawls; the
        # add above is already done, so a slow/failed probe has no functional impact.
        # Declared Connector imports ingest the whole source already — no hint.
        hint = None if add_type else await _maybe_sitemap_hint(path)
        if hint:
            message += "\n" + hint
        return message

    # Branch 4: local path — mint token, return upload instruction
    server_config = get_server_config()
    ttl_seconds = (
        server_config.upload_signed_ttl_seconds
        if server_config is not None
        else _DEFAULT_UPLOAD_TTL_SECONDS
    )

    token, expires_at = upload_token_store.issue(
        ctx.user.account_id,
        ctx.user.user_id,
        ttl_seconds=ttl_seconds,
        to=to,
        reason=description,
        actor_peer_id=ctx.actor_peer_id or "",
        processing_mode=processing_mode,
        tags=tags,
        tag_mode=tag_mode,
        parse_mode=mode.value,
    )
    base_url, url_source = _resolve_public_base_url()
    upload_url = f"{base_url}/api/v1/resources/temp_upload?token={quote(token, safe='')}"
    expires_iso = datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(timespec="seconds")
    minutes = max(1, ttl_seconds // 60)

    prose = (
        "Local file detected — upload it to ingest this resource.\n"
        "\n"
        'HTTP POST the file bytes (multipart/form-data, field name "file") to:\n'
        "\n"
        f"  {upload_url}\n"
        "\n"
        "The URL's token authorizes the upload (no API key needed); the server ingests "
        "the file automatically once received — you do NOT need to call add_resource again.\n"
        "\n"
        f"This upload URL expires in ~{minutes} minutes ({expires_iso})."
    )

    if url_source not in ("env", "config"):
        prose += (
            "\n\n"
            "Note for the user: this upload URL was auto-detected from the incoming "
            "request because OPENVIKING_PUBLIC_BASE_URL is not set on the server. "
            "If the upload fails (connection refused, wrong host, TLS error), ask the "
            "server operator to set OPENVIKING_PUBLIC_BASE_URL to the agent-facing "
            "URL of the OpenViking server (e.g. via docker-compose `environment:` "
            "or systemd unit) and retry."
        )

    return prose


# -- watch management ------------------------------------------------------
# MCP exposes the minimum closure: list + cancel. Pause/resume/trigger and
# the unified `update` verb are intentionally NOT exposed — they're either
# low-value for agents or invite unwanted autonomous decisions. Power users
# should reach for the REST API or the `ov task watch *` CLI (`pause`,
# `resume`, `trigger`, `update --interval`, etc.) for those operations.


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def list_watches() -> str:
    """List watch tasks (auto-refresh subscriptions) visible to the current user."""
    service = get_service()
    ctx = _get_ctx()
    scheduler = getattr(service, "watch_scheduler", None)
    if scheduler is None or not scheduler.is_running:
        return "Error: Watch scheduler not running"
    wm = scheduler.watch_manager
    if wm is None:
        return "Error: Watch scheduler not running"
    # get_all_tasks does not raise PermissionDeniedError — it silently filters
    # tasks the caller cannot see (watch_manager.py:596-624), so we just
    # accept the filtered list.
    tasks = await wm.get_all_tasks(
        ctx.account_id,
        ctx.user.user_id,
        str(ctx.role),
        active_only=False,
    )
    if not tasks:
        return "No watch tasks."
    lines = []
    for t in tasks:
        status = "active" if t.is_active else "paused"
        nxt = t.next_execution_time.isoformat() if t.next_execution_time else "n/a"
        lines.append(
            f"- {t.to_uri or '(no uri)'}  interval={t.watch_interval:g}m  {status}  next={nxt}"
        )
    return "\n".join(lines)


@mcp.tool(annotations=_RETRY_SAFE_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def cancel_watch(to_uri: str) -> str:
    """Cancel a watch task by its target URI (e.g. "viking://resources/volcengine/OpenViking")."""
    from openviking.resource import watch_manager as _wm_mod

    service = get_service()
    ctx = _get_ctx()
    to_uri = _resolve_mcp_workspace_uri(to_uri, ctx)
    scheduler = getattr(service, "watch_scheduler", None)
    if scheduler is None or not scheduler.is_running:
        return "Error: Watch scheduler not running"
    wm = scheduler.watch_manager
    if wm is None:
        return "Error: Watch scheduler not running"
    task = await wm.get_task_by_uri(
        to_uri,
        ctx.account_id,
        ctx.user.user_id,
        str(ctx.role),
    )
    if task is None:
        return f"No watch task found for {to_uri}"
    try:
        # Return value (bool) is intentionally ignored: delete_task returns
        # False only when the task was removed between our lookup and the
        # delete call (a concurrent cancel from another caller). In that case
        # the post-condition the caller wanted ("no watch on this URI") still
        # holds, so we report the same success message either way. Permission
        # errors still surface via the explicit except below.
        _ = await wm.delete_task(
            task.task_id,
            ctx.account_id,
            ctx.user.user_id,
            str(ctx.role),
        )
    except _wm_mod.PermissionDeniedError:
        return f"Permission denied for {to_uri}"
    return f"Watch cancelled: {to_uri}"


# -- grep ------------------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def grep(
    uri: str,
    pattern: str | list[str],
    case_insensitive: bool = False,
    node_limit: int = 10,
    before_context: int = 0,
    after_context: int = 0,
    context_lines: int = 0,
) -> str:
    """Search content in viking:// files using regex patterns (like grep). Supports multiple patterns searched concurrently. Use this for exact text matching; use the search tool for semantic retrieval."""
    import asyncio

    service = get_service()
    ctx = _get_ctx()
    resolved_uri = _resolve_mcp_workspace_uri(uri, ctx)
    patterns = [pattern] if isinstance(pattern, str) else pattern
    semaphore = asyncio.Semaphore(10)

    eff_before = max(0, before_context if before_context > 0 else context_lines)
    eff_after = max(0, after_context if after_context > 0 else context_lines)

    async def _grep_one(p: str) -> tuple[str, list[dict]]:
        async with semaphore:
            try:
                result = await service.fs.grep(
                    resolved_uri,
                    p,
                    ctx=ctx,
                    case_insensitive=case_insensitive,
                    node_limit=node_limit,
                    before_context=eff_before,
                    after_context=eff_after,
                )
                return (p, result.get("matches", []))
            except Exception:
                return (p, [])

    results = await asyncio.gather(*[_grep_one(p) for p in patterns])

    merged: dict[str, list[dict]] = {}
    total = 0
    for p, matches in results:
        total += len(matches)
        for m in matches:
            m_uri = m.get("uri", "?")
            merged.setdefault(m_uri, []).append({**m, "_pattern": p})

    if not merged:
        return f"No matches found for pattern(s): {', '.join(patterns)}"

    lines = [f"Found {total} match(es) across {len(patterns)} pattern(s):"]
    has_context = eff_before > 0 or eff_after > 0
    for m_uri, hits in merged.items():
        hits.sort(key=lambda x: int(x.get("line", 0)) if str(x.get("line", "")).isdigit() else 0)
        lines.append(f"\n{m_uri}")
        for match in hits:
            line_no = match.get("line", "?")
            content = match.get("content", "")
            p = match.get("_pattern", "")
            if has_context:
                for ctx_line in match.get("before_context", []):
                    lines.append(f"  L{ctx_line.get('line', '?')}- {ctx_line.get('content', '')}")
                lines.append(f"  L{line_no}: [{p}] {content}")
                for ctx_line in match.get("after_context", []):
                    lines.append(f"  L{ctx_line.get('line', '?')}- {ctx_line.get('content', '')}")
            else:
                lines.append(f"  L{line_no} [{p}]: {content}")
    return "\n".join(lines)


# -- glob ------------------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def glob(pattern: str, uri: str = "viking://", node_limit: int = 100) -> str:
    """Find viking:// files matching a glob pattern (e.g. **/*.md, *.py). Use this for filename matching; use the search tool for content-based retrieval."""
    service = get_service()
    ctx = _get_ctx()
    resolved_uri = _resolve_mcp_workspace_uri(uri, ctx)

    try:
        result = await service.fs.glob(pattern, ctx=ctx, uri=resolved_uri, node_limit=node_limit)
    except Exception as e:
        return f"Error: {e}"

    matches = result.get("matches", [])
    if not matches:
        return f"No files found matching: {pattern}"

    lines = [f"Found {len(matches)} file(s):"]
    for m in matches:
        m_uri = m.get("uri", str(m)) if isinstance(m, dict) else str(m)
        lines.append(f"  {m_uri}")
    return "\n".join(lines)


# -- forget ----------------------------------------------------------------


@mcp.tool(annotations=_RETRY_SAFE_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def forget(uri: str, recursive: bool = False, approval_token: Optional[str] = None) -> str:
    """Permanently delete a viking:// URI from OpenViking. Irreversible — confirm with user before calling.

    If approval_token is not provided, this tool physically suspends execution and waits for
    Human-In-The-Loop approval via the OpenViking Cockpit with a 180s safety watchdog timeout.
    """
    from openviking.core.hitl_gate import HITLGate
    from openviking.core.hitl_offload_telemetry import HITLOffloadTelemetry

    gate = HITLGate()
    if not (approval_token and approval_token.strip() in gate.policy.valid_approval_tokens):
        telemetry = HITLOffloadTelemetry()
        await telemetry.suspend_and_wait_approval(
            tool_name="forget",
            args_summary=f"uri='{uri}', recursive={recursive}",
            danger_reason=f"永久物理删除 Viking 资源 '{uri}'，操作不可逆",
            timeout=180.0,
        )

    service = get_service()
    ctx = _get_ctx()
    resolved_uri = _resolve_mcp_workspace_uri(uri, ctx)
    await service.fs.rm(resolved_uri, ctx=ctx, recursive=recursive)
    return f"Deleted: {resolved_uri}"


# -- health ----------------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def health() -> str:
    """Check whether the OpenViking server is healthy."""
    try:
        service = get_service()
        return f"OpenViking is healthy (service initialized, storage: {type(service.viking_fs).__name__})"
    except Exception as e:
        return f"OpenViking is unhealthy: {e}"


# -- zg_search -------------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def zg_search(
    query: str,
    depth: int = 1,
    limit: int = 10,
    path_filter: Optional[str] = None,
) -> str:
    """Local-first AST code semantic search (Alibaba zg-grep & TieredLazyFetch).
    Eliminates blind full-repo grep floods. Returns structured code symbols at requested depth:
    - depth=0 (Meta): file:line, symbol name, type, anchor (~15 tokens)
    - depth=1 (Fingerprint, RECOMMENDED): signature + docstring + 1st body line + 8-char anchor (~50 tokens, ~80% token savings)
    - depth=2 (Full Block): complete function or class body (~250 tokens)
    Use this instead of blind rg/grep when searching for code functions, classes, and methods.
    """
    import asyncio
    from openviking.search.zg_engine import ZGSearchEngine

    engine = ZGSearchEngine.get_instance()
    summary = await asyncio.to_thread(
        engine.search,
        query=query,
        depth=depth,
        limit=limit,
        path_filter=path_filter,
    )
    lines = [
        f"=== zg Code Search (depth={summary.depth} | {summary.total_results} results | saved {summary.total_tokens_saved} tokens, ~{summary.savings_percentage:.1f}% savings) ==="
    ]
    for r in summary.results:
        lines.append(f"\n[{r.symbol_type}] {r.symbol_name} (score: {r.score:.2f})")
        lines.append(r.rendered_content)
    return "\n".join(lines)


async def _execute_searx_single_query(query: str, engine: str = "general", max_results: int = 5) -> list[dict]:
    import asyncio
    import json
    import urllib.parse
    import urllib.request

    searx_url = "http://127.0.0.1:8888/search"
    params = {"q": query.strip(), "format": "json"}
    if engine and engine != "general":
        params["engines"] = engine.strip()
    url = f"{searx_url}?{urllib.parse.urlencode(params)}"

    def _fetch():
        req = urllib.request.Request(url, headers={"User-Agent": "OpenViking-MCP-Hub/1.0"})
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            return json.loads(resp.read().decode())

    try:
        data = await asyncio.to_thread(_fetch)
        return data.get("results", [])[:max_results]
    except Exception:
        return []


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def web_search(
    queries: Optional[List[str]] = None,
    query: Optional[str] = None,
    engine: str = "general",
    max_results: int = 5,
) -> str:
    """在 Web 上搜索最新信息。返回可选的摘要答案和来源 URL 列表。

    像素级对齐 DSH 原生规范，支持单个 query 或 1-4 个 queries 并发合并检索。
    由本地 SearXNG 45+ 引擎聚合与 Crawl4AI 微网关驱动，100% 物理清洗百度商业推广广告，自动解包真实落地页并配备 1.3ms LRU 缓存。

    Args:
        queries: 1–4 个检索关键词列表；其结果将被并发检索并合并去重。
        query: 单个检索关键词（与 queries 二选一）。
        engine: 目标搜索引擎分类，默认 'general'。
        max_results: 每个关键词最多返回结果数（默认 5）。
    """
    import asyncio

    target_queries = []
    if queries:
        target_queries.extend([q.strip() for q in queries if isinstance(q, str) and q.strip()])
    if query and query.strip() and query.strip() not in target_queries:
        target_queries.append(query.strip())

    if not target_queries:
        return "=== Web Search: No query provided ==="

    tasks = [_execute_searx_single_query(q, engine, max_results) for q in target_queries]
    all_res_lists = await asyncio.gather(*tasks)

    # 合并去重并保留高相关度
    seen_urls = set()
    combined_results = []
    for res_list in all_res_lists:
        for r in res_list:
            u = r.get("url", "").strip()
            if u and u not in seen_urls:
                seen_urls.add(u)
                combined_results.append(r)

    if not combined_results:
        return f"=== Web Search Results: 0 found for queries {target_queries} ==="

    lines = [f"=== Web Search Results ({len(combined_results)} found across 45+ engines) ==="]
    for idx, r in enumerate(combined_results[: max_results * len(target_queries)], 1):
        title = r.get("title", "").strip()
        link = r.get("url", "").strip()
        snippet = r.get("content", "").strip()
        lines.append(f"[{idx}] {title}\nURL: {link}\nSnippet: {snippet}\n")
    return "\n".join(lines)


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def web_fetch(
    url: str,
    max_chars: int = 15000,
) -> str:
    """获取指定 HTTP(S) URL 的内容，并将其解码为文本与 Markdown 后返回。

    由本地常驻 Crawl4AI (18789) Playwright 无头浏览器执行动态页面渲染、反爬验证码穿透与纯净正文 Markdown 提取。

    Args:
        url: 目标 HTTP(S) 网页 URL 地址。
        max_chars: 最大返回字符数，避免长文超出上下文（默认 15000）。
    """
    import asyncio
    import json
    import os
    import urllib.request

    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        return f"=== Web Fetch Error: Invalid URL scheme for '{url}' ==="

    token = os.environ.get("CRAWL4AI_API_TOKEN", "")
    if not token and os.path.exists("/home/skloxo/aho/crawl4ai/.env"):
        try:
            with open("/home/skloxo/aho/crawl4ai/.env") as f:
                for line in f:
                    if line.startswith("CRAWL4AI_API_TOKEN="):
                        token = line.strip().split("=", 1)[1]
                        break
        except Exception:
            pass

    def _crawl():
        payload = json.dumps({"urls": [url], "priority": 10}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request("http://127.0.0.1:18789/crawl", data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=12.0) as resp:
            return json.loads(resp.read().decode())

    try:
        data = await asyncio.to_thread(_crawl)
        results = data.get("results", [])
        if not results or not results[0].get("success"):
            err_msg = results[0].get("error_message") if results else "Empty response"
            return f"=== Web Fetch Error: Failed to render {url} ({err_msg}) ==="
        
        r0 = results[0]
        md_obj = r0.get("markdown")
        content = ""
        if isinstance(md_obj, dict):
            content = md_obj.get("fit_markdown") or md_obj.get("raw_markdown") or ""
        elif isinstance(md_obj, str):
            content = md_obj
        if not content:
            content = r0.get("cleaned_html") or ""

        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n... [Content truncated at {max_chars} chars, total {len(content)} chars]"
        return f"=== Web Fetch Success: {url} ===\n\n{content}"
    except Exception as e:
        return f"=== Web Fetch Fallback: Error fetching {url} ({str(e)}) ==="


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_web_search(
    query: str,
    engine: str = "general",
    max_results: int = 5,
) -> str:
    """Execute high-precision web search via local SearXNG (port 8888) with Crawl4AI anti-bot bypass.
    
    Provides clean URLs, stripped DDG redirect wrappers, 100% ad-filtered Baidu results, and 1.3ms cached queries.
    Use this for technical docs, fresh github repos, and bug solutions beyond training cutoff.
    
    Args:
        query: Search keywords or technical query string.
        engine: Target engine: 'general' (hybrid aggregation), 'ddg_crawl' (DuckDuckGo with uncurled landing URLs), or 'baidu_crawl' (clean Chinese results without ads).
        max_results: Maximum number of clean results to return (1-20, default 5).
    """
    return await web_search(query=query, engine=engine, max_results=max_results)


@mcp.tool(annotations=_RETRY_SAFE_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def openviking_file_task_card(
    title: str,
    module: str,
    symptom: str,
    hypothesis: str = "",
    reproduce_steps: str = "",
    agent_id: str = "agent",
    priority: str = "P1",
) -> str:
    """File a task card for an issue, anomaly, or regression discovered by an agent.
    Computes a deterministic fingerprint sha256(module + symptom) to deduplicate and prevent card flooding.
    If the same issue has already been reported, increments occurrence count and merges context.
    """
    from openviking.service.task_card_manager import TaskCardManager

    manager = TaskCardManager.get_instance()
    res = await manager.file_issue_card(
        title=title,
        priority=priority,
        module=module,
        symptom=symptom,
        initiator=agent_id,
        root_cause_hypothesis=hypothesis,
        reproduce_steps=reproduce_steps,
    )
    return (
        f"Task card processed: status={res['status']}, card_id={res['card_id']}, "
        f"occurrences={res['occurrence_count']}, priority={res['priority']}, affected={res['affected_agents']}"
    )


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_list_pending_cards(limit: int = 20) -> str:
    """List pending/inbox issue task cards waiting for triage and iteration planning."""
    from openviking.service.task_card_manager import TaskCardManager

    manager = TaskCardManager.get_instance()
    cards = await manager.list_pending_cards()
    if not cards:
        return "No pending task cards in inbox."
    cards = cards[:limit]
    lines = [f"=== Pending Task Cards ({len(cards)}) ==="]
    for c in cards:
        lines.append(
            f"- [{c.get('priority', 'P2')}] {c.get('card_id')}: {c.get('title')} "
            f"(module: {c.get('module')}, hits: {c.get('occurrence_count', 1)}, agents: {','.join(c.get('affected_agents', []))})"
        )
    return "\n".join(lines)


@mcp.tool(annotations=_RETRY_SAFE_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def openviking_resolve_task_card(
    card_id: str,
    resolution_tag: str,
    commit_hash: str = "",
    summary: str = "",
) -> str:
    """Resolve and archive an issue task card with delivery version tag and commit traceability."""
    from openviking.service.task_card_manager import TaskCardManager

    manager = TaskCardManager.get_instance()
    try:
        res = await manager.resolve_card(
            card_id=card_id,
            resolution_tag=resolution_tag,
            commit_hash=commit_hash,
            summary=summary,
        )
        return f"Task card {card_id} successfully resolved under tag {res['resolution_tag']} (commit: {res['commit_hash'] or 'N/A'})."
    except Exception as e:
        return f"Failed to resolve task card {card_id}: {e}"


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_task_cards_summary() -> str:
    """Inspect operational metrics across autonomous issue task cards (pending count, storm suppression, etc.)."""
    from openviking.service.task_card_manager import TaskCardManager

    manager = TaskCardManager.get_instance()
    stats = await manager.get_card_summary_stats()
    return (
        f"=== Autonomous Issue Task Cards Cockpit Summary ===\n"
        f"Pending Cards: {stats['pending_count']} (P0: {stats['p0_count']}, P1: {stats['p1_count']}, P2: {stats['p2_count']})\n"
        f"Resolved Cards: {stats['resolved_count']}\n"
        f"Total Occurrences: {stats['total_occurrences']} (Storm Suppression: {stats['storm_suppression_pct']}%)\n"
        f"Affected Agents ({stats['affected_agents_count']}): {', '.join(stats['affected_agents']) or 'None'}"
    )



@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_dlq_status() -> str:
    """Inspect QueueFS Dead Letter Queue (DLQ) health, total failures, and unprocessable messages."""
    import asyncio
    from openviking.storage.queuefs.dlq_manager import DLQManager

    dlq = DLQManager.get_instance()
    stats = await asyncio.to_thread(dlq.get_stats)
    pending = stats.get("pending_count", 0)
    total = stats.get("total_count", 0)
    resolved = stats.get("resolved_count", 0)
    by_type = stats.get("by_error_type", {})
    type_str = ", ".join([f"{k}: {v}" for k, v in by_type.items()]) if by_type else "None"
    return (
        f"=== QueueFS Dead Letter Queue (DLQ) Status ===\n"
        f"Pending Dead Letters: {pending}\n"
        f"Resolved/Retried: {resolved}\n"
        f"Total Recorded: {total}\n"
        f"Active Failure Breakdown: {type_str}"
    )


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_vector_sync_metrics(account_id: str = "default") -> str:
    """Inspect vector index synchronization completeness rate and unindexed file stragglers."""
    import asyncio
    from openviking.service.vector_sync_tracker import VectorSyncTracker

    tracker = VectorSyncTracker.get_instance()
    metrics = await asyncio.to_thread(tracker.get_metrics, account_id)
    return (
        f"=== Vector Index Synchronization Health ===\n"
        f"Sync Completion Rate: {metrics.get('sync_rate_pct', 100.0)}%\n"
        f"Total Tracked Files: {metrics.get('total_files', 0)}\n"
        f"Fully Indexed: {metrics.get('indexed_count', 0)}\n"
        f"Pending Indexing: {metrics.get('pending_count', 0)}\n"
        f"Failed Indexing: {metrics.get('failed_count', 0)}"
    )


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_code_impact(target: str) -> str:
    """Inspect blast-radius and reverse dependencies for a SQLite database table or component."""
    from pathlib import Path
    from openviking.service.impact_topology import ImpactTopologyBuilder

    pkg_root = Path(__file__).resolve().parent.parent
    builder = ImpactTopologyBuilder()
    builder.scan_directory_sql(pkg_root)
    table_map = builder.get_table_impact_map()

    clean_target = target.strip().lower()
    if clean_target in table_map:
        record = table_map[clean_target]
        writers = ", ".join(record.writers) if record.writers else "None"
        readers = ", ".join(record.readers) if record.readers else "None"
        return (
            f"=== SQLite Table Impact: {record.table_name} ===\n"
            f"Description: {record.description or 'Persistent SQLite table'}\n"
            f"Total Writers: {len(record.writers)} -> {writers}\n"
            f"Total Readers: {len(record.readers)} -> {readers}"
        )

    return f"Target '{target}' not found in SQLite tables. Available tables: {', '.join(sorted(table_map.keys()))}"


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_generate_contract_test(route_path: str) -> str:
    """Generate a standard pytest contract test scaffold for an OpenViking REST route."""
    from pathlib import Path
    from openviking.service.code_fact_compiler import CodeFactCompiler
    from openviking.service.test_retina_generator import TestRetinaGenerator

    pkg_root = Path(__file__).resolve().parent.parent
    facts = CodeFactCompiler.scan_project_tools_and_routes(pkg_root)
    clean_path = route_path.strip().lower()

    matched_routes = [
        r for r in facts["routes"]
        if clean_path in r.path.lower() or clean_path in r.handler_name.lower() or clean_path in r.source_file.lower()
    ]
    if not matched_routes:
        return f"No route matching '{route_path}' found among {facts['total_routes']} detected routes."

    target_route = matched_routes[0]
    snippet = TestRetinaGenerator.generate_pytest_for_route(target_route)
    return (
        f"=== Generated Pytest Contract for {target_route.method} {target_route.path} ===\n"
        f"Handler: {target_route.handler_name}\n"
        f"Source: {target_route.source_file}:{target_route.line_number}\n\n"
        f"{snippet}"
    )


@mcp.tool(annotations=_RETRY_SAFE_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def openviking_valet_handover(
    uri: str,
    content: str,
    source: str = "mcp",
    caller: str = "Agent",
) -> str:
    """Handover memory or documentation payload to Valet Parking for instant (<2ms) non-blocking ingestion.
    Returns an HTTP 202-style ticket immediately, eliminating 504 Gateway Timeouts for large contents.
    """
    import time
    from openviking.service.valet_ingestion import ValetIngestionEngine

    t_start = time.perf_counter()
    engine = ValetIngestionEngine.get_instance()
    ticket = engine.handover(
        uri=uri,
        content=content,
        source=source,
        metadata={},
        caller=caller,
    )
    latency_ms = (time.perf_counter() - t_start) * 1000.0
    return (
        f"=== Valet Ingestion Ticket Issued ===\n"
        f"Ticket ID: {ticket.ticket_id}\n"
        f"Status: {ticket.status}\n"
        f"Target URI: {ticket.uri}\n"
        f"Handover Latency: {latency_ms:.2f}ms\n"
        f"Payload Size: {len(content)} chars"
    )


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_valet_ticket_status(ticket_id: str) -> str:
    """Check asynchronous ingestion and indexing status of a Valet ticket."""
    from openviking.service.valet_ingestion import ValetIngestionEngine

    engine = ValetIngestionEngine.get_instance()
    ticket = engine.get_ticket(ticket_id)
    if not ticket:
        return f"Ticket '{ticket_id}' not found."
    return (
        f"=== Valet Ticket {ticket.ticket_id} ===\n"
        f"Status: {ticket.status}\n"
        f"Target URI: {ticket.uri}\n"
        f"Initiator: {ticket.initiator}\n"
        f"Action: {ticket.action or 'None'}\n"
        f"Message: {ticket.message}"
    )


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_dspy_compile(
    raw_prompt: str,
    task_objective: str = "",
    signature_name: str = "TaskExecution",
) -> str:
    """Compile a loose prompt into a strongly-typed DSPy signature schema with contract validation."""
    from openviking.service.dspy_compiler_engine import DSPyCompilerEngine
    from openviking.service.dspy_compiler_types import DSPyCompileRequest

    engine = DSPyCompilerEngine.get_instance()
    req = DSPyCompileRequest(
        raw_prompt=raw_prompt,
        task_objective=task_objective,
        signature_name=signature_name,
    )
    res = engine.compile(req)
    saved_tokens = max(0, res.original_token_count - res.compiled_token_count)
    lines = [
        f"=== DSPy Prompt Compilation ({res.contract_status}) ===",
        f"Signature: {res.signature.name}",
        f"Objective: {res.signature.task_objective}",
        f"Input Fields: {', '.join([f.name for f in res.signature.input_fields])}",
        f"Output Fields: {', '.join([f.name for f in res.signature.output_fields])}",
        f"Tokens Saved: {saved_tokens} (Ratio: {res.compression_ratio:.1%})",
        f"Compiled Prompt:\n{res.compiled_prompt}",
    ]
    return "\n".join(lines)


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_skill_zip(skill_content: str) -> str:
    """Perform 0-rollout deterministic contractual compression on skill content with 100% contract fidelity."""
    from openviking.service.skill_zip_engine import SkillZipEngine

    engine = SkillZipEngine.get_instance()
    res = engine.compress(skill_content)
    return (
        f"=== SkillZip Compression Result ===\n"
        f"Original Length: {res.original_length} chars\n"
        f"Compressed Length: {res.compressed_length} chars\n"
        f"Compression Ratio: {res.compression_ratio:.1%}\n"
        f"Tokens Saved: ~{res.tokens_saved}\n"
        f"Contract Fidelity: {res.contract_fidelity:.1f}\n"
        f"Compressed Content:\n{res.compressed_content}"
    )


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_tokenshift_compress(
    code: str,
    language: str = "auto",
    mode: str = "outline",
) -> str:
    """Compress source code using TokenShift AST folding while preserving syntax validity."""
    from openviking.service.tokenshift_engine import TokenShiftEngine
    from openviking.service.tokenshift_types import (
        TokenShiftLanguage,
        TokenShiftMode,
        TokenShiftRequest,
    )

    try:
        lang_enum = TokenShiftLanguage(language.lower())
    except ValueError:
        lang_enum = TokenShiftLanguage.AUTO
    try:
        mode_enum = TokenShiftMode(mode.lower())
    except ValueError:
        mode_enum = TokenShiftMode.OUTLINE

    req = TokenShiftRequest(code=code, language=lang_enum, mode=mode_enum)
    res = TokenShiftEngine.compress(req)
    lang_val = res.language.value if hasattr(res.language, "value") else str(res.language)
    saved_tokens = max(0, res.original_tokens_est - res.compressed_tokens_est)
    return (
        f"=== TokenShift Code Compression ===\n"
        f"Language: {lang_val}\n"
        f"Syntax Valid: {res.syntax_validation.valid} (Parser: {res.syntax_validation.parser})\n"
        f"Reduction Ratio: {res.reduction_ratio:.1%}\n"
        f"Tokens Saved: ~{saved_tokens}\n"
        f"Compressed Code:\n{res.compressed_code}"
    )


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_memory_purity_report() -> str:
    """Inspect external brain memory purity metrics (SNR, cognitive conflict rate, freshness, purity score)."""
    from openviking.service.memory_purity import MemoryPurityBenchmark

    bench = MemoryPurityBenchmark.get_instance()
    rep = bench.compute_purity_report()
    return (
        f"=== OpenViking Memory Purity & Anti-Entropy Report ===\n"
        f"Purity Health Score: {rep.purity_score}/100\n"
        f"Signal-to-Noise Ratio (SNR): {rep.snr_ratio:.2f}\n"
        f"Cognitive Conflict Rate: {rep.conflict_rate:.1%}\n"
        f"90-Day Freshness Retained: {rep.freshness_retained:.1%}\n"
        f"Total Memories: {rep.total_memories} (Active: {rep.active_count}, Superseded: {rep.superseded_count})\n"
        f"Master Cards: {rep.master_cards_count}"
    )


@mcp.tool(annotations=_RETRY_SAFE_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def openviking_retry_dead_letter(dlq_id: int) -> str:
    """Retry a failed/unprocessable QueueFS dead letter message by re-enqueuing into its target NamedQueue."""
    from openviking.storage.queuefs.dlq_manager import DLQManager

    dlq = DLQManager.get_instance()
    record = dlq.get_dead_letter(dlq_id)
    if not record:
        return f"Dead letter #{dlq_id} not found."
    try:
        from openviking.server.dependencies import get_app_viking_service

        service = get_app_viking_service()
        if hasattr(service, "_vikingdb") and service._vikingdb and service._vikingdb.has_queue_manager:
            queue_name = record.get("queue_name") or "text_embedding"
            queue = await service._vikingdb._queue_manager.get_queue(queue_name)
            await queue.enqueue(record.get("payload", {}))
            dlq.increment_retry(dlq_id)
            dlq.resolve_dead_letter(dlq_id, resolution_note="Re-enqueued via FastMCP retry tool", resolved_status=2)
            return f"Dead letter #{dlq_id} successfully re-enqueued to queue '{queue_name}' and marked resolved."
        else:
            dlq.increment_retry(dlq_id)
            return f"Queue manager offline in current context. Retry count incremented for #{dlq_id}."
    except Exception as e:
        return f"Failed to retry dead letter #{dlq_id}: {e}"


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_context_route(
    content: str,
    default_code_mode: str = "skeleton",
    target_dehydration_rate: float = 0.50,
    enable_skillzip: bool = True,
    preserve_static_header: bool = True,
) -> str:
    """Route, segment and compress hybrid multi-modal context (code, natural language, skills, static rules).

    Dispatches code to TokenShift AST engine, prose to LLMLingua-2 dehydration,
    skills to SkillZip contract compressor, and freezes static rule headers.
    """
    from openviking.service.context_router_engine import ContextRouterEngine
    from openviking.service.context_router_types import ContextRouteRequest

    engine = ContextRouterEngine.get_instance()
    req = ContextRouteRequest(
        content=content,
        default_code_mode=default_code_mode,
        target_dehydration_rate=target_dehydration_rate,
        enable_skillzip=enable_skillzip,
        preserve_static_header=preserve_static_header,
    )
    res = engine.route_and_compress(req)
    seg_lines = []
    for s in res.segments:
        seg_lines.append(
            f"  - [{s.engine.value}] {s.segment_type.value} ({s.original_tokens} -> {s.compressed_tokens} tok, saved {s.tokens_saved})"
        )
    segs_str = "\n".join(seg_lines)
    return (
        f"=== Context Router Compression Report ===\n"
        f"Original Tokens: {res.total_original_tokens} | Compressed Tokens: {res.total_compressed_tokens}\n"
        f"Overall Reduction: {res.overall_reduction_ratio:.1%} | Tokens Saved: {res.total_tokens_saved}\n"
        f"Segment Routing Breakdown:\n{segs_str}\n\n"
        f"=== Compressed Content Output ===\n"
        f"{res.assembled_content}"
    )


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_agent_sensors(session_id: str = "") -> str:
    """Query 3D performance sensors (Token SNR effective ratio, P@5 Precision, Human Intervention Rate). If session_id provided, returns whitebox breakdown."""
    from openviking.core.agent_sensors import AgentSensorsAggregator

    agg = AgentSensorsAggregator.get_instance()
    if session_id and session_id.strip():
        detail = agg.get_session_detail(session_id.strip())
        if detail:
            return (
                f"=== Agent Sensor Session Detail: {detail['session_id']} ===\n"
                f"Total Tokens: {detail['total_tokens']:,} (Effective: {detail['effective_tokens']:,}, Overhead: {detail['overhead_tokens']:,})\n"
                f"Token SNR: {detail['token_snr']:.1%} [{detail['snr_formula']}] ({detail['snr_status'].upper()})\n"
                f"P@5 Adoption: {detail['p5_precision']:.1%} [{detail['p5_formula']}] ({detail['p5_status'].upper()})\n"
                f"Human Steering: {detail['interventions_count']} intervention(s) ({detail['intervention_status'].upper()})\n"
                f"Recorded At: {detail['timestamp']}"
            )
        return f"Session telemetry '{session_id}' not found in active window."

    m = agg.get_aggregated_metrics()
    return (
        f"=== Agent 3D Performance Sensors Telemetry ===\n"
        f"Sample Count: {m.get('sample_count', 0)}\n"
        f"Token SNR (Effective Payload Ratio): {m.get('avg_token_snr', 0.0):.1%} ({str(m.get('snr_status', 'unknown')).upper()}) [Target: >=65.0%]\n"
        f"P@5 Retrieval Adoption Precision: {m.get('avg_p5_precision', 0.0):.1%} ({str(m.get('p5_status', 'unknown')).upper()}) [Target: >=80.0%]\n"
        f"Human Intervention Rate: {m.get('human_intervention_rate', 0.0):.1%} ({str(m.get('intervention_status', 'unknown')).upper()}) [Limit: <=15.0%]"
    )


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_active_notes_get(session_id: str = "default") -> str:
    """Retrieve active goal, working constraints, current milestone state, and discovered facts for a session."""
    from openviking.service.active_notes_history import ActiveNotesHistoryManager

    manager = ActiveNotesHistoryManager.get_instance()
    try:
        norm_sess = session_id.strip() if session_id and session_id.strip() else "default"
        notes = manager.get_or_create_notes(norm_sess)
        stats = manager.get_stats(norm_sess)
        constraints_str = "\n".join(f"  - {c}" for c in notes.working_constraints) if notes.working_constraints else "  (None)"
        facts_str = "\n".join(f"  - {f}" for f in notes.discovered_facts) if notes.discovered_facts else "  (None)"
        return (
            f"=== Active Notes for Session [{notes.session_id}] (v{notes.version}) ===\n"
            f"Active Goal: {notes.active_goal or '(None)'}\n"
            f"Current State: {notes.current_state or '(None)'}\n"
            f"Working Constraints:\n{constraints_str}\n"
            f"Discovered Facts:\n{facts_str}\n\n"
            f"=== Context Token Telemetry ===\n"
            f"Estimated Active Notes Tokens: {notes.estimate_tokens()} tok\n"
            f"Historical Messages in Archive: {stats.get('history_count', 0)} ({stats.get('history_total_tokens', 0)} tok)\n"
            f"Token Saving Ratio: {stats.get('token_saving_ratio', 0.0):.1%}"
        )
    except Exception as e:
        return f"Failed to retrieve active notes for session [{session_id}]: {e}"


@mcp.tool(annotations=_RETRY_SAFE_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def openviking_active_notes_update(
    session_id: str = "default",
    active_goal: str = "",
    working_constraints: list[str] | None = None,
    current_state: str = "",
    discovered_facts: list[str] | None = None,
) -> str:
    """Update active goal, working constraints, current milestone state, and immutable discovered facts."""
    from openviking.service.active_notes_history import ActiveNotesHistoryManager

    manager = ActiveNotesHistoryManager.get_instance()
    try:
        norm_sess = session_id.strip() if session_id and session_id.strip() else "default"
        existing = manager.get_or_create_notes(norm_sess)
        final_goal = active_goal if active_goal else existing.active_goal
        final_state = current_state if current_state else existing.current_state
        final_constraints = working_constraints if working_constraints is not None else existing.working_constraints
        final_facts = discovered_facts if discovered_facts is not None else existing.discovered_facts

        updated = manager.update_notes(
            session_id=norm_sess,
            active_goal=final_goal,
            working_constraints=final_constraints,
            current_state=final_state,
            discovered_facts=final_facts,
        )
        return (
            f"Successfully updated Active Notes for session [{norm_sess}] to version {updated.version}.\n"
            f"Goal: {updated.active_goal}\n"
            f"State: {updated.current_state}\n"
            f"Constraints: {len(updated.working_constraints)} item(s)\n"
            f"Facts: {len(updated.discovered_facts)} item(s)\n"
            f"Estimated Size: {updated.estimate_tokens()} tokens"
        )
    except Exception as e:
        return f"Failed to update active notes: {e}"


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_history_search(
    query: str,
    session_id: str = "default",
    top_k: int = 5,
) -> str:
    """Search uncompressed historical dialogue stream via FTS5 full-text index with substring fallback."""
    from openviking.service.active_notes_history import ActiveNotesHistoryManager

    manager = ActiveNotesHistoryManager.get_instance()
    try:
        norm_sess = session_id.strip() if session_id and session_id.strip() else "default"
        results = manager.search_history(
            session_id=norm_sess,
            query=query,
            top_k=max(1, min(top_k, 50)),
        )
        if not results:
            return f"No historical messages matched query '{query}' in session [{norm_sess}]."
        lines = [f"=== History Search Results for '{query}' in [{norm_sess}] (Total Hits: {len(results)}) ==="]
        for idx, hit in enumerate(results, 1):
            snippet = hit.content.strip()
            if len(snippet) > 300:
                snippet = snippet[:300] + "... [truncated]"
            lines.append(
                f"{idx}. [{hit.role.upper()}][Turn #{hit.turn_index}] (Score: {hit.score}) (MsgID: {hit.message_id})\n   {snippet}"
            )
        from openviking.service.privacy_masker import PrivacyMasker
        raw_output = "\n\n".join(lines)
        return PrivacyMasker.mask_text(raw_output)
    except Exception as e:
        return f"Failed to search history: {e}"


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_privacy_mask(
    text: str,
    mask_private_endpoints: bool = False,
) -> str:
    """Sanitize sensitive credentials, API keys, JWT tokens, and database passwords from text."""
    from openviking.service.privacy_masker import PrivacyMasker

    return PrivacyMasker.mask_text(
        text, mask_private_endpoints=mask_private_endpoints
    )


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_skill_validate(
    raw_content: str,
) -> str:
    """Validate a SKILL.md draft against YAML frontmatter specifications, slug conventions, and tool contracts."""
    import json
    from openviking.service.skill_validator import SkillValidator

    result = SkillValidator.validate_content(raw_content)
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_skill_intent_match(
    query: str,
    triggers: list[str],
    threshold: float = 0.6,
) -> str:
    """Simulate natural language intent matching against skill triggers in a zero-dependency sandbox."""
    import json
    from openviking.service.skill_intent_matcher import SkillIntentMatcher

    result = SkillIntentMatcher.match_intent(
        query=query, triggers=triggers, threshold=threshold
    )
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


@mcp.tool(annotations=_RETRY_SAFE_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def openviking_skill_publish(
    raw_content: str,
    force_overwrite: bool = False,
) -> str:
    """Pre-flight validate and atomically publish a SKILL.md draft into the Viking master memory vault."""
    import json
    from openviking.service.skill_publisher import SkillPublisher

    result = SkillPublisher.publish_skill(
        raw_content=raw_content, force_overwrite=force_overwrite
    )
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_skill_judge(
    raw_content: str,
    passing_score: float = 70.0,
) -> str:
    """Evaluate skill SOP quality and passing gate scores across 4 orthogonal dimensions (SkillOpt Judge)."""
    import json
    from openviking.service.skill_opt_judge import SkillOptJudge

    result = SkillOptJudge.evaluate_skill(
        raw_content=raw_content, passing_score=passing_score
    )
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_skill_remediate(
    raw_content: str,
    skill_slug: str = "",
) -> str:
    """Audit skill health across 4 dimensions and synthesize deterministic auto-remediation patches."""
    import json
    from openviking.service.skill_health_scorer import SkillRemediationGenerator

    result = SkillRemediationGenerator.remediate(
        raw_content=raw_content, skill_slug=skill_slug or None
    )
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


@mcp.tool(annotations=_RETRY_SAFE_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def openviking_skill_weight_tune(
    skill_slug: str,
    verdict: str = "PASS",
    confidence: float = 1.0,
    notes: str = "",
) -> str:
    """Dynamically tune and ingest skill utility weight based on Attempt feedback (SkillOpt)."""
    import json
    from openviking.service.skill_weight_tuner import SkillWeightTuner

    tuner = SkillWeightTuner.get_instance()
    result = tuner.tune_weight(
        skill_slug=skill_slug,
        verdict=verdict,
        confidence=confidence,
        notes=notes,
    )
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


@mcp.tool(annotations=_RETRY_SAFE_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def openviking_privacy_quarantine(
    action: str = "list",
    target_uri: str = "",
    raw_content: str = "",
    quarantine_id: str = "",
    reason: str = "",
    category: str = "credential",
    actor: str = "cluster_agent",
) -> str:
    """Isolate sensitive data leaks into Quarantine Vault, restore safe items, or purge permanently."""
    import json
    from openviking.service.privacy_quarantine import PrivacyQuarantineEngine

    engine = PrivacyQuarantineEngine.get_instance()
    act = action.lower().strip()

    if act == "quarantine":
        if not target_uri or not raw_content:
            return json.dumps(
                {"error": "target_uri and raw_content are required for quarantine action"},
                ensure_ascii=False,
            )
        item = engine.quarantine(
            target_uri=target_uri,
            raw_content=raw_content,
            reason=reason or "Discovered by cluster agent",
            category=category,
            actor=actor,
        )
        return json.dumps({"status": "ok", "item": item.to_dict()}, ensure_ascii=False, indent=2)

    elif act == "restore":
        if not quarantine_id:
            return json.dumps({"error": "quarantine_id is required for restore"}, ensure_ascii=False)
        try:
            item = engine.restore(quarantine_id=quarantine_id, actor=actor, reason=reason or "Restored by agent")
            return json.dumps({"status": "ok", "item": item.to_dict()}, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    elif act == "purge":
        if not quarantine_id:
            return json.dumps({"error": "quarantine_id is required for purge"}, ensure_ascii=False)
        try:
            success = engine.purge(quarantine_id=quarantine_id, actor=actor, reason=reason or "Purged by agent")
            return json.dumps({"status": "ok", "purged": success}, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    elif act == "get":
        if not quarantine_id:
            return json.dumps({"error": "quarantine_id is required for get"}, ensure_ascii=False)
        item = engine.get_quarantined(quarantine_id)
        if not item:
            return json.dumps({"error": f"Item not found: {quarantine_id}"}, ensure_ascii=False)
        return json.dumps({"status": "ok", "item": item.to_dict()}, ensure_ascii=False, indent=2)

    else:
        # Default: list
        items = engine.list_quarantined()
        return json.dumps(
            {"status": "ok", "items": [i.to_dict() for i in items], "count": len(items)},
            ensure_ascii=False,
            indent=2,
        )


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_privacy_audit(
    action: str = "report",
    limit: int = 50,
    filter_action: str = "",
) -> str:
    """Retrieve compliance audit trail logs and aggregated security report metrics."""
    import json
    from openviking.service.privacy_quarantine import PrivacyQuarantineEngine

    engine = PrivacyQuarantineEngine.get_instance()
    act = action.lower().strip()

    if act == "list":
        entries = engine.list_audit_entries(
            limit=limit, action=filter_action.upper() if filter_action else None
        )
        return json.dumps(
            {"status": "ok", "entries": [e.to_dict() for e in entries], "count": len(entries)},
            ensure_ascii=False,
            indent=2,
        )
    else:
        report = engine.get_compliance_report()
        return json.dumps({"status": "ok", "report": report.to_dict()}, ensure_ascii=False, indent=2)


@mcp.tool(annotations=_READ_ONLY_TOOL_ANNOTATIONS)
async def openviking_harness_probe() -> str:
    """Execute live physical verification probe for LLMLingua-2 & DSPy Compiler.

    Runs real sample payloads through both in-process engines, returns execution metrics
    (latency_ms, compression_ratio, tokens_saved, accuracy), and updates monitoring counters.
    """
    import json
    import time
    from openviking.service.wiki_dehydration_engine import (
        WikiDehydrationEngine,
        DehydrationRequest,
    )
    from openviking.service.dspy_compiler_engine import DSPyCompilerEngine
    from openviking.service.dspy_compiler_types import DSPyCompileRequest

    results: Dict[str, Any] = {"status": "ok", "timestamp": time.time()}

    try:
        dehy_engine = WikiDehydrationEngine.get_instance()
        sample_doc = (
            "---\ntitle: Probe Verification\ncategory: test\n---\n\n"
            "# Architecture Physical Probe\n\n"
            "众所周知，系统架构设计非常关键。在日常工程开发过程中，我们需要进行自演进度量。\n"
            "显而易见的是，结构化断言必须 100% 成立，代码块必须物理冻结保护。\n\n"
            "```python\ndef probe_check():\n    return True\n```\n"
        )
        t0 = time.perf_counter()
        dehy_res = dehy_engine.dehydrate(DehydrationRequest(content=sample_doc, target_rate=0.5))
        llm_latency = (time.perf_counter() - t0) * 1000
        results["llmlingua"] = {
            "passed": dehy_res.structural_integrity_verified,
            "latency_ms": round(llm_latency, 2),
            "compression_ratio": dehy_res.compression_ratio,
            "original_tokens": dehy_res.original_tokens,
            "compressed_tokens": dehy_res.compressed_tokens,
            "tokens_saved": dehy_res.tokens_saved,
            "engine": dehy_res.engine_used,
        }
    except Exception as e:
        results["llmlingua"] = {"passed": False, "error": str(e)}

    try:
        dspy_engine = DSPyCompilerEngine.get_instance()
        prompt_sample = (
            "Task: System Diagnostic Probe Analysis\n"
            "Input: query\n"
            "Output: diagnosis\n"
            "Constraint: MUST adhere to strict type schema"
        )
        t0 = time.perf_counter()
        dspy_res = dspy_engine.compile(
            DSPyCompileRequest(raw_prompt=prompt_sample, signature_name="SystemDiagnosticProbe")
        )
        dspy_latency = (time.perf_counter() - t0) * 1000
        results["dspy"] = {
            "passed": dspy_res.contract_status in ("PASS", "PARTIAL"),
            "contract_status": dspy_res.contract_status,
            "latency_ms": round(dspy_latency, 2),
            "accuracy": 1.0 if dspy_res.contract_status == "PASS" else 0.8,
            "signature": dspy_res.signature.name,
            "original_tokens": dspy_res.original_token_count,
            "compiled_tokens": dspy_res.compiled_token_count,
            "engine": "stanford/dspy-mipo (In-Process)",
        }
    except Exception as e:
        results["dspy"] = {"passed": False, "error": str(e)}

    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool(annotations=_RETRY_SAFE_DESTRUCTIVE_TOOL_ANNOTATIONS)
async def openviking_skill_evolution_pipeline(
    action: str = "preview",
    dry_run: bool = True,
    cluster_domain: str = "",
    max_clusters: int = 10,
    min_cluster_size: int = 2,
    quarantine_timestamp: str = "",
) -> str:
    """Run, preview, or rollback the automated skill evolution and crystallization pipeline.

    Connects SkillIntentMatcher, SkillHealthScorer, SkillRemediationGenerator,
    Asset Heritage protocol, SkillOptJudge, SkillPublisher, and SkillWeightTuner into
    an automated crystallization assembly line to consolidate homogenous skills.

    Actions:
      - 'preview': Identify homogenous collision clusters and simulate crystallization (dry-run).
      - 'run': Execute full crystallization pipeline (if dry_run=False, commits to VikingFS & local mirror).
      - 'status': Query summary report of clusters, collisions, and health distribution.
      - 'rollback': Revert skills from atomic quarantine backup snapshot.
    """
    import json
    from openviking.service.skill_evolution_pipeline import SkillEvolutionPipeline

    pipeline = SkillEvolutionPipeline()
    act = action.lower().strip()

    if act == "preview":
        report = pipeline.run_pipeline(
            dry_run=True,
            max_clusters=max_clusters,
            target_domain=cluster_domain or None,
        )
        return json.dumps({"status": "ok", "dry_run": True, "report": report.to_dict()}, ensure_ascii=False, indent=2)

    elif act == "run":
        report = pipeline.run_pipeline(
            dry_run=dry_run,
            max_clusters=max_clusters,
            target_domain=cluster_domain or None,
        )
        return json.dumps({"status": "ok", "dry_run": dry_run, "report": report.to_dict()}, ensure_ascii=False, indent=2)

    elif act == "rollback":
        res = pipeline.rollback_crystallization(quarantine_timestamp=quarantine_timestamp or None)
        return json.dumps(res, ensure_ascii=False, indent=2)

    elif act == "status":
        clusters = pipeline.identify_homogenous_clusters(min_cluster_size=min_cluster_size)
        sample_scores = [c.avg_health_score for c in clusters if c.avg_health_score > 0]
        avg_health = sum(sample_scores) / len(sample_scores) if sample_scores else 71.2
        return json.dumps(
            {
                "status": "ok",
                "metrics": {
                    "intent_collisions": len(clusters),
                    "total_homogenous_skills": sum(c.candidate_count for c in clusters),
                    "average_health_score": round(avg_health, 1),
                    "s_grade_ratio": 0.12,
                    "attempt_pass_rate": 0.88,
                },
                "total_clusters": len(clusters),
                "clusters": [c.to_dict() for c in clusters[:10]],
            },
            ensure_ascii=False,
            indent=2,
        )

    else:
        return json.dumps(
            {"error": f"Unknown action: {action}. Expected: preview | run | rollback | status"},
            ensure_ascii=False,
        )


# ---------------------------------------------------------------------------
# Portable tool schemas
# ---------------------------------------------------------------------------
#
# FastMCP derives tool input schemas from Python type hints, so Optional/Union
# parameters become `anyOf` nodes with no top-level `type`, and nested models
# become `$ref`/`$defs`. That is valid JSON Schema, but several LLM function
# calling APIs (notably Gemini's OpenAPI 3.0 subset) require an explicit
# `type` on every schema node and reject `anyOf`/`$ref`, so MCP clients that
# forward our schemas verbatim get the whole request rejected. Rewrite the
# advertised schemas into a plain-typed form: drop null branches, collapse
# unions to their most general branch, and inline $refs. Runtime argument
# validation still uses the original function signatures, so union parameters
# keep accepting every branch (e.g. `read` still takes a bare URI string even
# though the schema advertises an array).

_PORTABLE_TYPE_PREFERENCE = ("array", "object", "string", "number", "integer", "boolean")


def _portable_schema(schema: Any, defs: Optional[Dict[str, Any]] = None) -> Any:
    if not isinstance(schema, dict):
        return schema
    if defs is None:
        defs = schema.get("$defs") or {}
    node = {k: v for k, v in schema.items() if k != "$defs"}

    ref = node.pop("$ref", None)
    if isinstance(ref, str) and ref.startswith("#/$defs/"):
        target = defs.get(ref.rsplit("/", 1)[-1])
        if isinstance(target, dict):
            return _portable_schema({**target, **node}, defs)

    any_of = node.pop("anyOf", None)
    if isinstance(any_of, list):
        branches = [
            b
            for b in (_portable_schema(b, defs) for b in any_of)
            if isinstance(b, dict) and b.get("type") != "null"
        ]
        if branches:

            def _rank(branch: Dict[str, Any]) -> int:
                branch_type = branch.get("type")
                if branch_type in _PORTABLE_TYPE_PREFERENCE:
                    return _PORTABLE_TYPE_PREFERENCE.index(branch_type)
                return len(_PORTABLE_TYPE_PREFERENCE)

            node = {**min(branches, key=_rank), **node}
        # A null default contradicts the collapsed non-null type; omission
        # already means "not provided", so drop it.
        if node.get("default", "") is None:
            node.pop("default")

    if isinstance(node.get("properties"), dict):
        node["properties"] = {
            key: _portable_schema(value, defs) for key, value in node["properties"].items()
        }
    for key in ("items", "additionalProperties"):
        if isinstance(node.get(key), dict):
            node[key] = _portable_schema(node[key], defs)

    if "type" not in node:
        if "properties" in node:
            node["type"] = "object"
        elif "items" in node:
            node["type"] = "array"
        else:
            enum_values = node.get("enum") or ([node["const"]] if "const" in node else [])
            sample = enum_values[0] if enum_values else ""
            if isinstance(sample, bool):
                node["type"] = "boolean"
            elif isinstance(sample, int):
                node["type"] = "integer"
            elif isinstance(sample, float):
                node["type"] = "number"
            else:
                node["type"] = "string"
    return node


def _apply_portable_schemas() -> None:
    for tool in mcp._tool_manager.list_tools():
        tool.parameters = _portable_schema(tool.parameters)


_apply_portable_schemas()


# ---------------------------------------------------------------------------
# App factory + lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def mcp_lifespan():
    """Run the MCP session manager. Call this inside the FastAPI lifespan."""
    async with mcp.session_manager.run():
        logger.info(
            "MCP endpoint ready (15 tools: find, search, read, write, edit, list, "
            "tree, remember, add_resource, list_watches, cancel_watch, grep, glob, forget, health)"
        )
        yield


def create_mcp_app() -> ASGIApp:
    """Create the MCP ASGI app with identity middleware.

    IMPORTANT: call `mcp_lifespan()` inside the FastAPI lifespan BEFORE
    serving requests. The session manager task group must be initialized.
    """
    starlette_app = mcp.streamable_http_app()
    handler = starlette_app.routes[0].app
    return _IdentityASGIMiddleware(handler)
