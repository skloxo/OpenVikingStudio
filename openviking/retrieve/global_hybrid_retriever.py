# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Global single-stage hybrid retriever: vector + BM25 parallel recall with score fidelity."""

from __future__ import annotations

import asyncio
import math
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from openviking.core.context import ContextLevel
from openviking.core.retrieval_targets import default_target_directories
from openviking.core.retrieval_types import SearchType
from openviking.models.embedder.base import EmbedResult, embed_compat, embedder_supports_multimodal
from openviking.models.rerank import RerankClient
from openviking.retrieve.asymmetric_decay import AsymmetricDecayEngine
from openviking.retrieve.retrieval_stats import get_stats_collector
from openviking.retrieve.rrf_fusion import rrf_fuse
from openviking.server.identity import RequestContext
from openviking.storage.abstract_overview import AbstractOverviewFormatError, body_for_preview
from openviking.storage.bm25_fts_index import BM25FTSIndex, BM25Match
from openviking.storage.expr import FilterExpr
from openviking.storage.vikingdb_manager import VikingDBManager, VikingDBManagerProxy
from openviking.telemetry import get_current_telemetry
from openviking.utils.tags import normalize_search_tags
from openviking.utils.token_estimation import estimate_text_tokens, truncate_text_to_token_budget
from openviking_cli.exceptions import InvalidArgumentError
from openviking_cli.retrieve.types import ContextType, MatchedContext, QueryResult, TypedQuery
from openviking_cli.utils.config import RerankConfig
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)


def _has_context_type_filter(scope: Any) -> bool:
    """Recognize explicit type constraints in public DSL and internal filter ASTs."""
    if isinstance(scope, dict):
        return scope.get("field") == "context_type" or any(
            _has_context_type_filter(value)
            for value in scope.values()
            if isinstance(value, (dict, list))
        )
    if isinstance(scope, list):
        return any(_has_context_type_filter(value) for value in scope)
    if hasattr(scope, "payload"):
        return _has_context_type_filter(scope.payload)
    return getattr(scope, "field", None) == "context_type" or any(
        _has_context_type_filter(value) for value in getattr(scope, "conds", [])
    )


class RetrieverMode(str):
    THINKING = "thinking"
    QUICK = "quick"
    FAST = "fast"


