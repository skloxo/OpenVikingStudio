# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

import pytest
from unittest.mock import MagicMock, patch

from openviking.core.ahe_manifest import AHEManifest, AHEStatus
from scripts.ahe_gate_check import run_ahe_check


def test_ahe_gate_check_no_manifests():
    """When no manifests exist, check should pass with exit code 0."""
    with patch("scripts.ahe_gate_check.AHEEngine.get_instance") as mock_get_inst:
        mock_engine = MagicMock()
        mock_engine.run_pre_release_gate.return_value = {
            "total_manifests": 0,
            "drift_violations": [],
            "polar_violations": [],
            "gate_passed": True,
        }
        mock_get_inst.return_value = mock_engine

        assert run_ahe_check() == 0


def test_ahe_gate_check_clean_manifest():
    """Active manifest with clean snapshot should pass with exit code 0."""
    with patch("scripts.ahe_gate_check.AHEEngine.get_instance") as mock_get_inst:
        mock_engine = MagicMock()
        mock_engine.run_pre_release_gate.return_value = {
            "total_manifests": 1,
            "drift_violations": [],
            "polar_violations": [],
            "gate_passed": True,
        }
        mock_get_inst.return_value = mock_engine

        assert run_ahe_check() == 0


def test_ahe_gate_check_drift_detected():
    """Active manifest with drifted snapshot files should fail with exit code 1."""
    with patch("scripts.ahe_gate_check.AHEEngine.get_instance") as mock_get_inst:
        mock_engine = MagicMock()
        mock_engine.run_pre_release_gate.return_value = {
            "total_manifests": 1,
            "drift_violations": ["Manifest [m-1] Skill [test-skill]: Drift in skills/test/SKILL.md"],
            "polar_violations": [],
            "gate_passed": False,
        }
        mock_get_inst.return_value = mock_engine

        assert run_ahe_check() == 1


def test_ahe_gate_check_polar_failure():
    """Active manifest with polar judge assertion failure should fail with exit code 1."""
    with patch("scripts.ahe_gate_check.AHEEngine.get_instance") as mock_get_inst:
        mock_engine = MagicMock()
        mock_engine.run_pre_release_gate.return_value = {
            "total_manifests": 1,
            "drift_violations": [],
            "polar_violations": ["Manifest [m-1] Assumption [asm-1]: python test.py"],
            "gate_passed": False,
        }
        mock_get_inst.return_value = mock_engine

        assert run_ahe_check(run_polar=True) == 1
