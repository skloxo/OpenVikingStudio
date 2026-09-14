# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for PiDualLoop (Card-Runtime-PiDualLoop - v1.5.01)."""

import os
import time
from pathlib import Path
import pytest

from openviking.core.pi_dual_loop import (
    TreeEntry,
    TreeHashSnapshot,
    TreeDelta,
    PiDualLoopSensor,
    compute_tree_hash,
    detect_delta,
)


@pytest.fixture
def temp_workspace(tmp_path):
    """Creates a temporary directory structure for testing."""
    base = tmp_path / "workspace"
    base.mkdir()
    (base / "file_a.txt").write_text("Hello A", encoding="utf-8")
    (base / "file_b.py").write_text("print('B')", encoding="utf-8")
    sub = base / "subdir"
    sub.mkdir()
    (sub / "file_c.md").write_text("# Markdown C", encoding="utf-8")
    return base


def test_compute_tree_hash_basic(temp_workspace):
    snapshot = compute_tree_hash(temp_workspace)
    assert snapshot.root_dir == str(temp_workspace)
    assert snapshot.file_count == 3
    assert len(snapshot.root_hash) == 64  # sha256 hex
    assert "file_a.txt" in snapshot.entries
    assert "file_b.py" in snapshot.entries
    assert "subdir/file_c.md" in snapshot.entries
    assert snapshot.version == 1


def test_outer_loop_fast_probe_performance(temp_workspace):
    # Benchmark: outer loop on unchanged dir should be ultra-fast (< 5ms)
    sensor = PiDualLoopSensor(temp_workspace)
    changed, initial_snap, delta = sensor.probe()
    assert changed is True
    assert initial_snap.file_count == 3
    assert delta is not None

    # Second probe on identical dir
    start_t = time.perf_counter()
    changed2, cached_snap, delta2 = sensor.probe()
    elapsed_ms = (time.perf_counter() - start_t) * 1000

    assert changed2 is False
    assert delta2 is None
    assert cached_snap.root_hash == initial_snap.root_hash
    assert elapsed_ms < 10.0  # Fast path check completed in milliseconds


def test_delta_detection_add_modify_remove(temp_workspace):
    sensor = PiDualLoopSensor(temp_workspace)
    sensor.probe()

    # 1. Add new file
    (temp_workspace / "file_new.json").write_text("{}", encoding="utf-8")
    changed, snap_after_add, delta_add = sensor.probe()
    assert changed is True
    assert "file_new.json" in delta_add.added
    assert len(delta_add.modified) == 0
    assert len(delta_add.removed) == 0
    assert snap_after_add.version == 2

    # 2. Modify existing file
    time.sleep(0.01)  # Ensure mtime changes
    (temp_workspace / "file_a.txt").write_text("Hello A Modified Content", encoding="utf-8")
    changed, snap_after_mod, delta_mod = sensor.probe()
    assert changed is True
    assert "file_a.txt" in delta_mod.modified
    assert len(delta_mod.added) == 0
    assert len(delta_mod.removed) == 0
    assert snap_after_mod.version == 3

    # 3. Remove file
    (temp_workspace / "file_b.py").unlink()
    changed, snap_after_del, delta_del = sensor.probe()
    assert changed is True
    assert "file_b.py" in delta_del.removed
    assert len(delta_del.added) == 0
    assert len(delta_del.modified) == 0
    assert snap_after_del.version == 4


def test_ignore_patterns(temp_workspace):
    # Create git and pycache files
    git_dir = temp_workspace / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("git config", encoding="utf-8")
    
    pycache_dir = temp_workspace / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "compiled.pyc").write_text("pyc", encoding="utf-8")

    sensor = PiDualLoopSensor(temp_workspace, ignore_patterns=[".git", "__pycache__", "*.pyc"])
    changed, snap, _ = sensor.probe()
    
    assert changed is True
    assert not any(p.startswith(".git") for p in snap.entries)
    assert not any("__pycache__" in p for p in snap.entries)


def test_sensor_callback_dispatch(temp_workspace):
    dispatched = []

    def on_change(delta: TreeDelta):
        dispatched.append(delta)

    sensor = PiDualLoopSensor(temp_workspace)
    sensor.subscribe(on_change)

    # Initial probe dispatches creation delta
    sensor.probe()
    assert len(dispatched) == 1
    assert len(dispatched[0].added) == 3

    # No change -> no dispatch
    sensor.probe()
    assert len(dispatched) == 1

    # Modify -> dispatch
    time.sleep(0.01)
    (temp_workspace / "file_a.txt").write_text("Update", encoding="utf-8")
    sensor.probe()
    assert len(dispatched) == 2
    assert "file_a.txt" in dispatched[1].modified
