# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Search endpoints for OpenViking HTTP Server."""

import asyncio
import math
from typing import Any, Dict, List, Optional, Sequence, Union

from fastapi import APIRouter, Depends, Request
from fastapi import Response as FastAPIResponse

from openviking.core.path_variables import resolve_path_variables
from openviking.core.uri_validation import validate_request_viking_uri
from openviking.models.embedder.base import query_embed_cache_var
from openviking.pyagfs.exceptions import AGFSClientError, AGFSNotFoundError
from openviking.retrieve.context_assembler import AssembleParams, assemble_context
from openviking.server.auth import get_request_context
from openviking.server.dependencies import get_service
from openviking.server.error_mapping import map_exception
from openviking.server.identity import RequestContext
from openviking.server.models import Response
from openviking.server.routers.search_models import (
    CONTEXT_ONLY_FIELDS,
    FindRequest,
    GlobRequest,
    GrepRequest,
    SearchRequest,
    TimeField,
    context_only_fields_error,
)
from openviking.server.telemetry import run_operation
from openviking.utils.image_search import is_viking_uri
from openviking.utils.search_filters import (
    SearchContextTypeInput,
    _resolve_levels,
    merge_search_filter,
)
from openviking.utils.tags import build_search_tags_filter
from openviking_cli.exceptions import InvalidArgumentError, NotFoundError

__all__ = [
    "router",
    "CONTEXT_ONLY_FIELDS",
    "context_only_fields_error",
    "FindRequest",
    "SearchRequest",
    "GrepRequest",
    "GlobRequest",
]


def _sanitize_floats(obj: Any) -> Any:
    """Recursively replace inf/nan with 0.0 to ensure JSON compliance."""
    if isinstance(obj, float):
        if math.isinf(obj) or math.isnan(obj):
            return 0.0
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_floats(v) for v in obj]
    return obj


router = APIRouter(prefix="/api/v1/search", tags=["search"])


def _resolve_search_limit(limit: int, node_limit: Optional[int]) -> int:
    return node_limit if node_limit is not None else limit


def _resolve_search_filter(
    request_filter: Optional[Dict[str, Any]],
    context_type: Optional[SearchContextTypeInput],
    since: Optional[str],
    until: Optional[str],
    time_field: Optional[TimeField],
    tags: Optional[List[str]],
) -> Optional[Dict[str, Any]]:
    try:
        merged = merge_search_filter(
            request_filter,
            context_type=context_type,
            since=since,
            until=until,
            time_field=time_field,
        )
        tag_filter = build_search_tags_filter(tags)
        if not tag_filter:
            return merged
        if merged:
            if tag_filter.get("op") == "and" and isinstance(tag_filter.get("conds"), list):
                return {"op": "and", "conds": [merged, *tag_filter["conds"]]}
            return {"op": "and", "conds": [merged, tag_filter]}
        return tag_filter
    except ValueError as exc:
        raise InvalidArgumentError(str(exc)) from exc


def _resolve_uri_or_uris(uri: Union[str, List[str]], ctx: RequestContext) -> Union[str, List[str]]:
    """Resolve path variables in a single URI or list of URIs."""
    if isinstance(uri, list):
        return [validate_request_viking_uri(resolve_path_variables(u), ctx) for u in uri]
    if not uri:
        return ""
    return validate_request_viking_uri(resolve_path_variables(uri), ctx)


def _resolve_uri_list(uris: Sequence[str], ctx: RequestContext) -> list[str]:
    return [validate_request_viking_uri(resolve_path_variables(uri), ctx) for uri in uris]


def _resolve_image_url(
    image_url: str | list[str] | None, ctx: RequestContext
) -> str | list[str] | None:
    if image_url is None:
        return None
    if isinstance(image_url, list):
        resolved_items = []
        for url in image_url:
            r = _resolve_image_url(url, ctx)
            if r and isinstance(r, str) and r.strip():
                resolved_items.append(r.strip())
        return resolved_items if resolved_items else None
    if not isinstance(image_url, str):
        return None
    cleaned = image_url.strip()
    if not cleaned:
        return None
    resolved = resolve_path_variables(cleaned)
    if is_viking_uri(resolved):
        return validate_request_viking_uri(resolved, ctx, field_name="image_url")
    return resolved


