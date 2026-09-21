# -*- coding: utf-8 -*-
"""TokenShift AST-Aware Code Compression DTOs & Types.

Fulfills BLUEPRINT.md Topic 5 Wheel #3 (PointFive AST-Aware Code Compression).
Provides strict typed contracts for code outline, skeleton, and compact modes.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TokenShiftMode(str, Enum):
    OUTLINE = "outline"      # L0: Signatures, type annotations, and core docstrings only (~70% savings)
    SKELETON = "skeleton"    # L1: Signatures + control flow skeletons (if/try/for), body elided (~50% savings)
    COMPACT = "compact"      # L2: Lossless formatting, strip redundant noise/comments (~25% savings)


class TokenShiftLanguage(str, Enum):
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    SQL = "sql"
    SHELL = "shell"
    JSON = "json"
    AUTO = "auto"


class SyntaxValidationResult(BaseModel):
    valid: bool = True
    parser: str = "python_ast"
    error: Optional[str] = None


class TokenShiftRequest(BaseModel):
    code: str = Field(..., description="Raw source code content to compress")
    language: TokenShiftLanguage = Field(default=TokenShiftLanguage.AUTO, description="Target programming language")
    mode: TokenShiftMode = Field(default=TokenShiftMode.SKELETON, description="Compression mode (outline/skeleton/compact)")
    preserve_docstrings: bool = Field(default=True, description="Whether to preserve docstrings in outline/skeleton mode")
    strip_comments: bool = Field(default=True, description="Whether to remove non-essential comments")


class TokenShiftResult(BaseModel):
    compressed_code: str
    original_code: str
    language: str
    mode: str
    original_lines: int
    compressed_lines: int
    original_tokens_est: int
    compressed_tokens_est: int
    reduction_ratio: float = Field(..., description="Fraction of tokens saved, e.g. 0.52 for 52%")
    protected_nodes_count: int
    syntax_validation: SyntaxValidationResult
    elapsed_ms: float


class TokenShiftProtectResult(BaseModel):
    language: str
    total_symbols: int
    protected_symbols: List[str]
    frozen_signatures: List[str]
    ast_nodes_identified: int


class TokenShiftStats(BaseModel):
    total_calls: int = 0
    total_original_tokens: int = 0
    total_compressed_tokens: int = 0
    total_tokens_saved: int = 0
    average_reduction_ratio: float = 0.0
    syntax_pass_rate: float = 1.0
