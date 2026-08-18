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


DEFAULT_EMBEDDING_CHUNK_TOKENS = 1500
DEFAULT_EMBEDDING_OVERLAP_TOKENS = 150


def split_embedding_chunks(
    text: str,
    max_chunk_tokens: int = DEFAULT_EMBEDDING_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_EMBEDDING_OVERLAP_TOKENS,
) -> list[str]:
    """Split long text into semantically coherent chunks that fit within embedding token limits.

    Splitting hierarchy:
    1. If the entire text fits within max_chunk_tokens, return [text].
    2. Split by Markdown headers / double newlines (paragraphs).
    3. Greedily group paragraphs into chunks up to max_chunk_tokens.
    4. If an individual paragraph exceeds max_chunk_tokens, recursively split it by lines / sentences.
    5. Add overlap_tokens from the end of the previous chunk to maintain semantic continuity across boundaries.
    """
    if not text:
        return []

    total_tokens = estimate_embedding_input_tokens(text)
    if total_tokens <= max_chunk_tokens:
        return [text]

    if max_chunk_tokens <= 0:
        return [text]

    overlap_tokens = max(0, min(overlap_tokens, max_chunk_tokens // 2))

    def _break_into_atoms_by_sentence(block: str) -> list[str]:
        import re

        # Split on Chinese or Western sentence endings
        sentence_endings = re.compile(r"([。！？!?\n]+)")
        pieces = sentence_endings.split(block)
        if len(pieces) > 1:
            atoms = []
            curr = ""
            for piece in pieces:
                curr += piece
                if sentence_endings.match(piece) or estimate_embedding_input_tokens(curr) >= max_chunk_tokens // 2:
                    if estimate_embedding_input_tokens(curr) > max_chunk_tokens:
                        atoms.extend(_break_by_char_slices(curr))
                    else:
                        atoms.append(curr)
                    curr = ""
            if curr:
                if estimate_embedding_input_tokens(curr) > max_chunk_tokens:
                    atoms.extend(_break_by_char_slices(curr))
                else:
                    atoms.append(curr)
            return [a for a in atoms if a]
        return _break_by_char_slices(block)

    def _break_into_atoms_by_line(block: str) -> list[str]:
        if "\n" in block:
            parts = block.split("\n")
            atoms = []
            for i, p in enumerate(parts):
                atom = p + ("\n" if i < len(parts) - 1 else "")
                if estimate_embedding_input_tokens(atom) > max_chunk_tokens:
                    atoms.extend(_break_into_atoms_by_sentence(atom))
                else:
                    atoms.append(atom)
            return [a for a in atoms if a]
        return _break_into_atoms_by_sentence(block)

    def _break_into_atoms(block: str) -> list[str]:
        if "\n\n" in block:
            parts = block.split("\n\n")
            atoms = []
            for i, p in enumerate(parts):
                atom = p + ("\n\n" if i < len(parts) - 1 else "")
                if estimate_embedding_input_tokens(atom) > max_chunk_tokens:
                    atoms.extend(_break_into_atoms_by_line(atom))
                else:
                    atoms.append(atom)
            return [a for a in atoms if a]
        return _break_into_atoms_by_line(block)

    def _break_by_char_slices(block: str) -> list[str]:
        slices = []
        start = 0
        while start < len(block):
            low = start + 1
            high = len(block)
            best = low
            while low <= high:
                mid = (low + high) // 2
                if estimate_embedding_input_tokens(block[start:mid]) <= max_chunk_tokens:
                    best = mid
                    low = mid + 1
                else:
                    high = mid - 1
            slices.append(block[start:best])
            start = best
        return [s for s in slices if s]

    atoms = _break_into_atoms(text)

    chunks: list[str] = []
    current_atoms: list[str] = []
    current_tokens = 0

    for atom in atoms:
        atom_tokens = estimate_embedding_input_tokens(atom)
        if current_tokens + atom_tokens > max_chunk_tokens and current_atoms:
            chunk_str = "".join(current_atoms).strip()
            if chunk_str:
                chunks.append(chunk_str)

            # Form overlap from the tail of current_atoms
            overlap_atoms: list[str] = []
            overlap_accum = 0
            for prev_atom in reversed(current_atoms):
                prev_tok = estimate_embedding_input_tokens(prev_atom)
                if overlap_accum + prev_tok <= overlap_tokens:
                    overlap_atoms.insert(0, prev_atom)
                    overlap_accum += prev_tok
                else:
                    break

            current_atoms = overlap_atoms + [atom]
            current_tokens = overlap_accum + atom_tokens
        else:
            current_atoms.append(atom)
            current_tokens += atom_tokens

    if current_atoms:
        chunk_str = "".join(current_atoms).strip()
        if chunk_str:
            chunks.append(chunk_str)

    return chunks or [text]


def resolve_embedding_max_input_tokens(
    config: dict[str, object] | None,
    default: int | None = None,
) -> int | None:
    """Read and normalize max_input_tokens from an embedder config dict."""
    raw_value = (config or {}).get("max_input_tokens", default)
    if raw_value is None:
        return default

    try:
        max_tokens = int(str(raw_value))
    except (TypeError, ValueError):
        return default

    if max_tokens <= 0:
        return default
    return max_tokens

