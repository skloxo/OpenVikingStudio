# -*- coding: utf-8 -*-
"""Strongly typed DTO schemas for Context Router Pipeline.

Fulfills BLUEPRINT.md Topic 5 Section 4.2 (Context Router Pipeline).
Provides segment classification, per-engine routing metadata,
and aggregated compression telemetry models.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SegmentType(str, Enum):
    """Categorized segment type identified from heterogeneous prompt."""
    STATIC_HEADER = "static_header"
    NATURAL_LANGUAGE = "natural_language"
    CODE_BLOCK = "code_block"
    SKILL_CONTRACT = "skill_contract"
    DIALOGUE_HISTORY = "dialogue_history"


class RouteEngine(str, Enum):
    """Target specialized compression engine."""
    NATIVE_CACHING = "native_caching"
    LLMLINGUA2 = "llmlingua2"
    TOKENSHIFT = "tokenshift"
    SKILLZIP = "skillzip"
    ACTIVE_NOTES = "active_notes"
    PASSTHROUGH = "passthrough"


class ContextSegment(BaseModel):
    """A single sequential slice of the prompt routed to a specific engine."""
    index: int = Field(..., description="0-based sequential index of the segment")
    segment_type: SegmentType = Field(..., description="Detected semantic category")
    engine: RouteEngine = Field(..., description="Engine chosen for compression")
    language: Optional[str] = Field(default=None, description="Programming language if code block")
    raw_content: str = Field(..., description="Original raw text slice")
    compressed_content: str = Field(..., description="Compressed output text slice")
    original_tokens: int = Field(default=0, description="Estimated token count before compression")
    compressed_tokens: int = Field(default=0, description="Estimated token count after compression")
    tokens_saved: int = Field(default=0, description="Tokens eliminated")
    reduction_ratio: float = Field(default=0.0, description="Ratio of tokens saved (0.0 - 1.0)")
    latency_ms: float = Field(default=0.0, description="Processing latency in milliseconds")
    status: str = Field(default="ok", description="'ok', 'fallback', or 'bypassed'")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Engine specific details")


class ContextRouteRequest(BaseModel):
    """Input payload for context router pipeline."""
    content: str = Field(..., description="Full heterogeneous input prompt text")
    default_code_mode: str = Field(default="skeleton", description="'skeleton', 'outline', or 'compact'")
    target_dehydration_rate: float = Field(default=0.50, ge=0.1, le=0.9, description="Target retention for prose")
    enable_skillzip: bool = Field(default=True, description="Whether to apply SkillZip contract compression")
    preserve_static_header: bool = Field(default=True, description="Keep system instructions intact")
    max_target_tokens: Optional[int] = Field(default=None, description="Optional target token budget")


class ContextRouteResult(BaseModel):
    """End-to-end outcome of context routing and assembly."""
    assembled_content: str = Field(..., description="Reassembled compressed prompt in exact order")
    segments: List[ContextSegment] = Field(default_factory=list, description="All processed slices")
    total_original_tokens: int = Field(default=0)
    total_compressed_tokens: int = Field(default=0)
    total_tokens_saved: int = Field(default=0)
    overall_reduction_ratio: float = Field(default=0.0)
    total_latency_ms: float = Field(default=0.0)
    ast_syntax_valid: bool = Field(default=True, description="Whether all code blocks passed AST validation")
    engine_distribution: Dict[str, int] = Field(default_factory=dict, description="Counts of segments by engine")


class ContextRouterStats(BaseModel):
    """Thread-safe historical metrics for context router."""
    total_requests: int = Field(default=0)
    total_segments_routed: int = Field(default=0)
    total_original_tokens: int = Field(default=0)
    total_compressed_tokens: int = Field(default=0)
    total_tokens_saved: int = Field(default=0)
    average_reduction_ratio: float = Field(default=0.0)
    engine_call_counts: Dict[str, int] = Field(default_factory=dict)
