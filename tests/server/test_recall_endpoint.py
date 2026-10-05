# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

import httpx

from openviking.retrieve.context_assembler.params import DEFAULT_QUOTAS
from openviking.retrieve.context_assembler.recall_preset import (
    DEFAULT_MIN_SCORE,
    RECALL_SCORE_THRESHOLD,
    fold_recall_request,
)
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


def test_v1_aliases_fold_into_the_context_contract():
    params, aliases = fold_recall_request(
        {
            "query": "q",
            "max_chars": 6500,
            "min_score": 0.1,
            "render": "compact",
            "session_id": "s1",
        },
        {"max_chars", "min_score", "render", "session_id"},
    )

    assert params.max_tokens == 1625
    assert params.score_threshold == 0.1
    assert params.detail == "abstract"
    assert params.quotas == DEFAULT_QUOTAS
    assert params.dedup_turns == 5
    assert aliases == ["max_chars", "min_score", "render"]

    defaults, _ = fold_recall_request(
        {"query": "q", "min_score": DEFAULT_MIN_SCORE},
        set(),
    )
    assert defaults.score_threshold == RECALL_SCORE_THRESHOLD == DEFAULT_MIN_SCORE == 0.1
    assert defaults.dedup_turns == 0

    coding, _ = fold_recall_request(
        {"query": "q", "score_threshold": 0.35},
        {"score_threshold"},
    )
    assert coding.score_threshold == 0.35


async def test_recall_endpoint_omitted_min_score_keeps_v1_default(
    client: httpx.AsyncClient,
):
    response = await client.post(
        "/api/v1/search/recall",
        json={
            "query": "compatibility check",
            "quotas": {"events": 1, "entities": 0, "preferences": 0, "experiences": 0},
        },
    )
    # The deprecated /recall endpoint has been completely retired in Card-80 (v1.7.34)
    assert response.status_code == 404


async def test_recall_endpoint_assembles_context_and_signals_deprecation(
    client: httpx.AsyncClient,
):
    response = await client.post(
        "/api/v1/search/recall",
        json={
            "query": "what should I remember",
            "quotas": {"events": 1, "entities": 1, "preferences": 0, "experiences": 0},
            "max_chars": 1600,
            "min_score": 0.1,
            "render": True,
        },
    )
    assert response.status_code == 404


async def test_recall_excludes_profile_and_duplicate_hits(
    client: httpx.AsyncClient,
):
    response = await client.post(
        "/api/v1/search/recall",
        json={"query": "hello", "quotas": {"events": 3, "entities": 0, "preferences": 0}},
    )
    assert response.status_code == 404

