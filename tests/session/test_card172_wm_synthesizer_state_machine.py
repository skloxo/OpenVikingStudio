# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Retina unit tests for Card-172: Working Memory synthesizer state machine."""

import pytest
from openviking.session.wm_synthesizer import WorkingMemorySynthesizer


@pytest.fixture
def sample_wm() -> str:
    return """# Working Memory

## Session Title
Distributed Task Architecture

## Current State
- Initializing microservices
- Database connected

## Task & Goals
- Deploy worker fleet

## Key Facts & Decisions
- Decided Redis 7 on 2026-10-15
- Chosen 5 workers per node
- Retained cluster budget of $500

## Files & Context
- src/worker.py
- config/settings.yaml

## Errors & Corrections
- Fixed memory leak in worker pool

## Open Issues
- Network timeout under high load
"""


class TestWorkingMemoryStateMachine:
    """Test state machine guards, transitions, and anti-regression rules."""

    def test_parse_and_reminders(self, sample_wm: str):
        sections = WorkingMemorySynthesizer.parse_wm_sections(sample_wm)
        assert len(sections) == 7
        assert "## Session Title" in sections
        assert "## Key Facts & Decisions" in sections
        assert "Redis 7 on 2026-10-15" in sections["## Key Facts & Decisions"]

        # Below threshold -> no warnings
        warnings = WorkingMemorySynthesizer.build_wm_section_reminders(sample_wm)
        assert warnings == ""

        # Construct bloated section
        bloated_body = "\n".join(f"- Fact item number {i} with lots of context details" for i in range(30))
        bloated_wm = sample_wm.replace(
            sections["## Key Facts & Decisions"],
            bloated_body
        )
        bloated_warnings = WorkingMemorySynthesizer.build_wm_section_reminders(bloated_wm)
        assert "Key Facts & Decisions" in bloated_warnings
        assert "MUST be consolidated via UPDATE" in bloated_warnings

    def test_recover_ops_from_raw(self):
        raw = (
            '{"Session Title": {"op": "KEEP"}, '
            '"Current State": {"op": "UPDATE", "content": "- Done step 1\\n- Doing step 2"}, '
            '"Errors & Corrections": {"op": "APPEND", "items": ["Error 404 handled"]}}'
        )
        ops = WorkingMemorySynthesizer.recover_ops_from_raw(raw)
        assert ops["Session Title"]["op"] == "KEEP"
        assert ops["Current State"]["op"] == "UPDATE"
        assert "Done step 1" in ops["Current State"]["content"]
        assert ops["Errors & Corrections"]["op"] == "APPEND"
        assert "Error 404 handled" in ops["Errors & Corrections"]["items"]

    def test_append_only_guard(self, sample_wm: str):
        sections = WorkingMemorySynthesizer.parse_wm_sections(sample_wm)
        old_errors = sections["## Errors & Corrections"]

        # If LLM tries UPDATE on append-only section, it forces APPEND of fresh items
        update_op = {
            "op": "UPDATE",
            "content": "- Fixed memory leak in worker pool\n- Added TLS handshake retry",
        }
        guarded = WorkingMemorySynthesizer.enforce_append_only("Errors & Corrections", update_op, old_errors)
        assert guarded["op"] == "APPEND"
        assert guarded["items"] == ["Added TLS handshake retry"]

    def test_key_facts_anchor_protection(self, sample_wm: str):
        sections = WorkingMemorySynthesizer.parse_wm_sections(sample_wm)
        old_facts = sections["## Key Facts & Decisions"]

        # 1. Update that drops all dates/numbers/anchors should be rejected
        hallucinated_update = {
            "op": "UPDATE",
            "content": "- Things are working fine now with new configuration",
        }
        guarded = WorkingMemorySynthesizer.enforce_key_facts_consolidation(hallucinated_update, old_facts)
        # Should be salvaged to APPEND or KEEP, rejecting destructive UPDATE
        assert guarded["op"] in ("APPEND", "KEEP")

        # 2. Update that preserves anchors should pass
        valid_update = {
            "op": "UPDATE",
            "content": "- Decided Redis 7 on 2026-10-15\n- Chosen 5 workers per node and Retained cluster budget of $500",
        }
        valid_guarded = WorkingMemorySynthesizer.enforce_key_facts_consolidation(valid_update, old_facts)
        assert valid_guarded["op"] == "UPDATE"

    def test_files_no_regression_guard(self, sample_wm: str):
        sections = WorkingMemorySynthesizer.parse_wm_sections(sample_wm)
        old_files = sections["## Files & Context"]

        # Dropping src/worker.py while adding src/new_service.py
        lossy_update = {
            "op": "UPDATE",
            "content": "- src/new_service.py\n- config/settings.yaml",
        }
        guarded = WorkingMemorySynthesizer.enforce_files_no_regression(lossy_update, old_files)
        assert guarded["op"] == "APPEND"
        assert any("src/new_service.py" in it for it in guarded["items"])

    def test_title_stability_guard(self, sample_wm: str):
        sections = WorkingMemorySynthesizer.parse_wm_sections(sample_wm)
        old_title = sections["## Session Title"]

        # Stable related update
        related_update = {"op": "UPDATE", "content": "Distributed Architecture V2"}
        assert WorkingMemorySynthesizer.enforce_title_stability(related_update, old_title)["op"] == "UPDATE"

        # Drifting title with 0 overlapping keywords
        drifting_update = {"op": "UPDATE", "content": "Cooking Pasta Bolognese Recipe"}
        assert WorkingMemorySynthesizer.enforce_title_stability(drifting_update, old_title)["op"] == "KEEP"

    def test_open_issues_silently_dropped_restoration(self, sample_wm: str):
        sections = WorkingMemorySynthesizer.parse_wm_sections(sample_wm)
        old_issues = sections["## Open Issues"]

        # LLM emits update that forgot the timeout issue
        dropped_update = {
            "op": "UPDATE",
            "content": "- Newly discovered issue: disk full",
        }
        guarded = WorkingMemorySynthesizer.enforce_open_issues_resolved(dropped_update, old_issues)
        assert guarded["op"] == "UPDATE"
        assert "[silently dropped, restored]" in guarded["content"]
        assert "Network timeout under high load" in guarded["content"]

    def test_multiturn_merge_lifecycle(self, sample_wm: str):
        """Simulate multi-turn session commit state transitions."""
        # Turn 1: append new facts and errors
        t1_ops = {
            "Current State": {"op": "UPDATE", "content": "- Microservices deployed\n- Load balancer active"},
            "Errors & Corrections": {"op": "APPEND", "items": ["Timeout connecting to replica"]},
        }
        wm_t1 = WorkingMemorySynthesizer.merge_wm_sections(sample_wm, t1_ops)
        assert "Load balancer active" in wm_t1
        assert "Timeout connecting to replica" in wm_t1
        assert "Fixed memory leak in worker pool" in wm_t1

        # Turn 2: keep most, update goals
        t2_ops = {
            "Task & Goals": {"op": "UPDATE", "content": "- Monitor production health\n- Collect metrics"},
        }
        wm_t2 = WorkingMemorySynthesizer.merge_wm_sections(wm_t1, t2_ops)
        assert "Monitor production health" in wm_t2
        assert "Load balancer active" in wm_t2
        assert "Timeout connecting to replica" in wm_t2