async def _inline_read_content(
    result: Any,
    *,
    service: Any,
    ctx: RequestContext,
) -> Any:
    """Attach visible file content to ranked hits when it can be read."""
    if not isinstance(result, dict):
        return result

    hits = [
        hit
        for category in ("memories", "resources", "skills")
        for hit in result.get(category, [])
        if isinstance(hit, dict) and isinstance(hit.get("uri"), str)
    ]
    semaphore = asyncio.Semaphore(10)

    async def _read(hit: Dict[str, Any]) -> None:
        async with semaphore:
            try:
                hit["content"] = await service.fs.read_visible(hit["uri"], ctx=ctx)
            except Exception:
                pass

    await asyncio.gather(*(_read(hit) for hit in hits))
    return result


@router.post("/find")
async def find(
    request: FindRequest,
    raw_request: Request,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Semantic search without session context."""
    service = get_service()
    actual_limit = _resolve_search_limit(request.limit, request.node_limit)
    effective_filter = _resolve_search_filter(
        request.filter,
        request.context_type,
        request.since,
        request.until,
        request.time_field,
        request.tags,
    )
    resolved_target_uri = _resolve_uri_or_uris(request.target_uri, _ctx)
    resolved_image_url = _resolve_image_url(request.image_url, _ctx)
    execution = await run_operation(
        operation="search.find",
        telemetry=request.telemetry,
        fn=lambda: service.search.find(
            query=request.query,
            ctx=_ctx,
            target_uri=resolved_target_uri,
            limit=actual_limit,
            score_threshold=request.score_threshold,
            filter=effective_filter,
            level=_resolve_levels(request.level) or None,
            image_url=resolved_image_url,
            mode=request.mode,
            events_time_decay_protection=request.events_time_decay_protection,
        ),
    )
    result = execution.result
    if hasattr(result, "to_dict"):
        result = result.to_dict(include_provenance=request.include_provenance)
    if request.read_content:
        result = await _inline_read_content(result, service=service, ctx=_ctx)

    # 🛡️ Purity Gate: 自动清洗毒化/爬虫抓取失败的纯 HTML 垃圾网页切片与未清洗资源
    if result and isinstance(result, dict):
        for category in ("resources", "memories", "skills"):
            hits = result.get(category, [])
            if isinstance(hits, list):
                clean_hits = []
                for hit in hits:
                    if not isinstance(hit, dict):
                        continue
                    uri_val = str(hit.get("uri", ""))
                    abstract_val = str(hit.get("abstract", "") or hit.get("content", ""))
                    is_garbage = (
                        "<!DOCTYPE html" in abstract_val
                        or "open-platform-wrapper" in abstract_val
                        or "lark-markdown" in uri_val
                    )
                    if not is_garbage:
                        clean_hits.append(hit)
                result[category] = clean_hits

    is_internal_probe = raw_request.headers.get("x-openviking-internal-probe") == "1"
    if result and isinstance(result, dict) and request.query and not is_internal_probe:
        total = result.get("total", 0)
        all_hits = result.get("resources", []) + result.get("memories", []) + result.get("skills", [])
        top_score = max([float(x.get("score", 0.0)) for x in all_hits]) if all_hits else 0.0
        if total == 0 or top_score < 0.45:
            try:
                from openviking.service.entropy_watchdog import get_entropy_watchdog
                get_entropy_watchdog().notify_zero_hit(request.query)
            except Exception:
                pass
    return Response(
        status="ok",
        result=result,
        telemetry=execution.telemetry,
    ).model_dump(exclude_none=True)


def _context_ignored_fields(request: SearchRequest) -> List[str]:
    """Fields accepted but inert in context mode, surfaced through stats."""
    ignored: List[str] = []
    if request.level is not None:
        ignored.append("level")
    if (request.quotas is not None or request.purpose is not None) and (
        "limit" in request.model_fields_set or request.node_limit is not None
    ):
        ignored.append("limit")
    return ignored


async def _search_context(
    *,
    service: Any,
    ctx: RequestContext,
    request: SearchRequest,
    effective_filter: Optional[Dict[str, Any]],
    actual_limit: int,
):
    """Assemble an injection-ready context block for one request."""
    params = AssembleParams(
        query=request.query,
        image_url=_resolve_image_url(request.image_url, ctx),
        limit=actual_limit,
        score_threshold=request.score_threshold,
        filter=effective_filter,
        session_id=request.session_id,
        query_expansion=request.query_expansion,
        max_tokens=request.max_tokens,
        quotas=request.quotas,
        purpose=request.purpose,
        detail=request.detail,
        dedup_turns=request.dedup_turns,
        exclude_uris=_resolve_uri_list(request.exclude_uris, ctx),
        peer_scope=request.peer_scope,
        other_peer_penalty=request.other_peer_penalty,
        rewrite=request.rewrite,
        rewrite_max_bullets=request.rewrite_max_bullets,
    )
    execution = await run_operation(
        operation="search.context",
        telemetry=request.telemetry,
        fn=lambda: assemble_context(service=service, ctx=ctx, params=params),
    )
    result = execution.result
    ignored = _context_ignored_fields(request)
    if ignored:
        result.stats["ignored"] = ignored
    return Response(
        status="ok",
        result=_sanitize_floats(result.to_dict()),
        telemetry=execution.telemetry,
    ).model_dump(exclude_none=True)


@router.post("/search")
async def search(
    request: SearchRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Semantic search with optional session context."""
    # Install the request-scoped query embedding cache before any search work
    # spawns tasks: every find fanned out below shares this dict and reuses the
    # first embed of a given query text.
    query_embed_cache_var.set({})
    service = get_service()
    actual_limit = _resolve_search_limit(request.limit, request.node_limit)
    effective_filter = _resolve_search_filter(
        request.filter,
        request.context_type,
        request.since,
        request.until,
        request.time_field,
        request.tags,
    )
    if request.mode == "context":
        return await _search_context(
            service=service,
            ctx=_ctx,
            request=request,
            effective_filter=effective_filter,
            actual_limit=actual_limit,
        )
    resolved_target_uri = _resolve_uri_or_uris(request.target_uri, _ctx)
    resolved_image_url = _resolve_image_url(request.image_url, _ctx)

    async def _search():
        session = None
        # Intent off: skip session.load — SearchService will not scan session either.
        if request.session_id and service.search.is_intent_enabled():
            session = service.sessions.session(_ctx, request.session_id)
            await session.load()
        return await service.search.search(
            query=request.query,
            ctx=_ctx,
            target_uri=resolved_target_uri,
            session=session,
            limit=actual_limit,
            score_threshold=request.score_threshold,
            filter=effective_filter,
            level=_resolve_levels(request.level) or None,
            image_url=resolved_image_url,
            events_time_decay_protection=request.events_time_decay_protection,
        )

    execution = await run_operation(
        operation="search.search",
        telemetry=request.telemetry,
        fn=_search,
    )
    result = execution.result
    if hasattr(result, "to_dict"):
        result = result.to_dict(include_provenance=request.include_provenance)
    if request.read_content:
        result = await _inline_read_content(result, service=service, ctx=_ctx)
    result = _sanitize_floats(result)
    return Response(
        status="ok",
        result=result,
        telemetry=execution.telemetry,
    ).model_dump(exclude_none=True)


@router.post("/grep")
async def grep(
    request: GrepRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Content search with pattern."""
    service = get_service()
    resolved_uri = validate_request_viking_uri(resolve_path_variables(request.uri), _ctx)
    resolved_exclude_uri = None
    if request.exclude_uri:
        resolved_exclude_uri = validate_request_viking_uri(
            resolve_path_variables(request.exclude_uri), _ctx, field_name="exclude_uri"
        )
    try:
        result = await service.fs.grep(
            resolved_uri,
            request.pattern,
            ctx=_ctx,
            exclude_uri=resolved_exclude_uri,
            case_insensitive=request.case_insensitive,
            node_limit=request.node_limit,
            level_limit=request.level_limit,
            tags=request.tags,
            include_tags=request.include_tags,
            before_context=request.before_context,
            after_context=request.after_context,
        )
    except AGFSNotFoundError:
        raise NotFoundError(resolved_uri, "file")
    except AGFSClientError as e:
        mapped = map_exception(e, resource=resolved_uri, resource_type="file")
        if mapped is not None:
            raise mapped from e
        raise
    except Exception as exc:
        mapped = map_exception(exc, resource=resolved_uri, resource_type="file")
        if mapped is not None:
            raise mapped from exc
        raise
    return Response(status="ok", result=result)


@router.post("/glob")
async def glob(
    request: GlobRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """File pattern matching."""
    service = get_service()
    resolved_uri = validate_request_viking_uri(resolve_path_variables(request.uri), _ctx)
    try:
        result = await service.fs.glob(
            request.pattern,
            ctx=_ctx,
            uri=resolved_uri,
            node_limit=request.node_limit,
            extra_fields=request.extra_fields,
            tags=request.tags,
            include_tags=request.include_tags,
        )
    except AGFSNotFoundError:
        raise NotFoundError(resolved_uri or request.pattern, "file")
    except AGFSClientError as e:
        mapped = map_exception(e, resource=resolved_uri or request.pattern, resource_type="file")
        if mapped is not None:
            raise mapped from e
        raise
    except Exception as exc:
        mapped = map_exception(exc, resource=request.uri, resource_type="file")
        if mapped is not None:
            raise mapped from exc
        raise
    return Response(status="ok", result=result)
