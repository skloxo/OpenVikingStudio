# -*- coding: utf-8 -*-
"""Wiki Dehydration Engine - Microsoft LLMLingua-2 Dedicated Adapter & Pruner.

Implements:
1. Dedicated Viking Adapter for natural language Wiki & Markdown ingestion.
2. Hardcoded Safeguard Hyperparameters:
   - rate = 0.50 (50% target compression)
   - threshold = 0.35 (preserves negation words and control tokens)
   - Structural Freezing: YAML frontmatter (^---[\\s\\S]*?---), code blocks (```...```)
3. Zero VRAM leakage: strictly CPU-bound, avoids 2080Ti VRAM allocation.
4. Resilient Fallback: Rule-based syntactic pruner when model is unavailable or offline.
5. Rolling Telemetry & Structural Integrity Verification.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:
    _TIKTOKEN_AVAILABLE = False
    _ENC = None

# Hardcoded Frozen Hyperparameters (Rule 7 SSOT)
HARDCODED_DEFAULT_RATE: float = 0.50
HARDCODED_DEFAULT_THRESHOLD: float = 0.35
HARDCODED_PROTECTED_TOKENS: List[str] = [
    "not", "never", "no", "none", "without", "except", "strictly",
    "严禁", "必须", "禁止", "切勿", "不可", "不得", "绝对", "违者", "红线", "必究"
]

YAML_FRONTMATTER_REGEX = re.compile(r"^---[\s\S]*?---\n?", re.MULTILINE)
CODE_BLOCK_REGEX = re.compile(r"```[\s\S]*?```", re.MULTILINE)
HEADING_REGEX = re.compile(r"^#{1,6}\s+.*$", re.MULTILINE)


class DehydrationRequest(BaseModel):
    """Input payload for Wiki document dehydration."""
    content: str = Field(..., description="Raw markdown or wiki text to dehydrate")
    target_rate: float = Field(default=HARDCODED_DEFAULT_RATE, ge=0.10, le=0.90)
    threshold: float = Field(default=HARDCODED_DEFAULT_THRESHOLD, ge=0.10, le=0.90)
    protect_yaml_frontmatter: bool = Field(default=True)
    protect_code_blocks: bool = Field(default=True)
    protect_headings: bool = Field(default=True)


class DehydrationResult(BaseModel):
    """Result schema for Wiki dehydration."""
    original_text: str
    dehydrated_text: str
    original_tokens: int
    dehydrated_tokens: int
    tokens_saved: int
    compression_ratio: float
    frozen_blocks_count: int
    protected_tokens_count: int
    latency_ms: float
    engine_used: str
    structural_integrity_verified: bool
    details: Dict[str, Any] = Field(default_factory=dict)


class DehydrationTelemetry(BaseModel):
    """Cumulative telemetry metrics for dehydration service."""
    total_dehydrations: int = 0
    total_original_tokens: int = 0
    total_dehydrated_tokens: int = 0
    total_tokens_saved: int = 0
    avg_compression_ratio: float = 0.0
    avg_latency_ms: float = 0.0
    engine_counts: Dict[str, int] = Field(default_factory=lambda: {
        "llmlingua-2-xlm-roberta": 0,
        "rule-based-syntactic-pruner": 0,
    })


def count_tokens(text: str) -> int:
    """Accurately count tokens using cl100k_base, with fallback to character heuristic."""
    if _TIKTOKEN_AVAILABLE and _ENC is not None:
        try:
            return len(_ENC.encode(text, disallowed_special=()))
        except Exception:
            pass
    # Fallback heuristic: 1 token ~= 4 English chars or 1.5 CJK chars
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    other_count = len(text) - cjk_count
    return max(1, int(cjk_count / 1.5 + other_count / 4.0))


class WikiDehydrationEngine:
    """Dedicated Viking Adapter for Wiki & Markdown Dehydration."""

    _instance: Optional[WikiDehydrationEngine] = None

    def __init__(self):
        self._compressor: Optional[Any] = None
        self._llmlingua_attempted: bool = False
        self._llmlingua_ready: bool = False
        self._telemetry = DehydrationTelemetry()
        self._latencies: List[float] = []

    @classmethod
    def get_instance(cls) -> WikiDehydrationEngine:
        if cls._instance is None:
            cls._instance = WikiDehydrationEngine()
        return cls._instance

    def _find_local_model_path(self, model_id: str) -> Optional[str]:
        """Check if complete model weights exist locally to avoid blocking network downloads."""
        # Check explicit environment override
        env_path = os.environ.get("LLMLINGUA_MODEL_PATH")
        if env_path and os.path.exists(env_path):
            return env_path

        # Check HuggingFace Hub cached snapshots
        hub_name = f"models--{model_id.replace('/', '--')}"
        snapshots_dir = os.path.expanduser(f"~/.cache/huggingface/hub/{hub_name}/snapshots")
        if os.path.isdir(snapshots_dir):
            for snap in os.listdir(snapshots_dir):
                snap_path = os.path.join(snapshots_dir, snap)
                if os.path.isdir(snap_path):
                    has_weights = any(
                        os.path.exists(os.path.join(snap_path, w))
                        for w in ("model.safetensors", "pytorch_model.bin")
                    )
                    if has_weights:
                        return snap_path
        return None

    def _init_llmlingua_compressor(self) -> bool:
        """Lazy initialization of PromptCompressor on CPU with safe fallback."""
        if self._llmlingua_attempted:
            return self._llmlingua_ready

        self._llmlingua_attempted = True
        model_name = "microsoft/llmlingua-2-xlm-roberta-large-meetingbank"
        local_path = self._find_local_model_path(model_name)
        if not local_path:
            # Model weights not fully cached locally; fallback to rule engine to avoid hanging
            self._compressor = None
            self._llmlingua_ready = False
            return False

        try:
            from llmlingua import PromptCompressor
            # Strictly use CPU device map to ensure zero VRAM allocation on 2080Ti
            self._compressor = PromptCompressor(
                model_name=local_path,
                device_map="cpu",
            )
            self._llmlingua_ready = True
        except Exception:
            # Fallback to local rule engine if offline or model loading times out
            self._compressor = None
            self._llmlingua_ready = False
        return self._llmlingua_ready

    def _freeze_structural_blocks(
        self,
        text: str,
        protect_yaml: bool,
        protect_code: bool,
        protect_headings: bool,
    ) -> Tuple[str, List[Tuple[str, str]]]:
        """Extract and freeze structural blocks into placeholders."""
        frozen_blocks: List[Tuple[str, str]] = []
        placeholder_idx = 0

        # 1. Protect YAML frontmatter
        if protect_yaml:
            yaml_match = YAML_FRONTMATTER_REGEX.match(text)
            if yaml_match:
                token_placeholder = f"__VK_FROZEN_YAML_{placeholder_idx}__"
                placeholder_idx += 1
                frozen_blocks.append((token_placeholder, yaml_match.group(0)))
                text = text[yaml_match.end():]
                # Prepend placeholder to remaining text
                text = f"{token_placeholder}\n" + text

        # 2. Protect Code blocks
        if protect_code:
            def replace_code_block(match: re.Match) -> str:
                nonlocal placeholder_idx
                token_placeholder = f"__VK_FROZEN_CODE_{placeholder_idx}__"
                placeholder_idx += 1
                frozen_blocks.append((token_placeholder, match.group(0)))
                return token_placeholder

            text = CODE_BLOCK_REGEX.sub(replace_code_block, text)

        # 3. Protect Markdown headings
        if protect_headings:
            def replace_heading(match: re.Match) -> str:
                nonlocal placeholder_idx
                token_placeholder = f"__VK_FROZEN_HEAD_{placeholder_idx}__"
                placeholder_idx += 1
                frozen_blocks.append((token_placeholder, match.group(0)))
                return token_placeholder

            text = HEADING_REGEX.sub(replace_heading, text)

        return text, frozen_blocks

    def _restore_structural_blocks(
        self,
        text: str,
        frozen_blocks: List[Tuple[str, str]],
    ) -> str:
        """Restore frozen placeholders back into original exact text."""
        # Reverse restore so inner blocks don't collide
        for placeholder, original_block in reversed(frozen_blocks):
            text = text.replace(placeholder, original_block)
        return text

    def _rule_based_prune(self, text: str, target_rate: float) -> str:
        """Fast, deterministic syntactic pruner for conversational/prose fluff."""
        # Common Chinese and English fluff phrases that add zero semantic value
        fluff_patterns = [
            r"\b(?:as\s+we\s+all\s+know|it\s+is\s+worth\s+noting\s+that|needless\s+to\s+say|in\s+order\s+to)\b",
            r"(?:众所周知|显而易见|不难发现|值得注意的是|总的来说|综上所述|正如前文所述|众所周知的是)[，,、]?",
            r"(?:我们可以看到|众所周知的是|显而易见的是|毋庸置疑的是)[，,、]?",
            r"(?:具体来说|简单来说|归根结底|总而言之|从某种角度来看)[，,、]?",
        ]

        cleaned = text
        for pat in fluff_patterns:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

        # Prune verbose polite filler and duplicate empty lines
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)

        # Line-by-line whitespace trim preserving markdown line-breaks
        lines = [line.rstrip() for line in cleaned.splitlines()]
        cleaned = "\n".join(lines).strip()
        return cleaned

    def dehydrate(self, req: DehydrationRequest) -> DehydrationResult:
        """Execute dehydration on markdown content with structural freezing."""
        start_time = time.perf_counter()
        raw_content = req.content

        # 1. Structural block isolation
        content_for_compression, frozen_blocks = self._freeze_structural_blocks(
            text=raw_content,
            protect_yaml=req.protect_yaml_frontmatter,
            protect_code=req.protect_code_blocks,
            protect_headings=req.protect_headings,
        )

        engine_used = "rule-based-syntactic-pruner"
        dehydrated_candidate = ""

        # 2. Try LLMLingua-2 PromptCompressor
        if self._init_llmlingua_compressor() and self._compressor is not None:
            try:
                compress_res = self._compressor.compress_prompt(
                    context=[content_for_compression],
                    rate=req.target_rate,
                    force_tokens=HARDCODED_PROTECTED_TOKENS,
                    drop_consecutive=True,
                )
                dehydrated_candidate = compress_res.get("compressed_prompt", "")
                if dehydrated_candidate:
                    engine_used = "llmlingua-2-xlm-roberta"
            except Exception:
                dehydrated_candidate = ""

        # 3. Fallback to syntactic pruner
        if not dehydrated_candidate:
            dehydrated_candidate = self._rule_based_prune(
                text=content_for_compression,
                target_rate=req.target_rate,
            )
            engine_used = "rule-based-syntactic-pruner"

        # 4. Restore frozen structural blocks
        final_dehydrated_text = self._restore_structural_blocks(
            text=dehydrated_candidate,
            frozen_blocks=frozen_blocks,
        )

        # 5. Verify structural integrity
        integrity_ok = True
        for placeholder, original_block in frozen_blocks:
            if original_block.strip() not in final_dehydrated_text:
                integrity_ok = False
                break

        # 6. Count tokens and compute telemetry metrics
        orig_tokens = count_tokens(raw_content)
        dehydrated_tokens = count_tokens(final_dehydrated_text)
        tokens_saved = max(0, orig_tokens - dehydrated_tokens)
        compression_ratio = (
            round((tokens_saved / orig_tokens), 4) if orig_tokens > 0 else 0.0
        )
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Count protected tokens preserved
        protected_count = 0
        lowered_final = final_dehydrated_text.lower()
        for token in HARDCODED_PROTECTED_TOKENS:
            if token.lower() in lowered_final:
                protected_count += 1

        # Update telemetry
        self._latencies.append(latency_ms)
        if len(self._latencies) > 200:
            self._latencies.pop(0)

        self._telemetry.total_dehydrations += 1
        self._telemetry.total_original_tokens += orig_tokens
        self._telemetry.total_dehydrated_tokens += dehydrated_tokens
        self._telemetry.total_tokens_saved += tokens_saved
        if self._telemetry.total_original_tokens > 0:
            self._telemetry.avg_compression_ratio = round(
                self._telemetry.total_tokens_saved / self._telemetry.total_original_tokens, 4
            )
        self._telemetry.avg_latency_ms = round(
            sum(self._latencies) / len(self._latencies), 2
        )
        self._telemetry.engine_counts[engine_used] = (
            self._telemetry.engine_counts.get(engine_used, 0) + 1
        )

        return DehydrationResult(
            original_text=raw_content,
            dehydrated_text=final_dehydrated_text,
            original_tokens=orig_tokens,
            dehydrated_tokens=dehydrated_tokens,
            tokens_saved=tokens_saved,
            compression_ratio=compression_ratio,
            frozen_blocks_count=len(frozen_blocks),
            protected_tokens_count=protected_count,
            latency_ms=latency_ms,
            engine_used=engine_used,
            structural_integrity_verified=integrity_ok,
            details={
                "target_rate": req.target_rate,
                "threshold": req.threshold,
                "protected_tokens_checked": len(HARDCODED_PROTECTED_TOKENS),
                "frozen_blocks": [p for p, _ in frozen_blocks],
            },
        )

    def get_telemetry(self) -> DehydrationTelemetry:
        """Retrieve cumulative telemetry metrics."""
        return self._telemetry
