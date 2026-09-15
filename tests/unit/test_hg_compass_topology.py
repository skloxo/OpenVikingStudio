# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for HG-RAG Hierarchical Compass Topology, Read/Write Decoupling & REST APIs.
(Card-Knowledge-HG-RAG-HierarchicalCompass / v1.5.19)
"""

import pytest
from fastapi.testclient import TestClient

from openviking.retrieve.compass_topology import (
    CompassDirection,
    CompassNode,
    HierarchicalCompassNavigator,
)
from openviking.retrieve.read_write_decoupling import (
    KnowledgeDeskManager,
)
from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking_cli.session.user_id import UserIdentifier


def test_compass_node_and_navigator_traversal():
    """Verify HierarchicalCompassNavigator accurately traverses in 4 compass directions."""
    root = CompassNode(
        node_id="root",
        title="Root Architecture",
        content_snippet="Root Level Overview",
        depth=0,
        breadcrumbs=["Root"],
        children_ids=["child_a", "child_b"],
    )
    child_a = CompassNode(
        node_id="child_a",
        title="Child A Module",
        content_snippet="Module A details",
        depth=1,
        breadcrumbs=["Root", "Child A"],
        parent_id="root",
        sibling_next_id="child_b",
    )
    child_b = CompassNode(
        node_id="child_b",
        title="Child B Module",
        content_snippet="Module B details",
        depth=1,
        breadcrumbs=["Root", "Child B"],
        parent_id="root",
        sibling_prev_id="child_a",
    )

    nav = HierarchicalCompassNavigator()
    for n in (root, child_a, child_b):
        nav.add_node(n)

    # 1. Test Available directions
    root_dirs = nav.get_available_directions("root")
    assert CompassDirection.SOUTH in root_dirs
    assert CompassDirection.NORTH not in root_dirs

    a_dirs = nav.get_available_directions("child_a")
    assert CompassDirection.NORTH in a_dirs
    assert CompassDirection.EAST in a_dirs
    assert CompassDirection.WEST not in a_dirs

    # 2. Test Navigation: Root -> South (Child A)
    res_south = nav.navigate("root", CompassDirection.SOUTH, child_index=0)
    assert res_south.status == "SUCCESS"
    assert res_south.target_node is not None
    assert res_south.target_node.node_id == "child_a"

    # 3. Test Navigation: Child A -> East (Child B)
    res_east = nav.navigate("child_a", CompassDirection.EAST)
    assert res_east.status == "SUCCESS"
    assert res_east.target_node.node_id == "child_b"

    # 4. Test Navigation: Child B -> West (Child A)
    res_west = nav.navigate("child_b", CompassDirection.WEST)
    assert res_west.status == "SUCCESS"
    assert res_west.target_node.node_id == "child_a"

    # 5. Test Navigation: Child A -> North (Root)
    res_north = nav.navigate("child_a", CompassDirection.NORTH)
    assert res_north.status == "SUCCESS"
    assert res_north.target_node.node_id == "root"

    # 6. Test Full Lineage Path
    lineage = nav.get_full_lineage("child_b")
    assert len(lineage) == 2
    assert lineage[0].node_id == "root"
    assert lineage[1].node_id == "child_b"


def test_knowledge_desk_read_write_decoupling_and_swap():
    """Verify KnowledgeDeskManager enforces read/write decoupling and atomic desk swap."""
    desk = KnowledgeDeskManager.get_instance()
    stats = desk.get_stats()
    assert stats.serving_desk_ready
    assert stats.total_nodes >= 8
    assert stats.max_depth >= 2

    # Verify seed nodes exist in serving navigator
    serving_nav = desk.get_serving_navigator()
    root_node = serving_nav.get_node("root_openviking")
    assert root_node is not None
    assert "OpenViking" in root_node.title

    # Stage an edit in editorial desk
    staging_node = CompassNode(
        node_id="sec_test_custom",
        title="Custom Staging Section",
        content_snippet="Experimental Knowledge",
        depth=2,
        breadcrumbs=["OpenViking", "Custom"],
        parent_id="root_openviking",
    )
    desk._editorial_navigator.add_node(staging_node)

    # Prior to swap: serving desk should NOT see staging node
    assert desk.get_serving_navigator().get_node("sec_test_custom") is None

    # Perform atomic swap
    new_stats = desk.swap_editorial_to_serving()
    assert new_stats.active_version > stats.active_version
    # Post swap: serving desk now contains staging node
    assert desk.get_serving_navigator().get_node("sec_test_custom") is not None


def test_hg_compass_rest_api_endpoints():
    """Verify FastAPI endpoints for stats, node query, directional navigation and lineage."""
    app = create_app()

    def override_request_context():
        return RequestContext(
            user=UserIdentifier(account_id="acc_test", user_id="usr_test"),
            role=Role.ADMIN,
        )

    app.dependency_overrides[get_request_context] = override_request_context
    client = TestClient(app)

    # 1. GET /api/v1/rag/compass/stats
    resp = client.get("/api/v1/rag/compass/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_version" in data
    assert data["total_nodes"] > 0
    assert data["serving_desk_ready"] is True

    # 2. GET /api/v1/rag/compass/node/{node_id}
    resp = client.get("/api/v1/rag/compass/node/ch_retrieval")
    assert resp.status_code == 200
    node_data = resp.json()
    assert node_data["node"]["node_id"] == "ch_retrieval"
    assert "north" in node_data["available_directions"]
    assert "south" in node_data["available_directions"]

    # 3. POST /api/v1/rag/compass/navigate
    nav_payload = {
        "anchor_id": "ch_retrieval",
        "direction": "south",
        "child_index": 0,
    }
    resp = client.post("/api/v1/rag/compass/navigate", json=nav_payload)
    assert resp.status_code == 200
    nav_res = resp.json()
    assert nav_res["status"] == "SUCCESS"
    assert nav_res["target_node"]["node_id"] == "sec_bm25"
    assert "双轨多引擎检索体系" in nav_res["lineage_path"]

    # 4. POST /api/v1/rag/compass/lineage
    lineage_payload = {"node_id": "sec_zg"}
    resp = client.post("/api/v1/rag/compass/lineage", json=lineage_payload)
    assert resp.status_code == 200
    lineage_data = resp.json()
    assert lineage_data["depth"] == 2
    assert len(lineage_data["breadcrumbs"]) >= 3
    assert lineage_data["lineage_chain"][0]["node_id"] == "root_openviking"

    # 5. Error handling for non-existent node
    resp_404 = client.get("/api/v1/rag/compass/node/non_existent_node_xyz")
    assert resp_404.status_code == 404
