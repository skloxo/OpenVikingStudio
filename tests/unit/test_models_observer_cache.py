# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for ModelsObserver monotonic snapshot cache (SSOT).
Verifies sub-millisecond in-memory return, TTL expiry, cache invalidation, and concurrency.
"""

from concurrent.futures import ThreadPoolExecutor
import time
from unittest.mock import patch

from openviking.storage.observers.models_observer import ModelsObserver


class _DummyVLM:
    model = "mux-flash"
    provider = "openai"


class _DummyEmbedding:
    model_name = "qwen3-vl-emb"
    provider = "openai"


def test_models_observer_cache_hit_avoids_repeated_collection():
    """Verify multiple observer calls within TTL hit memory cache without repeated data collection."""
    ModelsObserver.invalidate_cache()

    observer = ModelsObserver(
        vlm_instance=_DummyVLM(),
        embedding_instance=_DummyEmbedding(),
    )

    with patch.object(
        observer,
        "_collect_all_records",
        wraps=observer._collect_all_records,
    ) as mock_collect:
        # Call 1: Miss - should collect records
        t1 = observer.get_status_table()
        assert mock_collect.call_count == 1
        assert "mux-flash" in t1
        assert "qwen3-vl-emb" in t1

        # Call 2: Hit - sub-millisecond memory return
        t2 = observer.get_status_table()
        assert mock_collect.call_count == 1
        assert t2 == t1

        # Call 3, 4, 5: Hit from getter methods
        vlm_rows = observer._get_vlm_usage()
        emb_rows = observer._get_embedding_usage()
        rer_rows = observer._get_rerank_usage()
        assert mock_collect.call_count == 1
        assert vlm_rows is not None
        assert emb_rows is not None
        assert isinstance(rer_rows, (list, type(None)))


def test_models_observer_cache_expiry_after_ttl():
    """Verify cache expires after TTL and automatically re-collects fresh records."""
    ModelsObserver.invalidate_cache()

    observer = ModelsObserver(
        vlm_instance=_DummyVLM(),
    )

    base_time = 1000.0

    with patch("openviking.storage.observers.models_observer.time.monotonic", return_value=base_time):
        with patch.object(
            observer,
            "_collect_all_records",
            wraps=observer._collect_all_records,
        ) as mock_collect:
            # Call 1 at t=1000.0 (miss)
            observer.get_status_table()
            assert mock_collect.call_count == 1

            # Call 2 at t=1004.0 (< 5.0s TTL -> hit)
            with patch("openviking.storage.observers.models_observer.time.monotonic", return_value=base_time + 4.0):
                observer.get_status_table()
                assert mock_collect.call_count == 1

            # Call 3 at t=1006.0 (> 5.0s TTL -> expired -> re-collect)
            with patch("openviking.storage.observers.models_observer.time.monotonic", return_value=base_time + 6.0):
                observer.get_status_table()
                assert mock_collect.call_count == 2


def test_models_observer_force_refresh_and_invalidate():
    """Verify force_refresh and invalidate_cache clear the cached snapshot immediately."""
    ModelsObserver.invalidate_cache()

    observer = ModelsObserver(
        vlm_instance=_DummyVLM(),
    )

    with patch.object(
        observer,
        "_collect_all_records",
        wraps=observer._collect_all_records,
    ) as mock_collect:
        observer.get_status_table()
        assert mock_collect.call_count == 1

        # force_refresh=True should bypass cache and re-collect
        observer.get_status_table(force_refresh=True)
        assert mock_collect.call_count == 2

        # invalidate_cache() should clear stored snapshot
        stats_before = ModelsObserver.get_cache_stats()
        assert stats_before["active_entries"] >= 1

        ModelsObserver.invalidate_cache()
        stats_after = ModelsObserver.get_cache_stats()
        assert stats_after["active_entries"] == 0

        # next call re-collects
        observer.get_status_table()
        assert mock_collect.call_count == 3


def test_models_observer_concurrent_readers():
    """Verify thread-safety when multiple concurrent reader threads query status table."""
    ModelsObserver.invalidate_cache()

    observer = ModelsObserver(
        vlm_instance=_DummyVLM(),
        embedding_instance=_DummyEmbedding(),
    )

    results = []

    def _reader():
        res = observer.get_status_table()
        return len(res)

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_reader) for _ in range(30)]
        for f in futures:
            results.append(f.result())

    # All threads should receive consistent non-empty table output
    assert len(results) == 30
    assert all(r > 0 for r in results)
    assert len(set(results)) == 1
