# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Card-79: Audit frequency filter alignment and false-positive self-healing."""

from __future__ import annotations

import sqlite3

from openviking.observability.usage_audit.frequency_analyzer import (
    analyze_endpoint_frequency,
    should_ignore_route_for_dormancy,
)


def _init_test_db() -> sqlite3.Connection:
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
    return conn


def test_should_ignore_route_for_dormancy():
    """Verify console routes and static assets are accurately excluded from dormant lists."""
    # Console and BFF routes must be ignored
    assert should_ignore_route_for_dormancy("/api/v1/console/dashboard/summary") is True
    assert should_ignore_route_for_dormancy("/api/v1/console/tokens") is True
    assert should_ignore_route_for_dormancy("/api/v1/console/audit/frequency") is True
    assert should_ignore_route_for_dormancy("/api/v1/console/peers") is True

    # Static assets and probe routes must be ignored
    assert should_ignore_route_for_dormancy("/favicon.ico") is True
    assert should_ignore_route_for_dormancy("/favicon.png") is True
    assert should_ignore_route_for_dormancy("/apple-touch-icon.png") is True
    assert should_ignore_route_for_dormancy("/service-worker.js") is True
    assert should_ignore_route_for_dormancy("/studio/service-worker.js") is True
    assert should_ignore_route_for_dormancy("/health") is True
    assert should_ignore_route_for_dormancy("/ready") is True
    assert should_ignore_route_for_dormancy("/metrics") is True

    # Doc and UI assets
    assert should_ignore_route_for_dormancy("/studio/overview") is True
    assert should_ignore_route_for_dormancy("/docs") is True
    assert should_ignore_route_for_dormancy("/redoc") is True
    assert should_ignore_route_for_dormancy("/openapi.json") is True
    assert should_ignore_route_for_dormancy("/__unmatched__") is True

    # Legitimate business routes must NEVER be ignored
    assert should_ignore_route_for_dormancy("/api/v1/search/find") is False
    assert should_ignore_route_for_dormancy("/api/v1/context/commit") is False
    assert should_ignore_route_for_dormancy("/api/v1/fs/read") is False
    assert should_ignore_route_for_dormancy("/api/v1/vikingfs/export") is False
    assert should_ignore_route_for_dormancy("/api/v1/admin/accounts") is False


def test_dormant_endpoints_exclude_console_and_static():
    """Verify dormant detection does not falsely report console or static routes."""
    conn = _init_test_db()
    # Insert call for search endpoint
    conn.execute(
        """
        INSERT INTO request_audit (
            request_id, account_id, user_id, method, route, api_type,
            status_code, duration_ms, created_at
        ) VALUES ('req-1', 'default', 'u-1', 'POST', '/api/v1/search/find', 'rest', 200, 15.0, '2026-10-01T12:00:00Z')
        """
    )

    registered_routes = [
        {"path": "/api/v1/search/find", "methods": ["POST"]},
        {"path": "/api/v1/vikingfs/export", "methods": ["POST"]},  # True dormant business route
        {"path": "/api/v1/console/dashboard/summary", "methods": ["GET"]},  # Console (must be ignored)
        {"path": "/api/v1/console/peers", "methods": ["GET"]},  # Console (must be ignored)
        {"path": "/favicon.ico", "methods": ["GET"]},  # Static (must be ignored)
        {"path": "/service-worker.js", "methods": ["GET"]},  # Static (must be ignored)
        {"path": "/health", "methods": ["GET"]},  # Probe (must be ignored)
    ]

    res = analyze_endpoint_frequency(
        conn,
        account_id="default",
        window="all",
        registered_routes=registered_routes,
    )

    dormant_paths = [d["route"] for d in res["dormant_endpoints"]]
    # Business dormant route must be detected
    assert "/api/v1/vikingfs/export" in dormant_paths
    # Excluded routes must not appear
    assert "/api/v1/console/dashboard/summary" not in dormant_paths
    assert "/api/v1/console/peers" not in dormant_paths
    assert "/favicon.ico" not in dormant_paths
    assert "/service-worker.js" not in dormant_paths
    assert "/health" not in dormant_paths
    # Exact dormant count should be 1
    assert res["dormant_endpoints_count"] == 1
    assert res["active_endpoints_count"] == 1
    assert res["total_endpoints_count"] == 2
    assert res["active_rate"] == 0.5


def test_multi_tenant_and_trusted_traffic_inclusion():
    """Verify default tenant includes trusted/system internal calls."""
    conn = _init_test_db()
    records = [
        ("req-1", "default", "u-1", "GET", "/api/v1/fs/read", "rest", 200, 10.0, "2026-10-01T12:00:00Z"),
        ("req-2", "trusted", None, "GET", "/api/v1/admin/accounts", "rest", 200, 5.0, "2026-10-01T12:05:00Z"),
        ("req-3", "system", None, "POST", "/api/v1/tasks/sync", "rest", 200, 20.0, "2026-10-01T12:10:00Z"),
        ("req-4", "tenant-b", "u-2", "GET", "/api/v1/private/info", "rest", 200, 8.0, "2026-10-01T12:15:00Z"),
    ]
    conn.executemany(
        """
        INSERT INTO request_audit (
            request_id, account_id, user_id, method, route, api_type,
            status_code, duration_ms, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        records,
    )

    # 1. Default tenant with include_trusted=True sees default + trusted + system
    res_default = analyze_endpoint_frequency(
        conn,
        account_id="default",
        include_trusted=True,
    )
    routes_default = [e["route"] for e in res_default["top_hot_endpoints"]]
    assert "/api/v1/fs/read" in routes_default
    assert "/api/v1/admin/accounts" in routes_default
    assert "/api/v1/tasks/sync" in routes_default
    assert "/api/v1/private/info" not in routes_default
    assert res_default["total_calls"] == 3

    # 2. Strict tenant-b sees only tenant-b
    res_tenant_b = analyze_endpoint_frequency(
        conn,
        account_id="tenant-b",
        include_trusted=True,
    )
    routes_tenant_b = [e["route"] for e in res_tenant_b["top_hot_endpoints"]]
    assert routes_tenant_b == ["/api/v1/private/info"]
    assert res_tenant_b["total_calls"] == 1

    # 3. Global admin '*' sees everything
    res_all = analyze_endpoint_frequency(
        conn,
        account_id="*",
    )
    assert res_all["total_calls"] == 4
