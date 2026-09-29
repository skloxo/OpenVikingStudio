# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Card-20F: VikingFS RelationStore, RelationService, and Live Topology Graph.
(Card-Graph-RealTopology-DynamicWiring / v1.5.82)
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.service.relation_service import RelationService
from openviking.storage.relations_store import RelationStore
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def temp_relation_store():
    """Create isolated temporary RelationStore instance."""
    tmpdir = tempfile.mkdtemp(prefix="test_rel_store_")
    db_file = Path(tmpdir) / "test_relations.db"
    store = RelationStore(db_path=db_file)
    RelationStore._instance = store
    yield store
    RelationStore.reset_instance()
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_relation_store_crud(temp_relation_store):
    """Verify add_link, add_links_batch, get_outbound, get_inbound, remove_link."""
    store = temp_relation_store

    # 1. Add single link
    item = store.add_link(
        from_uri="viking://resources/doc_a.md",
        to_uri="viking://resources/doc_b.md",
        reason="依赖模块 A",
        link_type="depends_on",
        weight=1.5,
    )
    assert item.from_uri == "viking://resources/doc_a.md"
    assert item.to_uri == "viking://resources/doc_b.md"
    assert item.reason == "依赖模块 A"

    # 2. Add batch links
    items = store.add_links_batch(
        from_uri="viking://resources/doc_a.md",
        to_uris=["viking://resources/doc_c.md", "viking://resources/doc_d.md"],
        reason="相关参考",
        link_type="references",
    )
    assert len(items) == 2

    # 3. Verify outbound query
    outbound = store.get_outbound("viking://resources/doc_a.md")
    assert len(outbound) == 3
    targets = [o["uri"] for o in outbound]
    assert "viking://resources/doc_b.md" in targets
    assert "viking://resources/doc_c.md" in targets
    assert "viking://resources/doc_d.md" in targets

    # 4. Verify inbound query
    inbound_b = store.get_inbound("viking://resources/doc_b.md")
    assert len(inbound_b) == 1
    assert inbound_b[0]["uri"] == "viking://resources/doc_a.md"

    # 5. Total count
    assert store.count_links() == 3

    # 6. Remove link
    removed = store.remove_link("viking://resources/doc_a.md", "viking://resources/doc_b.md")
    assert removed is True
    assert store.count_links() == 2

    outbound_after = store.get_outbound("viking://resources/doc_a.md")
    assert len(outbound_after) == 2


@pytest.mark.asyncio
async def test_relation_service_integration(temp_relation_store):
    """Verify RelationService link, relations, unlink delegation."""
    store = temp_relation_store
    service = RelationService(store=store)

    ctx = RequestContext(user=UserIdentifier(account_id="test", user_id="test"), role=Role.ADMIN)

    # Link
    await service.link(
        from_uri="viking://resources/skills/tdd",
        uris=["viking://resources/skills/code-review", "viking://resources/skills/implement"],
        ctx=ctx,
        reason="工程标准流转",
    )

    # Relations
    rels = await service.relations("viking://resources/skills/tdd", ctx=ctx)
    assert len(rels) == 2
    uris = [r["uri"] for r in rels]
    assert "viking://resources/skills/code-review" in uris
    assert "viking://resources/skills/implement" in uris

    # Unlink
    await service.unlink("viking://resources/skills/tdd", "viking://resources/skills/code-review", ctx=ctx)
    rels_after = await service.relations("viking://resources/skills/tdd", ctx=ctx)
    assert len(rels_after) == 1
    assert rels_after[0]["uri"] == "viking://resources/skills/implement"


def test_relations_api_and_topology_graph(temp_relation_store):
    """Verify REST endpoints for link, relations, and topology graph."""
    store = temp_relation_store
    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    # 1. POST /api/v1/relations/link
    link_resp = client.post(
        "/api/v1/relations/link",
        json={
            "from_uri": "viking://resources/arch_v1.md",
            "to_uris": ["viking://resources/arch_v2.md"],
            "reason": "版本演进",
            "link_type": "evolves_to",
        },
    )
    assert link_resp.status_code == 200

    # 2. GET /api/v1/relations?uri=...
    get_resp = client.get("/api/v1/relations?uri=viking://resources/arch_v1.md")
    assert get_resp.status_code == 200
    res_data = get_resp.json()
    assert res_data["status"] == "ok"
    assert len(res_data["result"]) == 1
    assert res_data["result"][0]["uri"] == "viking://resources/arch_v2.md"

    # 3. GET /api/v1/relations/topology
    topo_resp = client.get("/api/v1/relations/topology")
    assert topo_resp.status_code == 200
    topo_data = topo_resp.json()
    assert topo_data["status"] == "ok"
    result = topo_data["result"]
    assert "nodes" in result
    assert "edges" in result
    assert "stats" in result

    # Check explicit relation rendered into graph
    node_ids = {n["id"] for n in result["nodes"]}
    assert "viking://resources/arch_v1.md" in node_ids
    assert "viking://resources/arch_v2.md" in node_ids

    # Check edge
    edge_pairs = {(e["source"], e["target"]) for e in result["edges"]}
    assert ("viking://resources/arch_v1.md", "viking://resources/arch_v2.md") in edge_pairs

    # 4. Check canonical alias /api/v1/relations/graph
    graph_resp = client.get("/api/v1/relations/graph")
    assert graph_resp.status_code == 200
    assert graph_resp.json()["status"] == "ok"
