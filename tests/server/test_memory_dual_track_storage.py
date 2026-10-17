# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Dual-Track Memory Storage & Manifold Separation (Card-Memory-DualTrackStorage)."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from openviking.service.memory_dual_track import (
    DualTrackMemory,
    extract_dual_track,
    format_dual_track_markdown,
    get_embedding_text_for_content,
)
from openviking.service.entropy_gatekeeper import EntropyGatekeeper, GatekeeperDecision
from openviking.service.gatekeeper_prober import probe_nearest_vector


def test_extract_dual_track_explicit_headers():
    raw = """# Fix SQLite Lock Timeout
## 🎯 Semantic Anchor (因果归因与检索场景)
Fix SQLite concurrency busy lock by switching to write-ahead logging (WAL) and setting 15s timeout.

## ⚡ Delta Replay (代码重放轨)
```diff
--- a/storage/db.py
+++ b/storage/db.py
@@ -10,1 +10,2 @@
- conn = sqlite3.connect(path)
+ conn = sqlite3.connect(path, timeout=15.0)
+ conn.execute("PRAGMA journal_mode=WAL;")
```
<!-- MEMORY_FIELDS
{
  "version": 2,
  "dual_track": true
}
-->
"""
    dt = extract_dual_track(raw)
    assert dt.is_dual_track is True
    assert "Fix SQLite concurrency busy lock" in dt.semantic_anchor
    assert "conn = sqlite3.connect(path, timeout=15.0)" in dt.delta
    assert "```diff" not in dt.delta  # Code fences stripped for delta
    assert dt.title == "Fix SQLite Lock Timeout"
    assert dt.extra_fields.get("dual_track") is True


def test_extract_dual_track_embedded_diff_fence():
    raw = """遇到 Cloudflare 403 阻断，需在请求头携带 Chrome 真实指纹防封控。

```diff
--- a/proxy.py
+++ b/proxy.py
@@ -5,1 +5,2 @@
- headers = {"User-Agent": "curl/7.68.0"}
+ headers = {"User-Agent": "Mozilla/5.0 Chrome/128.0", "client-fingerprint": "chrome"}
```
"""
    dt = extract_dual_track(raw)
    assert dt.is_dual_track is True
    assert "Cloudflare 403 阻断" in dt.semantic_anchor
    assert "Mozilla/5.0 Chrome/128.0" in dt.delta


def test_extract_dual_track_naked_git_diff():
    naked_diff = """diff --git a/network/tunnel.py b/network/tunnel.py
index 1234567..89abcdef 100644
--- a/network/tunnel.py
+++ b/network/tunnel.py
@@ -42,6 +42,8 @@ def reconnect():
+    time.sleep(min(backoff * 2, 60))
+    logger.warning("Retrying FRP tunnel connection")
"""
    dt = extract_dual_track(naked_diff)
    assert dt.is_dual_track is True
    assert "network/tunnel.py" in dt.semantic_anchor
    assert "[Git Diff Delta]" in dt.semantic_anchor
    assert dt.delta == naked_diff.strip()


def test_extract_dual_track_pure_prose():
    prose = "OpenViking 是基于第一性原理的跨会话体外大脑，支持 FastMCP 与 VikingFS。"
    dt = extract_dual_track(prose)
    assert dt.is_dual_track is False
    assert dt.semantic_anchor == prose
    assert dt.delta == ""


def test_format_dual_track_markdown_roundtrip():
    formatted = format_dual_track_markdown(
        title="FRP Tunnel Auto Reconnect",
        semantic_anchor="Handle network jitter and disconnects by applying exponential backoff.",
        delta="""--- a/frp.py
+++ b/frp.py
@@ -1,1 +1,2 @@
+retry_with_backoff()""",
        extra_metadata={"category": "network"},
    )
    assert "# FRP Tunnel Auto Reconnect" in formatted
    assert "## 🎯 Semantic Anchor" in formatted
    assert "## ⚡ Delta Replay" in formatted
    assert "<!-- MEMORY_FIELDS" in formatted

    dt = extract_dual_track(formatted)
    assert dt.is_dual_track is True
    assert "Handle network jitter" in dt.semantic_anchor
    assert "retry_with_backoff()" in dt.delta
    assert dt.extra_fields.get("category") == "network"


def test_get_embedding_text_for_content():
    dual_content = format_dual_track_markdown(
        title="Sample",
        semantic_anchor="This is the high signal anchor",
        delta="""--- a/f.py
+++ b/f.py
@@ -1 +1 @@
-bad
+good""",
    )
    emb_text = get_embedding_text_for_content(dual_content)
    assert emb_text == "This is the high signal anchor"
    assert "bad" not in emb_text
    assert "--- a/f.py" not in emb_text


@pytest.mark.asyncio
async def test_probe_nearest_vector_uses_semantic_anchor():
    content = format_dual_track_markdown(
        title="Vector Probe Test",
        semantic_anchor="Quantum physics and entanglement principles in memory graphs",
        delta="```diff\n- old\n+ new\n```",
    )
    with patch("openviking.server.dependencies.get_service") as mock_get_service:
        mock_service = MagicMock()
        mock_search = MagicMock()
        mock_find = AsyncMock(return_value={"resources": [], "memories": [], "skills": []})
        mock_search.find = mock_find
        mock_service.search = mock_search
        mock_get_service.return_value = mock_service

        score, matched_uri, snippet = await probe_nearest_vector(content, "viking://resources/test.md")
        assert mock_find.called
        call_kwargs = mock_find.call_args.kwargs
        query_sent = call_kwargs.get("query", "")
        # Query should contain semantic anchor, NOT diff lines!
        assert "Quantum physics and entanglement" in query_sent
        assert "- old" not in query_sent


@pytest.mark.asyncio
async def test_entropy_gatekeeper_records_dual_track():
    gk = EntropyGatekeeper.get_instance()
    content = format_dual_track_markdown(
        title="Dual Track GK Ingestion",
        semantic_anchor="Unique novel pattern for dual track manifold separation testing.",
        delta="```diff\n+ line_added()\n```",
    )
    with patch.object(gk, "_probe_nearest_vector", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = (0.10, None, None)
        decision = await gk.evaluate_and_intercept("viking://resources/dual_test_gk.md", content)
        assert decision.action == "add"
        assert "[双轨写入" in decision.reason
