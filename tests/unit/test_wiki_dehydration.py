# -*- coding: utf-8 -*-
"""Unit tests for Card-LLMLingua-01: Wiki Dehydration & LLMLingua-2 Adapter.

Validates:
1. Hardcoded Safeguard Hyperparameters (rate=0.50, threshold=0.35, protected tokens).
2. Structural Freezing: YAML Frontmatter (100% byte-for-byte preserved).
3. Structural Freezing: Code blocks and Markdown headings intact.
4. Negation & Control word protection (zero semantic inversion).
5. Fluff pruning & measurable token reduction.
6. Cumulative telemetry metrics tracking.
7. FastAPI REST API endpoints (/api/v1/wiki/dehydrate, /batch, /stats).
"""

import pytest
from fastapi.testclient import TestClient

from openviking.service.wiki_dehydration_engine import (
    HARDCODED_DEFAULT_RATE,
    HARDCODED_DEFAULT_THRESHOLD,
    HARDCODED_PROTECTED_TOKENS,
    DehydrationRequest,
    WikiDehydrationEngine,
)


SAMPLE_WIKI_DOC = """---
title: OpenViking High-Density Cockpit Architecture
version: 1.5.46
status: production
---
# 架构总览与第一性原理

众所周知，系统界面是数据的容器，而不是任人涂抹的画布。
显而易见的是，我们必须严格遵循座舱级最高信息密度律。
在日常工程开发过程中，毋庸置疑的是，严禁任何人在代码库中私自引入未经审计的第三方依赖。
值得注意的是，我们必须保护否定词和控制词，严禁反转核心语义。

```python
def check_invariant(rule: str) -> bool:
    # 绝对禁止任何绿色
    assert "green" not in rule.lower()
    return True
```

总的来说，归根结底，正如前文所述，我们必须确保单文件规模在 100 到 300 行的黄金甜点区内。
"""


def test_hardcoded_hyperparameter_safeguards():
    """Verify that model tuning hyperparameters are frozen as SSOT in code."""
    assert HARDCODED_DEFAULT_RATE == 0.50
    assert HARDCODED_DEFAULT_THRESHOLD == 0.35
    for token in ["not", "never", "严禁", "必须", "禁止", "红线"]:
        assert token in HARDCODED_PROTECTED_TOKENS


def test_yaml_frontmatter_protection():
    """Verify YAML frontmatter is 100% preserved byte-for-byte."""
    engine = WikiDehydrationEngine.get_instance()
    req = DehydrationRequest(content=SAMPLE_WIKI_DOC)
    result = engine.dehydrate(req)

    assert result.structural_integrity_verified is True
    assert result.frozen_blocks_count >= 2  # YAML + Code block + Headings
    # YAML frontmatter must start the document exactly
    assert result.dehydrated_text.startswith("---\ntitle: OpenViking High-Density Cockpit Architecture")
    assert "version: 1.5.46\nstatus: production\n---" in result.dehydrated_text


def test_code_block_protection():
    """Verify code blocks are unaffected by text compression."""
    engine = WikiDehydrationEngine.get_instance()
    req = DehydrationRequest(content=SAMPLE_WIKI_DOC)
    result = engine.dehydrate(req)

    expected_code = '```python\ndef check_invariant(rule: str) -> bool:\n    # 绝对禁止任何绿色\n    assert "green" not in rule.lower()\n    return True\n```'
    assert expected_code in result.dehydrated_text


def test_negation_word_protection():
    """Verify critical control and negation words are strictly retained."""
    engine = WikiDehydrationEngine.get_instance()
    req = DehydrationRequest(content=SAMPLE_WIKI_DOC)
    result = engine.dehydrate(req)

    # Core control rules must not have negation words dropped
    assert "必须" in result.dehydrated_text
    assert "严禁" in result.dehydrated_text


def test_fluff_pruning_and_token_reduction():
    """Verify conversational filler words are pruned and tokens are saved."""
    engine = WikiDehydrationEngine.get_instance()
    req = DehydrationRequest(content=SAMPLE_WIKI_DOC)
    result = engine.dehydrate(req)

    # Conversational padding should be pruned
    assert "众所周知" not in result.dehydrated_text
    assert "显而易见" not in result.dehydrated_text
    assert "总的来说" not in result.dehydrated_text
    assert "毋庸置疑" not in result.dehydrated_text

    # Verify token savings
    assert result.tokens_saved > 0
    assert result.compression_ratio > 0.0
    assert result.latency_ms >= 0.0


def test_telemetry_metrics_tracking():
    """Verify cumulative dehydration stats are tracked in singleton."""
    engine = WikiDehydrationEngine.get_instance()
    telemetry = engine.get_telemetry()
    assert telemetry.total_dehydrations > 0
    assert telemetry.total_tokens_saved > 0
    assert telemetry.avg_latency_ms >= 0.0


def test_rest_api_dehydrate():
    """Verify FastAPI REST endpoint /api/v1/wiki/dehydrate."""
    from fastapi import FastAPI
    from openviking.server.routers.wiki_dehydration import router as wiki_router
    from openviking.server.auth import get_request_context
    from openviking.server.identity import RequestContext, Role, UserIdentifier

    app = FastAPI()
    app.include_router(wiki_router)
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    # 1. Single document dehydration
    resp = client.post(
        "/api/v1/wiki/dehydrate",
        json={"content": SAMPLE_WIKI_DOC, "target_rate": 0.50},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["structural_integrity_verified"] is True
    assert data["tokens_saved"] > 0
    assert "---" in data["dehydrated_text"]

    # 2. Batch dehydration
    batch_resp = client.post(
        "/api/v1/wiki/dehydrate/batch",
        json={"documents": [SAMPLE_WIKI_DOC, "# Simple doc\n众所周知测试。"], "target_rate": 0.50},
    )
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()
    assert batch_data["batch_count"] == 2
    assert batch_data["total_tokens_saved"] > 0

    # 3. Telemetry stats
    stats_resp = client.get("/api/v1/wiki/dehydrate/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_dehydrations"] >= 1
