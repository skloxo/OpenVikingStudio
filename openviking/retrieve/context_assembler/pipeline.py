# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Single-request context assembly: retrieve, budget, render, optionally digest.

One HTTP round trip replaces the per-type search-then-read loops each harness
plugin used to run, so every plugin inherits budgeting, tier degradation and
cross-turn dedup from one implementation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from openviking.retrieve.context_assembler.budget import (
    oversized_abstract_needs_body,
    per_entry_cap,
    plan_entries,
)
from openviking.retrieve.context_assembler.evidence_hops import run_evidence_hops
from openviking.retrieve.context_assembler.expansion import expand_queries
from openviking.retrieve.context_assembler.gather import _rank_key, gather_candidates
from openviking.retrieve.context_assembler.ledger import RecallLedger
from openviking.retrieve.context_assembler.models import AssembleResult
from openviking.retrieve.context_assembler.params import (
    AssembleParams,
    normalize_detail,
    normalize_evidence_hops,
    normalize_exclude_uris,
    normalize_penalties,
    normalize_quotas,
)
from openviking.retrieve.context_assembler.render import render_context
from openviking.retrieve.context_assembler.rerank_pool import apply_dpp_diversity
from openviking.retrieve.context_assembler.rewrite import rewrite_context, server_rewrite_enabled
from openviking.retrieve.context_assembler.tiers import needs_content, prefetch_contents
from openviking.retrieve.rerank_scoring import Reranker
from openviking.server.identity import RequestContext
from openviking.storage.bm25_fts_index import BM25FTSIndex
from openviking_cli.utils.config import get_openviking_config
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)


def _context_reranker(service: Any, params: AssembleParams) -> Optional[Reranker]:
    """The server's opt-in context reranker, when it applies to this request."""
    if not params.query.strip() or params.image_url:
        return None
    factory = getattr(service.search, "context_reranker", None)
    if not callable(factory):
        return None
    try:
        return factory()
    except Exception as exc:
        logger.warning("Context rerank unavailable, keeping vector scores: %s", exc)
        return None


async def _load_session(service: Any, ctx: RequestContext, session_id: Optional[str]) -> Any:
    if not session_id:
        return None
    try:
        session = await service.sessions.get(session_id, ctx, auto_create=True)
        if not await session.is_materialized():
            return None
        return session
    except Exception as exc:
        logger.info("Session %s unavailable for context assembly: %s", session_id, exc)
        return None


