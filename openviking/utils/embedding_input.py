# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Helpers for bounding text sent to embedding providers."""

from __future__ import annotations

import math

EMBEDDING_TRUNCATION_SUFFIX = "\n...(truncated for embedding)"


def estimate_embedding_input_tokens(text: str) -> int:
    """Estimate tokens for the raw text embedding input guard."""
    if not text:
        return 0
    cjk_chars = sum(
        1
        for char in text
        if "\u4e00" <= char <= "\u9fff"
        or "\u3040" <= char <= "\u30ff"
        or "\uac00" <= char <= "\ud7af"
    )
    other_chars = len(text) - cjk_chars
    return max(1, cjk_chars + math.ceil(other_chars / 4))


def truncate_embedding_input(
    text: str,
    max_tokens: int,
    suffix: str = EMBEDDING_TRUNCATION_SUFFIX,
) -> str:
    """Trim raw text before embedding using the local estimate above."""
    if not text:
        return text
    if max_tokens <= 0:
        return suffix.lstrip()
    if estimate_embedding_input_tokens(text) <= max_tokens:
        return text

    low = 0
    high = len(text)
    while low < high:
        mid = (low + high + 1) // 2
        if estimate_embedding_input_tokens(text[:mid]) <= max_tokens:
            low = mid
        else:
            high = mid - 1
    return text[:low].rstrip() + suffix


def resolve_embedding_max_input_tokens(
    config: dict[str, object] | None,
    default: int | None = None,
) -> int | None:
    """Read and normalize max_input_tokens from an embedder config dict."""
    raw_value = (config or {}).get("max_input_tokens", default)
    if raw_value is None:
        return default

    try:
        max_tokens = int(raw_value)
    except (TypeError, ValueError):
        return default

    if max_tokens <= 0:
        return default
    return max_tokens


def split_embedding_chunks(
    text: str,
    max_chunk_tokens: int = 1500,
    overlap_tokens: int = 100,
) -> list[str]:
    """Split text into semantic chunks bounded by max_chunk_tokens with optional overlap."""
    if not text:
        return []
    if max_chunk_tokens <= 0:
        return [text]
    if estimate_embedding_input_tokens(text) <= max_chunk_tokens:
        return [text]

    import re

    parts = [p for p in re.split(r"(\n\n+|(?<=\n)(?=#{1,6}\s)|(?<=[。！？\n]))", text) if p]
    if not parts:
        parts = [text]

    chunks: list[str] = []
    current_chunk = ""

    for part in parts:
        candidate = current_chunk + part
        cand_tokens = estimate_embedding_input_tokens(candidate)
        if cand_tokens <= max_chunk_tokens:
            current_chunk = candidate
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
                if overlap_tokens > 0:
                    low = 0
                    high = len(current_chunk)
                    while low < high:
                        mid = (low + high) // 2
                        tail = current_chunk[mid:]
                        if estimate_embedding_input_tokens(tail) <= overlap_tokens:
                            high = mid
                        else:
                            low = mid + 1
                    overlap_text = current_chunk[low:]
                    current_chunk = overlap_text + part
                else:
                    current_chunk = part
            else:
                current_chunk = part

            while estimate_embedding_input_tokens(current_chunk) > max_chunk_tokens:
                low = 0
                high = len(current_chunk)
                while low < high:
                    mid = (low + high + 1) // 2
                    if estimate_embedding_input_tokens(current_chunk[:mid]) <= max_chunk_tokens:
                        low = mid
                    else:
                        high = mid - 1
                slice_len = max(1, low)
                chunks.append(current_chunk[:slice_len].strip())
                if overlap_tokens > 0 and slice_len > 0:
                    tail_start = max(0, slice_len - overlap_tokens)
                    current_chunk = current_chunk[tail_start:]
                else:
                    current_chunk = current_chunk[slice_len:]

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks
