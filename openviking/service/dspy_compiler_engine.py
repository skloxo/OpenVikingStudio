# Copyright (c) 2026 OpenViking Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0.

"""
Stanford DSPy (MIPO) 强类型提示词编译与优化引擎 (SSOT)
落实 BLUEPRINT.md 课题五轮子 #5 (Stanford DSPy MIPO Compiler)
"""

import json
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from openviking.service.dspy_compiler_types import (
    BootstrapExample,
    CompiledSignature,
    DSPyCompileRequest,
    DSPyCompileResult,
    DSPyCompilerStats,
    DSPyFieldContract,
)


class DSPyCompilerEngine:
    """Stanford DSPy (MIPO) 强类型提示词编译器"""

    _instance: Optional["DSPyCompilerEngine"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._stats = DSPyCompilerStats()
        self._stats_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "DSPyCompilerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """轻量准确估算 Token 数量 (中英文混合)"""
        if not text:
            return 0
        cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        non_cjk_words = len(re.findall(r"[a-zA-Z0-9_]+", text))
        punctuation = len(re.findall(r"[^\w\s\u4e00-\u9fff]", text))
        tokens = int(cjk_chars * 0.75 + non_cjk_words * 1.3 + punctuation * 0.5)
        return max(1, tokens)

    def extract_signature(
        self,
        raw_prompt: str,
        custom_name: Optional[str] = None,
        custom_objective: Optional[str] = None,
    ) -> CompiledSignature:
        """从原始 Prompt 启发式解析出输入输出强类型签名与约束"""
        name = custom_name or "CompiledTaskSignature"
        lines = [line.strip() for line in raw_prompt.strip().split("\n") if line.strip()]

        objective = custom_objective or ""
        if not objective:
            for line in lines[:3]:
                if any(kw in line for kw in ["你是一个", "你是", "任务", "目标", "负责", "实现", "请"]):
                    clean_line = re.sub(r"^[#\-\*\s]+", "", line).strip()
                    objective = clean_line
                    break
            if not objective and lines:
                objective = lines[0]

        input_fields: List[DSPyFieldContract] = []
        output_fields: List[DSPyFieldContract] = []
        constraints: List[str] = []

        field_patterns = [
            (r"(?:输入|参数|Input|Query|Context|Schema)[:：\s]+`?([a-zA-Z0-9_]+)`?", "input"),
            (r"(?:输出|结果|Output|JSON|Result)[:：\s]+`?([a-zA-Z0-9_]+)`?", "output"),
        ]
        for pattern, direction in field_patterns:
            matches = re.findall(pattern, raw_prompt, flags=re.IGNORECASE)
            for m in set(matches):
                contract = DSPyFieldContract(name=m, field_type="str", description=f"Extracted {direction} parameter {m}")
                if direction == "input" and not any(f.name == m for f in input_fields):
                    input_fields.append(contract)
                elif direction == "output" and not any(f.name == m for f in output_fields):
                    output_fields.append(contract)

        if not input_fields:
            input_fields = [
                DSPyFieldContract(name="query", field_type="str", description="User natural language instruction or query", required=True),
                DSPyFieldContract(name="context", field_type="Optional[str]", description="Supplementary background context", required=False),
            ]
        if not output_fields:
            output_fields = [
                DSPyFieldContract(name="response", field_type="str", description="Structured verified execution result", required=True),
                DSPyFieldContract(name="confidence", field_type="float", description="Reliability score between 0.0 and 1.0", required=True),
            ]

        # 提取不可变约束与负向边界
        for line in lines:
            if any(kw in line for kw in ["严禁", "禁止", "不能", "必须", "不可", "不要", "DO NOT", "MUST"]):
                clean_constraint = re.sub(r"^[#\-\*\s]+", "", line).strip()
                if clean_constraint and clean_constraint not in constraints:
                    constraints.append(clean_constraint)

        if not constraints:
            constraints = [
                "Strictly abide by the defined schema. Do NOT fabricate non-existent fields or hallucinations.",
                "If required parameters or evidence are insufficient, trigger explicit abstention or request clarification.",
            ]

        return CompiledSignature(
            name=name,
            task_objective=objective,
            input_fields=input_fields,
            output_fields=output_fields,
            constraints=constraints,
        )

    def select_bootstrap_few_shots(
        self,
        candidates: List[BootstrapExample],
        max_count: int = 3,
    ) -> List[BootstrapExample]:
        """按质量分与已验证状态精选 Few-Shot 样本"""
        if not candidates or max_count <= 0:
            return []
        # 排序：verified优先，其次质量分倒序
        sorted_examples = sorted(
            candidates,
            key=lambda ex: (1 if ex.verified else 0, ex.quality_score),
            reverse=True,
        )
        return sorted_examples[:max_count]

    def compile(self, request: DSPyCompileRequest) -> DSPyCompileResult:
        """执行 Stanford DSPy (MIPO) 强类型编译流水线"""
        start_time = time.perf_counter()
        raw_prompt = request.raw_prompt.strip()

        # 1. 签名抽取与契约化
        signature = self.extract_signature(
            raw_prompt=raw_prompt,
            custom_name=request.signature_name,
            custom_objective=request.task_objective,
        )

        # 2. Bootstrap Few-Shot 样本精选
        selected_examples = self.select_bootstrap_few_shots(
            candidates=request.candidate_examples,
            max_count=request.max_few_shot,
        )

        # 3. 强类型提示词骨架合成
        parts: List[str] = []
        parts.append(f"### [DSPy Compiled Signature: {signature.name}]")
        parts.append(f"**Task Objective**: {signature.task_objective}\n")

        # 输入与输出规范
        parts.append("#### [Input Fields Specification]")
        for f in signature.input_fields:
            req_str = "Required" if f.required else "Optional"
            parts.append(f"- `{f.name}` ({f.field_type}, {req_str}): {f.description or 'No extra description'}")

        parts.append("\n#### [Output Schema Specification]")
        for f in signature.output_fields:
            parts.append(f"- `{f.name}` ({f.field_type}, Required): {f.description or 'Output result field'}")

        # 强类型格式规约
        if request.strict_typing:
            schema_keys = {f.name: f"<type: {f.field_type}>" for f in signature.output_fields}
            parts.append("\n#### [Strict Type Contract]")
            parts.append("You MUST return exclusively a valid JSON dictionary conforming to the following structure:")
            parts.append(f"```json\n{json.dumps(schema_keys, indent=2, ensure_ascii=False)}\n```")

        # 注入 Few-Shot
        if selected_examples:
            parts.append("\n#### [Bootstrap Verified Examples]")
            for idx, ex in enumerate(selected_examples, 1):
                parts.append(f"--- Example #{idx} (Score: {ex.quality_score:.2f}, Source: {ex.source}) ---")
                parts.append(f"Input:\n{json.dumps(ex.inputs, indent=2, ensure_ascii=False)}")
                parts.append(f"Output:\n{json.dumps(ex.outputs, indent=2, ensure_ascii=False)}\n")

        # 注入防幻觉与边界排斥规约
        if request.anti_hallucination_gate:
            parts.append("#### [Inviolable Constraints & Zero-Hallucination Barrier]")
            for c in signature.constraints:
                parts.append(f"- 🚫 {c}")
            parts.append("- 🚫 Zero-hallucination mandate: Never output mocked data, imaginary API endpoints, or ungrounded facts.")

        compiled_prompt = "\n".join(parts).strip()

        orig_tokens = self.estimate_tokens(raw_prompt)
        comp_tokens = self.estimate_tokens(compiled_prompt)
        ratio = round(comp_tokens / max(orig_tokens, 1), 3)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # 校验状态
        contract_status = "PASS"
        if not signature.input_fields or not signature.output_fields:
            contract_status = "PARTIAL"

        # 更新运行态指标
        with self._stats_lock:
            self._stats.total_compilations += 1
            self._stats.total_original_tokens += orig_tokens
            self._stats.total_compiled_tokens += comp_tokens
            if contract_status == "PASS":
                self._stats.pass_contract_count += 1
            n = self._stats.total_compilations
            self._stats.average_latency_ms = round(
                ((self._stats.average_latency_ms * (n - 1)) + elapsed_ms) / n, 2
            )

        return DSPyCompileResult(
            compiled_prompt=compiled_prompt,
            signature=signature,
            selected_few_shot=selected_examples,
            original_token_count=orig_tokens,
            compiled_token_count=comp_tokens,
            compression_ratio=ratio,
            contract_status=contract_status,
            anti_hallucination_injected=request.anti_hallucination_gate,
            elapsed_ms=elapsed_ms,
        )

    def get_stats(self) -> DSPyCompilerStats:
        """获取编译器全局度量"""
        with self._stats_lock:
            return self._stats.model_copy()

    def reset_stats(self) -> None:
        """重置度量统计"""
        with self._stats_lock:
            self._stats = DSPyCompilerStats()
