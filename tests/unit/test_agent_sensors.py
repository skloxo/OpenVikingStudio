# -*- coding: utf-8 -*-
"""Unit tests for Agent 3D Performance Sensors Aggregator."""

import os
import shutil
import tempfile
import pytest

from openviking.core.agent_sensors import (
    AgentSensorTelemetry,
    AgentSensorsAggregator,
)


@pytest.fixture
def temp_aggregator():
    temp_dir = tempfile.mkdtemp()
    aggregator = AgentSensorsAggregator(log_dir=temp_dir)
    yield aggregator
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_record_telemetry_and_metrics_calculation(temp_aggregator):
    # Effective 700 / Total 1000 = 0.70 SNR (optimal)
    # Top-5 hits 4 / 5 = 0.80 P@5 (optimal)
    # Interventions 0 = False
    pt1 = temp_aggregator.record_telemetry(
        session_id="sess-001",
        effective_tokens=700,
        total_tokens=1000,
        top5_hits=4,
        interventions_count=0,
    )
    assert pt1.token_snr == 0.70
    assert pt1.p5_precision == 0.80
    assert pt1.human_intervention_flag is False

    # Check JSONL written
    assert os.path.exists(temp_aggregator.metrics_file)
    with open(temp_aggregator.metrics_file, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1

    # Second point with intervention and lower SNR
    pt2 = temp_aggregator.record_telemetry(
        session_id="sess-002",
        effective_tokens=400,
        total_tokens=1000,
        top5_hits=3,
        interventions_count=2,
    )
    assert pt2.token_snr == 0.40
    assert pt2.p5_precision == 0.60
    assert pt2.human_intervention_flag is True

    summary = temp_aggregator.get_aggregated_metrics()
    assert summary["sample_count"] == 2
    # Avg SNR: (0.7 + 0.4) / 2 = 0.55 (< 0.65 => degraded)
    assert summary["avg_token_snr"] == 0.55
    assert summary["snr_status"] == "degraded"
    # Avg P@5: (0.8 + 0.6) / 2 = 0.70 (< 0.80 => suboptimal)
    assert summary["avg_p5_precision"] == 0.70
    assert summary["p5_status"] == "suboptimal"
    # Intervention rate: 1/2 = 0.50 (> 0.15 => elevated)
    assert summary["human_intervention_rate"] == 0.50
    assert summary["intervention_status"] == "elevated"
    assert len(summary["recent_timeline"]) == 2


def test_empty_cold_state():
    temp_dir = tempfile.mkdtemp()
    aggregator = AgentSensorsAggregator(log_dir=temp_dir)
    summary = aggregator.get_aggregated_metrics()
    assert summary["sample_count"] == 0
    assert summary["avg_token_snr"] == 0.0
    assert summary["snr_status"] == "insufficient_data"
    shutil.rmtree(temp_dir, ignore_errors=True)
