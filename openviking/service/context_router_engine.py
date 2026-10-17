# -*- coding: utf-8 -*-
"""Context Router Engine - Master Orchestrator for Multi-Engine Compression.

Fulfills BLUEPRINT.md Topic 5 Section 4.2.
Orchestrates:
1. TokenShift (AST-Aware Code Compression);
2. Microsoft LLMLingua-2 (Natural Language Dehydration);
3. Alibaba SkillZip (Skill Contract Six-Tuple Optimization);
4. Native Prompt Caching (Static Header Zero-Loss Bypass);
5. Graceful Fallback & AST Validation Retina Safeguards.
"""

from __future__ import annotations

import time
import threading
from typing import Dict, List

from openviking.service.context_router_segmenter import (
    RawSegment,
    estimate_tokens,
    segment_prompt,
)
from openviking.service.context_router_types import (
    ContextRouteRequest,
    ContextRouteResult,
    ContextRouterStats,
    ContextSegment,
    RouteEngine,
    SegmentType,
)
from openviking.service.tokenshift_engine import TokenShiftEngine
from openviking.service.tokenshift_types import (
    TokenShiftLanguage,
    TokenShiftMode,
    TokenShiftRequest,
)
from openviking.service.wiki_dehydration_engine import (
    DehydrationRequest,
    WikiDehydrationEngine,
)
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)


