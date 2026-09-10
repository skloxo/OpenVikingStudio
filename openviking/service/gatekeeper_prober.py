# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Vector nearest neighbor prober for Entropy Gatekeeper.

Performs internal memory service probe or fallback HTTP find probe
to locate top candidate matches and determine similarity score.
"""

import logging
from typing import Any, Optional, Tuple

import httpx

logger = logging.getLogger("openviking.entropy_gatekeeper.prober")


from openviking.core.defensive import defensive


@defensive(
    domain="gatekeeper",
    name="probe_nearest_vector",
    fallback=(0.0, None, None),
    log_level="warning",
)
async def probe_nearest_vector(
    content: str,
    uri: str,
    ctx: Any = None,
) -> Tuple[float, Optional[str], Optional[str]]:
    """Probe the vector database for the nearest active neighbor (Top-1)."""
    from openviking.service.memory_dual_track import get_embedding_text_for_content

    probe_text = get_embedding_text_for_content(content)
    probe_query = probe_text[:250].replace("\n", " ").strip()
    if not probe_query:
        return 0.0, None, None

    # 1. Priority: Internal memory service probe (Zero HTTP overhead, immunity to self-deadlock, <2ms)
    try:
        from openviking.server.dependencies import get_service
        service = get_service()
        if service and hasattr(service, "search") and hasattr(service.search, "find"):
            from openviking.server.identity import RequestContext, Role, UserIdentifier
            internal_ctx = ctx if isinstance(ctx, RequestContext) else RequestContext(user=UserIdentifier.the_default_user(), role=Role.ROOT)

            search_res = await service.search.find(
                query=probe_query,
                ctx=internal_ctx,
                limit=2,
                mode="fast",
            )
            if hasattr(search_res, "to_dict"):
                search_res = search_res.to_dict()
            if isinstance(search_res, dict):
                all_items = (
                    search_res.get("resources", [])
                    + search_res.get("memories", [])
                    + search_res.get("skills", [])
                )
                candidates = [c for c in all_items if c.get("uri") != uri]
                if candidates:
                    best = max(candidates, key=lambda x: float(x.get("score", 0.0)))
                    score = float(best.get("score", 0.0))
                    matched_uri = best.get("uri")
                    snippet = best.get("abstract") or best.get("content") or ""

                    # Read candidate original content to verify exact proposition equivalence
                    if matched_uri and score >= 0.75:
                        try:
                            if hasattr(service, "fs") and hasattr(service.fs, "read"):
                                orig_stat = await service.fs.read(matched_uri)
                                orig_text = orig_stat.get("content", "") if isinstance(orig_stat, dict) else str(orig_stat)
                                norm_in = " ".join(content.strip().split())
                                norm_orig = " ".join(orig_text.strip().split())
                                if norm_in and (norm_in == norm_orig or norm_in in norm_orig or norm_orig in norm_in):
                                    overlap = min(len(norm_in), len(norm_orig)) / max(len(norm_in), len(norm_orig))
                                    if overlap >= 0.90:
                                        score = 0.9900
                                        snippet = orig_text[:200]
                        except Exception as e:
                            logger.debug("[EntropyGatekeeperProber] Internal candidate text read failed: %s", e)

                    return score, matched_uri, snippet
                return 0.0, None, None
    except Exception as e:
        logger.debug("[EntropyGatekeeperProber] Internal memory probe failed, falling back to HTTP: %s", e)

    # 2. Fallback: HTTP find probe against local port 1933
    from openviking.service.entropy_watchdog import _resolve_api_key

    api_key = _resolve_api_key()
    async with httpx.AsyncClient(trust_env=False, timeout=5.0) as client:
        resp = await client.post(
            "http://127.0.0.1:1933/api/v1/search/find",
            json={"query": probe_query, "limit": 2, "mode": "fast"},
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-OpenViking-Account": "default",
                "X-OpenViking-User": "default",
                "X-OpenViking-Internal-Probe": "1",
            },
        )
        if resp.status_code == 200:
            data = resp.json().get("result", {})
            all_items = data.get("resources", []) + data.get("memories", []) + data.get("skills", [])
            candidates = [c for c in all_items if c.get("uri") != uri]
            if candidates:
                best = max(candidates, key=lambda x: float(x.get("score", 0.0)))
                score = float(best.get("score", 0.0))
                matched_uri = best.get("uri")
                snippet = best.get("abstract") or best.get("content") or ""

                if matched_uri and score >= 0.75:
                    try:
                        from openviking.server.dependencies import get_service
                        service = get_service()
                        if hasattr(service, "fs") and hasattr(service.fs, "read"):
                            orig_stat = await service.fs.read(matched_uri)
                            orig_text = orig_stat.get("content", "") if isinstance(orig_stat, dict) else str(orig_stat)
                            norm_in = " ".join(content.strip().split())
                            norm_orig = " ".join(orig_text.strip().split())
                            if norm_in and (norm_in == norm_orig or norm_in in norm_orig or norm_orig in norm_in):
                                overlap = min(len(norm_in), len(norm_orig)) / max(len(norm_in), len(norm_orig))
                                if overlap >= 0.90:
                                    score = 0.9900
                                    snippet = orig_text[:200]
                    except Exception as e:
                        logger.debug("[EntropyGatekeeperProber] Candidate original text read failed: %s", e)

                return score, matched_uri, snippet

    return 0.0, None, None
