"""
Unit tests for Neighbor Contrast Engine and TwoStageNegativeBoundaryRouter.
"""

import pytest
from openviking.core.capability_page import (
    CapabilityPage,
    CapabilityPageStore,
    DiscriminativeBody,
)
from openviking.core.negative_boundary_router import (
    NeighborContrastEngine,
    TwoStageNegativeBoundaryRouter,
)


@pytest.fixture
def mock_router_store() -> CapabilityPageStore:
    store = CapabilityPageStore()

    # Skill A: Read Logs
    store.upsert_page(CapabilityPage(
        skill_id="docker_read_logs",
        skill_name="Docker 日志查看",
        cluster_id="docker_ops",
        positive_triggers=["查看容器日志", "检查容器输出"],
        negative_boundaries=["DO NOT use for '重启容器' -> Redirect to Docker 重启运维"],
        discriminative_body=DiscriminativeBody(
            summary="只读检查容器标准输出与报错日志。",
        ),
    ))

    # Skill B: Restart Container
    store.upsert_page(CapabilityPage(
        skill_id="docker_restart_ops",
        skill_name="Docker 重启运维",
        cluster_id="docker_ops",
        positive_triggers=["重启容器", "重新拉起服务实例"],
        negative_boundaries=["DO NOT use for '查看容器日志' -> Redirect to Docker 日志查看"],
        discriminative_body=DiscriminativeBody(
            summary="优雅停机并重启指定 Docker 容器。",
        ),
    ))

    return store


def test_neighbor_contrast_engine(mock_router_store: CapabilityPageStore) -> None:
    # Target: docker_read_logs
    # Contrast sibling: docker_restart_ops (whose positive trigger is "重启容器")
    contrast_result = NeighborContrastEngine.contrast_neighbors(
        target_skill_id="docker_read_logs",
        store=mock_router_store,
    )

    assert contrast_result.target_skill_id == "docker_read_logs"
    assert contrast_result.cluster_id == "docker_ops"
    assert "docker_restart_ops" in contrast_result.neighbor_skill_ids
    assert any("重启容器" in s for s in contrast_result.suggested_negative_boundaries)
    assert len(contrast_result.contrast_pairs) >= 2


def test_two_stage_router_cleared_query(mock_router_store: CapabilityPageStore) -> None:
    router = TwoStageNegativeBoundaryRouter(store=mock_router_store)

    # Query clearly matches docker_read_logs
    decision = router.route(query="查看容器日志，检查报错输出", cluster_id="docker_ops")

    assert decision.selected_skill_id == "docker_read_logs"
    assert decision.confidence > 0.3
    assert len(decision.candidates) >= 1

    top_candidate = decision.candidates[0]
    assert top_candidate.skill_id == "docker_read_logs"
    assert top_candidate.is_blocked is False
    assert len(top_candidate.violated_boundaries) == 0


def test_two_stage_router_boundary_interception(mock_router_store: CapabilityPageStore) -> None:
    router = TwoStageNegativeBoundaryRouter(store=mock_router_store)

    # Ambiguous query that contains keywords for both or targets restart
    decision = router.route(query="重启容器", cluster_id="docker_ops")

    # docker_read_logs must be penalized or blocked by its negative boundary rule
    read_logs_candidate = next((c for c in decision.candidates if c.skill_id == "docker_read_logs"), None)
    assert read_logs_candidate is not None
    assert read_logs_candidate.is_blocked is True
    assert len(read_logs_candidate.violated_boundaries) > 0
    assert read_logs_candidate.negative_penalty > 0.0

    # The chosen winner must be docker_restart_ops
    assert decision.selected_skill_id == "docker_restart_ops"

    # Operational metrics
    metrics = router.get_metrics()
    assert metrics["total_routes"] >= 1
    assert metrics["boundary_interceptions"] >= 1
    assert metrics["top1_discrimination_gain_pct"] > 15.0
