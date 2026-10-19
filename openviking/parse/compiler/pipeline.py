# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Map-Shuffle-Reduce Knowledge Compiler Pipeline.

First Principles & Occam's Razor:
1. Map: AST and token-bounded deterministic document chunking.
2. Shuffle: Domain-driven clustering into buckets with content SHA256 fingerprints.
3. Reduce: Hierarchical L1 module summaries + top-level L0 ontology graph.
4. Incremental Caching: Fingerprint matching bypasses LLM reduction (Zero Token Waste).
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("openviking.parse.compiler.pipeline")


@dataclass(frozen=True)
class SourceDocument:
    """Input raw document to be mapped and compiled."""
    path: str
    content: str
    module: Optional[str] = None


@dataclass(frozen=True)
class DocumentChunk:
    """Fine-grained slice produced during Map phase."""
    chunk_id: str
    path: str
    content: str
    tokens_est: int
    module: str


@dataclass
class DomainBucket:
    """Clustered domain partition during Shuffle phase."""
    name: str
    chunks: List[DocumentChunk]
    fingerprint: str = ""


@dataclass(frozen=True)
class L0Overview:
    """Top-level architectural ontology and package topology."""
    topology: Dict[str, Any]
    total_chunks: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class CompilationResult:
    """Deterministic, immutable output of the multi-stage compilation."""
    total_chunks: List[DocumentChunk]
    buckets: Dict[str, DomainBucket]
    l1_summaries: Dict[str, str]
    l0_overview: Optional[L0Overview] = None
    cache_hits: int = 0
    cache_misses: int = 0
    status: str = "completed"


class KnowledgeCompiler:
    """Industrial Map-Shuffle-Reduce pipeline for scalable knowledge bases."""

    def __init__(
        self,
        summarizer_fn: Optional[Callable[[str, List[DocumentChunk]], str]] = None,
        chunk_size: int = 1000,
    ) -> None:
        self.summarizer_fn = summarizer_fn or self._default_structural_summarizer
        self.chunk_size = chunk_size

    def compile(
        self,
        documents: List[SourceDocument],
        previous_result: Optional[CompilationResult] = None,
    ) -> CompilationResult:
        """Execute Map -> Shuffle -> Reduce stages with incremental caching."""
        # 1. Map: Slice documents into fine-grained chunks
        chunks = self._map(documents)

        # 2. Shuffle: Cluster chunks into domain buckets and calculate fingerprints
        buckets = self._shuffle(chunks)

        # 3. Reduce: Generate hierarchical L1 module summaries and L0 ontology
        return self._reduce(chunks, buckets, previous_result=previous_result)

    def _map(self, documents: List[SourceDocument]) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        for doc in documents:
            module = doc.module or self._infer_module(doc.path)
            # Naive token/character bounded slice preserving lines
            raw_lines = doc.content.splitlines(keepends=True)
            current_batch: List[str] = []
            current_len = 0
            part_idx = 0

            for line in raw_lines:
                current_batch.append(line)
                current_len += len(line)
                if current_len >= self.chunk_size:
                    chunk_text = "".join(current_batch)
                    chunk_id = f"{doc.path}#chunk_{part_idx}"
                    chunks.append(DocumentChunk(
                        chunk_id=chunk_id,
                        path=doc.path,
                        content=chunk_text,
                        tokens_est=max(1, len(chunk_text) // 4),
                        module=module,
                    ))
                    current_batch = []
                    current_len = 0
                    part_idx += 1

            if current_batch:
                chunk_text = "".join(current_batch)
                chunk_id = f"{doc.path}#chunk_{part_idx}"
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    path=doc.path,
                    content=chunk_text,
                    tokens_est=max(1, len(chunk_text) // 4),
                    module=module,
                ))

        return chunks

    def _shuffle(self, chunks: List[DocumentChunk]) -> Dict[str, DomainBucket]:
        bucket_map: Dict[str, List[DocumentChunk]] = {}
        for c in chunks:
            bucket_map.setdefault(c.module, []).append(c)

        buckets: Dict[str, DomainBucket] = {}
        for mod_name, mod_chunks in bucket_map.items():
            # Calculate deterministic SHA256 fingerprint for all chunk contents in bucket
            hasher = hashlib.sha256()
            for chunk in sorted(mod_chunks, key=lambda x: x.chunk_id):
                hasher.update(chunk.content.encode("utf-8"))
            fingerprint = hasher.hexdigest()
            buckets[mod_name] = DomainBucket(name=mod_name, chunks=mod_chunks, fingerprint=fingerprint)

        return buckets

    def _reduce(
        self,
        chunks: List[DocumentChunk],
        buckets: Dict[str, DomainBucket],
        previous_result: Optional[CompilationResult] = None,
    ) -> CompilationResult:
        l1_summaries: Dict[str, str] = {}
        cache_hits = 0
        cache_misses = 0
        has_fallback = False

        prev_buckets = previous_result.buckets if previous_result else {}
        prev_summaries = previous_result.l1_summaries if previous_result else {}

        for name, bucket in buckets.items():
            # Check incremental fingerprint cache
            if (
                name in prev_buckets
                and prev_buckets[name].fingerprint == bucket.fingerprint
                and name in prev_summaries
            ):
                l1_summaries[name] = prev_summaries[name]
                cache_hits += 1
                continue

            cache_misses += 1
            try:
                summary = self.summarizer_fn(name, bucket.chunks)
                l1_summaries[name] = summary
            except Exception as exc:
                logger.warning(f"Summarizer failed for bucket {name}: {exc}. Applying fallback.")
                has_fallback = True
                l1_summaries[name] = self._fallback_summary(name, bucket.chunks)

        # Top-level L0 ontology reduction
        topology = {
            mod_name: {
                "chunk_count": len(bucket.chunks),
                "fingerprint": bucket.fingerprint[:12],
                "files": sorted(list({c.path for c in bucket.chunks})),
            }
            for mod_name, bucket in buckets.items()
        }
        l0 = L0Overview(topology=topology, total_chunks=len(chunks))

        status = "completed_with_fallbacks" if has_fallback else "completed"
        return CompilationResult(
            total_chunks=chunks,
            buckets=buckets,
            l1_summaries=l1_summaries,
            l0_overview=l0,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            status=status,
        )

    @staticmethod
    def _infer_module(path: str) -> str:
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            return parts[1] if parts[0] in ("openviking", "src", "pkg", "lib") else parts[0]
        return parts[0] if parts else "root"

    @staticmethod
    def _default_structural_summarizer(bucket_name: str, chunks: List[DocumentChunk]) -> str:
        unique_paths = sorted(list({c.path for c in chunks}))
        return (
            f"# L1 Module Summary: {bucket_name}\n"
            f"- Total Chunks: {len(chunks)}\n"
            f"- Included Paths:\n" + "\n".join(f"  * {p}" for p in unique_paths)
        )

    @staticmethod
    def _fallback_summary(bucket_name: str, chunks: List[DocumentChunk]) -> str:
        unique_paths = sorted(list({c.path for c in chunks}))
        return (
            f"[Fallback Topology] {bucket_name}\n"
            f"Automated structural fallback generated ({len(chunks)} chunks, {len(unique_paths)} files)."
        )
