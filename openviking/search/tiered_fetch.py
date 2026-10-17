# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Tiered Lazy Fetch (分级懒加载契约).
depth=0 (Meta) | depth=1 (Fingerprint, Recommended) | depth=2 (Full Block).
Enforces token hygiene and eliminates context flooding.
(Card-Retrieval-LocalFirst-zgSemanticSearch / v1.5.17)
"""

from enum import IntEnum
import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from openviking.search.ast_chunker import CodeSymbolChunk


class TierLevel(IntEnum):
    """Tiered Lazy Fetch Depth Hierarchy."""
    META = 0         # ~15 tokens: file:line, symbol name, type, anchor
    FINGERPRINT = 1  # ~50 tokens: signature + docstring + 1-line context (Default ~80% savings)
    FULL_BLOCK = 2   # ~250-800 tokens: complete function/class slice
    SURROUNDING = 3  # ~1000+ tokens: full block with enclosing scope


class TieredChunkResult(BaseModel):
    """Result item formatted according to requested depth."""
    uri: str
    file_path: str
    symbol_name: str
    symbol_type: str
    start_line: int
    end_line: int
    line_count: int
    fingerprint: str
    depth: int
    rendered_content: str
    estimated_tokens: int
    full_tokens_baseline: int
    token_savings_ratio: float
    score: float = 0.0


class TieredFetchSummary(BaseModel):
    """Aggregate token efficiency metrics for a search response."""
    depth: int
    total_results: int
    actual_tokens_total: int
    baseline_tokens_total: int
    total_tokens_saved: int
    savings_percentage: float
    results: List[TieredChunkResult]


class TieredLazyFetch:
    """Formats code symbol chunks according to Tiered Lazy Fetch contract."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Heuristic token estimator (~4 chars per token for code/en, ~1.5 for cjk)."""
        if not text:
            return 0
        return max(1, math.ceil(len(text) / 3.6))

    @classmethod
    def format_chunk(
        cls,
        chunk: CodeSymbolChunk,
        depth: int = 1,
        score: float = 0.0,
    ) -> TieredChunkResult:
        """Format a single chunk at specified depth."""
        full_code = "\n".join(chunk.lines)
        full_tokens = cls.estimate_tokens(full_code)

        if depth == TierLevel.META:
            # depth=0: compact pointer
            rendered = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line} [{chunk.symbol_type}] {chunk.symbol_name}"
        elif depth == TierLevel.FINGERPRINT:
            # depth=1: signature + docstring + 1st body line + fingerprint
            lines_out = [
                f"# @anchor {chunk.fingerprint} | {chunk.file_path}:{chunk.start_line}",
                chunk.signature,
            ]
            if chunk.docstring:
                short_doc = chunk.docstring.splitlines()[0] if chunk.docstring else ""
                lines_out.append(f'    """{short_doc}"""')
            # 1-line body context if available
            if len(chunk.lines) > 1:
                first_body = chunk.lines[1].strip()
                if first_body and not first_body.startswith('"""'):
                    lines_out.append(f"    {first_body} ... ({chunk.line_count - 1} lines omitted)")
            rendered = "\n".join(lines_out)
        else:
            # depth >= 2: full slice
            header = f"# {chunk.file_path}:{chunk.start_line}-{chunk.end_line} [{chunk.symbol_type} {chunk.symbol_name}]"
            rendered = f"{header}\n{full_code}"

        actual_tokens = cls.estimate_tokens(rendered)
        baseline = max(actual_tokens, full_tokens)
        savings = round(1.0 - (actual_tokens / max(1, baseline)), 4) if baseline > 0 else 0.0

        return TieredChunkResult(
            uri=chunk.uri,
            file_path=chunk.file_path,
            symbol_name=chunk.symbol_name,
            symbol_type=chunk.symbol_type,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            line_count=chunk.line_count,
            fingerprint=chunk.fingerprint,
            depth=depth,
            rendered_content=rendered,
            estimated_tokens=actual_tokens,
            full_tokens_baseline=baseline,
            token_savings_ratio=max(0.0, savings),
            score=score,
        )

    @classmethod
    def format_batch(
        cls,
        chunks: List[CodeSymbolChunk],
        depth: int = 1,
        scores: Optional[List[float]] = None,
    ) -> TieredFetchSummary:
        """Format a batch of symbol results and compute total token savings."""
        scores_list = scores or [0.0] * len(chunks)
        items: List[TieredChunkResult] = []
        actual_total = 0
        baseline_total = 0

        for idx, chunk in enumerate(chunks):
            s = scores_list[idx] if idx < len(scores_list) else 0.0
            formatted = cls.format_chunk(chunk, depth=depth, score=s)
            items.append(formatted)
            actual_total += formatted.estimated_tokens
            baseline_total += formatted.full_tokens_baseline

        saved = max(0, baseline_total - actual_total)
        savings_pct = round((saved / max(1, baseline_total)) * 100.0, 1) if baseline_total > 0 else 0.0

        return TieredFetchSummary(
            depth=depth,
            total_results=len(items),
            actual_tokens_total=actual_total,
            baseline_tokens_total=baseline_total,
            total_tokens_saved=saved,
            savings_percentage=savings_pct,
            results=items,
        )
