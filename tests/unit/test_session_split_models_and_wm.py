# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Card 5: Session monolith modularization into models and wm_synthesizer."""

import pytest
from datetime import datetime, timezone

from openviking.session.models import (
    SessionMeta,
    SessionStats,
    SessionCompression,
    ArchiveState,
    Usage,
    WM_SEVEN_SECTIONS,
    _default_memory_counts,
    _resolve_event_search_tags,
)
from openviking.session.wm_synthesizer import WorkingMemorySynthesizer
from openviking.session.session import Session


class TestSessionModelsSeparation:
    """Test that models can be imported and operated completely independently."""

    def test_session_meta_lifecycle(self):
        now_str = datetime.now(timezone.utc).isoformat()
        meta = SessionMeta(
            session_id="test_sess_001",
            created_at=now_str,
            updated_at=now_str,
            message_count=6,
            llm_token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )
        data = meta.to_dict()
        assert data["session_id"] == "test_sess_001"
        assert data["message_count"] == 6
        assert data["llm_token_usage"]["total_tokens"] == 150

        restored = SessionMeta.from_dict(data)
        assert restored.session_id == "test_sess_001"
        assert restored.message_count == 6
        assert restored.llm_token_usage["total_tokens"] == 150

    def test_session_stats_and_compression(self):
        stats = SessionStats(total_tokens=500, total_turns=2, compression_count=1)
        comp = SessionCompression(summary="summary text", original_count=10, compressed_count=4)
        assert stats.total_tokens == 500
        assert stats.total_turns == 2
        assert comp.original_count == 10
        assert comp.compressed_count == 4

    def test_archive_state_and_usage(self):
        state = ArchiveState(
            archive_id="arch_001",
            archive_uri="viking://sessions/s1/archives/0",
            index=0,
            state="completed",
            overview="Archive summary",
        )
        assert state.archive_id == "arch_001"
        assert state.coverage_start_index == 0
        assert state.coverage_end_index == 0

        usage = Usage(
            uri="viking://resources/skills/test_skill",
            type="skill",
            contribution=0.85,
            success=True,
        )
        assert usage.uri == "viking://resources/skills/test_skill"
        assert usage.type == "skill"
        assert usage.contribution == 0.85

    def test_backward_compatible_aliasing_in_session(self):
        """Session module must re-export models for 100% backward compatibility."""
        from openviking.session import SessionMeta as ExportedMeta
        from openviking.session import SessionStats as ExportedStats
        from openviking.session import SessionCompression as ExportedComp

        assert ExportedMeta is SessionMeta
        assert ExportedStats is SessionStats
        assert ExportedComp is SessionCompression


class TestWorkingMemorySynthesizerSeparation:
    """Test that WorkingMemorySynthesizer pure algorithms run independently and cleanly."""

    def test_parse_and_extract_bullets(self):
        sample_wm = """# Working Memory

## Session Title
Modular Architecture Plan

## Current State
- Step 1 completed
- Step 2 in progress

## Key Facts & Decisions
1. Decided SQLite WAL mode on 2026-09-20
2. Chose modular session refactoring
"""
        sections = WorkingMemorySynthesizer.parse_wm_sections(sample_wm)
        assert "## Session Title" in sections
        assert "## Current State" in sections
        assert "## Key Facts & Decisions" in sections

        bullets = WorkingMemorySynthesizer.extract_bullet_items(sections["## Current State"])
        assert len(bullets) == 2
        assert "Step 1 completed" in bullets
        assert "Step 2 in progress" in bullets

    def test_merge_wm_sections_guard_integration(self):
        old_wm = """# Working Memory

## Session Title
Title A

## Current State
- Task 1

## Errors & Corrections
- Fixed bug 1

## Key Facts & Decisions
- Decided X on 2026-09-01
- Kept 5 dollars budget
"""
        ops = {
            "Session Title": {"op": "UPDATE", "content": "Title A Updated"},
            "Errors & Corrections": {"op": "APPEND", "items": ["New error logged"]},
            "Key Facts & Decisions": {"op": "KEEP"},
        }
        merged = WorkingMemorySynthesizer.merge_wm_sections(old_wm, ops)
        assert "## Session Title\nTitle A Updated" in merged
        assert "New error logged" in merged
        assert "Decided X on 2026-09-01" in merged

    def test_session_transparent_delegation(self):
        """Verify that Session static methods properly delegate to WorkingMemorySynthesizer."""
        text = "## Test Section\n- Item 1\n- Item 2"
        res_direct = WorkingMemorySynthesizer.parse_wm_sections(text)
        res_delegated = Session._parse_wm_sections(text)
        assert res_direct == res_delegated

        bullets_direct = WorkingMemorySynthesizer.extract_bullet_items("- A\n- B")
        bullets_delegated = Session._wm_extract_bullet_items("- A\n- B")
        assert bullets_direct == bullets_delegated
