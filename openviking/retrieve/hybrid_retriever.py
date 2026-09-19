# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Hybrid Dense-Sparse Retriever & Telemetry Collector.

Key Principles:
1. Two-Way Parallel Stream: Dense Vector (semantic generalization) + SQLite FTS5 BM25 (exact symbols).
2. Reciprocal Rank Fusion: Non-parametric RRF k=60 combining candidates before reranking.
3. Provenance & Observability: Tracks Dense vs Sparse contribution and exact symbol boost.
4. Fail-Fast & Fallback: Graceful degradation if either stream has 0 candidates.
"""

import asyncio
import time
import threading
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from openviking.storage.bm25_fts_index import BM25FTSIndex, BM25Match
from openviking.retrieve.rrf_fusion import FusedCandidate, rrf_fuse


class HybridTelemetrySnapshot(BaseModel):
    """Aggregate metrics of hybrid retrieval performance."""
    total_hybrid_queries: int
    dense_candidates_total: int
    sparse_candidates_total: int
    hybrid_fused_total: int
    hybrid_overlap_rate: float
    exact_symbol_boost_count: int
    avg_latency_ms: float
    is_bm25_ready: bool
    rank_distribution: Dict[str, int] = Field(default_factory=dict)


class HybridRetrievalTelemetry:
    """Thread-safe telemetry collector for hybrid search metrics."""

    _instance: Optional["HybridRetrievalTelemetry"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._lock = threading.Lock()
        self.total_queries: int = 0
        self.dense_candidates: int = 0
        self.sparse_candidates: int = 0
        self.hybrid_fused: int = 0
        self.overlapping_candidates: int = 0
        self.exact_symbol_boosts: int = 0
        self.total_latency_ms: float = 0.0
        self.dense_only_count: int = 0
        self.sparse_only_count: int = 0
        self.hybrid_both_count: int = 0

    @classmethod
    def get_instance(cls) -> "HybridRetrievalTelemetry":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def record(
        self,
        dense_count: int,
        sparse_count: int,
        fused_count: int,
        overlap_count: int,
        symbol_boost: bool,
        latency_ms: float,
        dense_only: int = 0,
        sparse_only: int = 0,
    ):
        with self._lock:
            self.total_queries += 1
            self.dense_candidates += dense_count
            self.sparse_candidates += sparse_count
            self.hybrid_fused += fused_count
            self.overlapping_candidates += overlap_count
            self.hybrid_both_count += overlap_count
            self.dense_only_count += dense_only
            self.sparse_only_count += sparse_only
            if symbol_boost:
                self.exact_symbol_boosts += 1
            self.total_latency_ms += latency_ms

    def get_snapshot(self, is_bm25_ready: bool = True) -> HybridTelemetrySnapshot:
        with self._lock:
            q = max(1, self.total_queries)
            total_fused = max(1, self.hybrid_fused)
            overlap_rate = (self.overlapping_candidates / total_fused) if self.total_queries > 0 else 0.0
            distribution = {
                "hybrid_overlap": self.hybrid_both_count,
                "dense_only": self.dense_only_count,
                "sparse_only": self.sparse_only_count,
            }
            return HybridTelemetrySnapshot(
                total_hybrid_queries=self.total_queries,
                dense_candidates_total=self.dense_candidates,
                sparse_candidates_total=self.sparse_candidates,
                hybrid_fused_total=self.hybrid_fused,
                hybrid_overlap_rate=round(overlap_rate, 4),
                exact_symbol_boost_count=self.exact_symbol_boosts,
                avg_latency_ms=round(self.total_latency_ms / q, 2),
                is_bm25_ready=is_bm25_ready,
                rank_distribution=distribution,
            )


class HybridRetriever:
    """Orchestrator combining Vector Store and SQLite FTS5 BM25 with RRF."""

    def __init__(self, bm25_index: Optional[BM25FTSIndex] = None):
        self.bm25_index = bm25_index or BM25FTSIndex.get_instance()
        self.telemetry = HybridRetrievalTelemetry.get_instance()

    async def retrieve_hybrid(
        self,
        query: str,
        dense_candidates: List[Dict[str, Any]],
        limit: int = 10,
        context_type: Optional[str] = None,
        target_directories: Optional[List[str]] = None,
        k: int = 60,
    ) -> List[FusedCandidate]:
        """
        Blend pre-fetched dense vector candidates with fast FTS5 BM25 matches via RRF.
        """
        t0 = time.monotonic()

        # Run BM25 search in thread pool to prevent blocking asyncio loop
        sparse_matches: List[BM25Match] = await asyncio.to_thread(
            self.bm25_index.search,
            query=query,
            limit=limit * 2,
            context_type=context_type,
            target_directories=target_directories,
        )

        sparse_candidates = [
            {
                "uri": m.uri,
                "title": m.title,
                "level": m.level,
                "context_type": m.context_type,
                "bm25_score": m.bm25_score,
                "snippet": m.snippet,
            }
            for m in sparse_matches
        ]

        # Reciprocal Rank Fusion
        fused = rrf_fuse(
            dense_results=dense_candidates,
            sparse_results=sparse_candidates,
            k=k,
            top_k=limit * 2,
        )

        # Apply asymmetric lifecycle decay & demotion (superseded 0.20x, disputed 0.50x)
        from openviking.retrieve.asymmetric_decay import AsymmetricDecayEngine
        from openviking.service.memory_lifecycle_fsm import get_lifecycle_records_batch
        decay_engine = AsymmetricDecayEngine()

        # Batch query physical FSM store to eliminate data schism
        uris_to_check = [item.uri for item in fused]
        fsm_records = get_lifecycle_records_batch(uris_to_check)

        for item in fused:
            # Prefer physical FSM persistent status over stale vector metadata
            fsm_rec = fsm_records.get(item.uri)
            if fsm_rec:
                status = fsm_rec.status.value
            else:
                meta = item.extra_metadata
                nested_meta = meta.get("extra_metadata") if isinstance(meta.get("extra_metadata"), dict) else {}
                status = str(meta.get("status") or nested_meta.get("status") or "active")

            meta = item.extra_metadata
            nested_meta = meta.get("extra_metadata") if isinstance(meta.get("extra_metadata"), dict) else {}
            updated_ts = meta.get("updated_ts") or nested_meta.get("updated_ts")
            assessment = decay_engine.evaluate_candidate(
                uri=item.uri,
                raw_score=item.dense_score or item.normalized_score,
                updated_ts=updated_ts,
                status=status,
            )
            item.extra_metadata["status"] = status
            item.extra_metadata["decay_factor"] = assessment.decay_factor
            item.extra_metadata["adjusted_score"] = assessment.adjusted_score
            item.extra_metadata["is_immune"] = assessment.is_immune
            item.normalized_score = assessment.adjusted_score
            item.rrf_score = round(item.rrf_score * assessment.decay_factor, 6)

        # Re-sort after decay demotion
        fused.sort(key=lambda x: x.rrf_score, reverse=True)
        fused = fused[:limit]
        for idx, item in enumerate(fused, start=1):
            item.fused_rank = idx

        latency_ms = (time.monotonic() - t0) * 1000.0

        # Telemetry accounting
        overlap_count = sum(1 for f in fused if f.origin == "hybrid")
        dense_only = sum(1 for f in fused if f.origin == "dense_only")
        sparse_only = sum(1 for f in fused if f.origin == "sparse_only")
        symbol_boost = any(f.origin == "sparse_only" and f.fused_rank <= 3 for f in fused)

        self.telemetry.record(
            dense_count=len(dense_candidates),
            sparse_count=len(sparse_candidates),
            fused_count=len(fused),
            overlap_count=overlap_count,
            symbol_boost=symbol_boost,
            latency_ms=latency_ms,
            dense_only=dense_only,
            sparse_only=sparse_only,
        )

        return fused
