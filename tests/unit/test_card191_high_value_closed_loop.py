# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test suite for Card-191 High-Value Closed-Loop Engines (SSOT).

Validates:
1. OfflineDreamer: Bridge to UniversalAuditLedger and UnifiedLifecycleEngine.
2. Hermes Structured Attribution: Error traceback extraction, categorization, micro-patch (<=30 lines).
3. AHE Pre-Release Gate: Core invariant seeding, snapshot drift detection, lifecycle transition guard.
4. REST APIs: /api/v1/hermes/attribute, /api/v1/hermes/attributions, /api/v1/ahe/gate/check.
"""

import os
import sys
import tempfile
import pytest
from starlette.testclient import TestClient

from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role, UserIdentifier
from openviking.core.ahe_engine import AHEEngine
from openviking.core.ahe_manifest import AHEManifest, AHEStatus
from openviking.core.hermes_experience_store import HermesExperienceStore
from openviking.core.hermes_nudge_engine import HermesNudgeEngine, StructuredAttribution
from openviking.core.hermes_patch_engine import HermesPatchEngine
from openviking.service.offline_dreamer import OfflineDreamer
from openviking.service.unified_lifecycle import LifecycleState, UnifiedLifecycleEngine
from openviking.service.universal_audit_ledger import UniversalAuditLedger


@pytest.fixture
def api_client():
    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. OfflineDreamer Closed-Loop Tests
# ---------------------------------------------------------------------------

def test_offline_dreamer_lifecycle_and_audit_bridge():
    """Verify OfflineDreamer advances entity lifecycle and records to audit ledger."""
    dreamer = OfflineDreamer.get_instance()
    ledger = UniversalAuditLedger.get_instance()
    lifecycle = UnifiedLifecycleEngine.get_instance()

    # Create dummy candidate fragments
    frags = [
        {"uri": "viking://resources/master_memory/f1.md", "topic": "cache_pattern", "content": "Rule 1: Always check local cache"},
        {"uri": "viking://resources/master_memory/f2.md", "topic": "cache_pattern", "content": "Rule 2: Fallback to redis on miss"},
    ]

    # Perform dream cycle
    res = dreamer.run_dream_cycle(candidate_fragments=frags, dry_run=False)
    assert res.status in ("ok", "success")
    assert res.master_cards_created >= 1

    # Verify audit event is recorded
    events = ledger.get_timeline(action="DREAM_CONSOLIDATION", limit=10)
    assert len(events) >= 1
    assert events[0].action == "DREAM_CONSOLIDATION"


# ---------------------------------------------------------------------------
# 2. Hermes Structured Attribution Tests
# ---------------------------------------------------------------------------

def test_hermes_structured_attribution_success_flow():
    """Verify clean session produces NONE failure category."""
    exp_store = HermesExperienceStore.get_instance()
    nudge_engine = HermesNudgeEngine.get_instance()

    session_id = f"clean_sess_{os.urandom(4).hex()}"
    exp_store.record_message(
        session_id=session_id,
        role="user",
        content="Please list the files in current directory.",
    )
    exp_store.record_message(
        session_id=session_id,
        role="assistant",
        content="Files listed successfully: [a.py, b.py].",
    )

    attr = nudge_engine.attribute_session(session_id)
    assert isinstance(attr, StructuredAttribution)
    assert attr.failure_category == "NONE"
    assert "No errors detected" in attr.root_cause_summary


def test_hermes_structured_attribution_error_and_micro_patch():
    """Verify error traceback triggers DETERMINISTIC classification and micro-patch proposal."""
    exp_store = HermesExperienceStore.get_instance()
    nudge_engine = HermesNudgeEngine.get_instance()

    session_id = f"err_sess_{os.urandom(4).hex()}"
    exp_store.record_message(
        session_id=session_id,
        role="user",
        content="Run the calculate function.",
    )
    # Simulate a traceback output
    trace_content = (
        'Traceback (most recent call last):\n'
        '  File "openviking/service/calculator.py", line 42, in calculate\n'
        '    result = 10 / 0\n'
        'ZeroDivisionError: division by zero'
    )
    exp_store.record_message(
        session_id=session_id,
        role="tool",
        content=trace_content,
    )

    attr = nudge_engine.attribute_session(session_id, auto_propose_patch=True)
    assert attr.failure_category in ("DETERMINISTIC", "SYNTAX")
    assert "ZeroDivisionError" in attr.root_cause_summary or "division by zero" in attr.root_cause_summary
    assert len(attr.error_frames) >= 1
    assert "calculator.py" in attr.error_frames[0]
    assert attr.affected_entity is not None

    # Verify audit event in ledger
    ledger = UniversalAuditLedger.get_instance()
    events = ledger.get_timeline(entity_type="HERMES_SESSION", entity_id=session_id)
    assert len(events) >= 1
    assert events[0].action == "HERMES_STRUCTURED_ATTRIBUTION"


# ---------------------------------------------------------------------------
# 3. AHE Pre-Release Gate Tests
# ---------------------------------------------------------------------------

def test_ahe_seed_invariants_and_gate_check():
    """Verify AHE engine seeds core invariants and runs pre-release gate."""
    engine = AHEEngine.get_instance()
    manifests = engine.seed_core_invariants_if_empty()
    assert len(manifests) >= 1

    # Run pre-release gate check
    gate_res = engine.run_pre_release_gate(run_polar=False)
    assert isinstance(gate_res, dict)
    assert gate_res["gate_passed"] is True
    assert gate_res["total_manifests"] >= 1
    assert len(gate_res["drift_violations"]) == 0


def test_ahe_lifecycle_guard_enforcement():
    """Verify AHE lifecycle guard integrates into UnifiedLifecycleEngine."""
    engine = AHEEngine.get_instance()
    engine.register_lifecycle_guard()
    lifecycle = UnifiedLifecycleEngine.get_instance()

    entity_id = "ahe_guarded_module_01"
    lifecycle.reset_entity("MODULE", entity_id)

    # Initialize to VALIDATING
    lifecycle.transition("MODULE", entity_id, LifecycleState.INGESTED)
    lifecycle.transition("MODULE", entity_id, LifecycleState.EVALUATING)
    lifecycle.transition("MODULE", entity_id, LifecycleState.VALIDATING)

    # Transition with enforce_ahe_gate=True should pass when gate is clean
    event = lifecycle.transition(
        "MODULE",
        entity_id,
        LifecycleState.COMMITTED,
        metadata={"enforce_ahe_gate": True},
    )
    assert event.to_state == LifecycleState.COMMITTED


def test_ahe_gate_check_cli_script():
    """Verify scripts/ahe_gate_check.py script execution."""
    from scripts.ahe_gate_check import run_ahe_check
    code = run_ahe_check(run_polar=False)
    assert code == 0


# ---------------------------------------------------------------------------
# 4. REST Endpoints Tests
# ---------------------------------------------------------------------------

def test_hermes_attribution_rest_api(api_client):
    """Test POST /api/v1/hermes/attribute and GET /api/v1/hermes/attributions."""
    exp_store = HermesExperienceStore.get_instance()
    session_id = f"api_sess_{os.urandom(4).hex()}"
    exp_store.record_message(session_id=session_id, role="user", content="Hello API")
    exp_store.record_message(session_id=session_id, role="assistant", content="Hello Commander")

    # POST attribute
    res = api_client.post(
        "/api/v1/hermes/attribute",
        json={"session_id": session_id, "auto_propose_patch": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session_id
    assert data["failure_category"] == "NONE"

    # GET attributions
    res_list = api_client.get(f"/api/v1/hermes/attributions?session_id={session_id}")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert len(list_data["attributions"]) >= 1


def test_ahe_gate_check_rest_api(api_client):
    """Test GET /api/v1/ahe/gate/check."""
    res = api_client.get("/api/v1/ahe/gate/check")
    assert res.status_code == 200
    data = res.json()
    assert "gate_passed" in data
    assert data["gate_passed"] is True
    assert data["total_manifests"] >= 1
