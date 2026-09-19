# -*- coding: utf-8 -*-
"""Unit tests for Dreaming Defect Miner and EntropyCrystallizer integration."""

import time
import pytest
from openviking.core.dreaming_gate import (
    DreamingDefectMiner,
)
from openviking.service.entropy_crystallizer import (
    MemoryFragment,
)


@pytest.fixture(autouse=True)
def reset_miner():
    miner = DreamingDefectMiner.get_instance()
    miner.defects.clear()
    miner.status.status = "idle"
    miner.status.total_traces_scanned = 0
    miner.status.defects_mined = 0
    miner.status.crystals_fused = 0
    yield
    miner.defects.clear()


def test_dreaming_cycle_clustering():
    miner = DreamingDefectMiner.get_instance()
    traces = [
        {"success": False, "category": "NetworkTimeout", "turn": 3},
        {"success": False, "category": "NetworkTimeout", "turn": 5},
        {"success": False, "category": "NetworkTimeout", "turn": 7},
        {"success": False, "category": "SyntaxError", "turn": 2},
        {"success": True, "category": "NormalExecution", "turn": 1},
    ]

    result = miner.run_dreaming_cycle(sample_traces=traces)
    assert result["status"] == "completed"
    assert result["traces_scanned"] == 5
    assert result["defects_mined"] == 2
    assert len(miner.defects) == 2

    # High severity for cluster >= 3
    network_defect = next(d for d in miner.defects.values() if "NetworkTimeout" in d.cluster_topic)
    assert network_defect.severity == "high"
    assert network_defect.failing_traces_count == 3
    assert "DO NOT repeat failure pattern in NetworkTimeout" in network_defect.candidate_patch


def test_dreaming_cycle_unified_crystallizer():
    miner = DreamingDefectMiner.get_instance()
    from openviking.service.entropy_crystallizer import EntropyCrystallizer
    crystallizer = EntropyCrystallizer.get_instance()
    crystallizer.rule.min_cluster_size = 3
    crystallizer.rule.cooling_period_hours = 0.01  # relaxed for unit test

    now = time.time()
    frag1 = MemoryFragment(
        uri="viking://resources/f1.md",
        content="Antigravity IDE adheres strictly to NO GREEN EVER color standard.",
        created_at=now - 200,
        embedding=[0.8, 0.8, 0.8],
    )
    frag2 = MemoryFragment(
        uri="viking://resources/f2.md",
        content="Cockpit UI enforces NO GREEN EVER visual design covenant.",
        created_at=now - 150,
        embedding=[0.8, 0.81, 0.8],
    )
    frag3 = MemoryFragment(
        uri="viking://resources/f3.md",
        content="Visual system strictly prohibits green throughout all pages.",
        created_at=now - 100,
        embedding=[0.8, 0.79, 0.8],
    )

    result = miner.run_dreaming_cycle(
        sample_traces=[{"success": False, "category": "AssertionError"}],
        pending_fragments=[frag1, frag2, frag3],
    )
    assert result["status"] == "completed"
    assert result["crystals_fused"] == 1
    assert len(result["crystal_ids"]) == 1
    assert miner.status.crystals_fused == 1
