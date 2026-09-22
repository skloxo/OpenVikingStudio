# Copyright (c) 2026 OpenViking Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0.

"""
Stanford DSPy (MIPO) 提示词编译管线单元测试套件 (SSOT)
落实 BLUEPRINT.md 课题五轮子 #5 (Stanford DSPy MIPO Compiler Pipeline)
"""

import pytest
from httpx import ASGITransport, AsyncClient

from openviking.server.app import create_app
from openviking.service.dspy_compiler_engine import DSPyCompilerEngine
from openviking.service.dspy_compiler_types import (
    BootstrapExample,
    DSPyCompileRequest,
    DSPyFieldContract,
)


@pytest.fixture
def compiler_engine():
    engine = DSPyCompilerEngine.get_instance()
    engine.reset_stats()
    return engine


def test_dspy_signature_extraction(compiler_engine):
    """测试从原始 Prompt 自动提取强类型输入输出字段与约束"""
    raw_prompt = """
    你是一个全栈量化策略分析专家。
    输入参数: Query: 用户自然语言策略诉求, Context: 历史资产收益率矩阵
    输出字段: StrategyCode: 生成的 Python 代码, RiskLevel: 风险等级评级
    严禁引用未授权的第三方外部黑盒库。
    必须保证策略在历史极端行情下不发生穿仓。
    """
    signature = compiler_engine.extract_signature(
        raw_prompt=raw_prompt,
        custom_name="QuantStrategyGenerator",
    )
    assert signature.name == "QuantStrategyGenerator"
    assert "量化策略分析" in signature.task_objective or "Query" in signature.task_objective
    input_names = [f.name for f in signature.input_fields]
    output_names = [f.name for f in signature.output_fields]
    assert "Query" in input_names or "query" in input_names or len(input_names) >= 2
    assert "StrategyCode" in output_names or "strategycode" in output_names or len(output_names) >= 2
    assert len(signature.constraints) >= 2
    assert any("第三方" in c or "穿仓" in c for c in signature.constraints)


def test_dspy_bootstrap_few_shot_selection(compiler_engine):
    """测试 Bootstrap 样本质量筛选器"""
    candidates = [
        BootstrapExample(example_id="ex1", inputs={"q": "A"}, outputs={"a": "1"}, quality_score=0.6, verified=False),
        BootstrapExample(example_id="ex2", inputs={"q": "B"}, outputs={"a": "2"}, quality_score=0.95, verified=True),
        BootstrapExample(example_id="ex3", inputs={"q": "C"}, outputs={"a": "3"}, quality_score=0.85, verified=True),
        BootstrapExample(example_id="ex4", inputs={"q": "D"}, outputs={"a": "4"}, quality_score=0.99, verified=False),
    ]
    selected = compiler_engine.select_bootstrap_few_shots(candidates, max_count=2)
    assert len(selected) == 2
    # 优先 verified=True，且分数最高的是 ex2, ex3
    assert selected[0].example_id == "ex2"
    assert selected[1].example_id == "ex3"


def test_dspy_compile_full_pipeline(compiler_engine):
    """测试完整 DSPy MIPO 编译流程与防幻觉护栏注入"""
    req = DSPyCompileRequest(
        raw_prompt="请根据用户提问从数据库生成 PostgreSQL 查询语句。输入参数: Query, Schema。输出结果: SQL, Explanation。",
        signature_name="TextToSQLCompiler",
        candidate_examples=[
            BootstrapExample(
                example_id="gold_1",
                inputs={"Query": "查询活跃用户", "Schema": "users(id, status)"},
                outputs={"SQL": "SELECT id FROM users WHERE status = 'active';", "Explanation": "过滤活跃状态"},
                quality_score=0.98,
                verified=True,
            )
        ],
        max_few_shot=2,
        strict_typing=True,
        anti_hallucination_gate=True,
    )
    result = compiler_engine.compile(req)
    assert "### [DSPy Compiled Signature: TextToSQLCompiler]" in result.compiled_prompt
    assert "Strict Type Contract" in result.compiled_prompt
    assert "Zero-Hallucination Barrier" in result.compiled_prompt
    assert "Example #1" in result.compiled_prompt
    assert result.contract_status == "PASS"
    assert result.compiled_token_count > 0
    assert result.original_token_count > 0
    assert result.elapsed_ms >= 0.0

    stats = compiler_engine.get_stats()
    assert stats.total_compilations == 1
    assert stats.pass_contract_count == 1


def test_dspy_token_estimator(compiler_engine):
    """测试中英文混合 Token 估算器准确性"""
    text = "Hello World! 这是一个测试 Stanford DSPy 编译器的测试用例。"
    tokens = compiler_engine.estimate_tokens(text)
    assert 10 <= tokens <= 40
    assert compiler_engine.estimate_tokens("") == 0


@pytest.mark.asyncio
async def test_dspy_api_routes(compiler_engine):
    """测试 FastAPI 路由端点端到端正常连通"""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. 探测 stats
        resp = await client.get("/api/v1/dspy/stats")
        assert resp.status_code == 200
        stats_data = resp.json()
        assert "total_compilations" in stats_data

        # 2. 编译请求
        compile_payload = {
            "raw_prompt": "分析日志中的 500 报错并提取错误堆栈。输入: log_content。输出: error_stack, root_cause。",
            "signature_name": "LogDiagnosticsSignature",
            "max_few_shot": 1,
            "strict_typing": True,
            "anti_hallucination_gate": True,
        }
        compile_resp = await client.post("/api/v1/dspy/compile", json=compile_payload)
        assert compile_resp.status_code == 200
        data = compile_resp.json()
        assert data["contract_status"] == "PASS"
        assert "LogDiagnosticsSignature" in data["compiled_prompt"]
        assert data["original_token_count"] > 0

        # 3. 校验请求
        verify_resp = await client.post("/api/v1/dspy/verify", json=compile_payload)
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()
        assert verify_data["status"] in ["PASS", "PARTIAL"]

        # 4. 重置指标
        reset_resp = await client.post("/api/v1/dspy/reset-stats")
        assert reset_resp.status_code == 200
        assert reset_resp.json()["status"] == "ok"
