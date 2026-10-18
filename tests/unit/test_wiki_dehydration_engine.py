# -*- coding: utf-8 -*-
"""Unit tests for Card-LLMLingua-01 (Microsoft LLMLingua-2 Wiki Dehydration Engine).

Validates:
1. Structural preservation: YAML frontmatter, code blocks, and markdown tables are 100% frozen.
2. Hardcoded tuning safeguards: rate=0.50, threshold=0.35, critical negation & control word locks.
3. Fallback syntactic pruner: Strips boilerplate and conversational padding without semantic loss.
4. Telemetry stats tracking: Document counts, tokens saved, compression ratios, and latency.
5. REST API endpoints: /api/v1/wiki/dehydrate, /api/v1/wiki/dehydrate/batch, /api/v1/wiki/dehydrate/stats.
"""

import pytest
from fastapi.testclient import TestClient

from openviking.service.wiki_dehydration_engine import (
    DehydrationRequest,
    WikiDehydrationEngine,
)
from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role, UserIdentifier

SAMPLE_DOCUMENT = """---
title: OpenViking Architecture Blueprint
version: 1.5.46
category: knowledge-base
---

# 1. 概述与设计原则
众所周知，在现代软件工程中，架构的高内聚低耦合是不可或缺的。换句话说，系统的稳定性至关重要。
我们必须严格遵守以下准则：
- 严禁在代码中硬编码任何真实 API Key
- 系统运行状态必须保证 Fail-Fast 鲁棒性
- 任何情况下不能忽略未处理的异常

```python
def calculate_metrics(tokens: int) -> dict:
    # Critical calculation logic
    return {"tokens": tokens, "valid": True}
```

显而易见的是，下表展示了系统的分级指标：

| 引擎类型 | 目标压缩率 | 适用场景 |
| :--- | :--- | :--- |
| SkillZip | 30%~50% | 结构化技能六元组 |
| LLMLingua-2 | ~50% | 静态长篇 Wiki 与白皮书 |

毋庸置疑，通过合理的架构分层，我们可以显著降低 Token 消耗。
"""


@pytest.fixture
def engine():
    return WikiDehydrationEngine.get_instance()


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    return TestClient(app)


def test_structural_preservation_yaml(engine):
    """Ensure YAML frontmatter is 100% preserved without token alterations."""
    req = DehydrationRequest(content=SAMPLE_DOCUMENT, preserve_structure=True)
    res = engine.dehydrate(req)

    assert "---" in res.dehydrated_content
    assert "title: OpenViking Architecture Blueprint" in res.dehydrated_content
    assert "version: 1.5.46" in res.dehydrated_content
    assert res.structural_fidelity == 100.0
    assert res.frozen_blocks_count >= 3


def test_structural_preservation_code_and_tables(engine):
    """Ensure code blocks and Markdown tables remain intact."""
    req = DehydrationRequest(content=SAMPLE_DOCUMENT, preserve_structure=True)
    res = engine.dehydrate(req)

    # Code block intact
    assert "def calculate_metrics(tokens: int) -> dict:" in res.dehydrated_content
    assert 'return {"tokens": tokens, "valid": True}' in res.dehydrated_content

    # Table intact
    assert "| 引擎类型 | 目标压缩率 | 适用场景 |" in res.dehydrated_content
    assert "| SkillZip | 30%~50% | 结构化技能六元组 |" in res.dehydrated_content


def test_control_words_and_negations_preserved(engine):
    """Verify essential negative defense words and control tokens are kept."""
    req = DehydrationRequest(content=SAMPLE_DOCUMENT, preserve_structure=True)
    res = engine.dehydrate(req)

    assert "严禁" in res.dehydrated_content
    assert "必须" in res.dehydrated_content
    assert "不能" in res.dehydrated_content


def test_syntactic_pruner_removes_fillers(engine):
    """Verify conversational filler phrases are stripped by pruner."""
    req = DehydrationRequest(content=SAMPLE_DOCUMENT, preserve_structure=True)
    res = engine.dehydrate(req)

    # Verbose filler words should be removed or reduced
    assert "众所周知" not in res.dehydrated_content
    assert "换句话说" not in res.dehydrated_content
    assert "显而易见的是" not in res.dehydrated_content
    assert "毋庸置疑" not in res.dehydrated_content
    assert res.tokens_saved > 0
    assert res.compressed_chars < res.original_chars


def test_telemetry_stats_accumulation(engine):
    """Verify runtime metrics are aggregated properly."""
    stats_before = engine.get_stats()
    req = DehydrationRequest(content=SAMPLE_DOCUMENT, preserve_structure=True)
    res = engine.dehydrate(req)

    stats_after = engine.get_stats()
    assert stats_after.total_documents == stats_before.total_documents + 1
    assert stats_after.total_tokens_saved >= stats_before.total_tokens_saved + res.tokens_saved
    assert stats_after.avg_latency_ms >= 0.0


def test_rest_api_endpoints(client):
    """Verify HTTP REST endpoints for single and batch dehydration."""
    # 1. Single dehydrate
    payload = {
        "content": SAMPLE_DOCUMENT,
        "rate": 0.50,
        "threshold": 0.35,
        "preserve_structure": True,
    }
    resp = client.post("/api/v1/wiki/dehydrate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "dehydrated_content" in data
    assert data["structural_fidelity"] == 100.0
    assert data["tokens_saved"] > 0

    # 2. Stats
    resp_stats = client.get("/api/v1/wiki/dehydrate/stats")
    assert resp_stats.status_code == 200
    stats = resp_stats.json()
    assert stats["total_documents"] >= 1

    # 3. Batch dehydrate
    batch_payload = {
        "items": [
            "众所周知，第一点是必须遵守规则。",
            "换句话说，第二点是严禁泄漏密钥。",
        ],
        "rate": 0.50,
    }
    resp_batch = client.post("/api/v1/wiki/dehydrate/batch", json=batch_payload)
    assert resp_batch.status_code == 200
    batch_data = resp_batch.json()
    assert len(batch_data["results"]) == 2
    assert batch_data["total_tokens_saved"] >= 0
