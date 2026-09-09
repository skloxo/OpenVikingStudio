# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for ValetIngestionEngine and Dual-Track Tasks."""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from openviking.service.entropy_gatekeeper import GatekeeperDecision
from openviking.service.valet_ingestion import ValetIngestionEngine, ValetTicket


def test_valet_engine_singleton():
    e1 = ValetIngestionEngine.get_instance()
    e2 = ValetIngestionEngine.get_instance()
    assert e1 is e2


def test_valet_fast_handover_latency():
    """Driver handover must return immediately in < 15ms with a valid ticket."""
    engine = ValetIngestionEngine.get_instance()
    t0 = time.time()
    ticket = engine.handover(
        uri="viking://resources/master_memory/test_lesson.md",
        content="# Test lesson on Valet Ingestion architecture\nValid content for testing.",
        source="test",
        caller="TestAgent",
    )
    dt_ms = (time.time() - t0) * 1000
    assert dt_ms < 15.0  # Fast handover <15ms
    assert ticket.ticket_id.startswith("valet_") or ticket.ticket_id.startswith("ticket_valet_")
    assert "轻量增量入库" in ticket.message or "准入判定" in ticket.message or "门禁裁决" in ticket.message


@pytest.mark.asyncio
async def test_valet_async_processing_noop():
    """Valet worker processes record, correctly sets ticket to parked when noop."""
    engine = ValetIngestionEngine.get_instance()
    ticket_id = "ticket_valet_test_noop"
    uri = "viking://resources/master_memory/test_dup.md"
    content = "Duplicate content"
    
    with engine._tickets_lock:
        engine._tickets[ticket_id] = ValetTicket(ticket_id=ticket_id, uri=uri)

    mock_decision = GatekeeperDecision(
        action="noop",
        similarity=0.985,
        matched_uri="viking://resources/master_memory/orig.md",
        reason="[纯同义重复] 匹配",
        saved_bytes=len(content.encode("utf-8")),
    )

    with patch("openviking.service.entropy_gatekeeper.EntropyGatekeeper.evaluate_and_intercept", new_callable=AsyncMock) as mock_eval:
        mock_eval.return_value = mock_decision
        await engine._process_valet_record({
            "ticket_id": ticket_id,
            "uri": uri,
            "content": content,
            "metadata": {},
        })

    updated_ticket = engine.get_ticket(ticket_id)
    assert updated_ticket is not None
    assert updated_ticket.status == "parked"
    assert updated_ticket.action == "noop"
    assert updated_ticket.similarity == 0.985
    assert updated_ticket.matched_uri == "viking://resources/master_memory/orig.md"
    assert updated_ticket.deliverable_uri == "viking://resources/master_memory/orig.md"


@pytest.mark.asyncio
async def test_valet_async_processing_add():
    """Valet worker processes record, correctly parks new atomic knowledge."""
    engine = ValetIngestionEngine.get_instance()
    ticket_id = "ticket_valet_test_add"
    uri = "viking://resources/master_memory/test_new.md"
    content = "Atomic new knowledge content"

    with engine._tickets_lock:
        engine._tickets[ticket_id] = ValetTicket(ticket_id=ticket_id, uri=uri)

    mock_decision = GatekeeperDecision(
        action="add",
        similarity=0.45,
        matched_uri=None,
        reason="[独立新命题] 放行",
    )

    with patch("openviking.service.entropy_gatekeeper.EntropyGatekeeper.evaluate_and_intercept", new_callable=AsyncMock) as mock_eval, \
         patch.object(engine, "_write_local_file") as mock_write:
        mock_eval.return_value = mock_decision
        await engine._process_valet_record({
            "ticket_id": ticket_id,
            "uri": uri,
            "content": content,
            "metadata": {},
        })
        assert mock_write.called

    updated_ticket = engine.get_ticket(ticket_id)
    assert updated_ticket is not None
    assert updated_ticket.status == "parked"
    assert updated_ticket.action == "add"
    assert updated_ticket.deliverable_uri == uri
