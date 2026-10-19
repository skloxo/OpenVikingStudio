# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for typed RNFV data structures and invariants."""

import pytest

from openviking.storage.resource_rnfv import (
    BASE_VECTOR_PROJECTION,
    CONTROL_BASENAMES,
    FormalEntry,
    FormalTreeSnapshot,
    NewArtifactSnapshot,
    NewEntry,
    RequestIntent,
    RNFVSnapshot,
    ScalarIntent,
    VectorIndexSnapshot,
    VectorRecordSnapshot,
    canonical_vector_records_by_level,
)
from openviking.utils.ingest_options import IngestOptions


def test_new_and_formal_entry_immutability():
    new_e = NewEntry(md5="abc123", is_dir=False)
    assert new_e.md5 == "abc123"
    assert not new_e.is_dir
    with pytest.raises(AttributeError):
        new_e.md5 = "other"  # frozen

    formal_e = FormalEntry(is_dir=True)
    assert formal_e.is_dir
    with pytest.raises(AttributeError):
        formal_e.is_dir = False


def test_scalar_intent_validation():
    # valid
    s = ScalarIntent(field="search_tags", mode="replace", value=["tag1"])
    assert s.required_existing_fields() == frozenset({"search_tags"})

    # invalid field
    with pytest.raises(ValueError, match="unsupported resource scalar intent"):
        ScalarIntent(field="unknown_field", mode="replace", value="val")

    # invalid mode
    with pytest.raises(ValueError, match="unsupported scalar update mode"):
        ScalarIntent(field="search_tags", mode="invalid_mode", value=["tag1"])

    # invalid level
    with pytest.raises(ValueError, match="invalid scalar target levels"):
        ScalarIntent(field="search_tags", mode="replace", value=["tag1"], target_levels=frozenset({3}))


def test_request_intent_from_ingest_options():
    options = IngestOptions(search_tags=["prod", "ai"], search_tag_mode="append")
    req = RequestIntent.from_ingest_options(
        target_uri="viking://user/default/resources/doc.txt",
        processing_mode="full",
        ingest_options=options,
        vectorize=True,
    )
    assert req.target_uri == "viking://user/default/resources/doc.txt"
    assert req.processing_mode == "full"
    assert req.vectorize is True
    assert len(req.scalar_intents) == 1
    assert req.scalar_intents[0].field == "search_tags"
    assert req.scalar_intents[0].mode == "append"
    assert "search_tags" in req.required_vector_fields()
    assert BASE_VECTOR_PROJECTION.issubset(req.required_vector_fields())


def test_canonical_vector_records_by_level():
    r1 = VectorRecordSnapshot(record_id="rec_002", uri="viking://user/default/res", relative_path="", level=0)
    r2 = VectorRecordSnapshot(record_id="rec_001", uri="viking://user/default/res", relative_path="", level=0)
    r3 = VectorRecordSnapshot(record_id="rec_003", uri="viking://user/default/res", relative_path="", level=1)

    canonical, duplicates = canonical_vector_records_by_level([r1, r2, r3])
    # For level 0, rec_001 is smaller than rec_002, so rec_001 should be canonical
    assert canonical[0].record_id == "rec_001"
    assert canonical[1].record_id == "rec_003"
    assert len(duplicates) == 1
    assert duplicates[0].record_id == "rec_002"


def test_rnfv_snapshot_validation():
    req = RequestIntent(
        target_uri="viking://user/default/resources",
        processing_mode="full",
        vectorize=True,
        scalar_intents=(ScalarIntent(field="search_tags", mode="replace", value=["tag"]),),
    )
    new_snap = NewArtifactSnapshot(entries={})
    formal_snap = FormalTreeSnapshot(entries={})

    # Missing projected fields should raise
    invalid_v_snap = VectorIndexSnapshot(
        records_by_id={},
        projected_fields=frozenset({"id", "uri"}),  # missing md5, level, search_tags
    )
    rnfv = RNFVSnapshot(request=req, new=new_snap, formal=formal_snap, vectors=invalid_v_snap)
    with pytest.raises(ValueError, match="RNFV vector projection misses required fields"):
        rnfv.validate_for_planning()

    # Outside target_uri should raise
    valid_projection = frozenset(BASE_VECTOR_PROJECTION | {"search_tags"})
    outside_record = VectorRecordSnapshot(
        record_id="outside",
        uri="viking://user/other/forbidden",
        relative_path="",
        level=0,
    )
    outside_v_snap = VectorIndexSnapshot(
        records_by_id={"outside": outside_record},
        projected_fields=valid_projection,
    )
    rnfv_outside = RNFVSnapshot(request=req, new=new_snap, formal=formal_snap, vectors=outside_v_snap)
    with pytest.raises(ValueError, match="RNFV vector record is outside target"):
        rnfv_outside.validate_for_planning()

    # Valid snapshot
    inside_record = VectorRecordSnapshot(
        record_id="rec_ok",
        uri="viking://user/default/resources/subfile",
        relative_path="subfile",
        level=0,
    )
    ok_v_snap = VectorIndexSnapshot(
        records_by_id={"rec_ok": inside_record},
        projected_fields=valid_projection,
    )
    rnfv_ok = RNFVSnapshot(request=req, new=new_snap, formal=formal_snap, vectors=ok_v_snap)
    rnfv_ok.validate_for_planning()  # passes without exception
