"""Card #293 regression tests: CJK tokenizer, FTS5 schema v2, DF cache, and zero-embedding bm25_fast."""

from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from openviking.retrieve.global_hybrid_retriever import GlobalHybridRetriever, RetrieverMode
from openviking.server.identity import RequestContext, Role
from openviking.storage.bm25_fts_index import BM25FTSIndex
from openviking.storage.bm25_tokenizer import extract_cjk_tokens, sanitize_fts_query
from openviking.storage.viking_fs._semantic import _SemanticMixin
from openviking_cli.retrieve.types import ContextType, TypedQuery
from openviking_cli.session.user_id import UserIdentifier


def _ctx() -> RequestContext:
    return RequestContext(user=UserIdentifier(account_id="acc_default", user_id="usr_test"), role=Role.ADMIN)


class _DummyVikingFS(_SemanticMixin):
    def __init__(self, bm25_index: BM25FTSIndex):
        self.rerank_config = None
        self.retrieval_config = None
        self._bm25_index = bm25_index

    def _get_vector_store(self):
        return None

    def _get_embedder(self):
        return None

    def _ctx_or_default(self, ctx):
        return ctx or _ctx()

    async def _ensure_retrieval_scope(self, target_dir, ctx):
        return None


def test_cjk_tokenizer_and_query_sanitizer():
    tokens = extract_cjk_tokens("反重力客户端与OpenViking记忆网关")
    assert "反重" in tokens and "重力" in tokens and "反重力" in tokens
    assert "记忆" in tokens and "网关" in tokens
    fts_q = sanitize_fts_query("干部公寓 NVR 检查 _query_endpoint_frequency_sync 1933")
    assert "_query_endpoint_frequency_sync*" in fts_q
    assert "1933*" in fts_q
    assert '"干部"' in fts_q and '"公寓"' in fts_q


