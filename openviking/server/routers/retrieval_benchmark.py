# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
REST Endpoints for Gold Benchmark Evaluation & Knowledge Hygiene Auditing.
(Card-Hygiene-AsymmetricDecayAndBench / v1.5.31)
"""

import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from openviking.retrieve.asymmetric_decay import AsymmetricDecayEngine
from openviking.retrieve.knowledge_hygiene import KnowledgeHygieneEngine, HygieneReport
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.service.knowledge_hygiene_service import KnowledgeHygieneService
from openviking.storage.bm25_fts_index import BM25FTSIndex
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval-benchmark"])

# In-memory engines
_DECAY_ENGINE = AsymmetricDecayEngine()
_HYGIENE_ENGINE = KnowledgeHygieneEngine(_DECAY_ENGINE)

# Path to gold benchmarks dataset
_GOLD_FILE = Path(__file__).resolve().parent.parent.parent / "retrieve" / "gold_benchmarks.json"


def _load_gold_benchmarks() -> List[Dict[str, Any]]:
    if not _GOLD_FILE.exists():
        return []
    try:
        data = json.loads(_GOLD_FILE.read_text(encoding="utf-8"))
        return data.get("benchmarks", [])
    except Exception as e:
        logger.error(f"Failed to load gold benchmarks: {e}")
        return []


class BenchmarkRunRequest(BaseModel):
    category: Optional[str] = Field(None, description="Optional category filter: symbols, errors, architecture, domain")
    limit_queries: int = Field(15, ge=1, le=50, description="Max queries to execute")
    target_uri: str = Field("viking://", description="Target root URI")


class BenchmarkItemResult(BaseModel):
    id: str
    query: str
    category: str
    status: str  # "hit" | "miss" | "error"
    rank: Optional[int] = None
    reciprocal_rank: float = 0.0
    matched_uri: Optional[str] = None
    score: float = 0.0
    latency_ms: float = 0.0
    origin: str = "unknown"  # "hybrid" | "sparse_only" | "dense_only"


class BenchmarkRunResponse(BaseModel):
    total_evaluated: int
    hit_count: int
    hit_rate: float
    mrr: float
    avg_latency_ms: float
    category_summary: Dict[str, Dict[str, Any]]
    results: List[BenchmarkItemResult]


@router.get("/benchmark/suites")
async def get_benchmark_suites(
    _ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Retrieve available gold benchmark test suites and queries."""
    benchmarks = _load_gold_benchmarks()
    categories: Dict[str, int] = {}
    for b in benchmarks:
        c = b.get("category", "unknown")
        categories[c] = categories.get(c, 0) + 1

    return {
        "status": "ok",
        "result": {
            "total_queries": len(benchmarks),
            "categories": categories,
            "benchmarks": benchmarks,
        },
    }


