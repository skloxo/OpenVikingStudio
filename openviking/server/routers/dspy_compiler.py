# Copyright (c) 2026 OpenViking Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0.

"""Stanford DSPy (MIPO) 强类型提示词编译器 REST API 路由 (SSOT)

落实 BLUEPRINT.md 课题五轮子 #5 (Stanford DSPy MIPO Compiler)
支持系统真实 Prompt 模板拾取与编译产物安全落盘 (Card-102 / v1.7.56)。
"""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from openviking.service.dspy_apply import (
    ApplyDSPyRequest,
    ApplyDSPyResult,
    DSPyApplyService,
    PromptTemplateItem,
)
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


@router.get("/templates", response_model=List[PromptTemplateItem])
async def list_prompt_templates(
    search: Optional[str] = Query(default=None, description="Search keyword in template id/name/desc"),
    category: Optional[str] = Query(default=None, description="Category filter (compression, retrieval, etc.)"),
    limit: int = Query(default=50, ge=1, le=200, description="Max items to return"),
) -> List[PromptTemplateItem]:
    """Scan and list real prompt templates in openviking/prompts/templates."""
    service = DSPyApplyService()
    return service.list_prompt_templates(search=search, category=category, limit=limit)


@router.get("/template")
async def read_prompt_template(
    path: str = Query(..., description="Relative path of prompt template YAML"),
) -> dict:
    """Read prompt template YAML content and extracted metadata."""
    service = DSPyApplyService()
    try:
        return service.read_prompt_template(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read prompt template: {exc}")


@router.post("/apply", response_model=ApplyDSPyResult)
async def apply_compiled_prompt(request: ApplyDSPyRequest) -> ApplyDSPyResult:
    """Persist compiled prompt to disk with quarantine snapshotting."""
    service = DSPyApplyService()
    try:
        return service.apply_compiled_prompt(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist compiled prompt: {exc}")
