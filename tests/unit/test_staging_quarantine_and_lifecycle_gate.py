#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Card-Memory-StagingQuarantine-LifecycleGate (v1.5.04).
Validates staging session scan, backup manifest generation, restoration,
and Hook active baseline filtering guards.
"""

import json
from pathlib import Path
import tempfile
import pytest

from scripts.quarantine_staging_sessions import (
    scan_staging_targets,
    backup_targets,
    restore_archive,
)


def test_is_quarantined_or_staging_filter():
    """Verify Hook active baseline path guard properly blocks staging and archive noise."""
    from scripts.quarantine_staging_sessions import scan_staging_targets
    
    # Import the guard function dynamically from ov_pre_invocation
    hook_candidates = [
        Path(__file__).parents[3] / ".agents" / "hooks" / "ov_pre_invocation.py",
        Path.home() / ".gemini" / "config" / "hooks" / "ov_pre_invocation.py",
    ]
    hook_path = next((p for p in hook_candidates if p.exists()), None)
    assert hook_path is not None, "Hook file ov_pre_invocation.py not found in workspace or global config"
    
    import importlib.util
    spec = importlib.util.spec_from_file_location("ov_pre_invocation", hook_path)
    assert spec is not None and spec.loader is not None, "Failed to create spec for ov_pre_invocation"
    hook_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook_mod)
    
    is_guard = getattr(hook_mod, "is_quarantined_or_staging")
    
    # Positive assertions (Must be blocked)
    assert is_guard("viking://resources/staging/3070_sessions/2026-09-08_1de41a99.md") is True
    assert is_guard("viking://resources/staging/antigravity_sessions/session_01.md") is True
    assert is_guard("viking://resources/staging/2080ti_sessions/dump.md") is True
    assert is_guard("viking://resources/archive/zombie_sessions/old.md") is True
    assert is_guard("viking://resources/default/antigravity_sessions/draft.md") is True
    
    # Negative assertions (Active baseline - Must be allowed)
    assert is_guard("viking://resources/master_memory/evolution_lessons/20260908_153442_lesson.md") is False
    assert is_guard("viking://resources/master_memory/rules/AGENTS.md") is False
    assert is_guard("viking://resources/skills/cockpit-ui/SKILL.md") is False
    assert is_guard("") is False


def test_scan_and_backup_staging_targets():
    """Verify scanning staging directory and safely generating manifest and backup."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        staging_dir = Path(tmp_dir) / "staging"
        staging_dir.mkdir()
        archive_dir = Path(tmp_dir) / "archive"
        
        # Create mock session folders
        s3070 = staging_dir / "3070_sessions"
        s3070.mkdir()
        (s3070 / "test1.md").write_text("Session test 1", encoding="utf-8")
        (s3070 / "test2.md").write_text("Session test 2", encoding="utf-8")
        
        s_anti = staging_dir / "antigravity_sessions"
        s_anti.mkdir()
        (s_anti / "session_a.md").write_text("Antigravity trace", encoding="utf-8")
        
        # Other non-session directory
        normal_dir = staging_dir / "active_docs"
        normal_dir.mkdir()
        (normal_dir / "doc.md").write_text("Keep me", encoding="utf-8")
        
        targets = scan_staging_targets(staging_dir)
        assert "3070_sessions" in targets
        assert "antigravity_sessions" in targets
        assert "active_docs" not in targets
        assert len(targets) == 2
        
        # Perform backup
        manifest = backup_targets(targets, staging_dir, archive_dir)
        assert manifest["total_targets"] == 2
        assert manifest["total_files"] == 3
        assert (archive_dir / "quarantine_manifest.json").exists()
        
        # Verify content preserved in archive
        assert (archive_dir / "3070_sessions" / "test1.md").read_text(encoding="utf-8") == "Session test 1"
        assert (archive_dir / "antigravity_sessions" / "session_a.md").read_text(encoding="utf-8") == "Antigravity trace"
        
        # Verify restore capability
        restore_dir = Path(tmp_dir) / "restored_staging"
        restore_archive(archive_dir, restore_dir)
        assert (restore_dir / "3070_sessions" / "test1.md").exists()
        assert (restore_dir / "antigravity_sessions" / "session_a.md").exists()