@router.post("/benchmark/run", response_model=Dict[str, Any])
async def run_gold_benchmark(
    req: BenchmarkRunRequest,
    _ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Execute batch gold benchmark evaluation against local BM25/Dense retrieval."""
    benchmarks = _load_gold_benchmarks()
    if req.category:
        benchmarks = [b for b in benchmarks if b.get("category") == req.category]

    benchmarks = benchmarks[: req.limit_queries]
    if not benchmarks:
        return {
            "status": "ok",
            "result": {
                "total_evaluated": 0,
                "hit_count": 0,
                "hit_rate": 0.0,
                "mrr": 0.0,
                "avg_latency_ms": 0.0,
                "category_summary": {},
                "results": [],
            },
        }

    bm25 = BM25FTSIndex.get_instance()
    results: List[BenchmarkItemResult] = []
    total_rr = 0.0
    hit_count = 0
    total_latency = 0.0

    cat_stats: Dict[str, Dict[str, Any]] = {}

    for b in benchmarks:
        q = b["query"]
        cat = b.get("category", "general")
        expected_kw = b.get("expected_keywords", [])
        expected_pattern = b.get("expected_uri_pattern", "").lower()
        min_rank = b.get("min_acceptable_rank", 3)

        t0 = time.monotonic()
        # Perform fast FTS5 search
        matches = bm25.search(query=q, limit=5)
        latency = round((time.monotonic() - t0) * 1000.0, 2)
        total_latency += latency

        matched_rank = None
        matched_uri = None
        top_score = 0.0

        for idx, m in enumerate(matches):
            uri_lower = m.uri.lower()
            content_lower = (m.snippet or "").lower()
            pattern_hit = any(p in uri_lower for p in expected_pattern.split("|")) if expected_pattern else False
            kw_hit = any(kw.lower() in content_lower for kw in expected_kw)

            if pattern_hit or kw_hit:
                matched_rank = idx + 1
                matched_uri = m.uri
                top_score = m.bm25_score
                break

        is_hit = matched_rank is not None and matched_rank <= min_rank
        rr = (1.0 / matched_rank) if matched_rank else 0.0
        total_rr += rr
        if is_hit:
            hit_count += 1

        if cat not in cat_stats:
            cat_stats[cat] = {"total": 0, "hits": 0, "sum_rr": 0.0}
        cat_stats[cat]["total"] += 1
        if is_hit:
            cat_stats[cat]["hits"] += 1
        cat_stats[cat]["sum_rr"] += rr

        results.append(
            BenchmarkItemResult(
                id=b["id"],
                query=q,
                category=cat,
                status="hit" if is_hit else "miss",
                rank=matched_rank,
                reciprocal_rank=round(rr, 3),
                matched_uri=matched_uri,
                score=round(top_score, 4),
                latency_ms=latency,
                origin="sparse_only" if matches else "none",
            )
        )

    n = len(benchmarks)
    hit_rate = round((hit_count / n) * 100.0, 1) if n > 0 else 0.0
    mrr = round(total_rr / n, 4) if n > 0 else 0.0
    avg_lat = round(total_latency / n, 1) if n > 0 else 0.0

    summary = {}
    for c, st in cat_stats.items():
        cnt = st["total"]
        summary[c] = {
            "total": cnt,
            "hits": st["hits"],
            "hit_rate": round((st["hits"] / cnt) * 100.0, 1) if cnt > 0 else 0.0,
            "mrr": round(st["sum_rr"] / cnt, 3) if cnt > 0 else 0.0,
        }

    return {
        "status": "ok",
        "result": {
            "total_evaluated": n,
            "hit_count": hit_count,
            "hit_rate": hit_rate,
            "mrr": mrr,
            "avg_latency_ms": avg_lat,
            "category_summary": summary,
            "results": [r.model_dump() for r in results],
        },
    }


@router.post("/hygiene/dispatch", response_model=Dict[str, Any])
async def dispatch_hygiene_audit(
    trigger: str = Query("manual", description="Audit trigger source: manual or scheduled"),
    _ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Dispatch an asynchronous full-scale knowledge hygiene audit task registered in TaskCenter."""
    account_id = "default" if _ctx.role == Role.ROOT else _ctx.account_id
    user_id = "root" if _ctx.role == Role.ROOT else (_ctx.user.user_id if _ctx.user else "root")

    service = KnowledgeHygieneService.get_instance()
    task = await service.dispatch_audit(account_id=account_id, user_id=user_id, trigger=trigger)
    return {
        "status": "ok",
        "task_id": task.task_id,
        "message": "Asynchronous full-scale knowledge hygiene audit task dispatched successfully.",
    }


@router.get("/hygiene/report", response_model=Dict[str, Any])
async def get_hygiene_report(
    _ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Return full-scale knowledge hygiene health index and audit snapshot."""
    service = KnowledgeHygieneService.get_instance()
    report = service.get_latest_report()
    return {
        "status": "ok",
        "result": report.model_dump(),
    }