class GlobalHybridRetriever:
    """Single-stage global retriever combining dense vectors and FTS5 BM25 with score fidelity."""

    RERANK_CANDIDATE_MULTIPLIER = 2
    LEVEL_URI_SUFFIX = {0: ".abstract.md", 1: ".overview.md"}

    def __init__(
        self,
        storage: VikingDBManager,
        embedder: Optional[Any],
        rerank_config: Optional[RerankConfig] = None,
        retrieval_config: Optional[Any] = None,
        bm25_index: Optional[BM25FTSIndex] = None,
        **kwargs: Any,
    ):
        self.vector_store = storage
        self.embedder = embedder
        self.rerank_config = rerank_config
        self.retrieval_config = retrieval_config
        self.bm25_index = bm25_index
        self.rerank_max_input_tokens = rerank_config.max_input_tokens if rerank_config else 0
        self.threshold = rerank_config.threshold if rerank_config else 0.0

        if rerank_config and rerank_config.is_available():
            self._rerank_client = self._init_rerank_client(rerank_config)
        else:
            self._rerank_client = None

        self.decay_engine = AsymmetricDecayEngine()

    def _init_rerank_client(self, rerank_config: RerankConfig) -> Any:
        return RerankClient.from_config(rerank_config)

    def _create_vector_proxy(self, ctx: RequestContext) -> Any:
        return VikingDBManagerProxy(self.vector_store, ctx)

    async def retrieve(
        self,
        query: TypedQuery,
        ctx: RequestContext,
        limit: int = 5,
        mode: Optional[RetrieverMode | str] = None,
        score_threshold: Optional[float] = None,
        score_gte: bool = False,
        scope_dsl: Optional[FilterExpr | Dict[str, Any]] = None,
        level: Optional[List[int]] = None,
        events_time_decay_protection: Optional[str] = None,
        request_now: Optional[datetime] = None,
        search_type: SearchType = "semantic",
        has_explicit_target: Optional[bool] = None,
    ) -> QueryResult:
        t0 = time.monotonic()
        telemetry = get_current_telemetry()
        effective_threshold = self._resolve_threshold(score_threshold)
        image_query = query.image_query

        if mode is None:
            mode = RetrieverMode.THINKING if self._rerank_client else RetrieverMode.QUICK
        elif mode == RetrieverMode.FAST:
            mode = RetrieverMode.QUICK

        use_rerank = mode == RetrieverMode.THINKING and self._rerank_client is not None and not image_query
        target_dirs = [d for d in (query.target_directories or []) if d]
        if has_explicit_target is None:
            has_explicit_target = bool(target_dirs)
        if image_query and level is None:
            level = [2]

        vector_proxy = self._create_vector_proxy(ctx)
        if not await vector_proxy.collection_exists_bound():
            return QueryResult(query=query, matched_contexts=[], searched_directories=[])

        query_vector = None
        sparse_query_vector = None
        if search_type == "semantic" and self.embedder:
            if image_query and not await embedder_supports_multimodal(self.embedder):
                raise InvalidArgumentError("Image search requires a multimodal embedding model.")
            with telemetry.measure("search.embed_query"):
                embedding_input = getattr(query, "embedding_input", None) or query.query
                res: EmbedResult = await embed_compat(self.embedder, embedding_input, is_query=True)
                query_vector = res.dense_vector
                sparse_query_vector = res.sparse_vector

        context_type = query.context_type.value if query.context_type else None
        if (
            image_query
            and context_type is None
            and not has_explicit_target
            and not _has_context_type_filter(scope_dsl)
        ):
            context_type = ContextType.RESOURCE.value

        root_uris = target_dirs if target_dirs else default_target_directories(ctx, context_type=query.context_type)
        search_limit = limit * self.RERANK_CANDIDATE_MULTIPLIER if use_rerank else limit

        dense_task = self._search_dense(
            vector_proxy, query_vector, sparse_query_vector, query.query,
            context_type, target_dirs, scope_dsl, level, search_limit, search_type,
            events_time_decay_protection, request_now
        )

        async def _safe_bm25() -> tuple[list[dict[str, Any]], bool]:
            try:
                return await self._search_bm25(query.query, search_limit, context_type, target_dirs)
            except Exception as exc:
                logger.warning(f"[GlobalHybridRetriever] BM25 invocation fail-open degraded: {exc}")
                return [], False

        dense_res, (sparse_res, is_bm25_ready) = await asyncio.gather(dense_task, _safe_bm25())

        fused = self._fuse_and_rescore(
            dense_candidates=dense_res,
            sparse_candidates=sparse_res,
            limit=search_limit,
            is_bm25_ready=is_bm25_ready,
        )

        # Apply asymmetric time decay
        eval_now_dt = request_now or datetime.now(timezone.utc)
        eval_now_ts = eval_now_dt.timestamp()
        for item in fused:
            meta = item.get("extra_metadata") or {}
            raw_score = self._finite_score(item.get("_score", 0.0))
            raw_updated = meta.get("updated_ts") or item.get("updated_ts")
            updated_ts = self._parse_ts(raw_updated)
            status = str(meta.get("status") or item.get("status") or "active")
            mem_type = meta.get("memory_type") or item.get("memory_type")
            assessment = self.decay_engine.evaluate_candidate(
                uri=item.get("uri", ""),
                raw_score=raw_score,
                updated_ts=updated_ts,
                status=status,
                now_ts=eval_now_ts,
                active_count=int(meta.get("active_count") or item.get("active_count") or 0),
                memory_type=mem_type,
            )
            item["_score"] = assessment.adjusted_score
            item["extra_metadata"] = {
                **meta,
                "decay_factor": assessment.decay_factor,
                "is_immune": assessment.is_immune,
                "is_bm25_ready": is_bm25_ready,
            }

        candidates = sorted(fused, key=lambda x: self._finite_score(x.get("_score", 0.0)), reverse=True)
        scores = [candidate["_score"] for candidate in candidates]
        rerank_used = use_rerank and bool(candidates)
        if rerank_used:
            docs = [str(candidate.get("abstract", "")) for candidate in candidates]
            scores = await self._rerank_scores(query.query, docs, scores)

        passed_candidates = [
            {**candidate, "_final_score": score}
            for candidate, score in zip(candidates, scores, strict=True)
            if self._passes_threshold(score, effective_threshold, score_gte)
        ]

        matched = await self._convert_to_matched_contexts(passed_candidates, ctx=ctx)
        final = matched[:limit]

        elapsed_ms = (time.monotonic() - t0) * 1000
        get_stats_collector().record_query(
            context_type=context_type or "unknown",
            result_count=len(final),
            scores=[m.score for m in final],
            latency_ms=elapsed_ms,
            rerank_used=rerank_used,
        )

        return QueryResult(query=query, matched_contexts=final, searched_directories=root_uris)

    async def _search_dense(
        self, vector_proxy, q_vec, sq_vec, q_text, ctx_type, targets, scope, level, limit, s_type, decay_p, req_now
    ):
        decay_kw = {}
        if decay_p is not None:
            decay_kw = {
                "events_time_decay_protection": decay_p,
                "request_now": req_now or datetime.now(timezone.utc),
            }
        if s_type == "keywords":
            return await vector_proxy.search_by_keywords_in_tenant(
                query=q_text,
                context_type=ctx_type,
                target_directories=targets,
                extra_filter=scope,
                level=level,
                limit=limit,
            )
        return await vector_proxy.search_in_tenant(
            query_vector=q_vec,
            sparse_query_vector=sq_vec,
            context_type=ctx_type,
            target_directories=targets,
            extra_filter=scope,
            level=level,
            limit=limit,
            **decay_kw,
        )

    async def _search_bm25(self, query: str, limit: int, ctx_type: Optional[str], target_dirs: Optional[List[str]]) -> tuple[list[dict[str, Any]], bool]:
        if not self.bm25_index:
            try:
                self.bm25_index = BM25FTSIndex.get_instance()
            except Exception:
                return [], False
        try:
            matches: list[BM25Match] = await asyncio.to_thread(
                self.bm25_index.search,
                query=query,
                limit=limit,
                context_type=ctx_type,
                target_directories=target_dirs,
            )
            candidates = [
                {
                    "uri": m.uri,
                    "title": m.title,
                    "level": m.level,
                    "context_type": m.context_type,
                    "bm25_score": m.bm25_score,
                    "snippet": m.snippet,
                    "abstract": m.snippet or m.title,
                }
                for m in matches
            ]
            return candidates, True
        except Exception as exc:
            logger.warning(f"[GlobalHybridRetriever] BM25 FTS5 search fail-open degraded: {exc}")
            return [], False

    def _fuse_and_rescore(
        self,
        dense_candidates: list[dict[str, Any]],
        sparse_candidates: list[dict[str, Any]],
        limit: int,
        is_bm25_ready: bool,
    ) -> list[dict[str, Any]]:
        dense_by_uri: dict[str, dict[str, Any]] = {}
        for d in dense_candidates:
            u = d.get("uri", "")
            if not u:
                continue
            sc = self._finite_score(d.get("_score", 0.0))
            prev = dense_by_uri.get(u)
            if prev is None or sc > prev["_score"]:
                dense_by_uri[u] = {**d, "_score": sc}

        dense_list = list(dense_by_uri.values())

        if not sparse_candidates:
            for d in dense_list:
                d["extra_metadata"] = {
                    **(d.get("extra_metadata") or {}),
                    "origin": "dense_only",
                    "is_bm25_ready": is_bm25_ready,
                }
            return dense_list

        sparse_by_uri: dict[str, dict[str, Any]] = {}
        for s in sparse_candidates:
            u = s.get("uri", "")
            if not u:
                continue
            prev = sparse_by_uri.get(u)
            if prev is None or s.get("bm25_score", 0.0) > prev.get("bm25_score", 0.0):
                sparse_by_uri[u] = s
        sparse_list = list(sparse_by_uri.values())

        fused_items = rrf_fuse(
            dense_results=dense_list,
            sparse_results=sparse_list,
            top_k=limit,
        )

        results = []
        for item in fused_items:
            base_dense = dense_by_uri.get(item.uri)
            base_sparse = sparse_by_uri.get(item.uri)
            if base_dense:
                base_score = self._finite_score(base_dense.get("_score", 0.0))
                rrf_gain = min(0.10, item.rrf_score * 5.0)
                fused_score = round(min(1.0, base_score + rrf_gain), 4)
                record = dict(base_dense)
            else:
                base_score = 0.50
                rrf_gain = min(0.10, item.rrf_score * 5.0)
                fused_score = round(base_score + rrf_gain, 4)
                record = dict(base_sparse or {})
                record["_score"] = fused_score
                record["uri"] = item.uri
                record["context_type"] = record.get("context_type") or "resource"
                record["level"] = record.get("level", 2)
                record["abstract"] = record.get("abstract") or record.get("snippet", "")

            record["_score"] = fused_score
            record["extra_metadata"] = {
                **(record.get("extra_metadata") or {}),
                "origin": item.origin,
                "rrf_score": item.rrf_score,
                "fused_rank": item.fused_rank,
                "is_bm25_ready": is_bm25_ready,
            }
            results.append(record)
        return results

    def _resolve_threshold(self, threshold: Optional[float]) -> float:
        resolved = threshold if threshold is not None else self.threshold
        return resolved if resolved is not None else 0.0

    @staticmethod
    def _passes_threshold(score: float, threshold: float, score_gte: bool) -> bool:
        if score_gte:
            return score >= threshold
        return score > threshold

    @classmethod
    def _append_level_suffix(cls, uri: str, level: int) -> str:
        """Return user-facing URI with L0/L1 suffix reconstructed by level."""
        suffix = cls.LEVEL_URI_SUFFIX.get(level)
        if not uri or not suffix:
            return uri
        if uri.endswith(f"/{suffix}"):
            return uri
        if uri.endswith("/.abstract.md") or uri.endswith("/.overview.md"):
            return uri
        if uri.endswith("/") and not uri.endswith("://"):
            uri = uri.rstrip("/")
        return f"{uri}/{suffix}"

    @staticmethod
    def _finite_score(val: Any, default: float = 0.0) -> float:
        try:
            s = float(val)
            return s if math.isfinite(s) else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _parse_ts(val: Any) -> Optional[float]:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, datetime):
            return val.timestamp()
        if isinstance(val, str):
            try:
                return float(val)
            except ValueError:
                pass
            try:
                dt = datetime.fromisoformat(val)
                return dt.timestamp()
            except Exception:
                return None
        return None

    async def _rerank_scores(
        self,
        query: str,
        documents: List[str],
        fallback_scores: List[float],
    ) -> List[float]:
        """Return rerank scores or fall back to vector scores."""
        if not self._rerank_client or not documents:
            return fallback_scores

        rerank_query = query
        rerank_documents = [
            (index, document) for index, document in enumerate(documents) if document.strip()
        ]
        if not rerank_documents:
            return fallback_scores

        if self.rerank_max_input_tokens > 0:
            max_query_tokens = self.rerank_max_input_tokens * 3 // 4
            if estimate_text_tokens(query) > max_query_tokens:
                rerank_query = truncate_text_to_token_budget(query, max_query_tokens)
            document_tokens = self.rerank_max_input_tokens - estimate_text_tokens(rerank_query)
            rerank_documents = [
                (index, truncate_text_to_token_budget(document, document_tokens))
                for index, document in rerank_documents
            ]

        try:
            scores = await asyncio.to_thread(
                self._rerank_client.rerank_batch,
                rerank_query,
                [document for _, document in rerank_documents],
            )
        except Exception as e:
            logger.warning(
                "[GlobalHybridRetriever] Rerank failed, fallback to vector scores: %s", e
            )
            return fallback_scores

        if not scores or len(scores) != len(rerank_documents):
            logger.warning(
                "[GlobalHybridRetriever] Invalid rerank result, fallback to vector scores"
            )
            return fallback_scores

        normalized_scores = list(fallback_scores)
        for score, (index, _) in zip(scores, rerank_documents, strict=True):
            normalized_scores[index] = self._finite_score(score, fallback_scores[index])
        return normalized_scores

    async def _convert_to_matched_contexts(
        self,
        candidates: List[Dict[str, Any]],
        ctx: RequestContext,
    ) -> List[MatchedContext]:
        results = []
        for c in candidates:
            final_score = self._finite_score(c.get("_final_score", c.get("_score", 0.0)))
            level = int(c.get("level", 2))
            display_uri = self._append_level_suffix(c.get("uri", ""), level)
            abstract = str(c.get("abstract", "") or "")
            if level in (0, 1) and abstract:
                try:
                    abstract = body_for_preview(abstract)
                except AbstractOverviewFormatError as exc:
                    logger.warning("Malformed sidecar in retrieval result %s: %s", display_uri, exc)
                    abstract = ""

            mc = MatchedContext(
                uri=display_uri,
                context_type=(
                    ContextType(c["context_type"])
                    if c.get("context_type")
                    else ContextType.RESOURCE
                ),
                level=level,
                abstract=abstract,
                category=str(c.get("category", "") or ""),
                score=final_score,
                search_tags=normalize_search_tags(c.get("search_tags"), discard_invalid=True),
                origin_score=c.get("_origin_score"),
                time_score=c.get("_time_score"),
            )
            mc.extra_metadata = c.get("extra_metadata") or {}
            results.append(mc)

        results.sort(key=lambda x: x.score, reverse=True)
        return results
