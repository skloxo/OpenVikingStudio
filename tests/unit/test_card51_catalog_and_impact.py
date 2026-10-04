# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test suite for Card-51: Path Decoupling, Robust SQL Blast Radius & mtime Cache."""

import os
from pathlib import Path
import time
import pytest
from fastapi.testclient import TestClient

from openviking.server.routers.code_catalog import (
    _resolve_skills_roots,
    _get_primary_skills_root,
    _compute_dir_mtime,
    _get_cached_snapshot,
    _set_cached_snapshot,
    _SNAPSHOT_CACHE,
    router as catalog_router,
)
from openviking.service.impact_topology import ImpactTopologyBuilder


def test_resolve_skills_roots_dynamic_env(monkeypatch, tmp_path):
    """Verify _resolve_skills_roots dynamically parses SKILLS_ROOT and prioritizes custom roots."""
    dir1 = tmp_path / "skills1"
    dir2 = tmp_path / "skills2"
    dir1.mkdir()
    dir2.mkdir()

    monkeypatch.setenv("SKILLS_ROOT", f"{dir1.as_posix()}:{dir2.as_posix()}")

    roots = _resolve_skills_roots()
    assert dir1 in roots
    assert dir2 in roots

    # Test explicit custom root takes precedence
    custom_dir = tmp_path / "custom_skills"
    custom_dir.mkdir()
    custom_roots = _resolve_skills_roots(custom_dir.as_posix())
    assert custom_roots == [custom_dir]


def test_mtime_incremental_cache_resilience(tmp_path):
    """Verify mtime fingerprint allows cache reuse after TTL when files haven't changed."""
    watch_dir = tmp_path / "watched_repo"
    watch_dir.mkdir()
    file1 = watch_dir / "module_a.py"
    file1.write_text("print('hello')", encoding="utf-8")

    cache_key = "test_mtime_key"
    _SNAPSHOT_CACHE.pop(cache_key, None)

    # 1. Set snapshot with a very short TTL (0.05s)
    _set_cached_snapshot(
        cache_key,
        data={"val": 42},
        watch_path=watch_dir,
        glob_pattern="*.py",
        ttl=0.05,
    )

    # 2. Wait for TTL to expire
    time.sleep(0.08)

    # 3. Request again: since file1 hasn't been modified, mtime matches, cache is renewed!
    cached = _get_cached_snapshot(cache_key, watch_path=watch_dir, glob_pattern="*.py")
    assert cached is not None
    assert cached["val"] == 42

    # 4. Physically modify file (advance mtime)
    time.sleep(0.02)
    file1.write_text("print('updated')", encoding="utf-8")
    os.utime(file1, (time.time() + 10, time.time() + 10))

    # Force expiry to verify mtime mismatch
    _SNAPSHOT_CACHE[cache_key].expiry = time.monotonic() - 1.0
    stale = _get_cached_snapshot(cache_key, watch_path=watch_dir, glob_pattern="*.py")
    assert stale is None  # Cache successfully invalidated!


def test_clean_table_identifier_normalization():
    """Verify clean_table_identifier handles aliases, quotes, and filters keywords."""
    clean = ImpactTopologyBuilder.clean_table_identifier

    # Valid tables with aliases
    assert clean("users AS u") == "users"
    assert clean("orders o") == "orders"
    assert clean("`analytics_events`") == "analytics_events"
    assert clean("[dim_user_profile]") == "dim_user_profile"

    # Keywords and internal tables filtered
    assert clean("SELECT") is None
    assert clean("FROM") is None
    assert clean("sqlite_master") is None
    assert clean("sqlite_sequence") is None
    assert clean("123_invalid") is None
    assert clean("") is None


def test_multi_table_sql_readers_and_writers():
    """Verify impact topology captures multiple comma-separated tables and CREATE TABLE."""
    builder = ImpactTopologyBuilder()

    sql_code = """
    CREATE TABLE IF NOT EXISTS system_telemetry (
        id INTEGER PRIMARY KEY,
        metric TEXT
    );

    SELECT u.id, o.amount
    FROM table_users AS u, table_orders AS o
    WHERE u.id = o.user_id;

    INSERT OR REPLACE INTO system_telemetry VALUES (1, 'cpu');
    """

    builder.analyze_source_sql("service/worker.py", sql_code)
    impact_map = builder.get_table_impact_map()

    # Verify writers
    assert "system_telemetry" in impact_map
    assert "service/worker.py" in impact_map["system_telemetry"].writers

    # Verify multiple readers
    assert "table_users" in impact_map
    assert "service/worker.py" in impact_map["table_users"].readers

    assert "table_orders" in impact_map
    assert "service/worker.py" in impact_map["table_orders"].readers


@pytest.mark.asyncio
async def test_code_catalog_routes_smoke():
    """Verify code catalog routes execute smoothly with zero hardcoded failures."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(catalog_router)
    client = TestClient(app)

    # 1. Summary endpoint
    resp_sum = client.get("/api/v1/catalog/summary")
    assert resp_sum.status_code == 200
    data_sum = resp_sum.json()
    assert data_sum["status"] == "ok"
    assert "mcp_tools_detected" in data_sum["summary"]

    # 2. Code facts endpoint
    resp_code = client.get("/api/v1/catalog/code")
    assert resp_code.status_code == 200
    data_code = resp_code.json()
    assert data_code["total_routes"] > 0
    assert data_code["total_tools"] > 0

    # 3. Storage impact view
    resp_storage = client.get("/api/v1/catalog/views/storage")
    assert resp_storage.status_code == 200
    data_storage = resp_storage.json()
    assert data_storage["total_tables"] > 0
    assert "markdown_view" in data_storage
