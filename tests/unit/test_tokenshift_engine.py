# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test suite for PointFive TokenShift AST-Aware Code Compression Engine.

Fulfills BLUEPRINT.md Topic 5 Wheel #3 (AST-Aware Code Compression).
Verifies:
  1. Python L0 Outline mode (signatures & docstrings only, body elided)
  2. Python L1 Skeleton mode (control flow if/try/for preserved)
  3. Python L2 Compact mode (lossless whitespace & comment stripping)
  4. Syntax validation gate & graceful fallback
  5. TypeScript interface & function protection
  6. AST symbol & signature extraction (protect endpoint)
  7. RESTful API end-to-end data flow & telemetry stats
"""

import ast
import pytest
from fastapi.testclient import TestClient

from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role, UserIdentifier
from openviking.service.tokenshift_engine import TokenShiftEngine, TokenShiftTelemetry
from openviking.service.tokenshift_types import (
    TokenShiftLanguage,
    TokenShiftMode,
    TokenShiftRequest,
)

SAMPLE_PYTHON_CODE = '''# Sample Service Implementation
import os
from typing import Optional, List

class DataProcessor:
    """Core processor for high-frequency trading data."""

    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.cache = {}

    def process_records(self, records: List[dict]) -> int:
        """Process incoming financial records and return processed count."""
        count = 0
        if not records:
            return 0

        for r in records:
            try:
                val = r.get("price", 0.0) * 1.05
                self.cache[r.get("id")] = val
                count += 1
            except Exception as e:
                print(f"Error processing record: {e}")
                continue

        return count
'''

SAMPLE_TS_CODE = '''import React from 'react';

export interface UserProfile {
    id: string;
    username: string;
    roles: string[];
}

export const fetchProfile = async (id: string): Promise<UserProfile> => {
    // Internal network call
    const res = await fetch(`/api/users/${id}`);
    if (!res.ok) {
        throw new Error("Failed to load user");
    }
    return res.json();
};
'''


@pytest.fixture(autouse=True)
def reset_telemetry():
    TokenShiftTelemetry.get_instance().reset()
    yield
    TokenShiftTelemetry.get_instance().reset()


def test_tokenshift_python_outline():
    """Verify L0 Outline compresses to signatures and docstrings with 100% AST pass."""
    req = TokenShiftRequest(
        code=SAMPLE_PYTHON_CODE,
        language=TokenShiftLanguage.PYTHON,
        mode=TokenShiftMode.OUTLINE,
        preserve_docstrings=True,
    )
    res = TokenShiftEngine.compress(req)

    assert res.syntax_validation.valid is True
    assert res.reduction_ratio > 0.30
    assert "class DataProcessor" in res.compressed_code
    assert "def process_records" in res.compressed_code
    assert "Core processor for high-frequency" in res.compressed_code
    # Implementation details should be folded into ...
    assert "self.cache = {}" not in res.compressed_code
    assert "val = r.get" not in res.compressed_code

    # Assert AST parses without syntax errors
    tree = ast.parse(res.compressed_code)
    assert len(tree.body) >= 2


def test_tokenshift_python_skeleton():
    """Verify L1 Skeleton preserves control flow (if/for/try/return)."""
    req = TokenShiftRequest(
        code=SAMPLE_PYTHON_CODE,
        language=TokenShiftLanguage.PYTHON,
        mode=TokenShiftMode.SKELETON,
        preserve_docstrings=True,
    )
    res = TokenShiftEngine.compress(req)

    assert res.syntax_validation.valid is True
    assert res.reduction_ratio > 0.15
    # Control flow keywords must be preserved
    assert "if not records:" in res.compressed_code
    assert "return 0" in res.compressed_code
    assert "for r in records:" in res.compressed_code
    assert "try:" in res.compressed_code
    assert "return count" in res.compressed_code

    # Assert AST passes validation
    ast.parse(res.compressed_code)


def test_tokenshift_python_compact():
    """Verify L2 Compact removes redundant noise while preserving 100% logic."""
    code_with_noise = '''
# Redundant comment 1
def calculate_sum(a: int, b: int) -> int:


    # Calculate result
    result = a + b

    return result
'''
    req = TokenShiftRequest(
        code=code_with_noise,
        language=TokenShiftLanguage.PYTHON,
        mode=TokenShiftMode.COMPACT,
    )
    res = TokenShiftEngine.compress(req)

    assert res.syntax_validation.valid is True
    assert "def calculate_sum" in res.compressed_code
    assert "result = a + b" in res.compressed_code
    assert "return result" in res.compressed_code


def test_tokenshift_syntax_validation_gate():
    """Verify broken code is flagged by syntax gate and safely returned."""
    broken_code = "def unclosed_function(a: int\n    print('broken')"
    req = TokenShiftRequest(
        code=broken_code,
        language=TokenShiftLanguage.PYTHON,
        mode=TokenShiftMode.OUTLINE,
    )
    res = TokenShiftEngine.compress(req)

    assert res.syntax_validation.valid is False
    assert res.syntax_validation.error is not None
    # Safe fallback to original code
    assert res.compressed_code == broken_code


def test_tokenshift_typescript_compression():
    """Verify TypeScript interface and signatures are preserved."""
    req = TokenShiftRequest(
        code=SAMPLE_TS_CODE,
        language=TokenShiftLanguage.TYPESCRIPT,
        mode=TokenShiftMode.OUTLINE,
    )
    res = TokenShiftEngine.compress(req)

    assert res.syntax_validation.valid is True
    assert "export interface UserProfile" in res.compressed_code
    assert "username: string;" in res.compressed_code
    assert "export const fetchProfile" in res.compressed_code


def test_tokenshift_protect_symbols():
    """Verify protect endpoint extracts AST symbols and signatures."""
    res = TokenShiftEngine.protect(SAMPLE_PYTHON_CODE, TokenShiftLanguage.PYTHON)

    assert res.language == "python"
    assert "DataProcessor" in res.protected_symbols
    assert "process_records" in res.protected_symbols
    assert any("def process_records" in sig for sig in res.frozen_signatures)
    assert res.ast_nodes_identified >= 3


def test_tokenshift_rest_api():
    """Verify FastAPI router endpoints (/compress, /protect, /stats, /reset-stats)."""
    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )

    client = TestClient(app)

    # 1. Test POST /compress
    comp_resp = client.post(
        "/api/v1/tokenshift/compress",
        json={
            "code": SAMPLE_PYTHON_CODE,
            "language": "python",
            "mode": "outline",
            "preserve_docstrings": True,
        },
    )
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert comp_data["reduction_ratio"] > 0.20
    assert comp_data["syntax_validation"]["valid"] is True

    # 2. Test POST /protect
    prot_resp = client.post(
        "/api/v1/tokenshift/protect",
        json={"code": SAMPLE_PYTHON_CODE, "language": "python"},
    )
    assert prot_resp.status_code == 200
    prot_data = prot_resp.json()
    assert "DataProcessor" in prot_data["protected_symbols"]

    # 3. Test GET /stats
    stats_resp = client.get("/api/v1/tokenshift/stats")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()
    assert stats_data["total_calls"] >= 1
    assert stats_data["total_tokens_saved"] > 0

    # 4. Test POST /reset-stats
    reset_resp = client.post("/api/v1/tokenshift/reset-stats")
    assert reset_resp.status_code == 200
    assert reset_resp.json()["status"] == "ok"
