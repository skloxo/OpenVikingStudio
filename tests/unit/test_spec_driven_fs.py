# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Spec-Driven Workspace File System (AFS) & Compression Whitelist.
(Card-Harness-DeepSeek-AgentScope-SpecDriven - v1.5.03)

Verifies:
1. Isolatability: Static specification assets are strictly read-only; session sandboxes are read-write.
2. Path safety: Path traversal attempts are blocked.
3. Compression Whitelist: TaskPlan, SubAgentTracker, and AuthGrants are protected from compaction.
"""

from pathlib import Path
import pytest

from openviking.core.spec_driven_fs import (
    CompressionWhitelist,
    ProtectedPayload,
    SpecWorkspace,
    WhitelistType,
)


def test_spec_workspace_readonly_static_assets(tmp_path: Path):
    """Test static specification paths are strictly read-only."""
    static_dir = tmp_path / "static"
    sandbox_dir = tmp_path / "sandbox"
    static_dir.mkdir()
    sandbox_dir.mkdir()

    # Prepopulate static assets
    agents_md = static_dir / "AGENTS.md"
    agents_md.write_text("# Master Agents Spec\n", encoding="utf-8")
    skill_dir = static_dir / "skills" / "math"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Math Skill\n", encoding="utf-8")

    ws = SpecWorkspace(static_root=static_dir, sandbox_root=sandbox_dir, session_id="sess_1")

    # Verify is_read_only detection
    assert ws.is_read_only("AGENTS.md")
    assert ws.is_read_only("skills/math/SKILL.md")
    assert ws.is_read_only("BLUEPRINT.md")
    assert not ws.is_read_only("MEMORY.md")
    assert not ws.is_read_only("output/result.json")

    # Reading static asset works
    content = ws.read_text("AGENTS.md")
    assert "# Master Agents Spec" in content

    # Writing to static asset must raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        ws.write_text("AGENTS.md", "Modified content")
    assert "Cannot write to read-only static asset" in str(exc_info.value)

    with pytest.raises(PermissionError):
        ws.write_text("skills/math/SKILL.md", "Malicious patch")


def test_spec_workspace_sandbox_read_write(tmp_path: Path):
    """Test dynamic files in session sandbox are read-write and isolated."""
    static_dir = tmp_path / "static"
    sandbox_dir = tmp_path / "sandbox"
    static_dir.mkdir()
    sandbox_dir.mkdir()

    ws1 = SpecWorkspace(static_root=static_dir, sandbox_root=sandbox_dir, session_id="sess_1")
    ws2 = SpecWorkspace(static_root=static_dir, sandbox_root=sandbox_dir, session_id="sess_2")

    # Session 1 writes its memory
    ws1.write_text("MEMORY.md", "Session 1 memory state")
    assert ws1.exists("MEMORY.md")
    assert ws1.read_text("MEMORY.md") == "Session 1 memory state"

    # Session 2 has independent sandbox
    assert not ws2.exists("MEMORY.md")
    ws2.write_text("MEMORY.md", "Session 2 independent state")
    assert ws2.read_text("MEMORY.md") == "Session 2 independent state"
    assert ws1.read_text("MEMORY.md") == "Session 1 memory state"


def test_spec_workspace_traversal_prevention(tmp_path: Path):
    """Test path traversal attempts are detected and rejected."""
    static_dir = tmp_path / "static"
    sandbox_dir = tmp_path / "sandbox"
    static_dir.mkdir()
    sandbox_dir.mkdir()

    ws = SpecWorkspace(static_root=static_dir, sandbox_root=sandbox_dir, session_id="sess_1")

    with pytest.raises(ValueError) as exc_info:
        ws.resolve_path("../../etc/shadow")
    assert "Path traversal detected" in str(exc_info.value)


def test_compression_whitelist_exemption():
    """Test compression whitelist recognizes only designated enterprise types."""
    assert CompressionWhitelist.is_exempt(WhitelistType.TASK_PLAN)
    assert CompressionWhitelist.is_exempt(WhitelistType.SUBAGENT_TRACKER)
    assert CompressionWhitelist.is_exempt(WhitelistType.AUTH_GRANTS)
    assert CompressionWhitelist.is_exempt("TaskPlan")
    assert not CompressionWhitelist.is_exempt("RawChatLog")
    assert not CompressionWhitelist.is_exempt("RandomData")


def test_compression_whitelist_registration_and_filtering():
    """Test registration and filtering of protected payloads."""
    cw = CompressionWhitelist()

    p1 = cw.register(
        payload_id="plan_01",
        whitelist_type=WhitelistType.TASK_PLAN,
        content={"goal": "Refactor codebase", "steps": [1, 2, 3]},
    )
    p2 = cw.register(
        payload_id="tracker_01",
        whitelist_type=WhitelistType.SUBAGENT_TRACKER,
        content={"worker": "developer", "status": "running"},
    )
    p3 = cw.register(
        payload_id="auth_01",
        whitelist_type=WhitelistType.AUTH_GRANTS,
        content={"scope": "read:fs", "expires": 3600},
    )

    assert cw.get("plan_01") == p1
    assert len(cw.list_by_type(WhitelistType.TASK_PLAN)) == 1

    payloads = [p1, p2, p3]
    filtered = cw.filter_protected(payloads)
    assert len(filtered) == 3

    # Manually toggle protection flag off to verify filter
    p2.is_protected = False
    assert len(cw.filter_protected(payloads)) == 2
