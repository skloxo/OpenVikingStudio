"""
Unit tests for Tencent Capability Page and Deployment Isolation Indexer.
"""

import pytest
from openviking.core.capability_page import (
    CapabilityPage,
    CapabilityPageStore,
    DeploymentIsolationIndexer,
    DiscriminativeBody,
)


@pytest.fixture
def clean_store() -> CapabilityPageStore:
    return CapabilityPageStore()


def test_capability_page_crud(clean_store: CapabilityPageStore) -> None:
    page = CapabilityPage(
        skill_id="test_git_push",
        skill_name="Git 推流与 PR 提交",
        cluster_id="vcs_ops",
        positive_triggers=["提交代码", "推送 PR", "推流到 GitHub"],
        negative_boundaries=["DO NOT use for 'git clone 裸拉取'"],
        discriminative_body=DiscriminativeBody(
            summary="自动化推流并创建 PR，附带安全审计门禁。",
            prerequisites=["git installed"],
            inputs={"branch": "string"},
            outputs={"pr_url": "string"},
        ),
    )

    # 1. Upsert
    clean_store.upsert_page(page)
    assert clean_store.count() == 1

    # 2. Get
    retrieved = clean_store.get_page("test_git_push")
    assert retrieved is not None
    assert retrieved.skill_name == "Git 推流与 PR 提交"
    assert len(retrieved.positive_triggers) == 3
    assert len(retrieved.negative_boundaries) == 1

    # 3. List
    pages = clean_store.list_pages(cluster_id="vcs_ops")
    assert len(pages) == 1
    assert pages[0].skill_id == "test_git_push"

    # 4. Delete
    assert clean_store.delete_page("test_git_push") is True
    assert clean_store.get_page("test_git_push") is None
    assert clean_store.count() == 0


def test_deployment_isolation_rule() -> None:
    """
    CRITICAL RULE:
    Index text must strictly contain T+ and B, but NEVER contain T-.
    """
    page = CapabilityPage(
        skill_id="docker_logs_view",
        skill_name="Docker 日志审计",
        cluster_id="container_ops",
        positive_triggers=["查看容器日志", "检查报错信息"],
        negative_boundaries=["DO NOT use for '重启 Docker 容器服务' -> 严禁用于重启"],
        discriminative_body=DiscriminativeBody(
            summary="只读检查 Docker stdout/stderr 日志流。",
            prerequisites=["docker cli"],
        ),
    )

    indexed_text = DeploymentIsolationIndexer.get_indexable_content(page)

    # Assert T+ and B are present
    assert "Docker 日志审计" in indexed_text
    assert "查看容器日志" in indexed_text
    assert "只读检查 Docker stdout/stderr 日志流" in indexed_text

    # Assert T- is strictly absent
    assert "严禁用于重启" not in indexed_text
    assert "重启 Docker 容器服务" not in indexed_text

    # Verify retina isolation
    assert DeploymentIsolationIndexer.verify_isolation(page, indexed_text) is True

    # If someone accidentally leaked T- into the indexed text, it must be caught
    contaminated_text = indexed_text + "\nDO NOT use for '重启 Docker 容器服务' -> 严禁用于重启"
    assert DeploymentIsolationIndexer.verify_isolation(page, contaminated_text) is False
