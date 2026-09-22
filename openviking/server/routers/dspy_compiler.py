# Copyright (c) 2026 OpenViking Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0.

"""
Stanford DSPy (MIPO) 强类型提示词编译器 REST API 路由 (SSOT)
落实 BLUEPRINT.md 课题五轮子 #5 (Stanford DSPy MIPO Compiler)
"""

from fastapi import APIRouter, HTTPException
from openviking.service.dspy_compiler_engine import DSPyCompilerEngine
from openviking.service.dspy_compiler_types import (
    DSPyCompileRequest,
    DSPyCompileResult,
    DSPyCompilerStats,
)

router = APIRouter(prefix="/api/v1/dspy", tags=["dspy-compiler"])


@router.post("/compile", response_model=DSPyCompileResult)
async def compile_prompt(request: DSPyCompileRequest) -> DSPyCompileResult:
    """将松散原始 Prompt 编译为带有强类型 Schema 规约与精选 Few-Shot 的高精纯提示词"""
    try:
        engine = DSPyCompilerEngine.get_instance()
        return engine.compile(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DSPy compile error: {str(exc)}")


@router.post("/verify")
async def verify_signature(request: DSPyCompileRequest) -> dict:
    """验证原始 Prompt 的强类型签名提取与不可变契约有效性"""
    try:
        engine = DSPyCompilerEngine.get_instance()
        sig = engine.extract_signature(
            raw_prompt=request.raw_prompt,
            custom_name=request.signature_name,
            custom_objective=request.task_objective,
        )
        return {
            "status": "PASS" if sig.input_fields and sig.output_fields else "PARTIAL",
            "signature": sig.model_dump(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DSPy verify error: {str(exc)}")


@router.get("/stats", response_model=DSPyCompilerStats)
async def get_compiler_stats() -> DSPyCompilerStats:
    """获取编译器全局度量指标"""
    engine = DSPyCompilerEngine.get_instance()
    return engine.get_stats()


@router.post("/reset-stats")
async def reset_compiler_stats() -> dict:
    """重置编译器度量统计"""
    engine = DSPyCompilerEngine.get_instance()
    engine.reset_stats()
    return {"status": "ok", "message": "DSPy compiler statistics reset successfully"}
