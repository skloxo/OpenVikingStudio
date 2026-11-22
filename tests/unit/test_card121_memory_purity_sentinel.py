"""Unit tests for Card #121 MemoryPuritySentinel engine and BM25 hot-pruning."""

from __future__ import annotations

from pathlib import Path

import pytest

from openviking.server.identity import RequestContext, Role
from openviking.server.routers.memory_lifecycle import (
    PuritySweepRequest,
    get_purity_sentinel_status,
    sweep_memory_purity,
)
from openviking.service.memory_purity_sentinel import MemoryPuritySentinel
from openviking.storage.bm25_fts_index import BM25FTSIndex
from openviking_cli.session.user_id import UserIdentifier


def _seed_workspace(tmp_path: Path) -> tuple[Path, Path, BM25FTSIndex]:
    active = tmp_path / "viking" / "default"
    archive = active / "archive"
    bm25 = BM25FTSIndex(db_path=tmp_path / "bm25.db")

    # Protected authoritative assets (must never be touched even if name looks noisy)
    master = active / "resources" / "master_memory" / "recipes" / "draft_recipe.md"
    master.parent.mkdir(parents=True, exist_ok=True)
    master.write_text("# Verified Recipe\nKeep forever.", encoding="utf-8")

    # Valid active knowledge document
    good = active / "resources" / "architecture_guide.md"
    good.write_text("# Architecture Guide\nCore production design.", encoding="utf-8")

    # Low-value process noise files
    scratch = active / "resources" / "scratch" / "debug_trace.md"
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_text("temp stack trace", encoding="utf-8")

    draft = active / "resources" / "tmp_experiment_draft.md"
    draft.write_text("[DRAFT]\ntemporary debug log", encoding="utf-8")

    empty = active / "memories" / "empty_note.md"
    empty.parent.mkdir(parents=True, exist_ok=True)
    empty.write_text("   \n", encoding="utf-8")

    bm25.index_batch(
        [
            {
                "uri": "viking://user/default/resources/master_memory/recipes/draft_recipe.md",
                "title": "draft_recipe",
                "content": "Verified Recipe Keep forever",
                "context_type": "resource",
            },
            {
                "uri": "viking://user/default/resources/architecture_guide.md",
                "title": "architecture_guide",
                "content": "Core production design",
                "context_type": "resource",
            },
            {
                "uri": "viking://user/default/resources/scratch/debug_trace.md",
                "title": "debug_trace",
                "content": "temp stack trace",
                "context_type": "resource",
            },
            {
                "uri": "viking://user/default/resources/tmp_experiment_draft.md",
                "title": "tmp_experiment_draft",
                "content": "temporary debug log",
                "context_type": "resource",
            },
        ]
    )
    return active, archive, bm25


def test_sentinel_dry_run_preserves_files_and_index(tmp_path: Path) -> None:
    active, archive, bm25 = _seed_workspace(tmp_path)
    sentinel = MemoryPuritySentinel(
        active_root=active,
        archive_root=archive,
        audit_log_path=tmp_path / "audit.jsonl",
        bm25_index=bm25,
    )

    report = sentinel.run_once(dry_run=True)

    assert report.dry_run is True
    assert report.noise_detected == 3
    assert report.archived_count == 0
    assert (active / "resources" / "scratch" / "debug_trace.md").is_file()
    assert len(bm25.list_all_uris()) == 4


def test_sentinel_archives_noise_protects_master_and_prunes_bm25(tmp_path: Path) -> None:
    active, archive, bm25 = _seed_workspace(tmp_path)
    audit_path = tmp_path / "audit.jsonl"
    sentinel = MemoryPuritySentinel(
        active_root=active,
        archive_root=archive,
        audit_log_path=audit_path,
        bm25_index=bm25,
    )

    report = sentinel.run_once(dry_run=False)

    assert report.archived_count == 3
    assert report.bm25_deleted == 3
    assert report.active_snr_before < 0.95
    assert report.active_snr_after >= 0.95

    # Protected & valid active docs remain untouched
    assert (active / "resources" / "master_memory" / "recipes" / "draft_recipe.md").is_file()
    assert (active / "resources" / "architecture_guide.md").is_file()

    # Noise moved out of active root into archive/purity/
    assert not (active / "resources" / "scratch" / "debug_trace.md").exists()
    assert not (active / "resources" / "tmp_experiment_draft.md").exists()
    assert not (active / "memories" / "empty_note.md").exists()
    assert list((archive / "purity").rglob("*.md"))
    assert audit_path.is_file()

    # BM25 no longer returns archived URIs
    remaining_uris = set(bm25.list_all_uris())
    assert "viking://user/default/resources/architecture_guide.md" in remaining_uris
    assert "viking://user/default/resources/scratch/debug_trace.md" not in remaining_uris
    assert "viking://user/default/resources/tmp_experiment_draft.md" not in remaining_uris


@pytest.mark.asyncio
async def test_sentinel_daemon_lifecycle_and_router_handlers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    active, archive, bm25 = _seed_workspace(tmp_path)
    sentinel = MemoryPuritySentinel(
        active_root=active,
        archive_root=archive,
        audit_log_path=tmp_path / "audit.jsonl",
        bm25_index=bm25,
    )
    monkeypatch.setattr(MemoryPuritySentinel, "get_instance", classmethod(lambda cls: sentinel))

    ctx = RequestContext(user=UserIdentifier("default", "default"), role=Role.ADMIN)
    assert sentinel.start(interval_seconds=60.0) is True
    assert sentinel.status()["running"] is True

    sweep_res = await sweep_memory_purity(PuritySweepRequest(dry_run=False), ctx=ctx)
    assert sweep_res["status"] == "ok"
    assert sweep_res["result"]["archived_count"] == 3

    status_res = await get_purity_sentinel_status(ctx=ctx)
    assert status_res["status"] == "ok"
    assert status_res["result"]["sweep_count"] >= 1

    await sentinel.stop()
    assert sentinel.status()["running"] is False
