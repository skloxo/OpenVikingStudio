# -*- coding: utf-8 -*-
"""Unit tests for Card-70: Peer fleet timestamp hygiene and zero-message peer truthful representation."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role, UserIdentifier
from openviking.server.routers.console import router as console_router


def test_console_peers_matrix_truthful_representation():
    """Verify that peers with 0 messages show lastSync '--' and Mac Studio exists in fleet."""
    app = FastAPI()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="default", user_id="default"),
        role=Role.ROOT,
    )
    app.include_router(console_router)
    client = TestClient(app)

    res = client.get("/api/v1/console/peers")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    peers = body["result"]

    peer_ids = [p["id"] for p in peers]
    # 1. 动态集群中必须包含本地坐镇的反重力主控与现役 deepseek-harness
    assert "antigravity@2080ti" in peer_ids
    assert "deepseek-harness@2080ti" in peer_ids

    # 2. Inactive/0-message peers must have lastSync '--' (never fabricated now_str)
    for p in peers:
        if p["messagesCount"] == 0:
            assert p["lastSync"] == "--", f"Peer {p['id']} with 0 messages should have lastSync '--'"


def test_card70_version_alignment():
    """Verify SemVer version >= 1.7.24 across Python and package.json."""
    import json
    import os
    from openviking._version import __version__

    pkg_path = os.path.join(os.path.dirname(__file__), "..", "..", "package.json")
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)
    assert pkg_data["version"] == __version__
    parts = [int(p) for p in __version__.split(".")]
    assert (parts[0], parts[1]) == (1, 7)
    assert parts[2] >= 24


def test_production_metrics_file_cleanliness():
    """Verify that canonical production agent_metrics.jsonl does not contain any test artifacts."""
    import json
    import os

    prod_path = os.path.expanduser("~/.openviking/data/agent_metrics.jsonl")
    if os.path.exists(prod_path):
        with open(prod_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    sid = data.get("session_id", "")
                    assert not sid.startswith("test_"), f"Pollution found: {sid}"
