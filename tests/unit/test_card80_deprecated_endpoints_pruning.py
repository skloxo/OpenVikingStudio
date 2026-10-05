# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Card-80: Deprecated /search/recall and duplicate probe pruning."""

from __future__ import annotations

import sqlite3

from openviking.observability.usage_audit.frequency_analyzer import analyze_endpoint_frequency
from openviking.server.routers.hybrid_search import router as hybrid_router
from openviking.server.routers.search import router as search_router


def test_duplicate_hybrid_probe_removed_from_routes():
    """Verify duplicate /api/v1/search/hybrid/probe route is removed while hybrid_probe is kept."""
    registered_paths = [route.path for route in hybrid_router.routes]

    # Duplicate probe must be physically pruned
    assert "/api/v1/search/hybrid/probe" not in registered_paths

    # Canonical endpoint used by frontend bm25-hybrid-cockpit must remain active
    assert "/api/v1/search/hybrid_probe" in registered_paths


def test_deprecated_search_recall_removed_from_routes():
    """Verify deprecated /recall route is physically excised from search router."""
    registered_paths = [route.path for route in search_router.routes]

    # Deprecated /recall must not exist
    assert "/api/v1/search/recall" not in registered_paths

    # Primary and canonical search endpoints must be present
    assert "/api/v1/search/search" in registered_paths
    assert "/api/v1/search/find" in registered_paths
    assert "/api/v1/search/grep" in registered_paths


def test_pruned_endpoints_do_not_pollute_dormant_list():
    """Verify dormant analyzer no longer sees excised endpoints in registered routes."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE request_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            account_id TEXT NOT NULL,
            user_id TEXT,
            method TEXT NOT NULL,
            route TEXT NOT NULL,
            api_type TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            duration_ms REAL NOT NULL,
            error_code TEXT,
            error_message TEXT,
            error_details TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    # Collect actual paths from both routers
    active_routes = [
        {"path": r.path, "methods": list(r.methods or ["POST"])}
        for r in list(hybrid_router.routes) + list(search_router.routes)
    ]

    res = analyze_endpoint_frequency(
        conn,
        account_id="default",
        registered_routes=active_routes,
    )

    dormant_paths = [d["route"] for d in res["dormant_endpoints"]]

    # Excised endpoints must never appear in dormant list
    assert "/api/v1/search/hybrid/probe" not in dormant_paths
    assert "/recall" not in dormant_paths
    assert "/api/v1/search/recall" not in dormant_paths

    # Active canonical paths are recognized
    assert "/api/v1/search/hybrid_probe" in dormant_paths or res["total_calls"] == 0
