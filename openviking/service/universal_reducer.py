# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Universal Content Reducer (Card-190 SSOT).

Unifies the three distinct reduction engines into a single first-principles primitive:
1. CODE: PointFive AST-Aware Code Compression (wraps TokenShiftEngine).
2. SKILL: Six-Tuple 0-Rollout Contractual Compression (wraps SkillZipEngine).
3. TEXT: Structural Dehydration & Semantic Distillation (wraps WikiDehydrationEngine).

Guarantees:
- Automatic content-type detection with fallback to TEXT.
- 100% Fail-Open safety: parser or model failure returns unmodified text with zero loss.
- Standardized I/O schema and cross-module telemetry.
"""

from __future__ import annotations

from enum import Enum
import json
import logging
import re
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ReductionMode(str, Enum):
    """Reduction strategy selection."""
    AUTO = "auto"
    CODE = "code"
    SKILL = "skill"
    TEXT = "text"


ContentType = ReductionMode


class UniversalReduceRequest(BaseModel):
    """Standardized input payload for Universal Content Reducer."""
    content: str = Field(..., description="Raw text, code, or skill markdown")
    mode: ReductionMode = Field(default=ReductionMode.AUTO, description="Reduction mode")
    target_ratio: float = Field(default=0.5, ge=0.1, le=0.9, description="Target compression ratio")
    language: Optional[str] = Field(default=None, description="Explicit language hint for code (python, ts, json)")
    preserve_structure: bool = Field(default=True, description="Protect YAML frontmatter & markdown codeblocks")


class UniversalReduceResult(BaseModel):
    """Standardized output result for Universal Content Reducer."""
    content: str = Field(..., description="Reduced content")
    original_tokens: int = Field(default=0, description="Estimated original token count")
    reduced_tokens: int = Field(default=0, description="Estimated reduced token count")
    tokens_saved: int = Field(default=0, description="Tokens saved by reduction")
    compression_ratio: float = Field(default=0.0, description="Tokens reduced / original tokens")
    engine_used: str = Field(default="passthrough", description="Underlying engine invoked")
    detected_mode: str = Field(default="text", description="Resolved reduction mode")
    latency_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    fidelity_score: float = Field(default=1.0, description="Integrity / contract fidelity score [0.0, 1.0]")
    fail_open: bool = Field(default=False, description="True if compression failed and raw text was preserved")


class UniversalContentReducer:
    """Singleton universal dehydration and compression dispatcher."""

    _instance: Optional[UniversalContentReducer] = None

    @classmethod
    def get_instance(cls) -> "UniversalContentReducer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def detect_mode(content: str) -> ReductionMode:
        """Heuristically detect the nature of content (Skill vs Code vs Text)."""
        stripped = content.strip()
        if not stripped:
            return ReductionMode.TEXT

        # 1. Skill check: YAML frontmatter with skill identifiers or 6-tuple headings
        if stripped.startswith("---") and ("name:" in stripped or "description:" in stripped):
            if any(k in stripped for k in ["# SOP", "# Workflow", "## 核心", "## 六段式", "Interface", "Contract"]):
                return ReductionMode.SKILL

        # 2. JSON Code check
        if (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]")):
            try:
                json.loads(stripped)
                return ReductionMode.CODE
            except Exception:
                pass

        # 3. Code check: Python / TypeScript signatures
        code_markers = [
            r"^(import\s+|from\s+\w+\s+import|def\s+\w+\s*\(|class\s+\w+[\(:]|async\s+def\s+)",
            r"^(export\s+(const|function|class|interface|type)|const\s+\w+\s*=\s*\(|function\s+\w+\s*\()",
        ]
        first_few_lines = "\n".join(stripped.splitlines()[:15])
        for pat in code_markers:
            if re.search(pat, first_few_lines, re.MULTILINE):
                return ReductionMode.CODE

        # 4. Default: Markdown / Natural language text
        return ReductionMode.TEXT

    def reduce(self, req: UniversalReduceRequest) -> UniversalReduceResult:
        """Execute unified content reduction with Fail-Open guarantees."""
        start_time = time.perf_counter()
        raw_content = req.content

        if not raw_content or not raw_content.strip():
            return UniversalReduceResult(
                content=raw_content,
                original_tokens=0,
                reduced_tokens=0,
                tokens_saved=0,
                compression_ratio=0.0,
                engine_used="noop",
                detected_mode=req.mode.value,
                latency_ms=0.0,
                fidelity_score=1.0,
            )

        resolved_mode = req.mode if req.mode != ReductionMode.AUTO else self.detect_mode(raw_content)

        try:
            if resolved_mode == ReductionMode.CODE:
                result = self._reduce_code(req)
            elif resolved_mode == ReductionMode.SKILL:
                result = self._reduce_skill(req)
            else:
                result = self._reduce_text(req)

            result.latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            result.detected_mode = resolved_mode.value
            return result

        except Exception as exc:
            logger.warning(f"UniversalContentReducer encounter error, triggering Fail-Open: {exc}")
            latency = round((time.perf_counter() - start_time) * 1000, 2)
            orig_tok = max(1, int(len(raw_content) / 4))
            return UniversalReduceResult(
                content=raw_content,
                original_tokens=orig_tok,
                reduced_tokens=orig_tok,
                tokens_saved=0,
                compression_ratio=0.0,
                engine_used="fail_open_fallback",
                detected_mode=resolved_mode.value,
                latency_ms=latency,
                fidelity_score=1.0,
                fail_open=True,
            )

    def _reduce_code(self, req: UniversalReduceRequest) -> UniversalReduceResult:
        """Invoke TokenShift AST engine for code compression."""
        from openviking.service.tokenshift_engine import TokenShiftEngine
        from openviking.service.tokenshift_types import (
            TokenShiftLanguage,
            TokenShiftMode,
            TokenShiftRequest,
        )
        from openviking.service.tokenshift_transformers import detect_language

        raw_lang = req.language or detect_language(req.content)
        lang_enum = TokenShiftLanguage(raw_lang) if raw_lang in TokenShiftLanguage._value2member_map_ else TokenShiftLanguage.PYTHON

        ts_req = TokenShiftRequest(
            code=req.content,
            language=lang_enum,
            mode=TokenShiftMode.COMPACT,
        )
        ts_res = TokenShiftEngine.compress(ts_req)

        orig_tok = ts_res.original_tokens
        comp_tok = ts_res.compressed_tokens
        saved = max(0, orig_tok - comp_tok)
        ratio = saved / orig_tok if orig_tok > 0 else 0.0

        return UniversalReduceResult(
            content=ts_res.compressed_code,
            original_tokens=orig_tok,
            reduced_tokens=comp_tok,
            tokens_saved=saved,
            compression_ratio=round(ratio, 4),
            engine_used=f"tokenshift/{ts_res.syntax_validation.parser}",
            fidelity_score=1.0 if ts_res.syntax_validation.valid else 0.85,
        )

    def _reduce_skill(self, req: UniversalReduceRequest) -> UniversalReduceResult:
        """Invoke SkillZip 6-tuple contractual compression engine."""
        from openviking.service.skill_zip_engine import SkillZipEngine

        zip_engine = SkillZipEngine.get_instance()
        zip_res = zip_engine.compress(req.content)

        orig_tok = max(1, int(zip_res.original_length / 4))
        comp_tok = max(1, int(zip_res.compressed_length / 4))
        saved = max(0, orig_tok - comp_tok)

        return UniversalReduceResult(
            content=zip_res.compressed_content,
            original_tokens=orig_tok,
            reduced_tokens=comp_tok,
            tokens_saved=saved,
            compression_ratio=round(zip_res.compression_ratio, 4),
            engine_used="skill_zip/6tuple_contractual",
            fidelity_score=zip_res.contract_fidelity,
        )

    def _reduce_text(self, req: UniversalReduceRequest) -> UniversalReduceResult:
        """Invoke WikiDehydrationEngine for Markdown/text dehydration."""
        from openviking.service.wiki_dehydration_engine import (
            WikiDehydrationEngine,
            DehydrationRequest,
        )

        dehy_engine = WikiDehydrationEngine.get_instance()
        dehy_req = DehydrationRequest(
            content=req.content,
            target_rate=req.target_ratio,
            preserve_structure=req.preserve_structure,
            protect_yaml_frontmatter=req.preserve_structure,
            protect_code_blocks=req.preserve_structure,
        )
        dehy_res = dehy_engine.dehydrate(dehy_req)

        orig_tok = dehy_res.original_tokens
        comp_tok = dehy_res.compressed_tokens
        saved = dehy_res.tokens_saved

        return UniversalReduceResult(
            content=dehy_res.dehydrated_content,
            original_tokens=orig_tok,
            reduced_tokens=comp_tok,
            tokens_saved=saved,
            compression_ratio=round(dehy_res.compression_ratio, 4),
            engine_used=f"wiki_dehydration/{dehy_res.engine_used}",
            fidelity_score=1.0 if dehy_res.structural_integrity_verified else 0.9,
        )
