# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

import httpx

from openviking_cli.retrieve import ContextType, MatchedContext


class _FakeFindResult:
    def __init__(self, memories):
        self.memories = memories


def _memory(uri: str, score: float = 0.9, abstract: str = ""):
    return MatchedContext(
        uri=uri,
        context_type=ContextType.MEMORY,
        level=2,
        score=score,
        abstract=abstract,
        category=uri.split("/memories/", 1)[-1].split("/", 1)[0],
    )


def _self_memory_target(target_uri: str) -> bool:
    return target_uri.endswith("/memories/events") and "/peers/" not in target_uri


async def test_default_scope_searches_other_peers_with_an_open_context(
    client: httpx.AsyncClient,
):
    response = await client.post(
        "/api/v1/search/recall",
        headers={"X-OpenViking-Actor-Peer": "current"},
        json={
            "query": "peer memory",
            "quotas": {"events": 3, "entities": 0, "preferences": 0, "experiences": 0},
            "max_chars": 5000,
        },
    )
    # Deprecated /recall has been retired in Card-80 (v1.7.34)
    assert response.status_code == 404


async def test_actor_scope_skips_the_open_peer_scan(
    client: httpx.AsyncClient,
):
    response = await client.post(
        "/api/v1/search/recall",
        headers={"X-OpenViking-Actor-Peer": "current"},
        json={
            "query": "peer memory",
            "peer_scope": "actor",
            "quotas": {"events": 1, "entities": 0, "preferences": 0, "experiences": 0},
            "max_chars": 300,
        },
    )
    assert response.status_code == 404
