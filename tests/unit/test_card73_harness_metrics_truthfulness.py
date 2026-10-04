# -*- coding: utf-8 -*-
"""Unit tests for Card-73: Real engine stats connection and elimination of fake 99.1% AST gate rate.

Verifies:
1. get_harness_metrics connects directly to WikiDehydrationEngine & DSPyCompilerEngine.
2. Zero-sample state returns honest None for rates (no fake 99.1% or 48.5% mock data).
3. Real execution immediately reflects truthful token_retention_rate and compilation_accuracy.
4. Bulkhead fault isolation handles engine exceptions gracefully without 500.
"""

import pytest
from unittest.mock import MagicMock, patch

from openviking.server.identity import RequestContext, Role
from openviking.server.routers.system_harness import get_harness_metrics
from openviking.service.dspy_compiler_engine import DSPyCompilerEngine
from openviking.service.dspy_compiler_types import DSPyCompileRequest
from openviking.service.wiki_dehydration_engine import (
    DehydrationRequest,
    WikiDehydrationEngine,
)
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def mock_ctx():
    return RequestContext(user=UserIdentifier.the_default_user(), role=Role.USER)


@pytest.fixture(autouse=True)
def reset_engines():
    """Reset singleton engine stats before each test."""
    dehy = WikiDehydrationEngine.get_instance()
    dehy._total_documents = 0
    dehy._total_tokens_saved = 0
    dehy._sum_compression_ratio = 0.0
    dehy._total_latency_ms = 0.0

    dspy = DSPyCompilerEngine.get_instance()
    dspy.reset_stats()
    yield


@pytest.mark.asyncio
async def test_zero_sample_metrics_truthfulness(mock_ctx):
    """Verify 0-sample state returns truthful None instead of fake percentages."""
    res = await get_harness_metrics(window="24h", _ctx=mock_ctx)
    assert res.status_code == 200

    import json
    data = json.loads(res.body.decode("utf-8"))

    # LLMLingua-2
    llm = data["llmlingua"]
    assert llm["token_retention_rate"] is None
    assert llm["total_documents"] == 0
    assert "microsoft/llmlingua-2" in llm["active_engine"] or "syntactic-pruner" in llm["active_engine"]
    assert llm["status"] in ("ready", "idle")

    # DSPy
    dspy = data["dspy"]
    assert dspy["compilation_accuracy"] is None
    assert dspy["total_compilations"] == 0
    assert dspy["status"] == "ready"
    assert dspy["avg_latency_ms"] == 0.0

    # AST Gate must NOT be the fake 99.1% calculated from HTTP status codes!
    assert llm["ast_gate_rate"] != 99.1
    assert dspy["ast_gate_rate"] != 99.1


@pytest.mark.asyncio
async def test_real_execution_updates_harness_metrics(mock_ctx):
    """Verify actual execution of LLMLingua-2 and DSPy immediately flows into harness metrics."""
    # 1. Run genuine dehydration
    dehy = WikiDehydrationEngine.get_instance()
    req = DehydrationRequest(
        content="# Overview\n\nThis is a verbose introductory sentence with repeated redundant terms.\n"
    )
    dehy_res = dehy.dehydrate(req)
    assert dehy_res.tokens_saved >= 0

    # 2. Run genuine DSPy compile
    dspy = DSPyCompilerEngine.get_instance()
    compile_req = DSPyCompileRequest(
        raw_prompt="输入参数: code: str。输出参数: analysis: str。请检查并发缺陷。",
        signature_name="ConcurrencyAudit",
    )
    dspy_res = dspy.compile(compile_req)
    assert dspy_res.contract_status == "PASS"

    # 3. Query harness metrics
    res = await get_harness_metrics(window="24h", _ctx=mock_ctx)
    import json
    data = json.loads(res.body.decode("utf-8"))

    llm = data["llmlingua"]
    assert llm["total_documents"] == 1
    assert llm["token_retention_rate"] is not None
    assert llm["token_retention_rate"] > 0
    assert llm["status"] == "healthy"
    assert llm["avg_latency_ms"] > 0

    dspy_data = data["dspy"]
    assert dspy_data["total_compilations"] == 1
    assert dspy_data["compilation_accuracy"] == 100.0
    assert dspy_data["status"] == "healthy"
    assert dspy_data["avg_latency_ms"] > 0


@pytest.mark.asyncio
async def test_bulkhead_fault_isolation(mock_ctx):
    """Verify bulkhead isolation: engine failure results in offline status without 500 error."""
    with patch(
        "openviking.service.wiki_dehydration_engine.WikiDehydrationEngine.get_instance",
        side_effect=RuntimeError("GPU memory explosion"),
    ):
        res = await get_harness_metrics(window="24h", _ctx=mock_ctx)
        assert res.status_code == 200

        import json
        data = json.loads(res.body.decode("utf-8"))
        assert data["llmlingua"]["status"] == "offline"
        assert data["llmlingua"]["active_engine"] == "unavailable"
        assert data["llmlingua"]["token_retention_rate"] is None
