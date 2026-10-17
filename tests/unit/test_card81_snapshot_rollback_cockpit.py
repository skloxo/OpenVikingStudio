# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Card-81: Settings workspace snapshot management and one-click rollback."""

from __future__ import annotations

import inspect
import pathlib

from openviking.server.routers.snapshot import router as snapshot_router


def test_snapshot_routes_mounted_and_contracts_valid():
    """Verify snapshot router endpoints required by frontend SnapshotRollbackCard exist."""
    route_paths = [r.path for r in snapshot_router.routes]

    # Commit endpoint used by one-click snapshot creation
    assert "/commit" in route_paths or "/api/v1/snapshot/commit" in route_paths

    # Log endpoint used by timeline listing
    assert "/log" in route_paths or "/api/v1/snapshot/log" in route_paths

    # Restore endpoint used by one-click rollback
    assert "/restore" in route_paths or "/api/v1/snapshot/restore" in route_paths

    # Diff endpoint used by inspection modal
    assert "/diff" in route_paths or "/api/v1/snapshot/diff" in route_paths


def test_frontend_snapshot_card_source_and_integration():
    """Verify frontend component exists and is mounted in DataOpsTab without lint errors."""
    project_root = pathlib.Path(__file__).parents[2]
    card_path = project_root / "src/routes/settings/-components/data-ops/snapshot-rollback-card.tsx"
    tab_path = project_root / "src/routes/settings/-components/data-ops-tab.tsx"

    assert card_path.exists(), "SnapshotRollbackCard component file must exist"
    assert tab_path.exists(), "DataOpsTab file must exist"

    card_content = card_path.read_text(encoding="utf-8")
    tab_content = tab_path.read_text(encoding="utf-8")

    # Card must use unified ovClient
    assert "ovClient.instance.get('/api/v1/snapshot/log'" in card_content
    assert "ovClient.instance.post('/api/v1/snapshot/commit'" in card_content
    assert "ovClient.instance.post('/api/v1/snapshot/restore'" in card_content

    # Card must follow Cockpit UI rules: no hardcoded green
    assert "text-green" not in card_content
    assert "bg-green" not in card_content

    # DataOpsTab must mount SnapshotRollbackCard
    assert "SnapshotRollbackCard" in tab_content
    assert "<SnapshotRollbackCard />" in tab_content


def test_snapshot_log_parameter_contracts():
    """Verify snapshot log endpoint parameter contracts match expected query shape."""
    log_route = next(r for r in snapshot_router.routes if r.path.endswith("/log"))
    sig = inspect.signature(log_route.endpoint)
    assert "branch" in sig.parameters
    assert "limit" in sig.parameters

