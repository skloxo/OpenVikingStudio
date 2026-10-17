# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Contract and integration tests for Card-59: Active Notes & History FastMCP parity."""

from __future__ import annotations

import tempfile
import pytest

from openviking.server.mcp_endpoint import (
    openviking_active_notes_get,
    openviking_active_notes_update,
    openviking_history_search,
)
from openviking.service.active_notes_history import ActiveNotesHistoryManager


@pytest.fixture
def isolated_notes_manager(monkeypatch):
    """Fixture providing isolated SQLite database for ActiveNotesHistoryManager."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        mgr = ActiveNotesHistoryManager(db_path=tmp.name)
        monkeypatch.setattr(ActiveNotesHistoryManager, "get_instance", lambda *args, **kwargs: mgr)
        yield mgr


@pytest.mark.asyncio
async def test_active_notes_get_defaults(isolated_notes_manager):
    """Verify default retrieval for uninitialized session."""
    res = await openviking_active_notes_get(session_id="test_sess_01")
    assert "=== Active Notes for Session [test_sess_01] (v1) ===" in res
    assert "Active Goal: (None)" in res
    assert "Current State: (None)" in res
    assert "Working Constraints:\n  (None)" in res
    assert "Discovered Facts:\n  (None)" in res
    assert "Estimated Active Notes Tokens:" in res


@pytest.mark.asyncio
async def test_active_notes_update_and_get_roundtrip(isolated_notes_manager):
    """Verify atomic update and state persistence across calls."""
    # 1. Update notes with goal, constraints, and facts
    upd_res = await openviking_active_notes_update(
        session_id="test_sess_roundtrip",
        active_goal="Refactor MCP tool annotations and add Card-59",
        working_constraints=["NO GREEN EVER", "Single file <= 300 lines"],
        current_state="Phase 2 Implementation",
        discovered_facts=["SQLite WAL enabled", "FastMCP uses 4D tuples"],
    )
    assert "Successfully updated Active Notes for session [test_sess_roundtrip] to version 2." in upd_res
    assert "Constraints: 2 item(s)" in upd_res
    assert "Facts: 2 item(s)" in upd_res

    # 2. Get notes and assert accurate representation
    get_res = await openviking_active_notes_get(session_id="test_sess_roundtrip")
    assert "=== Active Notes for Session [test_sess_roundtrip] (v2) ===" in get_res
    assert "Active Goal: Refactor MCP tool annotations and add Card-59" in get_res
    assert "Current State: Phase 2 Implementation" in get_res
    assert "  - NO GREEN EVER" in get_res
    assert "  - Single file <= 300 lines" in get_res
    assert "  - SQLite WAL enabled" in get_res
    assert "  - FastMCP uses 4D tuples" in get_res


@pytest.mark.asyncio
async def test_history_search_fts5_and_fallback(isolated_notes_manager):
    """Verify uncompressed historical dialogue search via FTS5 and fallback."""
    sess = "sess_history_test"
    # Seed historical messages
    isolated_notes_manager.append_history(
        session_id=sess,
        role="user",
        content="Could you check if SQLite WAL mode is configured in active_notes_history.db?",
    )
    isolated_notes_manager.append_history(
        session_id=sess,
        role="assistant",
        content="Yes, PRAGMA journal_mode = WAL and synchronous = NORMAL are both enabled.",
    )
    isolated_notes_manager.append_history(
        session_id=sess,
        role="user",
        content="What about the token saving ratio on active notes?",
    )

    # 1. Search existing term
    search_res = await openviking_history_search(
        session_id=sess,
        query="journal_mode",
        top_k=5,
    )
    assert "=== History Search Results for 'journal_mode' in [sess_history_test]" in search_res
    assert "[ASSISTANT][Turn #2]" in search_res
    assert "PRAGMA journal_mode = WAL" in search_res

    # 2. Search another term
    search_res2 = await openviking_history_search(
        session_id=sess,
        query="token saving",
        top_k=5,
    )
    assert "token saving ratio" in search_res2

    # 3. Search non-matching term
    no_hit = await openviking_history_search(
        session_id=sess,
        query="completely_unrelated_random_term_xyz",
        top_k=5,
    )
    assert "No historical messages matched query 'completely_unrelated_random_term_xyz'" in no_hit


@pytest.mark.asyncio
async def test_active_notes_graceful_error_handling(isolated_notes_manager, monkeypatch):
    """Verify fail-safe error isolation when manager encounters internal errors."""
    def _buggy_get(*args, **kwargs):
        raise RuntimeError("Simulated SQLite disk I/O error")

    monkeypatch.setattr(isolated_notes_manager, "get_or_create_notes", _buggy_get)
    res = await openviking_active_notes_get(session_id="err_sess")
    assert "Failed to retrieve active notes for session [err_sess]: Simulated SQLite disk I/O error" in res
