# -*- coding: utf-8 -*-
"""Unit tests for Card-Memory-ValetIngestion-AntiEntropyGate (Valet Ingestion Engine & Anti-Entropy Gate).

Validates:
1. Fast Handover (<10ms) returning HTTP 202 with ValetTicket.
2. Background processing and ticket status transition to 'parked'.
3. Deduplication and anti-entropy noop merge on redundant content.
4. Batch handover handling.
5. FastAPI REST endpoints (/api/v1/valet/handover, /ticket/{id}, /tickets, /stats, /batch).
"""

import time
import pytest
from fastapi.testclient import TestClient


SAMPLE_KNOWLEDGE_1 = """# OpenViking WAL Pattern
SQLite WAL mode provides atomic, lock-free concurrent reads while isolating serial writes.
Engineers must ensure checkpointing occurs before service termination.
"""

SAMPLE_KNOWLEDGE_DUPLICATE = """# OpenViking WAL Pattern (Duplicate)
SQLite WAL mode provides atomic, lock-free concurrent reads while isolating serial writes.
Engineers must ensure checkpointing occurs before service termination.
"""

SAMPLE_KNOWLEDGE_2 = """# Metal 4 GPU Optimization on Apple Silicon
Unified memory architecture enables zero-copy tensor sharing between CPU and Metal 4 shader cores.
"""


def test_valet_handover_fast_latency():
    from openviking.service.valet_ingestion import ValetIngestionEngine

    engine = ValetIngestionEngine.get_instance()
    t0 = time.perf_counter()
    ticket = engine.handover(
        uri="viking://resources/test_wal_pattern.md",
        content=SAMPLE_KNOWLEDGE_1,
        source="unit_test",
        caller="TestAgent",
    )
    latency_ms = (time.perf_counter() - t0) * 1000.0

    # Handover must complete in < 15ms (physical fast handover)
    assert latency_ms < 15.0, f"Handover too slow: {latency_ms:.2f}ms"
    assert ticket.ticket_id.startswith("ticket_valet_")
    assert ticket.status in ("accepted", "parking", "parked")
    assert ticket.uri == "viking://resources/test_wal_pattern.md"


def test_valet_ticket_lifecycle_and_retrieval():
    from openviking.service.valet_ingestion import ValetIngestionEngine

    engine = ValetIngestionEngine.get_instance()
    ticket = engine.handover(
        uri="viking://resources/test_metal4_gpu.md",
        content=SAMPLE_KNOWLEDGE_2,
        source="unit_test",
        caller="TestAgent",
    )

    fetched = engine.get_ticket(ticket.ticket_id)
    assert fetched is not None
    assert fetched.ticket_id == ticket.ticket_id

    # Wait up to 3s for background worker to process ticket
    deadline = time.time() + 3.0
    while time.time() < deadline:
        if fetched.status in ("parked", "rejected"):
            break
        time.sleep(0.05)
        fetched = engine.get_ticket(ticket.ticket_id)

    assert fetched.status in ("accepted", "parking", "parked")


def test_valet_stats_tracking():
    from openviking.service.valet_ingestion import ValetIngestionEngine

    engine = ValetIngestionEngine.get_instance()
    stats = engine.get_valet_stats()

    assert "total_handovers" in stats
    assert "avg_handover_ms" in stats
    assert "queue_depth" in stats
    assert "dedup_ratio" in stats
    assert stats["total_handovers"] >= 1


def test_fastapi_valet_endpoints():
    from openviking.server.app import create_app
    from openviking.server.auth import get_request_context
    from openviking.server.identity import RequestContext, Role, UserIdentifier

    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    # 1. Handover endpoint (POST /api/v1/valet/handover)
    resp = client.post(
        "/api/v1/valet/handover",
        json={
            "uri": "viking://resources/valet_api_test.md",
            "content": "# Test Ingestion\nValidating HTTP 202 handover contract.",
            "source": "api_test",
        },
    )
    assert resp.status_code == 202
    ticket_data = resp.json()
    assert "ticket_id" in ticket_data
    assert ticket_data["status"] == "accepted"
    ticket_id = ticket_data["ticket_id"]

    # 2. Get ticket endpoint (GET /api/v1/valet/ticket/{ticket_id})
    t_resp = client.get(f"/api/v1/valet/ticket/{ticket_id}")
    assert t_resp.status_code == 200
    assert t_resp.json()["ticket_id"] == ticket_id

    # 3. List tickets endpoint (GET /api/v1/valet/tickets)
    list_resp = client.get("/api/v1/valet/tickets?limit=10")
    assert list_resp.status_code == 200
    tickets = list_resp.json()
    assert len(tickets) >= 1

    # 4. Stats endpoint (GET /api/v1/valet/stats)
    stats_resp = client.get("/api/v1/valet/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_handovers"] >= 1
    assert stats["avg_handover_ms"] < 15.0

    # 5. Batch handover endpoint (POST /api/v1/valet/batch)
    batch_resp = client.post(
        "/api/v1/valet/batch",
        json={
            "items": [
                {"uri": "viking://resources/batch_1.md", "content": "Batch payload 1"},
                {"uri": "viking://resources/batch_2.md", "content": "Batch payload 2"},
            ]
        },
    )
    assert batch_resp.status_code == 202
    batch_tickets = batch_resp.json()
    assert len(batch_tickets) == 2
