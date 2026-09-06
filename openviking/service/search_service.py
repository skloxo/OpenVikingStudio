# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Search Service for OpenViking.

Provides semantic search operations: search, find.
"""

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

from openviking.server.identity import RequestContext
from openviking.storage.viking_fs import VikingFS
from openviking.utils.image_search import (
    image_bytes_to_data_uri,
    is_data_image_uri,
    is_http_url,
    is_viking_uri,
)
from openviking_cli.exceptions import InvalidArgumentError, NotInitializedError
from openviking_cli.utils import get_logger

if TYPE_CHECKING:
    from openviking.session import Session

logger = get_logger(__name__)

QUERY_CACHE_TTL = 120.0  # 120s TTL to shield downstream models from storm amplification
QUERY_CACHE_MAXSIZE = 1000  # LRU capacity


def _ensure_non_empty_query(
    query: str,
    image_url: Optional[str] = None,
    filter: Optional[Dict] = None,
) -> None:
    """Reject a request that gives the search nothing to work with.

    A filter is an acceptable substitute for a query: the result set is then
    fully determined by the filter, which is exactly what an exact-match lookup
    (e.g. by a tag carrying an external id) needs. Without either one the call
    would return an arbitrary slice of the whole store.
    """
    if query.strip() or image_url or filter:
        return
    raise InvalidArgumentError(
        "Search query or image_url must not be empty unless a filter is provided."
    )


class SearchService:
    """Semantic search service with lightweight L0 query cache."""

    def __init__(self, viking_fs: Optional[VikingFS] = None):
        self._viking_fs = viking_fs
        self._query_cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def clear_cache(self) -> None:
        """Clear all in-memory query cache entries."""
        self._query_cache.clear()

    def _make_cache_key(
        self,
        op: str,
        query: str,
        target_uri: Union[str, List[str]],
        limit: int,
        score_threshold: Optional[float],
        filter: Optional[Dict],
        level: Optional[List[int]],
        image_url: Optional[str],
        ctx: RequestContext,
    ) -> str:
        account_id = getattr(ctx, "account_id", None) or getattr(getattr(ctx, "user", None), "account_id", "default")
        user_id = getattr(getattr(ctx, "user", None), "user_id", None) or "default"
        t_uri = tuple(sorted(target_uri)) if isinstance(target_uri, list) else target_uri
        lvl = tuple(level) if isinstance(level, list) else (level or "")
        flt = json.dumps(filter, sort_keys=True) if filter else ""
        img = (image_url[:100] + str(len(image_url))) if (image_url and len(image_url) > 100) else (image_url or "")
        raw = f"{account_id}:{user_id}:{op}:{query.strip().lower()}:{t_uri}:{limit}:{score_threshold}:{lvl}:{flt}:{img}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _get_cached(self, cache_key: str) -> Optional[Any]:
        if cache_key in self._query_cache:
            ts, res = self._query_cache[cache_key]
            if (time.time() - ts) < QUERY_CACHE_TTL:
                self._query_cache.move_to_end(cache_key)
                try:
                    from openviking.metrics.datasources.cache import CacheEventDataSource
                    CacheEventDataSource.record_hit("L0")
                except Exception:
                    pass
                return res
            del self._query_cache[cache_key]
        return None

    def _set_cached(self, cache_key: str, res: Any) -> None:
        self._query_cache[cache_key] = (time.time(), res)
        if len(self._query_cache) > QUERY_CACHE_MAXSIZE:
            self._query_cache.popitem(last=False)

    def set_viking_fs(self, viking_fs: VikingFS) -> None:
        """Set VikingFS instance (for deferred initialization)."""
        self._viking_fs = viking_fs

    def _ensure_initialized(self) -> VikingFS:
        """Ensure VikingFS is initialized."""
        if not self._viking_fs:
            raise NotInitializedError("VikingFS")
        return self._viking_fs

    def is_intent_enabled(self) -> bool:
        """Whether search uses session context for LLM intent analysis.

        When false, callers should skip session.load / get_context_for_search:
        VikingFS.search ignores session_info and searches with the raw query.
        Default is True (matches RetrievalConfig) when config is unset.
        """
        if not self._viking_fs or self._viking_fs.retrieval_config is None:
            return True
        return bool(self._viking_fs.retrieval_config.enable_intent)

    async def _resolve_image_url(
        self,
        image_url: Optional[str],
        ctx: RequestContext,
    ) -> Optional[str]:
        if not image_url:
            return None
        if is_viking_uri(image_url):
            viking_fs = self._ensure_initialized()
            content = await viking_fs.read_file_bytes(image_url, ctx=ctx)
            return image_bytes_to_data_uri(content, image_url)
        if is_data_image_uri(image_url) or is_http_url(image_url):
            return image_url
        raise InvalidArgumentError(
            "image_url must be a data:image base64 URI, http(s) URL, or viking:// URI."
        )

    async def search(
        self,
        query: str,
        ctx: RequestContext,
        target_uri: Union[str, List[str]] = "",
        session: Optional["Session"] = None,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter: Optional[Dict] = None,
        level: Optional[List[int]] = None,
        image_url: Optional[str] = None,
    ) -> Any:
        """Complex search with session context.

        Args:
            query: Query string
            target_uri: Target directory URI(s), supports str or List[str]
            session: Session object for context
            limit: Max results
            score_threshold: Score threshold
            filter: Metadata filters
            level: Filter by level (0=abstract, 1=overview, 2=file)

        Returns:
            FindResult
        """
        resolved_image_url = await self._resolve_image_url(image_url, ctx)
        _ensure_non_empty_query(query, resolved_image_url)
        viking_fs = self._ensure_initialized()

        session_info = None
        # Intent off: session_info is unused by VikingFS — skip the archive/message scan.
        if session is not None and self.is_intent_enabled() and not resolved_image_url:
            session_info = await session.get_context_for_search(query)

        result = await viking_fs.search(
            query=query,
            ctx=ctx,
            target_uri=target_uri,
            session_info=session_info,
            limit=limit,
            score_threshold=score_threshold,
            filter=filter,
            level=level,
            image_url=resolved_image_url,
        )
        try:
            from openviking.observability.events import try_publish_event
            result_count = len(result) if hasattr(result, "__len__") else 0
            account_id = getattr(ctx, "account_id", None) or "default"
            user_id = getattr(getattr(ctx, "user", None), "user_id", None) or "default"
            try_publish_event(
                "retrieval.query",
                {
                    "operation": "search",
                    "status": "success",
                    "result_count": result_count,
                    "account_id": account_id,
                    "user_id": user_id,
                },
            )
        except Exception:
            pass
        return result

    async def find(
        self,
        query: str,
        ctx: RequestContext,
        target_uri: Union[str, List[str]] = "",
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter: Optional[Dict] = None,
        level: Optional[List[int]] = None,
        image_url: Optional[str] = None,
    ) -> Any:
        """Semantic search without session context.

        Args:
            query: Query string
            target_uri: Target directory URI(s), supports str or List[str]
            limit: Max results
            score_threshold: Score threshold
            filter: Metadata filters
            level: Filter by level (0=abstract, 1=overview, 2=file)

        Returns:
            FindResult
        """
        resolved_image_url = await self._resolve_image_url(image_url, ctx)
        _ensure_non_empty_query(query, resolved_image_url, filter)
        viking_fs = self._ensure_initialized()

        cache_key = self._make_cache_key(
            op="find",
            query=query,
            target_uri=target_uri,
            limit=limit,
            score_threshold=score_threshold,
            filter=filter,
            level=level,
            image_url=resolved_image_url,
            ctx=ctx,
        )
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        result = await viking_fs.find(
            query=query,
            ctx=ctx,
            target_uri=target_uri,
            limit=limit,
            score_threshold=score_threshold,
            filter=filter,
            level=level,
            image_url=resolved_image_url,
        )
        self._set_cached(cache_key, result)

        try:
            from openviking.observability.events import try_publish_event
            result_count = len(result) if hasattr(result, "__len__") else 0
            account_id = getattr(ctx, "account_id", None) or "default"
            user_id = getattr(getattr(ctx, "user", None), "user_id", None) or "default"
            try_publish_event(
                "retrieval.query",
                {
                    "operation": "find",
                    "status": "success",
                    "result_count": result_count,
                    "account_id": account_id,
                    "user_id": user_id,
                },
            )
        except Exception:
            pass
        return result
