# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Card-166: Skill Usage Telemetry and ROI Engine."""

from datetime import datetime, timezone, timedelta
import tempfile
from pathlib import Path
import pytest

from openviking.service.skill_telemetry import SkillTelemetryStore


@pytest.fixture
def temp_telemetry_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_skill_telemetry.db"
        store = SkillTelemetryStore(db_path=db_path)
        yield store


class TestSkillTelemetryAndRoi:
    """Retina tests for skill invocation telemetry, ROI scoring, and zombie warnings."""

    def test_record_event_and_aggregation(self, temp_telemetry_store: SkillTelemetryStore):
        # Record events for cockpit-ui
        id1 = temp_telemetry_store.record_event(
            skill_id="cockpit-ui",
            bundle_name="cockpit-ui",
            event_type="invoke",
            success=True,
            tokens_saved=1200,
            latency_ms=45.2,
            caller_agent="antigravity",
        )
        assert id1 > 0

        # Record another event
        id2 = temp_telemetry_store.record_event(
            skill_id="cockpit-ui/scenarios/layout.md",
            bundle_name="cockpit-ui",
            event_type="jit_read",
            success=True,
            tokens_saved=800,
            latency_ms=12.0,
            caller_agent="antigravity",
        )
        assert id2 > 0

        # Record failed event for another skill
        id3 = temp_telemetry_store.record_event(
            skill_id="legacy-worker",
            bundle_name="legacy-worker",
            event_type="invoke",
            success=False,
            tokens_saved=0,
            latency_ms=120.0,
            caller_agent="hermes",
        )
        assert id3 > 0

        report = temp_telemetry_store.get_telemetry_report(
            days=30,
            all_registered_skills=["cockpit-ui", "legacy-worker", "dormant-skill"],
        )

        assert report["summary"]["total_invocations"] == 3
        assert report["summary"]["total_tokens_saved"] == 2000
        assert report["summary"]["active_skills_count"] == 3
        assert report["summary"]["dormant_skills_count"] == 1

        # Check bundle ranking
        assert len(report["bundle_rankings"]) >= 2
        cockpit_bundle = next(b for b in report["bundle_rankings"] if b["bundle_name"] == "cockpit-ui")
        assert cockpit_bundle["call_count"] == 2
        assert cockpit_bundle["tokens_saved"] == 2000
        assert cockpit_bundle["roi_score"] > 0

        # Check dormant warnings
        assert any(d["skill_id"] == "dormant-skill" for d in report["dormant_warnings"])

    def test_roi_formula_properties(self):
        # 0 calls -> 0 score
        assert SkillTelemetryStore.calculate_roi(0, 1.0, 5000) == 0.0

        # Low vs high calls
        low_roi = SkillTelemetryStore.calculate_roi(1, 1.0, 100)
        high_roi = SkillTelemetryStore.calculate_roi(100, 1.0, 8000)
        assert high_roi > low_roi
        assert high_roi <= 100.0

        # Failed executions get lower ROI
        perfect_roi = SkillTelemetryStore.calculate_roi(50, 1.0, 5000)
        failed_roi = SkillTelemetryStore.calculate_roi(50, 0.2, 5000)
        assert perfect_roi > failed_roi

    def test_pruning_old_events(self, temp_telemetry_store: SkillTelemetryStore):
        # Insert old event (100 days ago)
        old_time = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        temp_telemetry_store.record_event(
            skill_id="ancient-skill",
            created_at=old_time,
        )

        # Insert fresh event
        temp_telemetry_store.record_event(
            skill_id="fresh-skill",
        )

        # Prune older than 90 days
        pruned = temp_telemetry_store.prune_old_events(retention_days=90)
        assert pruned == 1

        report = temp_telemetry_store.get_telemetry_report(days=180)
        assert report["summary"]["total_invocations"] == 1
        assert report["top_roi_skills"][0]["skill_id"] == "fresh-skill"
