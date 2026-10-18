# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Automated unit & retina test for Card-Pipeline-WireUp-Production (v1.5.49).
Verifies:
1. Production wiring of LLMLingua-2 dehydration in content reading.
2. Production wiring of EntropyCrystallizer auto scan & lifecycle FSM superseding.
"""

import time
import pytest
from openviking.service.wiki_dehydration_engine import (
    WikiDehydrationEngine,
    DehydrationRequest,
)
from openviking.service.entropy_crystallizer import (
    EntropyCrystallizer,
    MemoryFragment,
)
from openviking.service.memory_lifecycle_fsm import (
    MemoryLifecycleStore,
    MemoryStatus,
)


def test_content_read_dehydration_pipeline():
    """Verify WikiDehydrationEngine reduces verbose natural language text while preserving structure."""
    raw_doc = (
        "---\n"
        "title: Architecture Guidelines\n"
        "version: 1.5.49\n"
        "---\n\n"
        "# System Directives\n\n"
        "In our software architecture, it is absolutely and unequivocally critical that developers "
        "always pay close attention to first principles and Occam's razor. Under no circumstances should "
        "redundant entity creation be allowed.\n\n"
        "```python\n"
        "def compute_hash(data: str) -> str:\n"
        "    return hashlib.sha256(data.encode()).hexdigest()\n"
        "```\n\n"
        "Furthermore, all monitoring dashboards must be decoupled from core serving loops so that "
        "background rendering never competes with high priority operations."
    )

    engine = WikiDehydrationEngine.get_instance()
    res = engine.dehydrate(DehydrationRequest(content=raw_doc, rate=0.50))

    assert res.compressed_chars < res.original_chars
    assert res.tokens_saved > 0
    assert "```python" in res.dehydrated_content
    assert "compute_hash" in res.dehydrated_content
    assert "---" in res.dehydrated_content


def test_entropy_crystallizer_auto_scan_and_fsm_integration(tmp_path):
    """Verify scan_and_auto_crystallize distills cold clusters and atomically marks fragments superseded in SQLite."""
    db_path = str(tmp_path / "lifecycle_crystallize.db")
    store = MemoryLifecycleStore(db_path=db_path)
    # Monkey-patch store singleton for test isolation
    orig_store = MemoryLifecycleStore._instance
    MemoryLifecycleStore._instance = store

    try:
        crystallizer = EntropyCrystallizer()
        crystallizer.rule.cooling_period_hours = 24.0
        crystallizer.rule.min_cluster_size = 5
        crystallizer.rule.min_avg_cosine_similarity = 0.70

        now = time.time()
        cold_ts = now - 3600 * 48  # 48 hours ago (well cooled)

        # 5 fragments with identical embeddings and topic
        fragments = [
            MemoryFragment(
                uri=f"viking://session/cluster_frag_{i}.md",
                content=f"Observation {i}: SQLite WAL mode provides high concurrency.",
                created_at=cold_ts,
                embedding=[0.8, 0.6, 0.0],
                metadata={"topic": "sqlite_concurrency"},
            )
            for i in range(5)
        ]

        results = crystallizer.scan_and_auto_crystallize(
            candidate_fragments=fragments,
            default_version_range="v1.5.49+",
        )

        assert len(results) == 1
        res = results[0]
        assert res.crystal.uri.startswith("viking://resources/crystals/axiom_")
        assert res.net_entropy_reduced == 4  # 5 fragments - 1 crystal = 4 net reduction
        assert len(res.superseded_uris) == 5

        # Check SQLite persistence for all 5 fragments
        for frag in fragments:
            rec = store.get_record(frag.uri)
            assert rec is not None
            assert rec.status == MemoryStatus.SUPERSEDED
            assert rec.superseded_by == res.crystal.uri

    finally:
        MemoryLifecycleStore._instance = orig_store
