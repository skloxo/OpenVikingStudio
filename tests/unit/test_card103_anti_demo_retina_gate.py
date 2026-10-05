# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit Tests for Card-103 Anti-Demo & Anti-Dangling Automated Retina Gate."""

from __future__ import annotations

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role, UserIdentifier
from openviking.service.anti_demo_service import AntiDemoGateService
from scripts.anti_demo_gate import run_anti_demo_gate, scan_file


def test_anti_demo_gate_full_repo_pass():
    """Verify that the real codebase has zero dangling demo features and 100% pass rate."""
    res = run_anti_demo_gate()
    assert res["status"] == "PASS"
    assert res["total_dangling_features_count"] == 0
    assert res["anti_demo_gate_pass_rate"] == 100.0
    assert res["scanned_components"] >= 200
    assert len(res["violations"]) == 0


def test_adversarial_demo_marker_detection(tmp_path: Path):
    """Adversarial Test: Verify @demo-only or mock-only triggers immediate gate violation."""
    file = tmp_path / "bad-component.tsx"
    file.write_text(
        "export function Bad() {\n  // @demo-only mock component\n  return <div>demo</div>\n}\n",
        encoding="utf-8",
    )
    violations = scan_file(file, tmp_path)
    assert len(violations) >= 1
    assert any(v["rule"] == "FORBIDDEN_DEMO_MARKER" for v in violations)


def test_adversarial_no_green_ever_detection(tmp_path: Path):
    """Adversarial Test: Verify green/emerald utility classes trigger NO_GREEN_EVER violation."""
    file = tmp_path / "green-component.tsx"
    file.write_text(
        "export function Green() {\n  return <div className=\"bg-green-500 text-emerald-400\">green</div>\n}\n",
        encoding="utf-8",
    )
    violations = scan_file(file, tmp_path)
    assert len(violations) >= 1
    assert any(v["rule"] == "NO_GREEN_EVER" for v in violations)


def test_adversarial_micro_font_detection(tmp_path: Path):
    """Adversarial Test: Verify micro-fonts (<12px) trigger MICRO_FONT_FLOOR violation."""
    file = tmp_path / "small-font.tsx"
    file.write_text(
        "export function Small() {\n  return <span className=\"text-[10px]\">tiny</span>\n}\n",
        encoding="utf-8",
    )
    violations = scan_file(file, tmp_path)
    assert len(violations) >= 1
    assert any(v["rule"] == "MICRO_FONT_FLOOR" for v in violations)


def test_adversarial_ungrounded_preset_cockpit(tmp_path: Path):
    """Adversarial Test: Verify cockpit with presets but no asset picker/query is flagged."""
    file = tmp_path / "dangling-cockpit.tsx"
    file.write_text(
        """export const DEMO_PRESETS = [{ label: 'test', val: 1 }]
export function DanglingCockpit() {
  const [val, setVal] = useState(DEMO_PRESETS[0])
  return <div>{val.label}</div>
}
""",
        encoding="utf-8",
    )
    violations = scan_file(file, tmp_path)
    assert len(violations) >= 1
    assert any(v["rule"] == "UNGROUNDED_PRESET_COCKPIT" for v in violations)


def test_adversarial_dangling_action_alert(tmp_path: Path):
    """Adversarial Test: Verify save button with only an alert is flagged."""
    file = tmp_path / "fake-save.tsx"
    file.write_text(
        """export function FakeSave() {
  return <button onClick={() => alert('保存成功')}>保存</button>
}
""",
        encoding="utf-8",
    )
    violations = scan_file(file, tmp_path)
    assert len(violations) >= 1
    assert any(v["rule"] == "DANGLING_ACTION_FAKE_ALERT" for v in violations)


def test_anti_demo_service_and_api_endpoint():
    """Verify runtime service caching and FastAPI endpoint /api/v1/system/anti-demo-audit."""
    service = AntiDemoGateService.get_instance()
    report1 = service.audit(force_refresh=True)
    assert report1.status == "PASS"
    assert report1.anti_demo_gate_pass_rate == 100.0
    assert report1.cached is False

    # Second call within TTL should be served from snapshot cache
    report2 = service.audit(force_refresh=False)
    assert report2.cached is True
    assert report2.scanned_components == report1.scanned_components

    # Live FastAPI endpoint test
    app = create_app()
    dummy_ctx = RequestContext(
        user=UserIdentifier(user_id="test_user", account_id="default"),
        role=Role.ADMIN,
    )
    app.dependency_overrides[get_request_context] = lambda: dummy_ctx

    client = TestClient(app)
    res = client.get("/api/v1/system/anti-demo-audit")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "PASS"
    assert data["anti_demo_gate_pass_rate"] == 100.0
    assert data["total_dangling_features_count"] == 0
