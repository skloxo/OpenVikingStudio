# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Stock Memory Crystallization & Offline Dream Recipe Distillation.
(Card-44 / v1.6.8)
"""

import json
import tempfile
import time
from pathlib import Path
import pytest

from openviking.service.dream_recipe_distiller import DreamRecipeDistiller, DistilledRecipe
from openviking.service.offline_dreamer import OfflineDreamer
from openviking.service.vector_sync_tracker import VectorSyncTracker
from openviking.service.memory_lifecycle_fsm import MemoryLifecycleStore, MemoryStatus
from openviking.service.memory_conflict_resolver import MemoryConflictResolver
from openviking.service.memory_purity import MemoryPurityBenchmark


@pytest.fixture
def temp_workspace(tmp_path):
    """Fixture providing isolated filesystem and SQLite stores for crystals, lessons, and unified ledger."""
    crystals_dir = tmp_path / "resources" / "master_memory" / "crystals"
    crystals_dir.mkdir(parents=True, exist_ok=True)
    master_dir = tmp_path / "resources" / "master_memory"
    master_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = tmp_path / "data" / "entropy_gatekeeper.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    # Isolated SQLite stores
    lifecycle_db = tmp_path / "memory_lifecycle.db"
    store = MemoryLifecycleStore(db_path=str(lifecycle_db))
    MemoryLifecycleStore._instance = store

    # Reset singletons
    OfflineDreamer.reset_for_testing()
    VectorSyncTracker.reset_for_testing()
    MemoryConflictResolver.reset_for_testing()
    MemoryPurityBenchmark._instance = None

    yield {
        "root": tmp_path,
        "crystals_dir": crystals_dir,
        "master_dir": master_dir,
        "ledger_path": ledger_path,
        "lifecycle_store": store,
    }

    OfflineDreamer.reset_for_testing()
    VectorSyncTracker.reset_for_testing()
    MemoryConflictResolver.reset_for_testing()
    MemoryPurityBenchmark._instance = None
    MemoryLifecycleStore._instance = None


def test_dream_recipe_distiller_four_tier_topology():
    """Verify DreamRecipeDistiller correctly extracts L0 Axioms, L1 SOP, L2 Boundaries, and L3 Lineage."""
    distiller = DreamRecipeDistiller(distiller_id="test_distiller")

    fragments = [
        {
            "uri": "viking://resources/master_memory/lessons/lesson_01.md",
            "content": (
                "---\ntopic: systemd_ops\n---\n"
                "# Systemd Service Architecture\n\n"
                "Systemd services must have Restart=always configured in production.\n"
                "1. 首先配置 /etc/systemd/system/openviking.service\n"
                "2. 执行 systemctl daemon-reload 重载单元\n"
                "严禁在无守护进程情况下裸跑后台服务，禁止使用 nohup 作为生产守护。\n"
            ),
        },
        {
            "uri": "viking://resources/master_memory/lessons/lesson_02.md",
            "content": (
                "---\ntopic: systemd_ops\n---\n"
                "# Systemd Verification SOP\n\n"
                "Single service instance must strictly enforce singleton guard via PID.\n"
                "- 接着通过 journalctl -u openviking -n 50 查看日志\n"
                "- 最后调用 curl 检查端口存活状态\n"
                "切勿随意 kill -9 强杀进程造成 SQLite 锁死。\n"
            ),
        },
    ]

    recipe = distiller.distill(fragments=fragments, theme="systemd_ops")
    assert recipe.theme == "systemd_ops"
    assert len(recipe.axioms) >= 1
    assert any("Restart=always" in a or "singleton" in a.lower() for a in recipe.axioms)
    assert len(recipe.recipe_steps) >= 2
    assert len(recipe.negative_boundaries) >= 2
    assert any("nohup" in b or "kill -9" in b for b in recipe.negative_boundaries)
    assert len(recipe.source_uris) == 2
    assert len(recipe.evidence_hashes) == 2
    assert recipe.purity_snr == 2.0

    rendered = distiller.render_markdown(recipe, "viking://resources/master_memory/crystals/master_test.md")
    assert "## 💎 L0: Core Invariant Axioms" in rendered
    assert "## 📋 L1: Operational Recipe SOP" in rendered
    assert "## 🚫 L2: Negative Boundaries & Anti-Patterns" in rendered
    assert "## 🔗 L3: Consolidated Source Fragments & Lineage" in rendered


def test_offline_dreamer_full_domain_scan_and_clustering(temp_workspace):
    """Verify OfflineDreamer deep scans all subdirectories in master_memory while ignoring crystals."""
    master_dir = temp_workspace["master_dir"]
    crystals_dir = temp_workspace["crystals_dir"]
    ledger_path = temp_workspace["ledger_path"]

    # 1. Create observations in observations/ subdir
    obs_dir = master_dir / "observations"
    obs_dir.mkdir(parents=True, exist_ok=True)
    (obs_dir / "obs_vector_01.md").write_text(
        "---\ntopic: vector_search\n---\n# Vector Search Baseline\nUse cosine similarity threshold 0.75.\n",
        encoding="utf-8",
    )
    (obs_dir / "obs_vector_02.md").write_text(
        "---\ntopic: vector_search\n---\n# Vector Search Fallback\nFallback to text BM25 when embeddings unavailable.\n严禁在超时后重复阻塞。\n",
        encoding="utf-8",
    )

    # 2. Create lessons in evolution_lessons/ subdir
    lessons_dir = master_dir / "evolution_lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    (lessons_dir / "lesson_sqlite_01.md").write_text(
        "---\ntopic: sqlite_wal\n---\n# SQLite WAL Mode\nEnable PRAGMA journal_mode=WAL immediately on boot.\n",
        encoding="utf-8",
    )

    # 3. Create a preexisting crystal in crystals/ (MUST BE IGNORED during scanning)
    (crystals_dir / "master_existing.md").write_text(
        "---\ntopic: vector_search\n---\n# Preexisting Master\n",
        encoding="utf-8",
    )

    dreamer = OfflineDreamer(crystals_dir=crystals_dir, ledger_path=ledger_path)
    frags = dreamer.load_unconsolidated_fragments(source_dir=master_dir)

    scanned_uris = [f["uri"] for f in frags]
    assert len(frags) == 3
    assert not any("crystals" in u for u in scanned_uris)
    topics = {f["topic"] for f in frags}
    assert "vector_search" in topics
    assert "sqlite_wal" in topics


def test_offline_dream_consolidation_vector_sync_and_ledger(temp_workspace):
    """Verify offline dream cycle consolidates fragments, registers VectorSync, supersedes DAG, and logs ledger."""
    master_dir = temp_workspace["master_dir"]
    crystals_dir = temp_workspace["crystals_dir"]
    ledger_path = temp_workspace["ledger_path"]

    # Seed 2 fragments with topic 'memory_gate'
    sub_dir = master_dir / "protocols"
    sub_dir.mkdir(parents=True, exist_ok=True)
    f1 = sub_dir / "gate_fast_probe.md"
    f1.write_text(
        "---\ntopic: memory_gate\n---\n# Fast Probe Budget\nProbe nearest vector within 250ms timebox.\n1. 调用 probe\n2. 超时立即放行\n严禁超过 1 秒阻塞写入通道。\n",
        encoding="utf-8",
    )
    f2 = sub_dir / "gate_wal_first.md"
    f2.write_text(
        "---\ntopic: memory_gate\n---\n# WAL First Ingestion\nAlways persist memory disk file before async indexing.\n",
        encoding="utf-8",
    )

    dreamer = OfflineDreamer(crystals_dir=crystals_dir, ledger_path=ledger_path, source_dir=master_dir)
    tracker = VectorSyncTracker.get_instance(db_path=temp_workspace["root"] / "vector_sync.db")

    result = dreamer.run_dream_cycle(
        theme="memory_gate",
        min_cluster_size=2,
        dry_run=False,
    )

    assert result.status == "ok"
    assert result.fragments_consolidated == 2
    assert result.master_cards_created == 1
    assert result.net_entropy_reduced == 1
    assert len(result.master_card_uris) == 1

    master_uri = result.master_card_uris[0]
    master_fname = master_uri.split("/")[-1]
    persisted_file = crystals_dir / master_fname
    assert persisted_file.exists()
    card_content = persisted_file.read_text(encoding="utf-8")
    assert "## 💎 L0: Core Invariant Axioms" in card_content
    assert "## 🚫 L2: Negative Boundaries & Anti-Patterns" in card_content

    # Invariant: Registered into VectorSyncTracker (Zero Ghost Crystals)
    state = tracker.get_record(master_uri)
    assert state is not None
    assert state.status.value == "PENDING"

    # Invariant: Superseded in Lifecycle Store
    lifecycle_store = MemoryLifecycleStore.get_instance()
    for s_uri in result.superseded_uris:
        rec = lifecycle_store.get_record(s_uri)
        assert rec is not None
        assert rec.status == MemoryStatus.SUPERSEDED
        assert rec.superseded_by == master_uri

    # Invariant: Unified Ledger logged
    assert ledger_path.exists()
    lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    last_event = json.loads(lines[-1])
    assert last_event["type"] == "DREAM_CONSOLIDATION"
    assert last_event["master_card_uri"] == master_uri
    assert last_event["theme"] == "memory_gate"
    assert last_event["net_entropy_reduced"] == 1


def test_memory_purity_governance_stream_with_dream_events(temp_workspace):
    """Verify MemoryPurityBenchmark accurately parses DREAM_CONSOLIDATION events and computes SNR gain."""
    ledger_path = temp_workspace["ledger_path"]
    crystals_dir = temp_workspace["crystals_dir"]

    # Write 1 Ingress Admission event and 1 Dream Consolidation event
    event1 = {
        "event_id": "#dec_0001",
        "action": "noop",
        "uri": "viking://resources/master_memory/test.md",
        "matched_uri": "viking://resources/master_memory/canonical.md",
        "similarity": 0.99,
        "reason": "Exact bitwise duplicate NOOP",
        "timestamp": time.time() - 100,
    }
    event2 = {
        "event_id": "#cry_0001",
        "type": "DREAM_CONSOLIDATION",
        "timestamp": time.time(),
        "theme": "wal_storage",
        "fragments_consolidated": 5,
        "master_card_uri": "viking://resources/master_memory/crystals/master_wal_storage_abc.md",
        "net_entropy_reduced": 4,
    }
    ledger_path.write_text(json.dumps(event1) + "\n" + json.dumps(event2) + "\n", encoding="utf-8")

    # Put 1 fake crystal file on disk
    (crystals_dir / "master_wal_storage_abc.md").write_text("# Master Crystal\n", encoding="utf-8")

    bench = MemoryPurityBenchmark(ledger_path=ledger_path, crystals_dir=crystals_dir)
    stream = bench.get_governance_stream(limit=10)

    assert len(stream) == 2
    # Stream is reversed (newest first)
    assert stream[0].event_id == "#cry_0001"
    assert stream[0].type == "DREAM_CONSOLIDATION"
    assert stream[0].action == "consolidate"
    assert stream[0].net_entropy_reduced == 4
    assert stream[1].event_id == "#dec_0000" or stream[1].type == "INGRESS_ADMISSION"

    report = bench.compute_purity_report()
    assert report.master_cards_count >= 1
    assert report.snr_ratio > 0.0


@pytest.mark.asyncio
async def test_rest_endpoint_crystal_detail_and_list(monkeypatch, tmp_path):
    """Verify REST endpoints /crystals and /detail correctly discover and return crystal details."""
    from openviking.server.routers.entropy_crystallizer import list_fact_crystals, get_fact_crystal_detail
    from openviking.server.identity import RequestContext, Role
    from openviking_cli.session.user_id import UserIdentifier

    crystals_dir = tmp_path / "resources" / "master_memory" / "crystals"
    crystals_dir.mkdir(parents=True, exist_ok=True)

    card_content = (
        "---\n"
        "uri: \"viking://resources/master_memory/crystals/master_auth_ops.md\"\n"
        "title: \"Master Auth Ops\"\n"
        "distilled_at: 1720000000.0\n"
        "status: active\n"
        "---\n\n"
        "# Master Auth Ops\n\n"
        "## 💎 L0: Core Invariant Axioms\n\n"
        "- Authentication tokens must be validated with Bearer scheme.\n\n"
        "## 🚫 L2: Negative Boundaries & Anti-Patterns\n\n"
        "- 🚫 Never accept plain text tokens without TLS.\n\n"
        "## 🔗 L3: Consolidated Source Fragments & Lineage\n\n"
        "- `viking://resources/master_memory/lessons/auth_01.md`\n"
    )
    (crystals_dir / "master_auth_ops.md").write_text(card_content, encoding="utf-8")

    # Patch crystals_dirs to include our tmp_path
    monkeypatch.setattr(
        Path, "home", lambda: tmp_path
    )
    # create the nested path that router looks for
    nest_dir = tmp_path / ".openviking" / "data" / "viking" / "default" / "resources" / "master_memory" / "crystals"
    nest_dir.mkdir(parents=True, exist_ok=True)
    (nest_dir / "master_auth_ops.md").write_text(card_content, encoding="utf-8")

    ctx = RequestContext(user=UserIdentifier(user_id="test", account_id="default"), role=Role(Role.ADMIN))
    
    # 1. List
    res = await list_fact_crystals(ctx=ctx)
    assert res["status"] == "ok"
    assert len(res["result"]) >= 1
    found = [c for c in res["result"] if "master_auth_ops" in c["uri"]]
    assert len(found) == 1
    assert "Bearer scheme" in found[0]["axiom"]
    assert len(found[0]["negative_boundary"]["deprecated_patterns"]) >= 1

    # 2. Detail
    det = await get_fact_crystal_detail(uri="viking://resources/master_memory/crystals/master_auth_ops.md", ctx=ctx)
    assert det["status"] == "ok"
    assert det["result"]["uri"] == "viking://resources/master_memory/crystals/master_auth_ops.md"
    assert "Bearer scheme" in det["result"]["axiom"]

