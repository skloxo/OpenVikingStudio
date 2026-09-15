# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Failure Classification & Anti-Loop Barrier with MultiTenantRuntimeContext.
(Card-Harness-DeepSeek-AgentScope-SpecDriven - v1.5.03)

Verifies:
1. Transient failure backoff & retry limits.
2. Deterministic failure anti-loop barrier & reflection prompt.
3. Fatal failure immediate halt.
4. MultiTenantRuntimeContext role-based access & attributes.
"""

import pytest

from openviking.core.failure_classifier import (
    ClassificationDecision,
    FailureCategory,
    FailureClassifier,
    MultiTenantRuntimeContext,
)


def test_transient_failure_backoff_and_retry_limit():
    """Test transient errors trigger exponential backoff and stop after max retries."""
    classifier = FailureClassifier(max_transient_retries=3, base_backoff_sec=0.1)

    tool_name = "http_request"
    args = {"url": "https://api.internal/data"}

    # Attempt 1
    d1 = classifier.evaluate(tool_name, args, "Request timeout (503 Service Unavailable)")
    assert d1.category == FailureCategory.TRANSIENT
    assert d1.can_retry is True
    assert d1.backoff_sec == 0.10

    # Attempt 2
    d2 = classifier.evaluate(tool_name, args, "429 Rate limit exceeded")
    assert d2.category == FailureCategory.TRANSIENT
    assert d2.can_retry is True
    assert d2.backoff_sec == 0.20

    # Attempt 3
    d3 = classifier.evaluate(tool_name, args, "Connection reset by peer")
    assert d3.category == FailureCategory.TRANSIENT
    assert d3.can_retry is True
    assert d3.backoff_sec == 0.40

    # Attempt 4 (Exceeds max retries -> no more retry)
    d4 = classifier.evaluate(tool_name, args, "Request timeout")
    assert d4.category == FailureCategory.TRANSIENT
    assert d4.can_retry is False
    assert d4.reflection_prompt is not None
    assert "exhausted all 3 transient retries" in d4.reflection_prompt


def test_deterministic_failure_anti_loop_barrier():
    """Test deterministic errors activate Anti-Loop Barrier and inject reflection."""
    classifier = FailureClassifier()

    tool_name = "query_database"
    args = {"table": "non_existent_table", "filter": "id=1"}

    # Deterministic failure (syntax error / 404 / missing table)
    decision = classifier.evaluate(
        tool_name,
        args,
        "Table 'non_existent_table' not found (404 Not Found)",
    )

    assert decision.category == FailureCategory.DETERMINISTIC
    assert decision.can_retry is False
    assert decision.reflection_prompt is not None
    assert "[Anti-Loop Barrier]" in decision.reflection_prompt
    assert "Repeating the identical call is blocked" in decision.reflection_prompt

    # Verify anti-loop barrier actively blocks identical duplicate call
    assert classifier.is_blocked(tool_name, args) is True

    # Different arguments for the same tool are not blocked
    different_args = {"table": "valid_table", "filter": "id=1"}
    assert classifier.is_blocked(tool_name, different_args) is False


def test_fatal_failure_immediate_halt():
    """Test fatal errors halt execution immediately without retry."""
    classifier = FailureClassifier()

    tool_name = "execute_code"
    args = {"code": "import os; os.system('cat /etc/shadow')"}

    decision = classifier.evaluate(
        tool_name,
        args,
        "Security violation: sandbox escape attempt detected",
    )

    assert decision.category == FailureCategory.FATAL
    assert decision.can_retry is False
    assert "Fatal error detected" in decision.reason
    assert classifier.is_blocked(tool_name, args) is True


def test_multitenant_runtime_context():
    """Test enterprise multi-tenant context attributes and role checking."""
    ctx = MultiTenantRuntimeContext(
        tenant_id="tenant_alpha",
        user_id="alice",
        session_id="sess_42",
        roles=["analyst", "developer"],
        attributes={"dept": "quant", "region": "asia"},
        is_admin=False,
    )

    assert ctx.tenant_id == "tenant_alpha"
    assert ctx.user_id == "alice"
    assert ctx.has_role("analyst") is True
    assert ctx.has_role("developer") is True
    assert ctx.has_role("admin") is False
    assert ctx.get_attr("dept") == "quant"
    assert ctx.get_attr("missing", "default_val") == "default_val"

    # Admin bypasses role checks
    admin_ctx = MultiTenantRuntimeContext(
        tenant_id="tenant_sys",
        user_id="root",
        session_id="sess_root",
        is_admin=True,
    )
    assert admin_ctx.has_role("any_random_role") is True
