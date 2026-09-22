# Copyright (c) 2026 OpenViking Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0.

"""
Stanford DSPy (MIPO) 强类型提示词编译器强类型 DTO 定义 (SSOT)
落实 BLUEPRINT.md 课题五轮子 #5 (Prompt Compilation & Zero-Hallucination Signature)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DSPyFieldContract(BaseModel):
    """强类型字段契约"""
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="字段名称，例如 query, schema, sql, decision")
    field_type: str = Field("str", description="类型标记: str, int, bool, List[str], Dict[str, Any]")
    description: str = Field("", description="字段自解释语义")
    required: bool = Field(True, description="是否必填")


class CompiledSignature(BaseModel):
    """编译后提示词签名 (Input -> Output)"""
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="签名名称，如 StructuredTextToSQL, AgentToolDispatcher")
    task_objective: str = Field(..., description="核心任务目标")
    input_fields: List[DSPyFieldContract] = Field(default_factory=list, description="输入契约字段列表")
    output_fields: List[DSPyFieldContract] = Field(default_factory=list, description="输出契约字段列表")
    constraints: List[str] = Field(default_factory=list, description="不可变边界与零幻觉排斥规则")


class BootstrapExample(BaseModel):
    """Bootstrap 少量示例样本 (Few-Shot)"""
    model_config = ConfigDict(extra="ignore")

    example_id: str = Field(..., description="样本唯一 ID")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="输入样例字典")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="期望输出样例字典")
    quality_score: float = Field(1.0, description="置信度/质量分 (0.0~1.0)")
    verified: bool = Field(True, description="是否经过沙箱/黄金断言验真")
    source: str = Field("synthetic_gold", description="样本来源: synthetic_gold, user_trajectory, teacher_rollout")


class DSPyCompileRequest(BaseModel):
    """DSPy 提示词编译请求"""
    model_config = ConfigDict(extra="ignore")

    raw_prompt: str = Field(..., description="原始松散或待编译的 Prompt")
    signature_name: Optional[str] = Field(None, description="自定义签名名称")
    task_objective: Optional[str] = Field(None, description="显式指定核心任务目标")
    candidate_examples: List[BootstrapExample] = Field(default_factory=list, description="候选 Few-Shot 样本池")
    max_few_shot: int = Field(3, ge=0, le=8, description="注入的最大 Few-Shot 样本数")
    strict_typing: bool = Field(True, description="强制强类型 JSON/Schema 输出规约")
    anti_hallucination_gate: bool = Field(True, description="注入主动弃答与负向边界排斥规约")


class DSPyCompileResult(BaseModel):
    """DSPy 提示词编译结果"""
    model_config = ConfigDict(extra="ignore")

    compiled_prompt: str = Field(..., description="编译合成后的高精纯强类型 Prompt")
    signature: CompiledSignature = Field(..., description="提取与固化的强类型签名")
    selected_few_shot: List[BootstrapExample] = Field(default_factory=list, description="被精选注入的 Few-Shot 样本")
    original_token_count: int = Field(..., description="原始 Prompt Token 估算")
    compiled_token_count: int = Field(..., description="编译后 Prompt Token 估算")
    compression_ratio: float = Field(..., description="Token 变化比率 ( compiled / original )")
    contract_status: str = Field("PASS", description="契约状态: PASS | PARTIAL | FAIL")
    anti_hallucination_injected: bool = Field(True, description="是否已注入防幻觉护栏")
    elapsed_ms: float = Field(..., description="编译耗时 (毫秒)")


class DSPyCompilerStats(BaseModel):
    """DSPy 编译器全局运行态指标"""
    model_config = ConfigDict(extra="ignore")

    total_compilations: int = Field(0, description="总编译调用次数")
    total_original_tokens: int = Field(0, description="累计原始 Token")
    total_compiled_tokens: int = Field(0, description="累计编译后 Token")
    average_latency_ms: float = Field(0.0, description="平均编译延迟 (ms)")
    pass_contract_count: int = Field(0, description="通过强类型契约校验次数")
