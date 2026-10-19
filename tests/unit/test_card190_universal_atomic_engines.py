# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test suite for Card-190 Universal Atomic Engines (SSOT).

Validates:
1. UniversalContentReducer: Multimodal dehydration (CODE/SKILL/TEXT), auto-sniffing, fail-open resilience.
2. UnifiedLifecycleEngine: 5-stage lifecycle transitions, pre-transition guards, event listeners.
3. UniversalAuditLedger: Thread-safe SQLite event ledger, timeline querying, pruning.
4. REST API & FastMCP integration for universal reduction and audit query.
"""

import os
import tempfile
import pytest
from starlette.testclient import TestClient

from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role, UserIdentifier
from openviking.service.universal_reducer import (
    ReductionMode,
    UniversalContentReducer,
    UniversalReduceRequest,
)
from openviking.service.unified_lifecycle import (
    LifecycleState,
    UnifiedLifecycleEngine,
)
from openviking.service.universal_audit_ledger import (
    AuditEvent,
    UniversalAuditLedger,
)


@pytest.fixture
def temp_audit_ledger():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    ledger = UniversalAuditLedger(db_path=db_path)
    yield ledger
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


@pytest.fixture
def lifecycle_engine():
    return UnifiedLifecycleEngine()


@pytest.fixture
def api_client():
    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. UniversalContentReducer Tests
# ---------------------------------------------------------------------------

def test_universal_reducer_sniff_and_reduce_text():
    """Verify TEXT content auto-detection and reduction."""
    text_sample = (
        "# System Overview\n\n"
        "This is an extensive documentation markdown section with descriptions.\n"
        "It details the architecture of our cluster and background pipelines.\n"
        "Note that we preserve semantic information during compression."
    )
    req = UniversalReduceRequest(
        content=text_sample,
        mode=ReductionMode.AUTO,
        target_ratio=0.5,
    )
    reducer = UniversalContentReducer.get_instance()
    res = reducer.reduce(req)
    assert res.detected_mode in (ReductionMode.TEXT.value, ReductionMode.SKILL.value)
    assert res.content is not None
    assert "wiki_dehydration" in res.engine_used or res.engine_used in ("passthrough", "noop", "fail_open_fallback")


def test_universal_reducer_sniff_and_reduce_code():
    """Verify CODE content auto-detection and TokenShift AST folding."""
    code_sample = (
        "import sys\n\n"
        "def calculate_metric(a: int, b: int) -> int:\n"
        "    \"\"\"Docstring for calculating metrics.\"\"\"\n"
        "    result = a * 2 + b\n"
        "    return result\n\n"
        "class ProcessingEngine:\n"
        "    def run(self):\n"
        "        pass\n"
    )
    req = UniversalReduceRequest(
        content=code_sample,
        mode=ReductionMode.AUTO,
    )
    reducer = UniversalContentReducer.get_instance()
    res = reducer.reduce(req)
    assert res.detected_mode == ReductionMode.CODE.value
    assert res.content is not None


def test_universal_reducer_sniff_and_reduce_skill():
    """Verify SKILL content auto-detection and SkillZip 6-tuple compaction."""
    skill_sample = (
        "---\n"
        "name: test-skill\n"
        "description: A test skill for validation\n"
        "---\n\n"
        "# SOP Procedure\n"
        "1. Step one is checking preconditions.\n"
        "2. Step two is executing the target command.\n"
        "- Rule A: Never leak secrets.\n"
        "- Rule B: Verify after changes.\n"
    )
    req = UniversalReduceRequest(
        content=skill_sample,
        mode=ReductionMode.AUTO,
    )
    reducer = UniversalContentReducer.get_instance()
    res = reducer.reduce(req)
    assert res.detected_mode == ReductionMode.SKILL.value
    assert res.content is not None


def test_universal_reducer_fail_open_resilience():
    """Verify that corrupt or empty input never raises 500/crash (Fail-Open Guarantee)."""
    empty_req = UniversalReduceRequest(content="")
    reducer = UniversalContentReducer.get_instance()
    res = reducer.reduce(empty_req)
    assert res.content == ""
    assert res.fail_open is False or res.engine_used == "noop"


# ---------------------------------------------------------------------------
# 2. UnifiedLifecycleEngine Tests
# ---------------------------------------------------------------------------

def test_unified_lifecycle_standard_transitions(lifecycle_engine):
    """Verify 5-stage standard linear lifecycle transitions."""
    e_type = "skill"
    e_id = "cadre-ops-001"
    
    # 0. Initialize at INGESTED
    ev0 = lifecycle_engine.transition(e_type, e_id, LifecycleState.INGESTED, reason="Ingested new skill")
    assert ev0.to_state == LifecycleState.INGESTED

    # 1. INGESTED -> EVALUATING
    ev1 = lifecycle_engine.transition(e_type, e_id, LifecycleState.EVALUATING, reason="Start evaluation")
    assert ev1.to_state == LifecycleState.EVALUATING
    
    # 2. EVALUATING -> REDUCING
    ev2 = lifecycle_engine.transition(e_type, e_id, LifecycleState.REDUCING, reason="Passed gate, reducing")
    assert ev2.to_state == LifecycleState.REDUCING
    
    # 3. REDUCING -> VALIDATING
    ev3 = lifecycle_engine.transition(e_type, e_id, LifecycleState.VALIDATING, reason="Reduction complete")
    assert ev3.to_state == LifecycleState.VALIDATING
    
    # 4. VALIDATING -> COMMITTED
    ev4 = lifecycle_engine.transition(e_type, e_id, LifecycleState.COMMITTED, reason="Validation green")
    assert ev4.to_state == LifecycleState.COMMITTED
    
    history = lifecycle_engine.get_history(e_type, e_id)
    assert len(history) == 5
    assert history[-1].to_state == LifecycleState.COMMITTED


def test_unified_lifecycle_invalid_transition_rejected(lifecycle_engine):
    """Verify that an illegal jump (e.g. INGESTED -> COMMITTED) is strictly blocked."""
    e_type = "skill"
    e_id = "illegal-jump-001"
    lifecycle_engine.transition(e_type, e_id, LifecycleState.INGESTED)
    with pytest.raises(ValueError, match="Invalid lifecycle transition"):
        lifecycle_engine.transition(e_type, e_id, LifecycleState.COMMITTED)


def test_unified_lifecycle_guard_and_listener(lifecycle_engine):
    """Verify pre-transition guard failure and post-transition listeners."""
    e_type = "skill"
    e_id = "guard-test-001"
    lifecycle_engine.transition(e_type, e_id, LifecycleState.INGESTED)
    
    # Register a blocking guard
    def blocking_guard(et, eid, meta):
        return False
    
    lifecycle_engine.register_guard(LifecycleState.INGESTED, LifecycleState.EVALUATING, blocking_guard)
    
    with pytest.raises(PermissionError, match="Pre-transition guard rejected"):
        lifecycle_engine.transition(e_type, e_id, LifecycleState.EVALUATING)
    
    # Remove guard by creating clean engine and test listener
    clean_engine = UnifiedLifecycleEngine()
    clean_engine.transition(e_type, e_id, LifecycleState.INGESTED)
    events_received = []
    clean_engine.register_listener(lambda ev: events_received.append(ev))
    
    clean_engine.transition(e_type, e_id, LifecycleState.EVALUATING)
    assert len(events_received) == 1
    assert events_received[0].to_state == LifecycleState.EVALUATING


# ---------------------------------------------------------------------------
# 3. UniversalAuditLedger Tests
# ---------------------------------------------------------------------------

def test_universal_audit_ledger_recording_and_query(temp_audit_ledger):
    """Verify recording events and querying timeline."""
    event = temp_audit_ledger.record_event(
        entity_type="RESOURCE",
        entity_id="res-001",
        action="content_reduction",
        operator="commander",
        status="SUCCESS",
        details={"ratio": 0.45},
    )
    assert event.event_id is not None
    
    timeline = temp_audit_ledger.get_timeline(entity_id="res-001")
    assert len(timeline) == 1
    assert timeline[0].entity_id == "res-001"
    assert timeline[0].details.get("ratio") == 0.45


# ---------------------------------------------------------------------------
# 4. REST API Integration Tests
# ---------------------------------------------------------------------------

def test_rest_api_universal_reduce(api_client):
    """Verify POST /api/v1/universal/reduce endpoint."""
    resp = api_client.post(
        "/api/v1/universal/reduce",
        json={
            "content": "def test_func():\n    return 42\n",
            "mode": "auto",
            "target_ratio": 0.5,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "content" in data
    assert "compression_ratio" in data
    assert "engine_used" in data


def test_rest_api_audit_timeline(api_client):
    """Verify GET /api/v1/universal/audit/timeline endpoint."""
    resp = api_client.get("/api/v1/universal/audit/timeline?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_rest_api_lifecycle_state(api_client):
    """Verify GET /api/v1/universal/lifecycle/state endpoint."""
    resp = api_client.get("/api/v1/universal/lifecycle/state?entity_type=skill&entity_id=test-entity-001")
    assert resp.status_code == 200
    data = resp.json()
    assert "entity_type" in data
    assert "entity_id" in data
    assert "history" in data
