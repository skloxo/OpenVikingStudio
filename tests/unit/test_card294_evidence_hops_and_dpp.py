"""Unit and multi-hop benchmark tests for Card #294 (evidence hops + DPP diversity)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List

import pytest
from pydantic import ValidationError

from openviking.retrieve.context_assembler.evidence_hops import (
    extract_bridge_terms,
    run_evidence_hops,
)
from openviking.retrieve.context_assembler.gather import Candidate, _rank_key
from openviking.retrieve.context_assembler.params import (
    AssembleParams,
    normalize_evidence_hops,
)
from openviking.retrieve.context_assembler.pipeline import assemble_context
from openviking.retrieve.context_assembler.rerank_pool import apply_dpp_diversity
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.search_models import SearchRequest
from openviking.storage.bm25_fts_index import BM25FTSIndex
from openviking_cli.session.user_id import UserIdentifier


def _make_candidate(
    uri: str,
    abstract: str,
    score: float,
    *,
    category: str = "resources",
) -> Candidate:
    ctx = RequestContext(user=UserIdentifier("default", "default"), role=Role.ADMIN)
    return Candidate(
        uri=uri,
        base_uri=uri,
        category=category,
        score=score,
        ranked_score=score,
        level=2,
        abstract=abstract,
        origin="self",
        is_directory=False,
        read_ctx=ctx,
    )


def test_extract_bridge_terms_respects_boundaries_and_idf() -> None:
    query = "甲公司并购乙公司后谁负责架构"
    evidence = [
        "甲公司并购乙公司之后，任命「陈墨」出任首席架构师，推进 ProjectHelios 落地。"
    ]
    terms = extract_bridge_terms(
        query,
        evidence,
        df_lookup=lambda candidates: {
            t: (1 if t in {"陈墨", "ProjectHelios"} else 80) for t in candidates
        },
        total_docs=100,
        max_terms=4,
    )

    assert "陈墨" in terms
    assert "ProjectHelios" in terms
    assert all("为陈" not in t and "的架" not in t for t in terms)


def test_dpp_rerank_diversifies_duplicate_top_hits() -> None:
    candidates = [
        _make_candidate("viking://user/a/1", "Kubernetes pod scheduling memory limit OOMKilled", 0.96),
        _make_candidate("viking://user/a/2", "Kubernetes pod scheduling memory limit OOMKilled retry", 0.95),
        _make_candidate("viking://user/a/3", "Kubernetes pod scheduling memory limit OOMKilled node", 0.94),
        _make_candidate("viking://user/a/4", "Kubernetes pod scheduling memory limit OOMKilled cgroup", 0.93),
        _make_candidate("viking://user/b/1", "Redis cluster slot migration timeout failover", 0.90),
        _make_candidate("viking://user/c/1", "PostgreSQL autovacuum dead tuple bloat index", 0.89),
        _make_candidate("viking://user/d/1", "Nginx upstream keepalive connection reset 502", 0.88),
    ]

    diversified = apply_dpp_diversity(candidates, top_n=4, alpha=0.3)
    top4_prefixes = [c.uri.rsplit("/", 1)[0] for c in diversified[:4]]

    assert len(set(top4_prefixes)) >= 3
    assert diversified[0].uri == "viking://user/a/1"


@pytest.mark.asyncio
async def test_evidence_hops_timeout_fails_closed_and_clamps_hops() -> None:
    assert normalize_evidence_hops(99) == 2
    assert normalize_evidence_hops(-3) == 0

    initial = [_make_candidate("viking://user/doc1", "Alpha triggers ProjectOrion.", 0.9)]

    async def _slow_gather(_query: str, _excluded: set[str]) -> List[Candidate]:
        await asyncio.sleep(0.5)
        return [_make_candidate("viking://user/doc2", "ProjectOrion uses Rust.", 0.8)]

    merged, stats = await run_evidence_hops(
        query="Alpha",
        initial_candidates=initial,
        evidence_hops=5,
        gather_hop_fn=_slow_gather,
        rank_key=_rank_key,
        excluded=set(),
        timeout_s=0.1,
    )

    assert stats["hops_requested"] == 2
    assert stats["status"] == "timeout"
    assert [c.uri for c in merged] == ["viking://user/doc1"]


@pytest.mark.asyncio
async def test_zero_overlap_multihop_pipeline_improves_ae10(tmp_path: Path) -> None:
    BM25FTSIndex.reset_instance()
    fts = BM25FTSIndex.get_instance(db_path=tmp_path / "bm25.db")
    docs = {
        "viking://user/default/resources/doc1": (
            "doc1",
            "甲公司并购乙公司之后，任命「陈墨」担任首席架构师。",
        ),
        "viking://user/default/resources/doc2": (
            "doc2",
            "陈墨目前全面负责「天枢调度引擎」的核心架构研发。",
        ),
        "viking://user/default/resources/doc3": (
            "doc3",
            "天枢调度引擎底层采用 Rust 无锁环形队列实现微秒级派单。",
        ),
        "viking://user/default/resources/noise1": (
            "noise1",
            "园区食堂本周三提供清真牛肉面与蔬菜沙拉套餐。",
        ),
    }
    fts.index_batch(
        [
            {"uri": uri, "title": title, "content": body, "context_type": "resource"}
            for uri, (title, body) in docs.items()
        ]
    )

    class _FakeSearch:
        def is_intent_enabled(self) -> bool:
            return False

        async def find(self, *, query: str, limit: int = 10, **_kwargs: Any) -> Any:
            hits = fts.search(query, limit=limit)
            items = [
                SimpleNamespace(
                    uri=h.uri,
                    score=max(0.1, 1.0 - idx * 0.05),
                    abstract=docs[h.uri][1],
                    level=2,
                )
                for idx, h in enumerate(hits)
                if h.uri in docs
            ]
            return SimpleNamespace(memories=[], resources=items, skills=[])

    service = SimpleNamespace(search=_FakeSearch(), sessions=None, viking_fs=None)
    ctx = RequestContext(user=UserIdentifier("default", "default"), role=Role.ADMIN)

    res_single = await assemble_context(
        service=service,
        ctx=ctx,
        params=AssembleParams(
            query="甲公司并购乙公司",
            query_expansion="off",
            evidence_hops=0,
            dpp_diversity=False,
        ),
    )
    single_uris = {e.uri for e in res_single.entries}
    assert res_single.stats["evidence_hops"]["status"] == "off"
    assert "viking://user/default/resources/doc1" in single_uris
    assert "viking://user/default/resources/doc3" not in single_uris

    res_multi = await assemble_context(
        service=service,
        ctx=ctx,
        params=AssembleParams(
            query="甲公司并购乙公司",
            query_expansion="off",
            evidence_hops=2,
            dpp_diversity=True,
        ),
    )
    multi_uris = {e.uri for e in res_multi.entries[:10]}
    expected_chain = {
        "viking://user/default/resources/doc1",
        "viking://user/default/resources/doc2",
        "viking://user/default/resources/doc3",
    }
    assert res_multi.stats["evidence_hops"]["status"] == "used"
    assert res_multi.stats["evidence_hops"]["hops_executed"] == 2
    assert res_multi.stats["dpp_diversity"] is True
    assert expected_chain.issubset(multi_uris)
    BM25FTSIndex.reset_instance()


def test_search_request_enforces_context_only_for_card294_fields() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(query="hello", mode="list", evidence_hops=1)

    with pytest.raises(ValidationError):
        SearchRequest(query="hello", mode="list", dpp_diversity=True)

    req = SearchRequest(query="hello", mode="context", evidence_hops=2, dpp_diversity=True)
    assert req.evidence_hops == 2
    assert req.dpp_diversity is True