async def assemble_context(
    *,
    service: Any,
    ctx: RequestContext,
    params: AssembleParams,
) -> AssembleResult:
    """Run the full assembly pipeline for one request."""
    quotas = normalize_quotas(params.quotas, params.purpose)
    penalties = normalize_penalties(params.other_peer_penalty)

    intent_checker = getattr(service.search, "is_intent_enabled", None)
    intent_enabled = intent_checker() if callable(intent_checker) else True
    expansion_mode = params.query_expansion if intent_enabled else "off"
    needs_session = bool(params.session_id) and (expansion_mode == "auto" or params.dedup_turns > 0)
    session = await _load_session(service, ctx, params.session_id) if needs_session else None

    queries, expansion_status = await expand_queries(
        query=params.query,
        session=session,
        mode=expansion_mode,
    )

    ledger = await RecallLedger.load(
        service=service,
        ctx=ctx,
        session=session,
        dedup_turns=params.dedup_turns,
    )
    cooled = ledger.cooled_uris() if ledger else set()
    excluded = normalize_exclude_uris(params.exclude_uris) | cooled
    reranker = _context_reranker(service, params)

    candidates, gather_stats = await gather_candidates(
        service=service,
        ctx=ctx,
        queries=queries,
        quotas=quotas,
        limit=params.limit,
        score_threshold=params.score_threshold,
        filter=params.filter,
        image_url=params.image_url,
        peer_scope=params.peer_scope,
        penalties=penalties,
        excluded=excluded,
        reranker=reranker,
        rerank_query="\n".join(queries),
    )

    hops = normalize_evidence_hops(params.evidence_hops)
    hop_stats: Dict[str, Any] = {
        "hops_requested": hops,
        "hops_executed": 0,
        "bridge_queries": [],
        "added": 0,
        "status": "off",
    }
    if hops > 0 and candidates and params.query.strip():
        df_lookup = None
        total_docs = 0
        try:
            fts = BM25FTSIndex.get_instance()
            total_docs = fts.get_stats().total_docs
            df_lookup = fts.get_terms_df
        except Exception as exc:
            logger.debug("BM25 DF context unavailable for evidence hops: %s", exc)

        async def _gather_hop(hop_query: str, hop_excluded: set[str]):
            hop_candidates, _ = await gather_candidates(
                service=service,
                ctx=ctx,
                queries=[hop_query],
                quotas=quotas,
                limit=params.limit,
                score_threshold=params.score_threshold,
                filter=params.filter,
                image_url=None,
                peer_scope=params.peer_scope,
                penalties=penalties,
                excluded=hop_excluded,
                reranker=reranker,
                rerank_query=hop_query,
            )
            return hop_candidates

        hop_timeout = float(
            getattr(get_openviking_config().retrieval, "recall_intent_timeout_s", 5.0) or 5.0
        )
        min_ev_score = float(getattr(reranker, "threshold", 0.0) or 0.0)
        candidates, hop_stats = await run_evidence_hops(
            query=params.query,
            initial_candidates=candidates,
            evidence_hops=hops,
            gather_hop_fn=_gather_hop,
            rank_key=_rank_key,
            excluded=excluded,
            min_evidence_score=min_ev_score,
            df_lookup=df_lookup,
            total_docs=total_docs,
            timeout_s=hop_timeout,
        )

    if params.dpp_diversity and len(candidates) > 2:
        candidates = apply_dpp_diversity(candidates, top_n=min(10, len(candidates)))

    # Read only the candidates whose planned tier actually needs a body: with
    # the default tiers that is the events bucket, not every hit.
    pins = normalize_detail(params.detail)
    cap = per_entry_cap(params.max_tokens, len(candidates))
    readable = [
        c
        for c in candidates
        if needs_content(c, pins.for_category(c.category)) or oversized_abstract_needs_body(c, cap)
    ]
    contents: Dict[str, str] = {}
    if readable:
        contents = await prefetch_contents(service=service, candidates=readable)

    plan = plan_entries(
        candidates,
        contents,
        max_tokens=params.max_tokens,
        detail=pins,
    )

    rendered = render_context(plan.entries) if params.render else ""

    digest = ""
    rewrite_status = "off"
    rewrite_usage: Optional[Dict[str, int]] = None
    if plan.entries and server_rewrite_enabled(params.rewrite):
        digest, rewrite_status, rewrite_usage = await rewrite_context(
            query=params.query,
            rendered=rendered or render_context(plan.entries),
            max_bullets=params.rewrite_max_bullets,
            valid_uris=[entry.uri for entry in plan.entries],
        )
        if rewrite_status == "no_relevant":
            rendered = ""

    # A digest that reports no relevant memory blanks the block, so this turn
    # served nothing: recording those URIs would cool them for `dedup_turns`
    # turns without the reader ever having seen them, and hold them back from
    # the later turn they are relevant to.
    served = plan.entries if rewrite_status != "no_relevant" else []
    if ledger and served:
        try:
            await ledger.record(served)
        except Exception as exc:
            logger.debug("Recall ledger record failed (%s); dedup stays best-effort", exc)

    stats: Dict[str, Any] = {
        **gather_stats,
        **plan.stats,
        "purpose": params.purpose,
        "query_expansion": expansion_status,
        "planned_queries": queries,
        "evidence_hops": hop_stats,
        "dpp_diversity": bool(params.dpp_diversity),
        "score_threshold": params.score_threshold,
        "other_peer_penalties": penalties,
        "rewrite": rewrite_status,
        "rewrite_usage": rewrite_usage,
        "dedup": {
            "turns": params.dedup_turns,
            "status": ledger.status if ledger else "off",
            "cooled": len(cooled),
            "turn": ledger.turn if ledger else None,
        },
    }
    return AssembleResult(
        entries=plan.entries,
        rendered=rendered,
        digest=digest,
        stats=stats,
    )
