# -*- coding: utf-8 -*-
# Copyright (c) 2026 OpenViking Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0.

"""
Unit Test Suite for Card-52 (v1.7.6):
Compiler Contract Authenticity, Honest Syntax Validation & Single SSOT Tracking.
First Principles:
1. No False Compliances: Inferred fields must yield PARTIAL contract status.
2. Honest Parser Truth: Non-AST/Unknown languages report valid=False & text_strip_unverified.
3. Pure SQLite SSOT: Vector fast-path count is queried from persistent DB, eliminating memory drift.
"""

import os
import pytest
import sqlite3
from typing import Any, Dict

from openviking.service.dspy_compiler_engine import DSPyCompilerEngine
from openviking.service.dspy_compiler_types import DSPyCompileRequest
from openviking.service.tokenshift_engine import TokenShiftEngine
from openviking.service.tokenshift_types import (
    TokenShiftLanguage,
    TokenShiftMode,
    TokenShiftRequest,
)
from openviking.service.vector_sync_tracker import VectorSyncTracker


@pytest.fixture
def compiler_engine():
    engine = DSPyCompilerEngine.get_instance()
    engine.reset_stats()
    return engine


def test_dspy_contract_authenticity_inferred_vs_explicit(compiler_engine):
    """
    Test 1: Verify DSPy compiler contract status reflects field inference honestly.
    - Inferred fields -> is_inferred=True -> contract_status="PARTIAL"
    - Explicit fields -> is_inferred=False -> contract_status="PASS"
    """
    # 1. Unstructured prompt (Inferred fields)
    unstructured_prompt = "请帮我总结一下今天早盘市场风格偏好，并给出日内交易建议。"
    sig_inferred = compiler_engine.extract_signature(
        raw_prompt=unstructured_prompt,
        custom_name="MarketSummarizer",
    )
    assert sig_inferred.is_inferred is True

    req_inferred = DSPyCompileRequest(
        task_name="MarketSummarizer",
        raw_prompt=unstructured_prompt,
        target_model="mux-flash",
    )
    result_inferred = compiler_engine.compile(req_inferred)
    assert result_inferred.contract_status == "PARTIAL"
    assert result_inferred.signature.is_inferred is True

    # 2. Structured prompt (Explicit field contracts)
    structured_prompt = """
    你是一个严谨的金融量化数据提取器。
    输入参数: Query: 用户自然语言查询, MarketData: 市场行情切片数据
    输出字段: AlphaFactor: 因子计算逻辑, RiskAssessment: 风险暴露分析
    约束要求: 绝对禁止使用未校验的黑盒包。
    """
    sig_explicit = compiler_engine.extract_signature(
        raw_prompt=structured_prompt,
        custom_name="AlphaExtractor",
    )
    assert sig_explicit.is_inferred is False

    req_explicit = DSPyCompileRequest(
        task_name="AlphaExtractor",
        raw_prompt=structured_prompt,
        target_model="mux-flash",
    )
    result_explicit = compiler_engine.compile(req_explicit)
    assert result_explicit.contract_status == "PASS"
    assert result_explicit.signature.is_inferred is False


def test_tokenshift_syntax_honest_validation():
    """
    Test 2: Verify TokenShift reports syntax validation honestly.
    - Supported AST languages (Python, JSON) -> valid=True
    - Non-AST or unsupported languages (Shell, SQL, Custom) -> valid=False, parser="text_strip_unverified"
    """
    # 1. Python AST parsing (Valid)
    py_code = "def calculate_ratio(a: float, b: float) -> float:\n    # Return safe division\n    return a / b if b != 0 else 0.0\n"
    py_req = TokenShiftRequest(
        code=py_code,
        language=TokenShiftLanguage.PYTHON,
        mode=TokenShiftMode.COMPACT,
    )
    py_res = TokenShiftEngine.compress(py_req)
    assert py_res.syntax_validation.valid is True
    assert py_res.syntax_validation.parser == "python_ast"

    # 2. JSON AST parsing (Valid)
    json_text = '{\n  "name": "OpenViking",\n  "status": "active"\n}'
    json_req = TokenShiftRequest(
        code=json_text,
        language=TokenShiftLanguage.JSON,
        mode=TokenShiftMode.COMPACT,
    )
    json_res = TokenShiftEngine.compress(json_req)
    assert json_res.syntax_validation.valid is True
    assert json_res.syntax_validation.parser == "json"

    # 3. Shell script (No AST parser -> Honest report)
    shell_code = "#!/usr/bin/env bash\n# Print system greeting\necho 'Starting OpenViking Studio...'\nexit 0\n"
    shell_req = TokenShiftRequest(
        code=shell_code,
        language=TokenShiftLanguage.SHELL,
        mode=TokenShiftMode.COMPACT,
    )
    shell_res = TokenShiftEngine.compress(shell_req)
    assert shell_res.syntax_validation.valid is False
    assert shell_res.syntax_validation.parser == "text_strip_unverified"
    assert "echo 'Starting OpenViking Studio...'" in shell_res.compressed_code

    # 4. Unknown/Unsupported language -> Honest report
    sql_code = "-- SQL query or proprietary DSL\nSELECT id, name FROM cluster_nodes WHERE status = 'healthy';\n"
    sql_req = TokenShiftRequest(
        code=sql_code,
        language=TokenShiftLanguage.SQL,
        mode=TokenShiftMode.COMPACT,
    )
    sql_res = TokenShiftEngine.compress(sql_req)
    assert sql_res.syntax_validation.valid is False
    assert sql_res.syntax_validation.parser == "text_strip_unverified"


def test_vector_sync_tracker_sqlite_ssot_fast_path(tmp_path):
    """
    Test 3: Verify VectorSyncTracker operates purely on SQLite SSOT.
    - Multiple fast_path marks on same URI do not cause memory count inflation.
    - Account ID isolation is properly observed in fast_path_count queries.
    - Rebooting tracker preserves physical metrics perfectly with zero memory state drift.
    """
    db_file = str(tmp_path / "test_sync_ssot.db")
    tracker = VectorSyncTracker(db_path=db_file)

    # 1. Record pending and multiple fast-path calls for the same URI
    target_uri = "viking://resources/doc_alpha.md"
    tracker.mark_pending(target_uri, account_id="default")
    for _ in range(5):
        tracker.mark_fast_path(target_uri, account_id="default")

    # Metrics fast_path_count must strictly equal 1 (DB row count with fast_path=1)
    metrics_initial = tracker.get_metrics(account_id="default")
    assert metrics_initial["fast_path_count"] == 1
    assert metrics_initial["total_files"] == 1

    # 2. Insert another URI under a different account
    tenant_uri = "viking://resources/tenant_b/doc_beta.md"
    tracker.mark_fast_path(tenant_uri, account_id="tenant_b")

    # Isolated metrics
    default_metrics = tracker.get_metrics(account_id="default")
    tenant_metrics = tracker.get_metrics(account_id="tenant_b")
    all_metrics = tracker.get_metrics()

    assert default_metrics["fast_path_count"] == 1
    assert tenant_metrics["fast_path_count"] == 1
    assert all_metrics["fast_path_count"] == 2

    # 3. Simulate process restart / new instance reading from DB
    rebooted_tracker = VectorSyncTracker(db_path=db_file)
    rebooted_all = rebooted_tracker.get_metrics()
    assert rebooted_all["fast_path_count"] == 2
    assert rebooted_all["total_files"] == 2
