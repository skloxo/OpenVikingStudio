# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests verifying Overwrite Immunity, URI Isolation, and Bitwise NOOP.

Validates the Charlie Munger Inversion Root-Cause Fixes:
1. High-similarity update (Sim >= 0.95) to an existing URI MUST physically write to disk.
2. Documents containing 'bug fixed', '已废弃', '已修正' must NOT be classified as 'delete'.
3. Identical content written to different URIs must NOT be dropped across URIs.
4. Identical content written to the same URI (0 byte delta) is a genuine bitwise NOOP.
5. Ingestion pipeline preserves data integrity and does not silently swallow updates.
"""

import time
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock


LARGE_BASE_DOC = """# Comprehensive VPS and Cloud Hosting Evaluation Guide
This document contains detailed benchmarks, network latency statistics, and pricing matrices.
""" + "\n".join([f"- Provider Cluster Region Node {i:04d}: latency 35ms, bandwidth 1Gbps, active" for i in range(400)])

LARGE_UPDATED_DOC = LARGE_BASE_DOC + """

## Critical Update (Oct 2026)
- DigitalOcean Credit: $200 / 60 days
- Kamatera Limit: 1 instance only, 30 days
- VPS Registration Cheatsheet updated with latest gateway parameters.
"""


@pytest.mark.asyncio
async def test_high_similarity_overwrite_immunity_eval():
    """Verify that updating an existing URI with high similarity is classified as UPDATE and NOT NOOP."""
    from openviking.service.entropy_gatekeeper import EntropyGatekeeper

    gk = EntropyGatekeeper.get_instance()
    gk.reset_for_testing()

    test_uri = "viking://resources/unit_test_vps_cheatsheet.md"

    # Step 1: Initial creation (ADD)
    dec1 = await gk.evaluate_and_intercept(uri=test_uri, content=LARGE_BASE_DOC)
    assert dec1.action == "add", f"Expected 'add' on first write, got {dec1.action}"

    # Step 2: High similarity update (diff is ~200 chars on 15KB doc -> sim > 0.98)
    # Simulate vector probe returning 0.985 against existing knowledge
    with patch.object(gk, "_probe_nearest_vector", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = (0.9850, test_uri, "Comprehensive VPS and Cloud Hosting")
        
        # When evaluating an overwrite to the same URI (or an existing URI),
        # Overwrite Immunity must guarantee action == 'update' (never 'noop'!)
        dec2 = await gk.evaluate_and_intercept(uri=test_uri, content=LARGE_UPDATED_DOC)
        
        assert dec2.action == "update", (
            f"FATAL: Overwrite update was misclassified as {dec2.action}! "
            f"Sim was {dec2.similarity:.4f}. It must be 'update' to physically overwrite disk."
        )


@pytest.mark.asyncio
async def test_bug_fixed_keywords_not_classified_as_delete():
    """Verify that documents discussing bug fixes or deprecations are NOT classified as DELETE."""
    from openviking.service.entropy_gatekeeper import EntropyGatekeeper

    gk = EntropyGatekeeper.get_instance()
    gk.reset_for_testing()

    bug_report_content = """# Memory Leak Postmortem & Resolution
We investigated the memory leak in the WebSocket gateway.
The bug fixed in commit 7a8f9c was caused by an unclosed async generator.
The old connection handler is 已废弃 and must not be used.
"""

    with patch.object(gk, "_probe_nearest_vector", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = (0.3500, None, None)
        
        dec = await gk.evaluate_and_intercept(
            uri="viking://resources/postmortem_bug_fixed.md",
            content=bug_report_content,
        )

        assert dec.action != "delete", (
            f"FATAL: Content containing 'bug fixed'/'已废弃' was falsely classified as 'delete'! Got: {dec.action}"
        )
        assert dec.action in ("add", "update")


@pytest.mark.asyncio
async def test_cross_uri_fingerprint_isolation():
    """Verify that writing identical content to different URIs does NOT drop the second URI."""
    from openviking.service.entropy_gatekeeper import EntropyGatekeeper

    gk = EntropyGatekeeper.get_instance()
    gk.reset_for_testing()

    shared_template = """# Standard System Metric Schema
version: 1.0.0
metrics:
  - cpu_usage
  - memory_rss
  - token_snr
"""

    # First URI
    dec1 = await gk.evaluate_and_intercept(uri="viking://resources/schema_node_a.yaml", content=shared_template)
    assert dec1.action == "add"

    # Second URI with the EXACT same content
    dec2 = await gk.evaluate_and_intercept(uri="viking://resources/schema_node_b.yaml", content=shared_template)
    assert dec2.action != "noop", (
        f"FATAL: schema_node_b was swallowed by cross-URI collision! Got action: {dec2.action}"
    )
    assert dec2.action == "add"


@pytest.mark.asyncio
async def test_exact_bitwise_same_uri_is_honest_noop():
    """Verify that writing identical content to the SAME URI is classified as true bitwise NOOP."""
    from openviking.service.entropy_gatekeeper import EntropyGatekeeper

    gk = EntropyGatekeeper.get_instance()
    gk.reset_for_testing()

    content = "Stable invariant baseline documentation with strict rules."
    uri = "viking://resources/stable_rules.md"

    dec1 = await gk.evaluate_and_intercept(uri=uri, content=content)
    assert dec1.action == "add"

    # Re-writing EXACT same content to the SAME URI
    dec2 = await gk.evaluate_and_intercept(uri=uri, content=content)
    assert dec2.action == "noop"
    assert dec2.similarity == 1.0000
    assert "指纹" in dec2.reason or "Bitwise" in dec2.reason or "NOOP" in dec2.reason


@pytest.mark.asyncio
async def test_valet_worker_overrides_noop_when_disk_missing_or_changed(tmp_path):
    """Verify that ValetIngestion physically writes to disk even if Gatekeeper returned NOOP."""
    from openviking.service.valet_ingestion import ValetIngestionEngine
    from openviking.service.entropy_gatekeeper import GatekeeperDecision

    engine = ValetIngestionEngine.get_instance()
    test_uri = "viking://resources/unit_test_valet_safeguard.md"
    target_file = engine._resolve_uri_to_path(test_uri)
    if target_file and target_file.exists():
        target_file.unlink()

    mock_noop_decision = GatekeeperDecision(
        action="noop",
        similarity=0.9999,
        matched_uri=test_uri,
        matched_text_snippet="Fake snippet",
        reason="Fake Gatekeeper NOOP decision",
        saved_bytes=100,
        uri=test_uri,
    )

    with patch("openviking.service.valet_ingestion.EntropyGatekeeper.get_instance") as mock_gk_cls:
        mock_gk = AsyncMock()
        mock_gk.evaluate_and_intercept.return_value = mock_noop_decision
        mock_gk_cls.return_value = mock_gk

        record = {
            "ticket_id": "test_ticket_safeguard_001",
            "uri": test_uri,
            "content": "# Safeguard Validated Content\nMust physically exist on disk.",
            "caller": "UnitTest",
            "source": "unit_test",
        }

        # Process record directly through valet worker
        await engine._process_valet_record(record)

        # Verification: Physical file MUST exist and contain the content despite Gatekeeper NOOP!
        assert target_file.exists(), "FATAL: Valet failed to override NOOP! Physical file does not exist on disk."
        disk_content = target_file.read_text(encoding="utf-8")
        assert "Safeguard Validated Content" in disk_content, "FATAL: Content on disk did not match!"

        # Clean up
        target_file.unlink()

