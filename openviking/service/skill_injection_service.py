# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill Injection & Adaptive Token-Budget Compression Service.

Provides:
1. 0-Rollout deterministic just-in-time skill injection for running agents.
2. Code-block and YAML frontmatter invariant protection.
3. Adaptive token-budget tiered degradation (Contracts > Rules > Interface > Workflow).
4. Direct FastMCP & REST API injection integration.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from openviking.service.skill_zip_engine import SkillZipEngine, SkillTuple


class SkillInjectionResult(BaseModel):
    """Result of skill injection with optional adaptive compression."""
    is_compact: bool
    original_length: int
    compressed_length: int
    estimated_tokens: int
    tokens_saved: int
    compression_ratio: float
    contract_fidelity: float
    latency_ms: float
    content: str


class SkillInjectionService:
    """Singleton service for agent runtime just-in-time skill injection."""

    _instance: Optional[SkillInjectionService] = None

    def __init__(self):
        self._zip_engine = SkillZipEngine.get_instance()

    @classmethod
    def get_instance(cls) -> SkillInjectionService:
        if cls._instance is None:
            cls._instance = SkillInjectionService()
        return cls._instance

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count: ~1 token per 4 characters for Latin, ~1.2 per CJK char."""
        if not text:
            return 0
        cjk_count = len(re.findall(r"[\u4e00-\u9fa5]", text))
        other_count = max(0, len(text) - cjk_count)
        return int(cjk_count * 1.2 + other_count / 4.0)

    def compress_for_injection(
        self,
        raw_content: str,
        compact: bool = False,
        budget_tokens: Optional[int] = None,
    ) -> SkillInjectionResult:
        """Compress skill content adaptively for runtime agent injection."""
        t_start = time.perf_counter()
        orig_len = len(raw_content or "")
        orig_tokens = self.estimate_tokens(raw_content or "")

        if not raw_content or not raw_content.strip():
            return SkillInjectionResult(
                is_compact=False,
                original_length=0,
                compressed_length=0,
                estimated_tokens=0,
                tokens_saved=0,
                compression_ratio=0.0,
                contract_fidelity=1.0,
                latency_ms=0.0,
                content="",
            )

        if not compact and not budget_tokens:
            latency_ms = (time.perf_counter() - t_start) * 1000.0
            return SkillInjectionResult(
                is_compact=False,
                original_length=orig_len,
                compressed_length=orig_len,
                estimated_tokens=orig_tokens,
                tokens_saved=0,
                compression_ratio=0.0,
                contract_fidelity=1.0,
                latency_ms=round(latency_ms, 2),
                content=raw_content,
            )

        # 1. 保护代码块免遭口水话正则与字符替换污染
        code_blocks: List[str] = []
        def _stash_code(match: re.Match) -> str:
            placeholder = f"__OPENVIKING_CODE_BLOCK_{len(code_blocks)}__"
            code_blocks.append(match.group(0))
            return placeholder

        stashed_text = re.sub(r"```[\s\S]*?```", _stash_code, raw_content)

        # 2. 执行 0-rollout 契约抽稀
        zip_res = self._zip_engine.compress(stashed_text)
        hoisted: SkillTuple = zip_res.six_tuple

        # 默认紧凑文本使用 SkillZipEngine 的全量抽稀结果
        candidate_text = zip_res.compressed_content

        # 还原代码块
        for idx, block in enumerate(code_blocks):
            candidate_text = candidate_text.replace(f"__OPENVIKING_CODE_BLOCK_{idx}__", block)

        est_tokens = self.estimate_tokens(candidate_text)

        # 3. 若设定了 budget_tokens 且超出预算，执行优先级阶梯裁剪
        if budget_tokens and est_tokens > budget_tokens:
            frontmatter = ""
            if raw_content.startswith("---"):
                parts = raw_content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = f"---{parts[1]}---\n"

            truncated_sections: List[str] = []
            if frontmatter:
                truncated_sections.append(frontmatter.strip())
            if hoisted.contracts:
                truncated_sections.append("# Contracts\n" + "\n".join(f"- {c}" for c in hoisted.contracts))

            # 检查剩余预算
            curr_text = "\n\n".join(truncated_sections)
            curr_tokens = self.estimate_tokens(curr_text)

            if curr_tokens < budget_tokens and hoisted.rules:
                allowed_rules = []
                for r in hoisted.rules:
                    trimmed_r = self._zip_engine._trim_verbal_noise(r)
                    if self.estimate_tokens("\n".join(allowed_rules + [f"- {trimmed_r}"])) + curr_tokens < budget_tokens:
                        allowed_rules.append(f"- {trimmed_r}")
                if allowed_rules:
                    truncated_sections.append("# Rules\n" + "\n".join(allowed_rules))

            curr_text = "\n\n".join(truncated_sections)
            curr_tokens = self.estimate_tokens(curr_text)

            if curr_tokens < budget_tokens and hoisted.interface:
                trimmed_iface = hoisted.interface.strip()[:300]
                truncated_sections.append(f"# Interface\n{trimmed_iface}")

            curr_text = "\n\n".join(truncated_sections)
            curr_tokens = self.estimate_tokens(curr_text)

            if curr_tokens < budget_tokens and hoisted.workflow:
                allowed_steps = []
                for idx, w in enumerate(hoisted.workflow, 1):
                    step_line = f"{idx}. {self._zip_engine._trim_verbal_noise(w)}"
                    if self.estimate_tokens("\n".join(allowed_steps + [step_line])) + curr_tokens < budget_tokens:
                        allowed_steps.append(step_line)
                if allowed_steps:
                    truncated_sections.append("# Workflow\n" + "\n".join(allowed_steps))

            candidate_text = "\n\n".join(truncated_sections).strip() + "\n"
            for idx, block in enumerate(code_blocks):
                candidate_text = candidate_text.replace(f"__OPENVIKING_CODE_BLOCK_{idx}__", block)
            est_tokens = self.estimate_tokens(candidate_text)


        comp_len = len(candidate_text)
        compression_ratio = max(0.0, (orig_len - comp_len) / orig_len) if orig_len > 0 else 0.0
        tokens_saved = max(0, orig_tokens - est_tokens)
        latency_ms = (time.perf_counter() - t_start) * 1000.0

        return SkillInjectionResult(
            is_compact=True,
            original_length=orig_len,
            compressed_length=comp_len,
            estimated_tokens=est_tokens,
            tokens_saved=tokens_saved,
            compression_ratio=round(compression_ratio, 4),
            contract_fidelity=zip_res.contract_fidelity,
            latency_ms=round(latency_ms, 2),
            content=candidate_text,
        )

    def inject_into_dict(
        self,
        skill_dict: Dict[str, Any],
        compact: bool = False,
        budget_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Apply injection compression to a skill dictionary in-place."""
        if not skill_dict or not (compact or budget_tokens):
            return skill_dict

        raw_content = skill_dict.get("content") or skill_dict.get("raw_content") or ""
        if not raw_content:
            return skill_dict

        result = self.compress_for_injection(raw_content, compact=compact, budget_tokens=budget_tokens)
        skill_dict["raw_content"] = raw_content
        skill_dict["content"] = result.content
        skill_dict["is_compact"] = result.is_compact
        skill_dict["compression"] = {
            "ratio": result.compression_ratio,
            "original_length": result.original_length,
            "compressed_length": result.compressed_length,
            "estimated_tokens": result.estimated_tokens,
            "tokens_saved": result.tokens_saved,
            "contract_fidelity": result.contract_fidelity,
            "latency_ms": result.latency_ms,
        }
        return skill_dict
