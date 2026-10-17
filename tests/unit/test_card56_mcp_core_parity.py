# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Card-56: FastMCP Core Tooling Parity & Zero-Dangling Tri-Closing.

Validates that FastMCP exposes all core capabilities:
1. openviking_valet_handover & openviking_valet_ticket_status
2. openviking_dspy_compile
3. openviking_skill_zip
4. openviking_tokenshift_compress
5. openviking_memory_purity_report
6. openviking_retry_dead_letter
"""

import pytest
import re
from openviking.server.mcp_endpoint import (
    openviking_valet_handover,
    openviking_valet_ticket_status,
    openviking_dspy_compile,
    openviking_skill_zip,
    openviking_tokenshift_compress,
    openviking_memory_purity_report,
    openviking_retry_dead_letter,
)


@pytest.mark.asyncio
async def test_mcp_valet_tools():
    """Verify valet handover and ticket status tools through FastMCP interface."""
    res = await openviking_valet_handover(
        uri="viking://resources/mcp_test_doc.md",
        content="# Test Document\n\nLong memory content for asynchronous valet ingestion.",
        source="mcp",
        caller="TestAgent",
    )
    assert "Valet Ingestion Ticket Issued" in res
    assert "Target URI: viking://resources/mcp_test_doc.md" in res
    assert "Status: accepted" in res

    # Extract ticket ID
    m = re.search(r"Ticket ID:\s*([a-zA-Z0-9_\-]+)", res)
    assert m is not None, f"Ticket ID not found in: {res}"
    ticket_id = m.group(1)

    # Check status tool
    status_res = await openviking_valet_ticket_status(ticket_id)
    assert ticket_id in status_res
    assert "Target URI: viking://resources/mcp_test_doc.md" in status_res
    assert "Status:" in status_res


@pytest.mark.asyncio
async def test_mcp_dspy_compile_tool():
    """Verify DSPy prompt compilation tool through FastMCP."""
    raw_prompt = """
    输入字段: query, context
    输出字段: answer
    Objective: Answer user question accurately based on context.
    """
    res = await openviking_dspy_compile(
        raw_prompt=raw_prompt,
        task_objective="Answer user query",
        signature_name="QASignature",
    )
    assert "DSPy Prompt Compilation" in res
    assert "QASignature" in res
    assert "query" in res
    assert "answer" in res


@pytest.mark.asyncio
async def test_mcp_skill_zip_tool():
    """Verify SkillZip contractual compression tool through FastMCP."""
    skill = """
    # Interface
    - tool_a
    - tool_b

    # Workflow
    1. Step one
    2. Step two

    # Contracts
    - Invariant: Never use green in UI
    - Invariant: Always test before commit

    # Evidence
    - Automated tests pass
    """
    res = await openviking_skill_zip(skill)
    assert "SkillZip Compression Result" in res
    assert "Contract Fidelity: 1.0" in res
    assert "Never use green in UI" in res


@pytest.mark.asyncio
async def test_mcp_tokenshift_compress_tool():
    """Verify TokenShift AST code folding tool through FastMCP."""
    py_code = """
def calculate_metrics(values: list[float]) -> dict:
    '''Calculate statistical metrics for given values.'''
    total = sum(values)
    mean = total / len(values) if values else 0.0
    return {"mean": mean, "count": len(values)}
"""
    res = await openviking_tokenshift_compress(
        code=py_code,
        language="python",
        mode="outline",
    )
    assert "TokenShift Code Compression" in res
    assert "Language: python" in res
    assert "Syntax Valid: True" in res
    assert "def calculate_metrics" in res


@pytest.mark.asyncio
async def test_mcp_memory_purity_report_tool():
    """Verify Memory Purity report tool through FastMCP."""
    res = await openviking_memory_purity_report()
    assert "OpenViking Memory Purity & Anti-Entropy Report" in res
    assert "Purity Health Score:" in res
    assert "Signal-to-Noise Ratio" in res
    assert "Cognitive Conflict Rate" in res


@pytest.mark.asyncio
async def test_mcp_retry_dead_letter_tool():
    """Verify QueueFS dead letter retry tool through FastMCP."""
    from openviking.storage.queuefs.dlq_manager import DLQManager

    dlq = DLQManager.get_instance()
    test_id = dlq.record_dead_letter(
        queue_name="test_queue",
        msg_id="test_msg_999",
        payload={"task": "test"},
        error_type="TEST_ERROR",
        error_message="Test unprocessable message",
        uri="viking://test/error",
    )
    assert test_id > 0

    res = await openviking_retry_dead_letter(test_id)
    assert f"#{test_id}" in res
