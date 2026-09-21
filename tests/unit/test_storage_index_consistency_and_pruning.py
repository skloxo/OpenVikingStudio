# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Card 6: Storage index consistency checking and orphan pruning."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from openviking.server.identity import RequestContext, Role
from openviking.storage.index_consistency import (
    IndexExpectation,
    IndexConsistencyReport,
    check_index_consistency,
)


@pytest.fixture
def mock_ctx():
    return RequestContext(user="u1", role=Role.ROOT)


class TestIndexConsistencyReportModel:
    """Test the enhanced IndexConsistencyReport data model and scoring."""

    def test_perfect_consistency_score(self):
        exp = (IndexExpectation(uri="viking://resources/f1.md", rel_path="f1.md", level=2),)
        report = IndexConsistencyReport(
            expected=exp,
            missing_records=(),
            orphan_records=(),
            bm25_orphan_uris=(),
            consistency_score=100.0,
        )
        assert report.ok is True
        assert report.consistency_score == 100.0
        data = report.to_dict()
        assert data["ok"] is True
        assert data["expected_count"] == 1
        assert data["missing_record_count"] == 0
        assert data["orphan_record_count"] == 0
        assert data["bm25_orphan_count"] == 0

    def test_imperfect_consistency_with_orphans(self):
        exp = (
            IndexExpectation(uri="viking://resources/f1.md", rel_path="f1.md", level=2),
            IndexExpectation(uri="viking://resources/f2.md", rel_path="f2.md", level=2),
        )
        report = IndexConsistencyReport(
            expected=exp,
            missing_records=(),
            orphan_records=("viking://resources/deleted_file.md",),
            bm25_orphan_uris=("viking://resources/ghost_doc.md",),
            consistency_score=0.0,
        )
        assert report.ok is False
        data = report.to_dict()
        assert data["ok"] is False
        assert "viking://resources/deleted_file.md" in data["orphan_records"]
        assert "viking://resources/ghost_doc.md" in data["bm25_orphan_records"]


class TestCheckIndexConsistencyWithOrphanPruning:
    """Test forward check, reverse orphan detection, and prune actions."""

    @pytest.mark.asyncio
    async def test_detect_missing_and_orphan_records_dry_run(self, mock_ctx):
        viking_fs = AsyncMock()
        # Entries in FS: f1.md exists, but f2.md does not
        entries = [
            {"isDir": False, "rel_path": "f1.md", "name": "f1.md", "size": 100},
            {"isDir": False, "rel_path": "f2.md", "name": "f2.md", "size": 100},
        ]
        viking_fs.read_file.return_value = "content"
        viking_fs.exists.return_value = True

        # Vector store has f1.md (level 2) and orphan.md, but is missing f2.md
        vector_store = AsyncMock()

        async def fake_filter(**kwargs):
            filter_expr = kwargs.get("filter")
            if filter_expr and getattr(filter_expr, "value", None) == "viking://resources/f1.md":
                return [{"uri": "viking://resources/f1.md", "level": 2}]
            return []

        async def fake_scroll(**kwargs):
            return [
                {"uri": "viking://resources/f1.md"},
                {"uri": "viking://resources/orphan.md"},
            ]

        vector_store.filter = fake_filter
        vector_store.scroll = fake_scroll

        # Mock BM25 index with ghost.md
        bm25_index = MagicMock()
        bm25_index.list_all_uris.return_value = [
            "viking://resources/f1.md",
            "viking://resources/ghost.md",
        ]

        # Dry run (prune=False)
        report = await check_index_consistency(
            viking_fs=viking_fs,
            vector_store=vector_store,
            root_uri="viking://resources",
            entries=entries,
            ctx=mock_ctx,
            prune=False,
            bm25_index=bm25_index,
        )

        assert report.ok is False
        # f2.md should be missing
        missing_uris = [item.uri for item in report.missing_records]
        assert "viking://resources/f2.md" in missing_uris
        # orphan.md should be detected
        assert "viking://resources/orphan.md" in report.orphan_records
        # ghost.md should be in BM25 orphans
        assert "viking://resources/ghost.md" in report.bm25_orphan_uris
        assert report.pruned_vector_count == 0
        assert report.pruned_bm25_count == 0

    @pytest.mark.asyncio
    async def test_prune_orphans_actively(self, mock_ctx):
        viking_fs = AsyncMock()
        entries = [
            {"isDir": False, "rel_path": "f1.md", "name": "f1.md", "size": 100},
        ]
        viking_fs.read_file.return_value = "content"
        viking_fs.exists.return_value = True

        vector_store = AsyncMock()

        async def fake_filter(**kwargs):
            filter_expr = kwargs.get("filter")
            target_uri = getattr(filter_expr, "value", None)
            if target_uri == "viking://resources":
                return [
                    {"uri": "viking://resources", "level": 0},
                    {"uri": "viking://resources", "level": 1},
                ]
            return [{"uri": "viking://resources/f1.md", "level": 2}]

        async def fake_scroll(**kwargs):
            return [
                {"uri": "viking://resources"},
                {"uri": "viking://resources/f1.md"},
                {"uri": "viking://resources/stale_vector_1.md"},
                {"uri": "viking://resources/stale_vector_2.md"},
            ]

        vector_store.filter = fake_filter
        vector_store.scroll = fake_scroll
        vector_store.remove_by_uri = AsyncMock(return_value=1)

        bm25_index = MagicMock()
        bm25_index.list_all_uris.return_value = [
            "viking://resources/f1.md",
            "viking://resources/stale_bm25.md",
        ]
        bm25_index.prune_orphans.return_value = 1

        # Prune = True
        report = await check_index_consistency(
            viking_fs=viking_fs,
            vector_store=vector_store,
            root_uri="viking://resources",
            entries=entries,
            ctx=mock_ctx,
            prune=True,
            bm25_index=bm25_index,
        )

        assert report.pruned_vector_count == 2
        assert vector_store.remove_by_uri.await_count == 2
        assert report.pruned_bm25_count == 1
        bm25_index.prune_orphans.assert_called_once()
        # Since missing is 0 and all orphans were pruned, score returns to 100.0
        assert report.consistency_score == 100.0
