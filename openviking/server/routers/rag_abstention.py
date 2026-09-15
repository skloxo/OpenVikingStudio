# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
REST Router for RAG Grounding Verification, MinHash Deduplication & Abstention Gate.
(Card-RAG-Abstention-ZeroHallucination-Pipeline / v1.5.18)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.retrieve.abstention_gate import AbstentionGate, AbstentionDecision, AbstentionTelemetrySnapshot
from openviking.retrieve.minhash_dedup import MinHashDedup, ChunkDedupResult

router = APIRouter(tags=["rag_abstention"])


class VerifyRequest(BaseModel):
    query: str
    evidence_chunks: List[str] = Field(default_factory=list)
    custom_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    enable_dedup: bool = True


class DedupItem(BaseModel):
    id: str
    content: str


class DedupRequest(BaseModel):
    chunks: List[DedupItem]
    threshold: float = Field(default=0.80, ge=0.5, le=1.0)


@router.get("/api/v1/rag/metrics")
async def get_rag_metrics(_ctx: RequestContext = Depends(get_request_context)):
    """Get cumulative telemetry for RAG abstention gate and grounding verification."""
    gate = AbstentionGate.get_instance()
    metrics = gate.get_telemetry()
    return JSONResponse(status_code=200, content=metrics.model_dump())


@router.post("/api/v1/rag/verify")
async def verify_and_gate_rag(
    req: VerifyRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """
    Verify query-evidence grounding and decide whether to answer or abstain.
    Optionally deduplicates near-identical evidence chunks with MinHash LSH.
    """
    gate = AbstentionGate.get_instance()
    chunks = req.evidence_chunks
    dedup_results: List[ChunkDedupResult] = []

    if req.enable_dedup and chunks:
        deduper = MinHashDedup(threshold=0.80)
        items = [(f"chk_{i}", c) for i, c in enumerate(chunks)]
        dedup_results = deduper.deduplicate(items)
        # Keep non-duplicates for grounding verification
        active_chunks = [r.content for r in dedup_results if not r.is_duplicate]
    else:
        active_chunks = chunks

    decision = gate.verify_and_decide(
        query=req.query,
        evidence_chunks=active_chunks,
        custom_threshold=req.custom_threshold,
    )

    return JSONResponse(
        status_code=200,
        content={
            "decision": decision.model_dump(),
            "dedup_results": [r.model_dump() for r in dedup_results],
            "effective_evidence_count": len(active_chunks),
            "original_evidence_count": len(chunks),
        },
    )


@router.post("/api/v1/rag/dedup")
async def deduplicate_chunks(
    req: DedupRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Run MinHash LSH deduplication across candidate chunks."""
    deduper = MinHashDedup(threshold=req.threshold)
    items = [(item.id, item.content) for item in req.chunks]
    results = deduper.deduplicate(items)
    return JSONResponse(
        status_code=200,
        content={"results": [r.model_dump() for r in results]},
    )
