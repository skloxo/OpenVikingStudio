# -*- coding: utf-8 -*-
"""Unit tests for Context Router Pipeline.

Fulfills BLUEPRINT.md Topic 5 Section 4.2.
Verifies:
1. Heterogeneous prompt segmentation (code, prose, skill, static header);
2. TokenShift AST code block routing and syntax validity;
3. Natural language prose dehydration routing;
4. SkillZip contractual compression routing;
5. Static header zero-loss preservation and graceful error fallback;
6. Thread-safe telemetry statistics;
7. FastAPI REST API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role, UserIdentifier
from openviking.service.context_router_engine import ContextRouterEngine
from openviking.service.context_router_segmenter import segment_prompt
from openviking.service.context_router_types import (
    ContextRouteRequest,
    RouteEngine,
    SegmentType,
)


@pytest.fixture
def complex_prompt():
    return """<identity>
You are an expert AI trading strategist operating on OpenViking infrastructure.
Follow all strict risk management invariants.
</identity>

# Market Analysis
Recent micro-structure volatility indicates high liquidity in top perpetual contracts.
The momentum indicators suggest potential breakout patterns across secondary pairs.
We must avoid premature order submissions during wide spread intervals.

```python
import math
from typing import Dict, List, Optional

class RiskEngine:
    \"\"\"Risk assessment engine for algorithmic execution.\"\"\"

    def __init__(self, max_drawdown: float = 0.05):
        self.max_drawdown = max_drawdown
        self.active_positions: Dict[str, float] = {}

    def evaluate_spread(self, bid: float, ask: float) -> bool:
        if bid <= 0 or ask <= 0:
            return False
        spread = (ask - bid) / bid
        if spread > 0.002:
            return False
        return True
```

---
name: position_sizing
description: Dynamic volatility-based position sizing skill.
---
# Rules
1. Calculate ATR for 14 periods.
2. Limit risk per trade to 1% of portfolio equity.
"""


def test_segmenter_heterogeneous_prompt(complex_prompt):
    """Verify segmenter correctly partitions composite prompt into ordered slices."""
    segments = segment_prompt(complex_prompt, preserve_static_header=True)
    assert len(segments) >= 4

    types = [s.segment_type for s in segments]
    assert SegmentType.STATIC_HEADER in types
    assert SegmentType.NATURAL_LANGUAGE in types
    assert SegmentType.CODE_BLOCK in types
    assert SegmentType.SKILL_CONTRACT in types

    code_seg = next(s for s in segments if s.segment_type == SegmentType.CODE_BLOCK)
    assert code_seg.language == "python"
    assert "class RiskEngine:" in code_seg.content
    assert code_seg.engine == RouteEngine.TOKENSHIFT


def test_route_code_to_tokenshift(complex_prompt):
    """Verify code block gets routed to TokenShift with valid AST output."""
    engine = ContextRouterEngine.get_instance()
    req = ContextRouteRequest(
        content=complex_prompt,
        default_code_mode="skeleton",
        preserve_static_header=True,
    )
    result = engine.route_and_compress(req)

    assert result.ast_syntax_valid is True
    assert result.total_compressed_tokens < result.total_original_tokens
    assert result.total_tokens_saved > 0
    assert result.overall_reduction_ratio > 0.0

    # Ensure code fence formatting is preserved in assembled prompt
    assert "```python" in result.assembled_content
    assert "class RiskEngine:" in result.assembled_content
    assert "```" in result.assembled_content


def test_route_natural_language_to_dehydration():
    """Verify prose paragraphs are routed to LLMLingua-2 dehydration engine."""
    prose = (
        "This is an extensive analysis of distributed consensus algorithms in modern "
        "replicated state machines. It is important to realize that Raft provides "
        "understandable state machine replication compared to multi-Paxos. "
        "In our production system we must never violate log matching invariants."
    )
    engine = ContextRouterEngine.get_instance()
    req = ContextRouteRequest(
        content=prose,
        preserve_static_header=False,
        target_dehydration_rate=0.5,
    )
    result = engine.route_and_compress(req)

    assert len(result.segments) == 1
    seg = result.segments[0]
    assert seg.segment_type == SegmentType.NATURAL_LANGUAGE
    assert seg.engine == RouteEngine.LLMLINGUA2
    assert seg.compressed_content.strip()


def test_static_header_zero_loss_preservation():
    """Verify static header is kept 100% loss-free (Native Caching target)."""
    text = "<identity>You are Antigravity system agent.</identity>\n\nHello world."
    engine = ContextRouterEngine.get_instance()
    req = ContextRouteRequest(content=text, preserve_static_header=True)
    result = engine.route_and_compress(req)

    assert len(result.segments) >= 2
    header_seg = result.segments[0]
    assert header_seg.segment_type == SegmentType.STATIC_HEADER
    assert header_seg.engine == RouteEngine.NATIVE_CACHING
    assert header_seg.status == "bypassed"
    assert header_seg.compressed_content == header_seg.raw_content
    assert header_seg.tokens_saved == 0


def test_fallback_on_corrupted_code():
    """Verify syntax error in code block gracefully falls back with zero crash."""
    corrupt_block = "```python\ndef broken(:\n    pass\n```"
    engine = ContextRouterEngine.get_instance()
    req = ContextRouteRequest(content=corrupt_block)
    result = engine.route_and_compress(req)

    assert len(result.segments) == 1
    seg = result.segments[0]
    assert seg.segment_type == SegmentType.CODE_BLOCK
    assert "broken" in result.assembled_content


def test_context_router_telemetry_and_reset(complex_prompt):
    """Verify thread-safe telemetry accumulators and reset mechanism."""
    engine = ContextRouterEngine.get_instance()
    engine.reset_stats()

    stats_before = engine.get_stats()
    assert stats_before.total_requests == 0

    req = ContextRouteRequest(content=complex_prompt)
    engine.route_and_compress(req)

    stats_after = engine.get_stats()
    assert stats_after.total_requests == 1
    assert stats_after.total_segments_routed >= 4
    assert stats_after.total_tokens_saved > 0
    assert stats_after.engine_call_counts.get("tokenshift", 0) >= 1

    engine.reset_stats()
    assert engine.get_stats().total_requests == 0


def test_context_router_rest_endpoints(complex_prompt):
    """Verify FastAPI REST endpoints: /route, /segment, /stats, /reset-stats."""
    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    # 1. Segment dry-run preview
    res_seg = client.post("/api/v1/context-router/segment", json={"content": complex_prompt})
    assert res_seg.status_code == 200
    data_seg = res_seg.json()
    assert data_seg["status"] == "ok"
    assert data_seg["segments_count"] >= 4

    # 2. Route & compress
    res_route = client.post("/api/v1/context-router/route", json={
        "content": complex_prompt,
        "default_code_mode": "skeleton",
    })
    assert res_route.status_code == 200
    data_route = res_route.json()
    assert "assembled_content" in data_route
    assert data_route["total_tokens_saved"] > 0
    assert len(data_route["segments"]) >= 4

    # 3. Stats & Reset
    res_stats = client.get("/api/v1/context-router/stats")
    assert res_stats.status_code == 200
    assert res_stats.json()["total_requests"] >= 1

    res_reset = client.post("/api/v1/context-router/reset-stats")
    assert res_reset.status_code == 200
    assert res_reset.json()["status"] == "ok"
