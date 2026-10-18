# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Card-28: Interactive Relations Linking/Unlinking API & VikingFS Grep Integration.
(Card-Relations-Interactive-Linking-And-Grep-Cockpit / v1.5.92)
"""

import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.storage.relations_store import RelationStore
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def isolated_relation_store():
    """Create isolated temporary RelationStore instance."""
    tmpdir = tempfile.mkdtemp(prefix="test_rel_interactive_")
    db_file = Path(tmpdir) / "test_relations.db"
    store = RelationStore(db_path=db_file)
    RelationStore._instance = store
    yield store
    RelationStore.reset_instance()
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def app_client(isolated_relation_store):
    """Create FastAPI test client with mocked admin identity."""
    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    return TestClient(app)


def test_interactive_relation_link_and_unlink(app_client):
    """Test full cycle: link -> query -> unlink -> query verification."""
    client = app_client

    source_uri = "viking://resources/models/llama3.md"
    target_1 = "viking://resources/skills/reasoning.md"
    target_2 = "viking://resources/eval/benchmark.md"

    # 1. Initially no relations
    get_res = client.get(f"/api/v1/relations?uri={source_uri}")
    assert get_res.status_code == 200
    assert len(get_res.json()["result"]) == 0

    # 2. Link target_1 with custom metadata
    link_res_1 = client.post(
        "/api/v1/relations/link",
        json={
            "from_uri": source_uri,
            "to_uris": target_1,
            "reason": "具备强推理能力",
            "link_type": "supports",
            "weight": 2.0,
        },
    )
    assert link_res_1.status_code == 200
    assert link_res_1.json()["status"] == "ok"
    assert link_res_1.json()["result"]["count"] == 1

    # 3. Link target_2 with list format
    link_res_2 = client.post(
        "/api/v1/relations/link",
        json={
            "from_uri": source_uri,
            "to_uris": [target_2],
            "reason": "通过基准评测",
            "link_type": "evaluated_by",
            "weight": 1.0,
        },
    )
    assert link_res_2.status_code == 200
    assert link_res_2.json()["status"] == "ok"

    # 4. Verify relations query lists both
    get_res_2 = client.get(f"/api/v1/relations?uri={source_uri}")
    assert get_res_2.status_code == 200
    rels = get_res_2.json()["result"]
    assert len(rels) == 2
    uris = {r["uri"] for r in rels}
    assert target_1 in uris
    assert target_2 in uris

    # Verify link metadata
    target_1_item = next(r for r in rels if r["uri"] == target_1)
    assert target_1_item["reason"] == "具备强推理能力"
    assert target_1_item["link_type"] == "supports"
    assert target_1_item["weight"] == 2.0

    # 5. Unlink target_1
    unlink_res = client.post(
        "/api/v1/relations/unlink",
        json={
            "from_uri": source_uri,
            "to_uri": target_1,
        },
    )
    assert unlink_res.status_code == 200
    assert unlink_res.json()["status"] == "ok"
    assert unlink_res.json()["result"]["removed"] is True

    # 6. Verify only target_2 remains
    get_res_3 = client.get(f"/api/v1/relations?uri={source_uri}")
    assert get_res_3.status_code == 200
    rels_3 = get_res_3.json()["result"]
    assert len(rels_3) == 1
    assert rels_3[0]["uri"] == target_2

    # 7. Unlink non-existent link returns False without crash
    unlink_res_none = client.post(
        "/api/v1/relations/unlink",
        json={
            "from_uri": source_uri,
            "to_uri": "viking://resources/non_existent.md",
        },
    )
    assert unlink_res_none.status_code == 200
    assert unlink_res_none.json()["result"]["removed"] is False


def test_relation_link_validation(app_client):
    """Verify validation and edge cases for relations API."""
    client = app_client

    # Empty target_uris
    res = client.post(
        "/api/v1/relations/link",
        json={
            "from_uri": "viking://resources/node.md",
            "to_uris": [],
        },
    )
    # Should handle empty list gracefully
    assert res.status_code == 200
    assert res.json()["result"]["count"] == 0
