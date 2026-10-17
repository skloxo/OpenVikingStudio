# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for zg Local-First Semantic Search & TieredLazyFetch Token Shield.
(Card-Retrieval-LocalFirst-zgSemanticSearch / v1.5.30)
"""

import tempfile
from pathlib import Path
import pytest

from openviking.search.ast_chunker import ASTChunker, CodeSymbolChunk
from openviking.search.tiered_fetch import TieredLazyFetch, TieredFetchSummary, TierLevel
from openviking.search.zg_engine import ZGSearchEngine


SAMPLE_PYTHON_CODE = '''"""Sample module docstring for testing."""

class AuthenticationService:
    """Handles token validation and permission verification."""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.active_sessions = {}

    def verify_token(self, token: str, user_id: str) -> bool:
        """Verify JWT signature and check session status."""
        if not token or not user_id:
            return False
        # Simulating complex crypto check
        signature = token.split(".")[-1] if "." in token else token
        return len(signature) > 16 and user_id in self.active_sessions


async def calculate_endpoint_frequency(time_window: str = "24h", limit: int = 50) -> dict:
    """Aggregate audit request metrics and calculate endpoint frequency."""
    metrics = {"window": time_window, "total_calls": 128}
    return metrics
'''


class TestASTChunker:
    """Tests for discrete AST Python symbol chunking."""

    def test_chunk_classes_and_methods(self):
        chunks = ASTChunker.parse_python(SAMPLE_PYTHON_CODE, file_path="services/auth.py")
        assert len(chunks) >= 4

        # Verify AuthenticationService class chunk
        class_chunk = next((c for c in chunks if c.symbol_name == "AuthenticationService"), None)
        assert class_chunk is not None
        assert class_chunk.symbol_type == "class"
        assert class_chunk.start_line == 3
        assert "Handles token validation" in class_chunk.docstring

        # Verify verify_token method chunk
        method_chunk = next((c for c in chunks if c.symbol_name == "verify_token"), None)
        assert method_chunk is not None
        assert method_chunk.symbol_type == "method"
        assert method_chunk.parent_class == "AuthenticationService"
        assert "def verify_token(self, token: str, user_id: str) -> bool" in method_chunk.signature
        assert method_chunk.fingerprint is not None
        assert len(method_chunk.fingerprint) == 8

        # Verify async function chunk
        async_func = next((c for c in chunks if c.symbol_name == "calculate_endpoint_frequency"), None)
        assert async_func is not None
        assert async_func.symbol_type == "async_function"
        assert "Aggregate audit request metrics" in async_func.docstring


class TestTieredLazyFetch:
    """Tests for TieredLazyFetch depth contracts and token shield computation."""

    @pytest.fixture
    def sample_chunk(self) -> CodeSymbolChunk:
        chunks = ASTChunker.parse_python(SAMPLE_PYTHON_CODE, file_path="services/auth.py")
        return next(c for c in chunks if c.symbol_name == "verify_token")

    def test_depth_0_meta(self, sample_chunk):
        res = TieredLazyFetch.format_chunk(sample_chunk, depth=TierLevel.META, score=0.95)
        assert res.depth == 0
        assert "verify_token" in res.rendered_content
        assert "services/auth.py:10-16 [method] verify_token" == res.rendered_content
        # Implementation body must not be in depth 0
        assert "signature = token.split" not in res.rendered_content
        assert res.token_savings_ratio > 0.6

    def test_depth_1_fingerprint_recommended(self, sample_chunk):
        res = TieredLazyFetch.format_chunk(sample_chunk, depth=TierLevel.FINGERPRINT, score=0.95)
        assert res.depth == 1
        assert "def verify_token" in res.rendered_content
        assert "Verify JWT signature" in res.rendered_content
        assert "@anchor" in res.rendered_content
        # Implementation body details should be omitted in depth 1
        assert "self.active_sessions" not in res.rendered_content
        # Depth 1 saves substantial tokens compared to full baseline
        assert res.token_savings_ratio >= 0.5
        assert res.estimated_tokens < res.full_tokens_baseline

    def test_depth_2_full_block(self, sample_chunk):
        res = TieredLazyFetch.format_chunk(sample_chunk, depth=TierLevel.FULL_BLOCK, score=0.95)
        assert res.depth == 2
        assert "def verify_token" in res.rendered_content
        assert "signature = token.split" in res.rendered_content
        assert "self.active_sessions" in res.rendered_content
        assert res.token_savings_ratio == 0.0

    def test_summary_aggregation(self):
        chunks = ASTChunker.parse_python(SAMPLE_PYTHON_CODE, file_path="services/auth.py")
        summary = TieredLazyFetch.format_batch(chunks, depth=1)
        assert summary.depth == 1
        assert summary.total_results == len(chunks)
        assert summary.total_tokens_saved > 0
        assert summary.savings_percentage > 50.0


class TestZGSearchEngine:
    """Tests for ZGSearchEngine indexing and quartet retrieval."""

    def test_index_and_search_in_temp_db(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_file = tmp_path / "test_zg.db"

            engine = ZGSearchEngine(repo_root=tmp_path, db_path=db_file)

            # Create dummy python file
            sample_file = tmp_path / "auth.py"
            sample_file.write_text(SAMPLE_PYTHON_CODE, encoding="utf-8")

            # Index directory
            indexed_count = engine.index_directory(tmp_path)
            assert indexed_count >= 4

            # Verify stats
            stats = engine.get_stats()
            assert stats.total_symbols >= 4
            assert stats.total_files == 1
            assert stats.is_ready is True

            # Search by exact symbol name
            summary = engine.search(query="verify_token", depth=1, limit=5)
            assert summary.total_results >= 1
            top_hit = summary.results[0]
            assert top_hit.symbol_name == "verify_token"
            assert top_hit.depth == 1

            # Search by docstring semantic intent
            summary_semantic = engine.search(query="JWT signature verification", depth=1, limit=5)
            assert summary_semantic.total_results >= 1
            assert any(r.symbol_name == "verify_token" for r in summary_semantic.results)

            # Test path filter
            summary_filtered = engine.search(query="verify_token", depth=1, path_filter="non_existent_path")
            assert summary_filtered.total_results == 0


class TestZGRouterEndpoint:
    """End-to-end FastAPI endpoint tests for zg search router."""

    @pytest.fixture
    def test_client(self):
        from fastapi import FastAPI
        from starlette.testclient import TestClient
        from openviking.server.routers.zg_search import router as zg_router
        from openviking.server.auth import get_request_context
        from openviking.server.identity import RequestContext, Role, UserIdentifier

        app = FastAPI()
        app.include_router(zg_router)

        dummy_ctx = RequestContext(
            user=UserIdentifier("test_account", "test_user"),
            role=Role.ADMIN,
        )
        app.dependency_overrides[get_request_context] = lambda: dummy_ctx
        return TestClient(app)

    def test_zg_stats_endpoint(self, test_client):
        resp = test_client.get("/api/v1/search/zg/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        result = data["result"]
        assert "total_symbols" in result
        assert "avg_savings_ratio" in result
        assert "is_ready" in result

    def test_zg_search_endpoint(self, test_client):
        payload = {
            "query": "ASTChunker",
            "depth": 1,
            "limit": 5,
        }
        resp = test_client.post("/api/v1/search/zg", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        result = data["result"]
        assert "depth" in result
        assert result["depth"] == 1
        assert "total_results" in result
        assert "savings_percentage" in result
        assert "results" in result
        assert isinstance(result["results"], list)

