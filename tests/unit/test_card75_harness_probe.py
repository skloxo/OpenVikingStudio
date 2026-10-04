# -*- coding: utf-8 -*-
"""Unit tests for Card-75: Active Physical Verification Probe, FastMCP Tool Parity & Single File Rules.

Verifies:
1. POST /api/v1/system/harness/probe executes live physical probe across both engines.
2. Probe updates WikiDehydrationEngine & DSPyCompilerEngine stats in real time.
3. Subsequent get_harness_metrics call transitions from zero-sample None to live validated metrics.
4. FastMCP tool openviking_harness_probe returns truthful execution report.
5. Strict adherence to Single File Hard Limits (<= 500 lines) and version alignment (1.7.29).
"""

import json
from pathlib import Path
import pytest

from openviking._version import __version__
from openviking.server.identity import RequestContext, Role
from openviking.server.mcp_endpoint import openviking_harness_probe
from openviking.server.routers.system_harness import (
    get_harness_metrics,
    trigger_harness_probe,
)
from openviking.service.dspy_compiler_engine import DSPyCompilerEngine
from openviking.service.wiki_dehydration_engine import WikiDehydrationEngine
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def mock_ctx():
    return RequestContext(user=UserIdentifier.the_default_user(), role=Role.USER)


@pytest.fixture(autouse=True)
def reset_engines():
    """Reset singleton engine stats before each test."""
    dehy = WikiDehydrationEngine.get_instance()
    dehy._total_documents = 0
    dehy._total_tokens_saved = 0
    dehy._sum_compression_ratio = 0.0
    dehy._total_latency_ms = 0.0

    dspy = DSPyCompilerEngine.get_instance()
    dspy.reset_stats()
    yield


@pytest.mark.asyncio
async def test_trigger_harness_probe_live(mock_ctx):
    """Verify POST /api/v1/system/harness/probe executes and updates real stats."""
    # 1. Before probe: 0 samples
    metrics_before = await get_harness_metrics(window="24h", _ctx=mock_ctx)
    data_before = json.loads(metrics_before.body.decode("utf-8"))
    assert data_before["llmlingua"]["total_documents"] == 0
    assert data_before["llmlingua"]["token_retention_rate"] is None
    assert data_before["dspy"]["total_compilations"] == 0
    assert data_before["dspy"]["compilation_accuracy"] is None

    # 2. Trigger active probe
    probe_res = await trigger_harness_probe(_ctx=mock_ctx)
    assert probe_res.status_code == 200
    probe_data = json.loads(probe_res.body.decode("utf-8"))

    assert probe_data["status"] == "ok"
    assert "timestamp" in probe_data
    assert probe_data["llmlingua"] is not None
    assert probe_data["llmlingua"]["passed"] is True
    assert probe_data["llmlingua"]["latency_ms"] >= 0
    assert probe_data["dspy"] is not None
    assert probe_data["dspy"]["passed"] is True
    assert probe_data["dspy"]["accuracy"] >= 0.8

    # 3. After probe: stats updated truthfully
    metrics_after = await get_harness_metrics(window="24h", _ctx=mock_ctx)
    data_after = json.loads(metrics_after.body.decode("utf-8"))
    assert data_after["llmlingua"]["total_documents"] >= 1
    assert data_after["llmlingua"]["token_retention_rate"] is not None
    assert data_after["llmlingua"]["token_retention_rate"] > 0
    assert data_after["dspy"]["total_compilations"] >= 1
    assert data_after["dspy"]["compilation_accuracy"] == 100.0


@pytest.mark.asyncio
async def test_fastmcp_harness_probe_tool():
    """Verify FastMCP tool openviking_harness_probe runs and returns JSON result."""
    output_str = await openviking_harness_probe()
    assert isinstance(output_str, str)
    payload = json.loads(output_str)

    assert payload["status"] == "ok"
    assert payload["llmlingua"]["passed"] is True
    assert payload["dspy"]["passed"] is True
    assert "compression_ratio" in payload["llmlingua"]
    assert "accuracy" in payload["dspy"]


def test_version_and_single_file_governance():
    """Verify Card-75 version 1.7.29 and single file strict lines limits."""
    # 1. Version alignment
    assert __version__ == "1.7.29"
    root_dir = Path(__file__).resolve().parent.parent.parent
    pkg_json = root_dir / "package.json"
    if pkg_json.exists():
        with open(pkg_json, "r", encoding="utf-8") as f:
            pkg_data = json.load(f)
            assert pkg_data["version"] == "1.7.29"

    # 2. Single file limits check (<= 500 lines)
    harness_router = root_dir / "openviking" / "server" / "routers" / "system_harness.py"
    with open(harness_router, "r", encoding="utf-8") as f:
        router_lines = len(f.readlines())
    assert router_lines <= 500, f"system_harness.py has {router_lines} lines (exceeds 500 hard limit!)"

    catalog_file = root_dir / "openviking" / "service" / "harness_catalog.py"
    with open(catalog_file, "r", encoding="utf-8") as f:
        cat_lines = len(f.readlines())
    assert cat_lines <= 300, f"harness_catalog.py has {cat_lines} lines (exceeds 300 target!)"

    frontend_card = root_dir / "src" / "routes" / "monitoring" / "-components" / "harness-engine-card.tsx"
    with open(frontend_card, "r", encoding="utf-8") as f:
        card_lines = len(f.readlines())
    assert card_lines <= 300, f"harness-engine-card.tsx has {card_lines} lines (exceeds 300 target!)"
