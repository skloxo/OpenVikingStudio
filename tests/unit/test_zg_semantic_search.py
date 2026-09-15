# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for zg (zvec-grep) Code Semantic Search & TieredLazyFetch.
(Card-Retrieval-LocalFirst-zgSemanticSearch / v1.5.17)
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from openviking.search.ast_chunker import ASTChunker, CodeSymbolChunk
from openviking.search.tiered_fetch import TieredLazyFetch, TierLevel, TieredFetchSummary
from openviking.search.zg_engine import ZGSearchEngine
from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking_cli.session.user_id import UserIdentifier

SAMPLE_PYTHON_CODE = '''# Sample Module
"""Module docstring."""

def regular_helper(x: int, y: int = 0) -> int:
    """Add two numbers together."""
    res = x + y
    return res

class DataProcessor:
    """Processes pipeline data."""
    def __init__(self, name: str):
        self.name = name

    async def process_batch(self, items: list) -> int:
        """Process items asynchronously."""
        count = len(items)
        return count
'''


def test_ast_chunker_symbol_extraction():
    """Verify AST parser extracts functions, classes, and methods with accurate line spans."""
    chunks = ASTChunker.parse_python(SAMPLE_PYTHON_CODE, file_path="sample.py")
    assert len(chunks) == 4  # regular_helper, DataProcessor, __init__, process_batch

    # 1. Top-level function
    helper = next(c for c in chunks if c.symbol_name == "regular_helper")
    assert helper.symbol_type == "function"
    assert helper.start_line == 4
    assert helper.end_line == 7
    assert helper.line_count == 4
    assert "regular_helper" in helper.signature
    assert helper.docstring == "Add two numbers together."
    assert len(helper.fingerprint) == 8

    # 2. Class definition
    cls_chunk = next(c for c in chunks if c.symbol_name == "DataProcessor" and c.symbol_type == "class")
    assert cls_chunk.start_line == 9
    assert cls_chunk.end_line == 17
    assert cls_chunk.docstring == "Processes pipeline data."

    # 3. Async method inside class
    method = next(c for c in chunks if c.symbol_name == "process_batch")
    assert method.symbol_type == "async_method"
    assert method.parent_class == "DataProcessor"
    assert method.start_line == 14
    assert method.end_line == 17
    assert "process_batch" in method.signature


def test_tiered_lazy_fetch_contract():
    """Verify depth=0, depth=1, depth=2 contracts and token savings calculation."""
    chunks = ASTChunker.parse_python(SAMPLE_PYTHON_CODE, file_path="sample.py")
    method = next(c for c in chunks if c.symbol_name == "process_batch")

    # Depth 0: Meta
    d0 = TieredLazyFetch.format_chunk(method, depth=TierLevel.META)
    assert d0.depth == 0
    assert "sample.py:14-17" in d0.rendered_content
    assert "[async_method] process_batch" in d0.rendered_content
    assert d0.estimated_tokens < 30
    assert d0.token_savings_ratio > 0.0

    # Depth 1: Fingerprint (Default recommended)
    d1 = TieredLazyFetch.format_chunk(method, depth=TierLevel.FINGERPRINT)
    assert d1.depth == 1
    assert f"# @anchor {method.fingerprint}" in d1.rendered_content
    assert method.signature in d1.rendered_content
    assert "Process items asynchronously." in d1.rendered_content

    # Depth 2: Full block
    d2 = TieredLazyFetch.format_chunk(method, depth=TierLevel.FULL_BLOCK)
    assert d2.depth == 2
    assert "count = len(items)" in d2.rendered_content
    assert d2.estimated_tokens >= d1.estimated_tokens

    # Batch summary token savings
    summary = TieredLazyFetch.format_batch(chunks, depth=TierLevel.FINGERPRINT)
    assert summary.depth == 1
    assert summary.total_results == 4
    assert summary.actual_tokens_total < summary.baseline_tokens_total
    assert summary.savings_percentage > 0.0


def test_zg_search_engine(tmp_path):
    """Verify ZGSearchEngine indexing, exact symbol search, and intent retrieval."""
    test_file = tmp_path / "processor.py"
    test_file.write_text(SAMPLE_PYTHON_CODE, encoding="utf-8")

    engine = ZGSearchEngine(repo_root=tmp_path, db_path=tmp_path / "test_zg.db")
    count = engine.index_directory(dir_path=tmp_path)
    assert count == 4

    # 1. Search exact symbol
    res_sym = engine.search("regular_helper", depth=1, limit=5)
    assert res_sym.total_results >= 1
    assert res_sym.results[0].symbol_name == "regular_helper"

    # 2. Search natural language intent from docstring
    res_intent = engine.search("pipeline", depth=1, limit=5)
    assert res_intent.total_results >= 1
    matched_names = [r.symbol_name for r in res_intent.results]
    assert "DataProcessor" in matched_names

    # 3. Fetch by anchor fingerprint
    fp = res_sym.results[0].fingerprint
    fetched = engine.fetch_by_fingerprint(fp, depth=2)
    assert fetched is not None
    assert fetched["symbol_name"] == "regular_helper"
    assert "res = x + y" in fetched["rendered_content"]

    # 4. Engine statistics
    stats = engine.get_stats()
    assert stats.total_symbols == 4
    assert stats.total_files == 1
    assert stats.is_ready is True


def test_zg_search_rest_endpoints():
    """Verify /api/v1/search/zg/* endpoints."""
    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="test-user"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    # 1. GET /api/v1/search/zg/stats
    stats_res = client.get("/api/v1/search/zg/stats")
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert "total_symbols" in stats_data
    assert "is_ready" in stats_data

    # 2. POST /api/v1/search/zg/search
    search_res = client.post(
        "/api/v1/search/zg/search",
        json={"query": "rrf_fuse", "depth": 1, "limit": 5},
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert "depth" in search_data
    assert "total_results" in search_data
    assert "savings_percentage" in search_data
    assert "results" in search_data
