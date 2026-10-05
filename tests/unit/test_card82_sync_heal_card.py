# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Card-82: Tasks and queue one-click sync-heal and dead letter self-healing cockpit."""

from __future__ import annotations

import pathlib

from openviking.server.routers.queue import router as queue_router


def test_queue_sync_heal_routes_mounted_and_valid():
    """Verify queue self-healing endpoints required by OneClickSyncHealCard exist."""
    route_paths = [r.path for r in queue_router.routes]

    # Metrics endpoint
    assert "/sync-metrics" in route_paths or "/api/v1/queue/sync-metrics" in route_paths

    # Straggler self-heal endpoint
    assert "/sync-heal" in route_paths or "/api/v1/queue/sync-heal" in route_paths

    # Retry failed DLQ endpoint
    assert "/retry_failed" in route_paths or "/api/v1/queue/retry_failed" in route_paths

    # Clear DLQ endpoint
    assert "/clear_dlq" in route_paths or "/api/v1/queue/clear_dlq" in route_paths


def test_frontend_sync_heal_component_and_integration():
    """Verify frontend component exists, mounted in TasksMetricsCards, and follows Cockpit UI rules."""
    project_root = pathlib.Path(__file__).parents[2]
    card_path = project_root / "src/routes/tasks/-components/one-click-sync-heal-card.tsx"
    metrics_path = project_root / "src/routes/tasks/-components/tasks-metrics-cards.tsx"
    zh_i18n_path = project_root / "src/i18n/locales/zh-CN/tasks.ts"
    en_i18n_path = project_root / "src/i18n/locales/en/tasks.ts"

    assert card_path.exists(), "OneClickSyncHealCard component file must exist"
    assert metrics_path.exists(), "TasksMetricsCards file must exist"

    card_content = card_path.read_text(encoding="utf-8")
    metrics_content = metrics_path.read_text(encoding="utf-8")
    zh_content = zh_i18n_path.read_text(encoding="utf-8")
    en_content = en_i18n_path.read_text(encoding="utf-8")

    # Card line count must not exceed 250 lines
    card_lines = len(card_content.splitlines())
    assert card_lines <= 250, f"OneClickSyncHealCard must be <= 250 lines, got {card_lines}"

    # Card must use unified ovClient
    assert "ovClient.instance.get" in card_content
    assert "ovClient.instance.post" in card_content
    assert "/api/v1/queue/sync-metrics" in card_content
    assert "/api/v1/queue/sync-heal" in card_content
    assert "/api/v1/queue/retry_failed" in card_content
    assert "/api/v1/queue/clear_dlq" in card_content

    # Card must follow Cockpit UI rules: NO GREEN EVER
    assert "text-green" not in card_content
    assert "bg-green" not in card_content

    # TasksMetricsCards must mount OneClickSyncHealCard
    assert "OneClickSyncHealCard" in metrics_content
    assert "<OneClickSyncHealCard />" in metrics_content

    # Both zh-CN and en i18n must declare syncHeal keys
    assert "syncHeal:" in zh_content
    assert "syncHeal:" in en_content
    assert "btnSyncHeal:" in zh_content
    assert "btnSyncHeal:" in en_content
    assert "btnRetryFailed:" in zh_content
    assert "btnRetryFailed:" in en_content
    assert "btnClearDlq:" in zh_content
    assert "btnClearDlq:" in en_content