class ContextRouterEngine:
    """Singleton service for heterogeneous prompt routing and assembly."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._stats = ContextRouterStats()
        self._stats_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "ContextRouterEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def get_stats(self) -> ContextRouterStats:
        with self._stats_lock:
            return self._stats.model_copy()

    def reset_stats(self) -> None:
        with self._stats_lock:
            self._stats = ContextRouterStats()

    def _record_telemetry(self, orig_tok: int, comp_tok: int, segments_count: int, engines: Dict[str, int]) -> None:
        with self._stats_lock:
            self._stats.total_requests += 1
            self._stats.total_segments_routed += segments_count
            self._stats.total_original_tokens += orig_tok
            self._stats.total_compressed_tokens += comp_tok
            saved = max(0, orig_tok - comp_tok)
            self._stats.total_tokens_saved += saved
            if self._stats.total_original_tokens > 0:
                self._stats.average_reduction_ratio = round(
                    self._stats.total_tokens_saved / self._stats.total_original_tokens, 4
                )
            for eng, count in engines.items():
                self._stats.engine_call_counts[eng] = self._stats.engine_call_counts.get(eng, 0) + count

    def segment_preview(self, content: str, preserve_static: bool = True) -> List[Dict[str, any]]:
        """Dry-run preview of how the prompt would be cut into segments."""
        raws = segment_prompt(content, preserve_static_header=preserve_static)
        preview = []
        for idx, r in enumerate(raws):
            orig_t = estimate_tokens(r.content)
            preview.append({
                "index": idx,
                "segment_type": r.segment_type.value,
                "engine": r.engine.value,
                "language": r.language,
                "tokens_est": orig_t,
                "preview_text": r.content[:160] + ("..." if len(r.content) > 160 else ""),
            })
        return preview

    def route_and_compress(self, req: ContextRouteRequest) -> ContextRouteResult:
        """Execute end-to-end adaptive segmentation, multi-engine dispatch, and reassembly."""
        t0 = time.perf_counter()
        raw_segments = segment_prompt(req.content, preserve_static_header=req.preserve_static_header)
        
        processed_segments: List[ContextSegment] = []
        engine_distribution: Dict[str, int] = {}
        all_ast_valid = True

        for idx, raw in enumerate(raw_segments):
            seg = self._process_segment(idx, raw, req)
            if seg.engine.value not in engine_distribution:
                engine_distribution[seg.engine.value] = 0
            engine_distribution[seg.engine.value] += 1
            if seg.metadata.get("ast_valid") is False:
                all_ast_valid = False
            processed_segments.append(seg)

        # Reassemble prompt preserving exact sequential ordering
        assembled_parts = [s.compressed_content for s in processed_segments]
        assembled_content = "".join(assembled_parts)

        tot_orig = sum(s.original_tokens for s in processed_segments)
        tot_comp = sum(s.compressed_tokens for s in processed_segments)
        tot_saved = max(0, tot_orig - tot_comp)
        overall_ratio = round(tot_saved / max(1, tot_orig), 4)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        self._record_telemetry(tot_orig, tot_comp, len(processed_segments), engine_distribution)

        return ContextRouteResult(
            assembled_content=assembled_content,
            segments=processed_segments,
            total_original_tokens=tot_orig,
            total_compressed_tokens=tot_comp,
            total_tokens_saved=tot_saved,
            overall_reduction_ratio=overall_ratio,
            total_latency_ms=elapsed_ms,
            ast_syntax_valid=all_ast_valid,
            engine_distribution=engine_distribution,
        )

    def _process_segment(self, idx: int, raw: RawSegment, req: ContextRouteRequest) -> ContextSegment:
        """Route a single segment to its corresponding compression engine with fallback."""
        seg_t0 = time.perf_counter()
        orig_tokens = estimate_tokens(raw.content)

        # 1. Static Header -> Native Caching (100% loss-free passthrough)
        if raw.segment_type == SegmentType.STATIC_HEADER:
            return ContextSegment(
                index=idx,
                segment_type=raw.segment_type,
                engine=RouteEngine.NATIVE_CACHING,
                raw_content=raw.content,
                compressed_content=raw.content,
                original_tokens=orig_tokens,
                compressed_tokens=orig_tokens,
                tokens_saved=0,
                reduction_ratio=0.0,
                latency_ms=0.1,
                status="bypassed",
                metadata={"reason": "immutable_static_header"},
            )

        # 2. Code Block -> TokenShift AST Engine
        if raw.segment_type == SegmentType.CODE_BLOCK:
            try:
                mode_enum = TokenShiftMode(req.default_code_mode.lower())
            except Exception:
                mode_enum = TokenShiftMode.SKELETON

            try:
                lang_hint = TokenShiftLanguage.AUTO
                if raw.language:
                    try:
                        lang_hint = TokenShiftLanguage(raw.language.lower())
                    except Exception:
                        lang_hint = TokenShiftLanguage.AUTO

                ts_req = TokenShiftRequest(
                    code=raw.content,
                    language=lang_hint,
                    mode=mode_enum,
                    preserve_docstrings=True,
                )
                ts_res = TokenShiftEngine.compress(ts_req)
                reconstructed = f"{raw.fence_prefix}{ts_res.compressed_code}{raw.fence_suffix}"
                comp_tokens = estimate_tokens(reconstructed)
                is_valid = ts_res.syntax_validation.valid if ts_res.syntax_validation else True
                lat = round(ts_res.elapsed_ms, 2)
                return ContextSegment(
                    index=idx,
                    segment_type=raw.segment_type,
                    engine=RouteEngine.TOKENSHIFT,
                    language=raw.language,
                    raw_content=f"{raw.fence_prefix}{raw.content}{raw.fence_suffix}",
                    compressed_content=reconstructed,
                    original_tokens=orig_tokens,
                    compressed_tokens=comp_tokens,
                    tokens_saved=max(0, orig_tokens - comp_tokens),
                    reduction_ratio=round(max(0, orig_tokens - comp_tokens) / max(1, orig_tokens), 4),
                    latency_ms=lat,
                    status="ok" if is_valid else "fallback",
                    metadata={
                        "ast_valid": is_valid,
                        "mode": ts_res.mode,
                        "protected_symbols": ts_res.protected_nodes_count,
                    },
                )
            except Exception as e:
                logger.warning("TokenShift routing fallback on segment %d: %s", idx, e)
                full_raw = f"{raw.fence_prefix}{raw.content}{raw.fence_suffix}"
                return ContextSegment(
                    index=idx,
                    segment_type=raw.segment_type,
                    engine=RouteEngine.TOKENSHIFT,
                    language=raw.language,
                    raw_content=full_raw,
                    compressed_content=full_raw,
                    original_tokens=orig_tokens,
                    compressed_tokens=orig_tokens,
                    tokens_saved=0,
                    reduction_ratio=0.0,
                    latency_ms=round((time.perf_counter() - seg_t0) * 1000, 2),
                    status="fallback",
                    metadata={"error": str(e), "ast_valid": True},
                )

        # 3. Natural Language -> LLMLingua-2 Dehydration Engine
        if raw.segment_type == SegmentType.NATURAL_LANGUAGE:
            try:
                dehydrator = WikiDehydrationEngine.get_instance()
                d_req = DehydrationRequest(
                    content=raw.content,
                    target_rate=req.target_dehydration_rate,
                    preserve_structure=True,
                )
                d_res = dehydrator.dehydrate(d_req)
                comp_tokens = estimate_tokens(d_res.dehydrated_content)
                lat = round((time.perf_counter() - seg_t0) * 1000, 2)
                return ContextSegment(
                    index=idx,
                    segment_type=raw.segment_type,
                    engine=RouteEngine.LLMLINGUA2,
                    raw_content=raw.content,
                    compressed_content=d_res.dehydrated_content,
                    original_tokens=orig_tokens,
                    compressed_tokens=comp_tokens,
                    tokens_saved=max(0, orig_tokens - comp_tokens),
                    reduction_ratio=round(max(0, orig_tokens - comp_tokens) / max(1, orig_tokens), 4),
                    latency_ms=lat,
                    status="ok",
                    metadata={
                        "engine_used": d_res.engine_used,
                        "structural_fidelity": d_res.structural_fidelity,
                    },
                )
            except Exception as e:
                logger.warning("LLMLingua-2 dehydration fallback on segment %d: %s", idx, e)
                return ContextSegment(
                    index=idx,
                    segment_type=raw.segment_type,
                    engine=RouteEngine.LLMLINGUA2,
                    raw_content=raw.content,
                    compressed_content=raw.content,
                    original_tokens=orig_tokens,
                    compressed_tokens=orig_tokens,
                    tokens_saved=0,
                    reduction_ratio=0.0,
                    latency_ms=round((time.perf_counter() - seg_t0) * 1000, 2),
                    status="fallback",
                    metadata={"error": str(e)},
                )

        # 4. Skill Contract -> SkillZip Engine
        if raw.segment_type == SegmentType.SKILL_CONTRACT and req.enable_skillzip:
            try:
                from openviking.service.skill_zip_engine import SkillZipEngine
                zip_engine = SkillZipEngine.get_instance()
                zip_res = zip_engine.compress(raw.content)
                comp_tokens = estimate_tokens(zip_res.compressed_skill)
                lat = round((time.perf_counter() - seg_t0) * 1000, 2)
                return ContextSegment(
                    index=idx,
                    segment_type=raw.segment_type,
                    engine=RouteEngine.SKILLZIP,
                    raw_content=raw.content,
                    compressed_content=zip_res.compressed_skill,
                    original_tokens=orig_tokens,
                    compressed_tokens=comp_tokens,
                    tokens_saved=max(0, orig_tokens - comp_tokens),
                    reduction_ratio=round(max(0, orig_tokens - comp_tokens) / max(1, orig_tokens), 4),
                    latency_ms=lat,
                    status="ok",
                    metadata={"zip_reduction_ratio": zip_res.reduction_ratio},
                )
            except Exception as e:
                logger.debug("SkillZip routing fallback: %s", e)

        # Default Passthrough
        return ContextSegment(
            index=idx,
            segment_type=raw.segment_type,
            engine=raw.engine,
            raw_content=raw.content,
            compressed_content=raw.content,
            original_tokens=orig_tokens,
            compressed_tokens=orig_tokens,
            tokens_saved=0,
            reduction_ratio=0.0,
            latency_ms=round((time.perf_counter() - seg_t0) * 1000, 2),
            status="passthrough",
            metadata={},
        )
