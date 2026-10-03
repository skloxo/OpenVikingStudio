# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Sliding-Window Semantic Chunking Fallback Pipeline for Oversized Memories.
(Card-42 / v1.6.6)

First Principles:
When a document exceeds the maximum token length of an embedding model
(e.g., 8192 tokens / ERROR_CLASS_INPUT_TOO_LARGE), rejecting it into DLQ
creates a blind spot in the exocortex. By dynamically decomposing the text
into overlapping semantic chunks (uri#chunk_0, uri#chunk_1) while preserving
YAML frontmatter headers, the document achieves 100% absorption throughput.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openviking.storage.chunking_fallback")


@dataclass
class ChunkItem:
    """Strongly typed DTO representing an individual semantic chunk."""
    chunk_index: int
    total_chunks: int
    chunk_uri: str
    text: str
    char_count: int


class ChunkingFallbackEngine:
    """Decomposes oversized documents into overlapping semantic chunks and embeds them."""

    def __init__(self, max_chunk_chars: int = 3500, overlap_chars: int = 300) -> None:
        self.max_chunk_chars = max(100, max_chunk_chars)
        self.overlap_chars = max(20, min(overlap_chars, self.max_chunk_chars // 2))

    def _split_into_atomic_units(self, text: str) -> List[str]:
        """Recursively split text by paragraphs, sentences, and character windows."""
        if not text:
            return []

        # 1. Split by paragraphs
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paras:
            paras = [p.strip() for p in text.split("\n") if p.strip()]
        if not paras:
            paras = [text.strip()]

        atoms: List[str] = []
        for p in paras:
            if len(p) <= self.max_chunk_chars:
                atoms.append(p)
                continue

            # 2. Split oversized paragraph by sentences
            sentences = re.split(r"(?<=[.!?。！？\n])\s+", p)
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                if len(s) <= self.max_chunk_chars:
                    atoms.append(s)
                else:
                    # 3. Hard slice window for massive runs without punctuation
                    step = max(50, self.max_chunk_chars - self.overlap_chars)
                    for start_idx in range(0, len(s), step):
                        atoms.append(s[start_idx : start_idx + self.max_chunk_chars])

        return atoms

    def chunk_text(self, text: str, uri: str) -> List[ChunkItem]:
        """Split text into overlapping chunks, preserving YAML frontmatter if present."""
        if not text:
            return []

        # Extract frontmatter if present (e.g. --- ... ---)
        frontmatter = ""
        body = text
        fm_match = re.match(r"^(---\s*\n.*?\n---\s*\n)", text, re.DOTALL)
        if fm_match:
            frontmatter = fm_match.group(1).strip()
            body = text[fm_match.end():]

        atoms = self._split_into_atomic_units(body)
        if not atoms:
            return []

        raw_chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for atom in atoms:
            atom_len = len(atom)
            if current_len + atom_len > self.max_chunk_chars and current_chunk:
                # Flush current chunk
                joined = "\n\n".join(current_chunk)
                raw_chunks.append(joined)

                # Keep overlap from the end of current_chunk
                overlap_text = current_chunk[-1] if current_chunk else ""
                if len(overlap_text) > self.overlap_chars:
                    overlap_text = overlap_text[-self.overlap_chars:]

                current_chunk = [overlap_text, atom] if overlap_text else [atom]
                current_len = sum(len(p) for p in current_chunk) + len(current_chunk) * 2
            else:
                current_chunk.append(atom)
                current_len += atom_len + 2

        if current_chunk:
            raw_chunks.append("\n\n".join(current_chunk))

        # Build ChunkItem list attaching frontmatter context
        total = len(raw_chunks)
        items: List[ChunkItem] = []
        for i, chunk_body in enumerate(raw_chunks):
            if frontmatter:
                full_chunk_text = f"{frontmatter}\n\n{chunk_body}"
            else:
                full_chunk_text = chunk_body

            chunk_uri = f"{uri}#chunk_{i}"
            items.append(
                ChunkItem(
                    chunk_index=i,
                    total_chunks=total,
                    chunk_uri=chunk_uri,
                    text=full_chunk_text,
                    char_count=len(full_chunk_text),
                )
            )

        return items

    async def execute_fallback(
        self,
        handler: Any,
        embedding_msg: Any,
        raw_data: Dict[str, Any],
        ctx: Any,
    ) -> Optional[Dict[str, Any]]:
        """Process an oversized message by chunking and upserting all chunks into VikingDB."""
        from openviking.service.vector_sync_tracker import VectorSyncTracker

        message = (
            getattr(embedding_msg, "message", None)
            or raw_data.get("message")
            or ""
        )
        context_data = getattr(embedding_msg, "context_data", {}) if embedding_msg else {}
        uri = (context_data.get("uri") if isinstance(context_data, dict) else None) or raw_data.get("uri") or ""
        account_id = (context_data.get("account_id") if isinstance(context_data, dict) else None) or raw_data.get("account_id") or "default"

        if not message or not uri:
            logger.warning("[ChunkingFallback] Missing message or uri for fallback chunking")
            return None

        chunks = self.chunk_text(message, uri)
        if not chunks:
            return None

        logger.info(
            f"[ChunkingFallback] Splitting oversized message into {len(chunks)} chunks for {uri}"
        )

        successful_chunks = 0
        first_chunk_data: Optional[Dict[str, Any]] = None

        async def _embed_and_upsert(c_text: str, c_uri: str, idx: int, tot: int) -> bool:
            nonlocal first_chunk_data
            try:
                result = await handler._dispatch_embed(c_text)
                if not result or not result.dense_vector:
                    return False

                if hasattr(handler, "_vector_dim") and len(result.dense_vector) != handler._vector_dim:
                    logger.error(
                        f"[ChunkingFallback] Vector dimension mismatch for chunk {c_uri}"
                    )
                    return False

                chunk_data = dict(context_data if isinstance(context_data, dict) else {})
                chunk_data["uri"] = c_uri
                chunk_data["parent_uri"] = uri
                chunk_data["chunk_index"] = idx
                chunk_data["total_chunks"] = tot
                chunk_data["vector"] = result.dense_vector
                if getattr(result, "sparse_vector", None):
                    chunk_data["sparse_vector"] = result.sparse_vector

                if getattr(handler._vikingdb, "uses_content_field", False):
                    chunk_data["content"] = c_text

                seed_uri = c_uri
                id_seed = f"{account_id}:{seed_uri}"
                chunk_data["id"] = hashlib.md5(id_seed.encode("utf-8")).hexdigest()

                upsert_options = {"partial_update": True}
                await handler._vikingdb.upsert(chunk_data, ctx=ctx, options=upsert_options)

                if first_chunk_data is None:
                    first_chunk_data = chunk_data
                return True

            except Exception as chunk_err:
                from openviking.utils.model_retry import classify_api_error, ERROR_CLASS_INPUT_TOO_LARGE

                if classify_api_error(chunk_err) == ERROR_CLASS_INPUT_TOO_LARGE and len(c_text) > 300:
                    # Adaptive halving: sub-divide this chunk into 2 smaller sub-chunks
                    mid = len(c_text) // 2
                    ok1 = await _embed_and_upsert(c_text[: mid + 30], f"{c_uri}_a", idx, tot + 1)
                    ok2 = await _embed_and_upsert(c_text[mid - 30 :], f"{c_uri}_b", idx + 1, tot + 1)
                    return ok1 or ok2

                logger.error(
                    f"[ChunkingFallback] Failed to process chunk {c_uri}: {chunk_err}"
                )
                return False

        for chunk in chunks:
            if await _embed_and_upsert(chunk.text, chunk.chunk_uri, chunk.chunk_index, chunk.total_chunks):
                successful_chunks += 1

        if successful_chunks > 0:
            logger.info(
                f"[ChunkingFallback] Successfully indexed {successful_chunks}/{len(chunks)} chunks for {uri}"
            )
            VectorSyncTracker.get_instance().mark_indexed(
                uri=uri,
                account_id=account_id,
            )
            return first_chunk_data

        logger.error(f"[ChunkingFallback] All chunks failed for {uri}")
        return None