def test_schema_v1_to_v2_upgrade_and_cjk_snippet_retrieval(tmp_path: Path):
    db_path = tmp_path / "bm25_v1.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE VIRTUAL TABLE fts_documents USING fts5(
            uri UNINDEXED,
            title,
            content,
            level UNINDEXED,
            context_type UNINDEXED,
            tokenize="unicode61 tokenchars '_' remove_diacritics 2"
        );
        """
    )
    conn.execute(
        "INSERT INTO fts_documents(uri, title, content, level, context_type) VALUES (?, ?, ?, ?, ?)",
        (
            "viking://resources/master_memory/legacy_v1.md",
            "旧库无损平滑升级",
            "反重力旧库无损平滑升级至二代中文索引保持零丢数",
            2,
            "resource",
        ),
    )
    conn.commit()
    conn.close()

    idx = BM25FTSIndex(db_path=db_path)
    legacy_hits = idx.search("平滑升级中文索引", limit=5)
    assert legacy_hits and legacy_hits[0].uri.endswith("legacy_v1.md")
    assert idx.index_batch(
        [
            {
                "uri": "viking://resources/master_memory/recipes/no_green.md",
                "title": "视觉底线 NO GREEN EVER 铁律",
                "content": "全系统界面绝对禁止使用绿色，状态良好统一采用冰青色 cyan-500。",
                "level": 2,
                "context_type": "resource",
            },
            {
                "uri": "viking://resources/master_memory/recipes/nvr_ops.md",
                "title": "干部公寓安防监控运维",
                "content": "华庭-NVR-01 与 海康 ISAPI 接口巡检脚本以及大华设备排障流程。",
                "level": 2,
                "context_type": "resource",
            },
        ]
    ) == 2

    hits = idx.search("华庭安防监控巡检", limit=5)
    assert hits and hits[0].uri.endswith("nvr_ops.md")
    assert "<b>" in hits[0].snippet

    no_green_hits = idx.search("绝对禁止使用绿色", limit=5)
    assert no_green_hits and no_green_hits[0].uri.endswith("no_green.md")


def test_target_directories_overfetch_and_df_cache_invalidation(tmp_path: Path):
    idx = BM25FTSIndex(db_path=tmp_path / "bm25_df.db")
    docs = [
        {
            "uri": f"viking://resources/other/doc_{i}.md",
            "title": "deploy guide",
            "content": "deploy guide repeated term " * 4,
            "level": 2,
            "context_type": "resource",
        }
        for i in range(6)
    ] + [
        {
            "uri": "viking://resources/target_dir/focus.md",
            "title": "deploy guide focus",
            "content": "deploy guide in target dir",
            "level": 2,
            "context_type": "resource",
        }
    ]
    idx.index_batch(docs)

    scoped = idx.search("deploy", limit=2, target_directories=["viking://resources/target_dir"])
    assert len(scoped) == 1 and scoped[0].uri.endswith("focus.md")

    assert idx.get_term_df("deploy") == 7
    df_map = idx.get_terms_df(["deploy", "nonexistent_term_xyz"])
    assert df_map["deploy"] == 7 and df_map["nonexistent_term_xyz"] == 0

    idx.delete_document("viking://resources/other/doc_0.md")
    assert idx.get_term_df("deploy") == 6


@pytest.mark.asyncio
async def test_bm25_fast_zero_embedding_end_to_end(tmp_path: Path):
    idx = BM25FTSIndex(db_path=tmp_path / "bm25_fast.db")
    idx.index_document(
        uri="viking://resources/docs/zero_emb",
        title="零向量 bm25_fast 检索规范",
        content="开启 zero_embedding 模式时彻底跳过 embedder 与向量库初始化。",
        level=2,
        context_type="resource",
    )

    retriever = GlobalHybridRetriever(storage=None, embedder=None, bm25_index=idx)
    query = TypedQuery(query="零向量检索跳过", context_type=ContextType.RESOURCE, intent="")
    res_fast = await retriever.retrieve(query=query, ctx=_ctx(), limit=5, mode=RetrieverMode.BM25_FAST)
    assert len(res_fast.matched_contexts) == 1
    assert res_fast.matched_contexts[0].uri == "viking://resources/docs/zero_emb"
    assert res_fast.matched_contexts[0].score > 0.0

    # Alias "zero_embedding" through VikingFS.find with storage=None & embedder=None
    vfs = _DummyVikingFS(bm25_index=idx)
    find_res = await vfs.find(query="bm25_fast 零向量", mode="zero_embedding", limit=5, ctx=_ctx())
    assert len(find_res.resources) == 1

    # Ensure embedder would never be called even if an erroring mock were present
    fail_embedder = AsyncMock()
    fail_embedder.embed_async.side_effect = AssertionError("embedder must not be called in bm25_fast")
    retriever2 = GlobalHybridRetriever(storage=None, embedder=fail_embedder, bm25_index=idx)
    res2 = await retriever2.retrieve(query=query, ctx=_ctx(), limit=5, mode="zero_embedding")
    assert len(res2.matched_contexts) == 1
    assert fail_embedder.embed_async.call_count == 0


def test_gold_benchmarks_cjk_bm25_recall_and_latency(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    benchmarks = json.loads((repo_root / "openviking" / "retrieve" / "gold_benchmarks.json").read_text("utf-8"))["benchmarks"]

    # Build self-contained FTS index from workspace repo docs/code (no prod DB touched)
    idx = BM25FTSIndex(db_path=tmp_path / "gold_bench.db")
    docs = []
    root_agents = repo_root / "AGENTS.md"
    if root_agents.exists():
        docs.append(
            {
                "uri": "viking://resources/AGENTS.md",
                "title": "AGENTS.md",
                "content": root_agents.read_text("utf-8", errors="ignore")[:32000],
                "level": 2,
                "context_type": "resource",
            }
        )
    for sub in ("openviking", "openviking_gateway", "docs", ".agents", "packages", "skills", "src"):
        root = repo_root / sub
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix in (".py", ".md", ".ts", ".tsx") and p.stat().st_size < 160_000:
                text = p.read_text("utf-8", errors="ignore")
                rel = p.relative_to(repo_root).as_posix()
                docs.append(
                    {
                        "uri": f"viking://resources/{rel}",
                        "title": p.stem,
                        "content": text[:16000],
                        "level": 2,
                        "context_type": "resource",
                    }
                )
    assert docs, "expected workspace corpus documents for gold benchmark"
    idx.index_batch(docs)

    hits = 0
    latencies = []
    for item in benchmarks:
        t0 = time.perf_counter()
        matches = idx.search(item["query"], limit=5)
        latencies.append((time.perf_counter() - t0) * 1000.0)
        patterns = [p.strip().lower() for p in item.get("expected_uri_pattern", "").split("|") if p.strip()]
        keywords = [k.lower() for k in item.get("expected_keywords", []) if k]
        matched = False
        for m in matches:
            uri_low = m.uri.lower()
            text_low = f"{m.title} {m.snippet}".lower()
            if any(p in uri_low for p in patterns) or any(kw in text_low for kw in keywords):
                matched = True
                break
        if matched:
            hits += 1

    recall_at_5 = hits / len(benchmarks)
    avg_ms = sum(latencies) / len(latencies)
    assert recall_at_5 >= 0.88, f"Expected R@5 >= 0.88 on gold benchmarks, got {recall_at_5:.3f}"
    assert avg_ms < 15.0, f"Expected avg BM25 query latency < 15ms, got {avg_ms:.2f}ms"
