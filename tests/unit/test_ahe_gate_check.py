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
        mock_engine.list_manifests.return_value = []
        mock_get_inst.return_value = mock_engine

        assert run_ahe_check() == 0


def test_ahe_gate_check_clean_manifest():
    """Active manifest with clean snapshot should pass with exit code 0."""
    manifest = AHEManifest(
        manifest_id="test-clean-manifest",
        skill_name="test-skill",
        status=AHEStatus.ACTIVE,
    )
    with patch("scripts.ahe_gate_check.AHEEngine.get_instance") as mock_get_inst:
        mock_engine = MagicMock()
        mock_engine.list_manifests.return_value = [manifest]
        mock_engine.check_snapshot_drift.return_value = {
            "snapshot_clean": True,
            "drifted_files": [],
        }
        mock_get_inst.return_value = mock_engine

        assert run_ahe_check() == 0


def test_ahe_gate_check_drift_detected():
    """Active manifest with drifted snapshot files should fail with exit code 1."""
    manifest = AHEManifest(
        manifest_id="test-drift-manifest",
        skill_name="test-skill",
        status=AHEStatus.ACTIVE,
    )
    with patch("scripts.ahe_gate_check.AHEEngine.get_instance") as mock_get_inst:
        mock_engine = MagicMock()
        mock_engine.list_manifests.return_value = [manifest]
        mock_engine.check_snapshot_drift.return_value = {
            "snapshot_clean": False,
            "drifted_files": [{"path": "skills/test/SKILL.md", "reason": "hash_mismatch"}],
        }
        mock_get_inst.return_value = mock_engine

        assert run_ahe_check() == 1


def test_ahe_gate_check_polar_failure():
    """Active manifest with polar judge assertion failure should fail with exit code 1."""
    manifest = AHEManifest(
        manifest_id="test-polar-manifest",
        skill_name="test-skill",
        status=AHEStatus.VERIFIED,
    )
    with patch("scripts.ahe_gate_check.AHEEngine.get_instance") as mock_get_inst:
        mock_engine = MagicMock()
        mock_engine.list_manifests.return_value = [manifest]
        mock_engine.check_snapshot_drift.return_value = {
            "snapshot_clean": True,
            "drifted_files": [],
        }
        mock_engine.verify_manifest.return_value = {
            "results": [
                {
                    "assumption_id": "asm-1",
                    "command": "python test.py",
                    "verdict": "fail",
                    "exit_code": 1,
                }
            ]
        }
        mock_get_inst.return_value = mock_engine

        assert run_ahe_check(run_polar=True) == 1
