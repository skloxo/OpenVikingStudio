# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Regression unit tests for Card-104: Ghost slice pruning and vector consistency resync."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from openviking.server.identity import RequestContext, Role
from openviking.storage.index_consistency import (
    IndexExpectation,
    IndexConsistencyReport,
    check_index_consistency,
    _fetch_index_records,
)
from scripts.prune_ghost_slices import is_protected_uri


@pytest.fixture
def mock_ctx():
    return RequestContext(user="test_admin", role=Role.ROOT)


class TestCard104WhitelistProtection:
    """Test physical immunity whitelist rules."""

    def test_protected_uris(self):
        assert is_protected_uri("viking://resources/master_memory/evolution_lessons/l1.md") is True
        assert is_protected_uri("viking://resources/skills/core/skill.md") is True
        assert is_protected_uri("viking://resources/crystals/c1.json") is True

    def test_unprotected_and_test_remnants(self):
        assert is_protected_uri("viking://resources/paperclip_doc_1/doc.md") is False
        assert is_protected_uri("viking://resources/staging/old_session.md") is False
        # Test remnants are allowed even under master_memory
        assert is_protected_uri("viking://resources/master_memory/test_card152_changed.md") is False
        assert is_protected_uri("viking://resources/master_memory/test_card104_temp.md") is False


class TestCard104VectorFilterContract:
    """Test vector store filter contract alignment with VikingDBManager."""

    @pytest.mark.asyncio
    async def test_fetch_index_records_passes_dict_filter(self, mock_ctx):
        mock_vs = AsyncMock()
        mock_vs.filter.return_value = [{"uri": "viking://resources/doc.md", "level": 2}]

        records = await _fetch_index_records(mock_vs, "viking://resources/doc.md", mock_ctx)
        assert len(records) == 1
        assert records[0]["uri"] == "viking://resources/doc.md"

        # Verify filter argument was passed as dict contract
        call_kwargs = mock_vs.filter.call_args.kwargs
        assert "filter" in call_kwargs
        filter_dict = call_kwargs["filter"]
        assert isinstance(filter_dict, dict)
        assert filter_dict["op"] == "must"
        assert filter_dict["field"] == "uri"
        assert filter_dict["conds"] == ["viking://resources/doc.md"]


class TestCard104OrphanPruningAndScore:
    """Test forward check, orphan detection, and score recovery."""

    @pytest.mark.asyncio
    async def test_clean_prune_recovers_score_to_100(self, mock_ctx):
        viking_fs = AsyncMock()
        entries = [
            {"isDir": False, "rel_path": "active_file.md", "name": "active_file.md", "size": 128},
        ]
        viking_fs.read_file.return_value = "content"
        viking_fs.exists.return_value = True

        vector_store = AsyncMock()

        async def fake_filter(**kwargs):
            filter_expr = kwargs.get("filter")
            target_uri = (
                filter_expr.get("conds", [None])[0]
                if isinstance(filter_expr, dict)
                else getattr(filter_expr, "value", None)
            )
            if target_uri == "viking://resources":
                return [
                    {"uri": "viking://resources", "level": 0},
                    {"uri": "viking://resources", "level": 1},
                ]
            if target_uri == "viking://resources/active_file.md":
                return [{"uri": "viking://resources/active_file.md", "level": 2}]
            return []

        async def fake_scroll(**kwargs):
            return [
                {"uri": "viking://resources/active_file.md"},
                {"uri": "viking://resources/zombie_vector_slice.md"},
            ]

        vector_store.filter = fake_filter
        vector_store.scroll = fake_scroll
        vector_store.remove_by_uri = AsyncMock(return_value=1)

        bm25_index = MagicMock()
        bm25_index.list_all_uris.return_value = [
            "viking://resources/active_file.md",
            "viking://resources/master_memory/test_card152_changed.md",
        ]
        bm25_index.prune_orphans.return_value = 1

        report = await check_index_consistency(
            viking_fs=viking_fs,
            vector_store=vector_store,
            root_uri="viking://resources",
            entries=entries,
            ctx=mock_ctx,
            prune=True,
            bm25_index=bm25_index,
        )

        assert report.consistency_score == 100.0
        assert report.pruned_vector_count == 1
        assert report.pruned_bm25_count == 1
        assert len(report.missing_records) == 0
