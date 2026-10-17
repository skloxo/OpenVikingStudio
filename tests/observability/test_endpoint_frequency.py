# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit and integration tests for endpoint frequency ranking and dormant detection."""

from __future__ import annotations

import sqlite3
from typing import Any
import pytest

from openviking.observability.usage_audit.frequency_analyzer import (
    analyze_endpoint_frequency,
    categorize_route,
)
from openviking.observability.usage_audit.api_service import UsageAuditQueryService
from openviking.server.identity import RequestContext, Role
from openviking_cli.session.user_id import UserIdentifier


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


def test_categorize_route():
    assert categorize_route("/api/v1/search/find") == "Memory Core"
    assert categorize_route("/api/v1/context/commit") == "Memory Core"
    assert categorize_route("/api/v1/observer/system") == "Observability & Metrics"
    assert categorize_route("/api/v1/console/audit") == "Observability & Metrics"
    assert categorize_route("/api/v1/admin/accounts") == "Admin & Accounts"
    assert categorize_route("/api/v1/fs/read") == "File & VikingFS"
    assert categorize_route("/mcp") == "FastMCP Tools"
    assert categorize_route("/studio/monitoring") == "Internal & UI Assets"
    assert categorize_route("/__unmatched__") == "Internal & UI Assets"
    assert categorize_route("/api/v1/custom/endpoint") == "General Endpoints"


def test_analyze_endpoint_frequency_ranking_and_dormant():
    conn = _init_test_db()
    # Insert mock records
    records = [
        ("req-1", "acct-1", "u-1", "GET", "/api/v1/admin/accounts", "rest", 200, 10.0, "2026-09-18T10:00:00Z"),
        ("req-2", "acct-1", "u-1", "GET", "/api/v1/admin/accounts", "rest", 200, 15.0, "2026-09-18T11:00:00Z"),
        ("req-3", "acct-1", "u-1", "POST", "/mcp", "mcp", 200, 50.0, "2026-09-18T12:00:00Z"),
        ("req-4", "acct-1", "u-1", "POST", "/api/v1/search/find", "rest", 500, 30.0, "2026-09-18T13:00:00Z"),
        ("req-5", "acct-2", "u-2", "GET", "/api/v1/other", "rest", 200, 5.0, "2026-09-18T14:00:00Z"),
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

    registered_routes = [
        {"path": "/api/v1/admin/accounts", "methods": ["GET"]},
        {"path": "/mcp", "methods": ["POST"]},
        {"path": "/api/v1/search/find", "methods": ["POST"]},
        {"path": "/api/v1/fs/read", "methods": ["GET"]},
        {"path": "/api/v1/dormant/feature", "methods": ["POST"]},
        {"path": "/studio/overview", "methods": ["GET"]},  # should be ignored
        {"path": "/docs", "methods": ["GET"]},  # should be ignored
    ]

    res = analyze_endpoint_frequency(
        conn,
        account_id="acct-1",
        window="all",
        registered_routes=registered_routes,
    )

    assert res["total_calls"] == 4
    assert len(res["top_hot_endpoints"]) == 3
    # Top hot should be /api/v1/admin/accounts with 2 calls
    top = res["top_hot_endpoints"][0]
    assert top["route"] == "/api/v1/admin/accounts"
    assert top["call_count"] == 2
    assert top["share_percent"] == 50.0
    assert top["error_rate"] == 0.0

    # Find endpoint had 1 call with status 500 -> error_rate 1.0
    find_ep = next(e for e in res["top_hot_endpoints"] if e["route"] == "/api/v1/search/find")
    assert find_ep["call_count"] == 1
    assert find_ep["error_rate"] == 1.0

    # Dormant endpoints detection
    dormant_paths = [d["route"] for d in res["dormant_endpoints"]]
    assert "/api/v1/fs/read" in dormant_paths
    assert "/api/v1/dormant/feature" in dormant_paths
    assert "/studio/overview" not in dormant_paths
    assert "/docs" not in dormant_paths

    # Active rate calculation
    assert res["active_endpoints_count"] == 3
    assert res["dormant_endpoints_count"] == 2
    assert res["total_endpoints_count"] == 5
    assert res["active_rate"] == 0.6


class MockStore:
    def __init__(self) -> None:
        self.frequency_args: dict[str, Any] | None = None

    async def query_endpoint_frequency(self, **kwargs):
        self.frequency_args = kwargs
        return {"total_calls": 42, "window": kwargs.get("window")}


class MockInventory:
    async def get_counts(self, _ctx):
        return {}


@pytest.mark.asyncio
async def test_api_service_endpoint_frequency():
    store = MockStore()
    service = UsageAuditQueryService(store=store, inventory=MockInventory(), timezone_name="UTC")

    admin_ctx = RequestContext(
        user=UserIdentifier(account_id="acct-test", user_id="admin-user"),
        role=Role.ADMIN,
    )
    result = await service.endpoint_frequency(
        ctx=admin_ctx,
        window="7d",
        registered_routes=[{"path": "/test", "methods": ["GET"]}],
    )
    assert result["total_calls"] == 42
    assert store.frequency_args is not None
    assert store.frequency_args["account_id"] == "acct-test"
    assert store.frequency_args["user_id"] is None  # Admin gets account-wide
    assert store.frequency_args["window"] == "7d"
    assert len(store.frequency_args["registered_routes"]) == 1
