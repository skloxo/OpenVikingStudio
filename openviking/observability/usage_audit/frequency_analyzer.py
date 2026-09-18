# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Endpoint invocation frequency analyzer and dormant feature detection engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3
from typing import Any, Sequence


def categorize_route(route: str) -> str:
    """Categorize an endpoint route into a clean functional domain."""
    lowered = (route or "").lower()
    if any(k in lowered for k in ("/search/", "/context", "/memory", "/rag/", "/sessions/")):
        return "Memory Core"
    if any(k in lowered for k in ("/observer/", "/system/", "/metrics", "/telemetry", "/console/")):
        return "Observability & Metrics"
    if any(k in lowered for k in ("/admin/", "/accounts")):
        return "Admin & Accounts"
    if any(k in lowered for k in ("/fs/", "/vikingfs")):
        return "File & VikingFS"
    if "/mcp" in lowered:
        return "FastMCP Tools"
    if any(k in lowered for k in ("/studio", "/__unmatched__")) or lowered in ("/", ""):
        return "Internal & UI Assets"
    return "General Endpoints"


def _parse_window_time(window: str) -> str | None:
    """Convert window identifier to UTC cutoff ISO string."""
    now = datetime.now(timezone.utc)
    if window == "24h":
        cutoff = now - timedelta(hours=24)
    elif window == "7d":
        cutoff = now - timedelta(days=7)
    elif window == "30d":
        cutoff = now - timedelta(days=30)
    elif window == "all":
        return None
    else:
        cutoff = now - timedelta(days=7)
    return cutoff.isoformat()


def analyze_endpoint_frequency(
    conn: sqlite3.Connection,
    *,
    account_id: str,
    user_id: str | None = None,
    window: str = "all",
    registered_routes: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compute endpoint frequency rankings, dormant routes, and category shares."""
    where_parts = ["account_id = ?"]
    params: list[Any] = [account_id]

    if user_id:
        where_parts.append("user_id = ?")
        params.append(user_id)

    cutoff_iso = _parse_window_time(window)
    if cutoff_iso:
        where_parts.append("created_at >= ?")
        params.append(cutoff_iso)

    where_sql = " AND ".join(where_parts)

    query = f"""
        SELECT
            route,
            method,
            api_type,
            COUNT(*) AS call_count,
            SUM(CASE WHEN status_code >= 200 AND status_code < 400 THEN 1 ELSE 0 END) AS success_count,
            AVG(duration_ms) AS avg_duration_ms,
            MAX(created_at) AS last_called_at
        FROM request_audit
        WHERE {where_sql}
        GROUP BY route, method
        ORDER BY call_count DESC
    """
    rows = conn.execute(query, params).fetchall()

    total_calls = sum(int(r["call_count"] or 0) for r in rows)
    hot_endpoints: list[dict[str, Any]] = []
    category_counts: dict[str, int] = {}
    active_route_keys: set[str] = set()

    for r in rows:
        route_str = str(r["route"] or "")
        method_str = str(r["method"] or "GET").upper()
        call_count = int(r["call_count"] or 0)
        success_count = int(r["success_count"] or 0)
        avg_dur = round(float(r["avg_duration_ms"] or 0.0), 2)
        error_rate = round(max(0.0, 1.0 - (success_count / max(call_count, 1))), 4)
        share_pct = round((call_count / max(total_calls, 1)) * 100.0, 2)
        cat = categorize_route(route_str)

        category_counts[cat] = category_counts.get(cat, 0) + call_count
        active_route_keys.add(route_str)

        hot_endpoints.append(
            {
                "route": route_str,
                "method": method_str,
                "api_type": str(r["api_type"] or "rest"),
                "category": cat,
                "call_count": call_count,
                "share_percent": share_pct,
                "avg_duration_ms": avg_dur,
                "error_rate": error_rate,
                "last_called_at": r["last_called_at"],
            }
        )

    # Category breakdown
    category_breakdown = [
        {
            "category": cat,
            "call_count": cnt,
            "share_percent": round((cnt / max(total_calls, 1)) * 100.0, 2),
        }
        for cat, cnt in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # Dormant endpoint detection
    dormant_endpoints: list[dict[str, Any]] = []
    ignored_prefixes = ("/studio", "/docs", "/redoc", "/openapi", "/__unmatched__", "/static")

    if registered_routes:
        for reg in registered_routes:
            p = str(reg.get("path") or "")
            if not p or any(p.startswith(ign) for ign in ignored_prefixes) or p == "/":
                continue
            if p not in active_route_keys:
                cat = categorize_route(p)
                methods = reg.get("methods") or ["GET"]
                dormant_endpoints.append(
                    {
                        "route": p,
                        "methods": [m for m in methods if m not in ("HEAD", "OPTIONS")],
                        "category": cat,
                        "status": "dormant",
                        "call_count": 0,
                        "recommendation": (
                            "当前窗口内零调用。建议结合业务排查：若属于低频运维接口可保留；"
                            "若为历史遗留或废弃特性可考虑安全下线。"
                        ),
                    }
                )

    # Sort dormant endpoints by category and route
    dormant_endpoints.sort(key=lambda x: (x["category"], x["route"]))

    active_count = len(hot_endpoints)
    dormant_count = len(dormant_endpoints)
    total_endpoints = active_count + dormant_count
    active_rate = round(active_count / max(total_endpoints, 1), 4)

    return {
        "window": window,
        "total_calls": total_calls,
        "active_endpoints_count": active_count,
        "dormant_endpoints_count": dormant_count,
        "total_endpoints_count": total_endpoints,
        "active_rate": active_rate,
        "top_hot_endpoints": hot_endpoints,
        "dormant_endpoints": dormant_endpoints,
        "category_breakdown": category_breakdown,
    }
