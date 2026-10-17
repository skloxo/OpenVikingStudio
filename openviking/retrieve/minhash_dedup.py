# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
MinHash LSH Near-Duplicate Deduplication & NFKC Normalization.
(Card-RAG-Abstention-ZeroHallucination-Pipeline / v1.5.18)
"""

import hashlib
import unicodedata
from typing import List, Set, Tuple
from pydantic import BaseModel, Field


class ChunkDedupResult(BaseModel):
    """Result of deduplication with cluster ID and duplicate flag."""
    chunk_id: str
    content: str
    is_duplicate: bool
    duplicate_of: str | None = None
    similarity_score: float = 0.0


class MinHashDedup:
    """
    MinHash Locality-Sensitive Hashing (LSH) for text chunk deduplication.
    Uses 64 hash functions with 16 bands x 4 rows for Jaccard threshold ~0.80.
    """

    def __init__(self, num_perm: int = 64, num_bands: int = 16, threshold: float = 0.80):
        self.num_perm = num_perm
        self.num_bands = num_bands
        self.rows_per_band = num_perm // num_bands
        self.threshold = threshold
        # Deterministic seed coefficients (a * x + b) % prime
        self._prime = 4294967311  # 2^32 + 15
        self._a = [(i * 10007 + 3) % self._prime for i in range(1, num_perm + 1)]
        self._b = [(i * 20011 + 7) % self._prime for i in range(1, num_perm + 1)]

    @staticmethod
    def normalize_text(text: str) -> str:
        """NFKC normalization, lowercasing, and whitespace collapse."""
        normalized = unicodedata.normalize("NFKC", text).lower()
        return " ".join(normalized.split())

    def get_shingles(self, text: str, k: int = 3) -> Set[str]:
        """Extract character k-shingles from normalized text."""
        norm = self.normalize_text(text)
        if len(norm) <= k:
            return {norm} if norm else set()
        return {norm[i : i + k] for i in range(len(norm) - k + 1)}

    def compute_signature(self, shingles: Set[str]) -> List[int]:
        """Compute MinHash signature array of length num_perm."""
        if not shingles:
            return [0] * self.num_perm

        # Hash each shingle to a 32-bit int
        shingle_hashes = [
            int(hashlib.md5(s.encode("utf-8")).hexdigest()[:8], 16)
            for s in shingles
        ]

        sig = []
        for i in range(self.num_perm):
            a_i = self._a[i]
            b_i = self._b[i]
            # Find min permuted hash
            min_val = min((a_i * h + b_i) % self._prime for h in shingle_hashes)
            sig.append(min_val)
        return sig

    @staticmethod
    def estimate_jaccard(sig_a: List[int], sig_b: List[int]) -> float:
        """Estimate Jaccard similarity as fraction of matching signature slots."""
        if not sig_a or not sig_b or len(sig_a) != len(sig_b):
            return 0.0
        matches = sum(1 for a, b in zip(sig_a, sig_b) if a == b)
        return matches / len(sig_a)

    def deduplicate(
        self,
        chunks: List[Tuple[str, str]],  # List of (chunk_id, content)
    ) -> List[ChunkDedupResult]:
        """
        Deduplicate chunks using LSH buckets and MinHash similarity.
        Returns list of ChunkDedupResult preserving order.
        """
        # band_idx -> band_hash -> chunk_id
        buckets: List[dict[str, str]] = [{} for _ in range(self.num_bands)]
        signatures: dict[str, List[int]] = {}
        results: List[ChunkDedupResult] = []

        for chunk_id, content in chunks:
            shingles = self.get_shingles(content)
            sig = self.compute_signature(shingles)
            signatures[chunk_id] = sig

            matched_id: str | None = None
            max_sim = 0.0

            # Check LSH bands for candidate collisions
            for band_idx in range(self.num_bands):
                start = band_idx * self.rows_per_band
                end = start + self.rows_per_band
                band_key = hashlib.md5(
                    "".join(str(x) for x in sig[start:end]).encode("utf-8")
                ).hexdigest()

                if band_key in buckets[band_idx]:
                    candidate_id = buckets[band_idx][band_key]
                    cand_sig = signatures.get(candidate_id)
                    if cand_sig:
                        sim = self.estimate_jaccard(sig, cand_sig)
                        if sim >= self.threshold and sim > max_sim:
                            max_sim = sim
                            matched_id = candidate_id
                else:
                    buckets[band_idx][band_key] = chunk_id

            if matched_id:
                results.append(
                    ChunkDedupResult(
                        chunk_id=chunk_id,
                        content=content,
                        is_duplicate=True,
                        duplicate_of=matched_id,
                        similarity_score=round(max_sim, 3),
                    )
                )
            else:
                results.append(
                    ChunkDedupResult(
                        chunk_id=chunk_id,
                        content=content,
                        is_duplicate=False,
                        duplicate_of=None,
                        similarity_score=1.0,
                    )
                )

        return results
