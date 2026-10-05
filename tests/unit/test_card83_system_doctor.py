# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Card-83: Settings system doctor health check and storage integrity cockpit."""

from __future__ import annotations

import pathlib

from openviking.server.db_integrity_check import (
    get_last_database_check_report,
    run_database_integrity_self_check,
)
from openviking.server.routers.rsi import router as rsi_router


def test_system_doctor_backend_contracts_and_execution():
    """Verify system doctor endpoints exist and integrity check returns valid contract structure."""
    route_paths = [r.path for r in rsi_router.routes]

    # Health report endpoints
    assert "/bootstrap/health" in route_paths or "/api/v1/rsi/bootstrap/health" in route_paths
    assert "/bootstrap/health/run" in route_paths or "/api/v1/rsi/bootstrap/health/run" in route_paths

    # Verify execution output shape
    report = run_database_integrity_self_check()
    assert "status" in report
    assert report["status"] in ("healthy", "warning")
    assert "total_databases" in report
    assert "passed_databases" in report
    assert "fts5_rebuilt_count" in report
    assert "duration_ms" in report
    assert "databases" in report

    cached = get_last_database_check_report()
    assert cached is not None
    assert cached["status"] == report["status"]


def test_frontend_system_doctor_component_and_integration():
    """Verify frontend component exists, mounted in DataOpsTab, and follows Cockpit UI rules."""
    project_root = pathlib.Path(__file__).parents[2]
    card_path = project_root / "src/routes/settings/-components/data-ops/system-doctor-card.tsx"
    tab_path = project_root / "src/routes/settings/-components/data-ops-tab.tsx"
    zh_i18n_path = project_root / "src/i18n/locales/zh-CN/settings.ts"
    en_i18n_path = project_root / "src/i18n/locales/en/settings.ts"

    assert card_path.exists(), "SystemDoctorCard component file must exist"
    assert tab_path.exists(), "DataOpsTab file must exist"

    card_content = card_path.read_text(encoding="utf-8")
    tab_content = tab_path.read_text(encoding="utf-8")
    zh_content = zh_i18n_path.read_text(encoding="utf-8")
    en_content = en_i18n_path.read_text(encoding="utf-8")

    # Card line count must not exceed 250 lines
    card_lines = len(card_content.splitlines())
    assert card_lines <= 250, f"SystemDoctorCard must be <= 250 lines, got {card_lines}"

    # Card must use unified ovClient
    assert "ovClient.instance.get" in card_content
    assert "ovClient.instance.post" in card_content
    assert "/api/v1/rsi/bootstrap/health" in card_content
    assert "/api/v1/rsi/bootstrap/health/run" in card_content

    # Card must follow Cockpit UI rules: NO GREEN EVER
    assert "text-green" not in card_content
    assert "bg-green" not in card_content

    # DataOpsTab must mount SystemDoctorCard
    assert "SystemDoctorCard" in tab_content
    assert "<SystemDoctorCard />" in tab_content

    # Both zh-CN and en i18n must declare doctor keys
    assert "doctorTitle:" in zh_content
    assert "doctorTitle:" in en_content
    assert "btnRunDoctor:" in zh_content
    assert "btnRunDoctor:" in en_content
    assert "healthStatusHealthy:" in zh_content
    assert "healthStatusHealthy:" in en_content
