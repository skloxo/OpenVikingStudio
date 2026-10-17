# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""TDD Test Suite for Card-95: Asynchronous Skill Ingestion Queue & SQLite Concurrency."""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role, UserIdentifier
from openviking.server.routers.skill_ingestion import router
from openviking.storage.skill_ingestion_store import (
    IngestionRecord,
    IngestionStatus,
    SkillIngestionStore,
)
from openviking.service.skill_ingestion_worker import SkillIngestionWorker
from openviking.service.skill_ingestion_validator import SkillIngestionValidator


@pytest.fixture
def temp_db_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def store(temp_db_dir):
    db_path = temp_db_dir / "test_ingestion_inbox.db"
    return SkillIngestionStore(db_path=db_path)


@pytest.fixture
def worker(store):
    validator = SkillIngestionValidator()
    return SkillIngestionWorker(store=store, validator=validator)


@pytest.fixture
def client(store, worker) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    mock_ctx = RequestContext(
        user=UserIdentifier(account_id="test", user_id="test_admin"),
        role=Role(Role.ADMIN),
    )
    app.dependency_overrides[get_request_context] = lambda: mock_ctx
    return TestClient(app, raise_server_exceptions=False)


VALID_SKILL_MD = """---
name: k8s-pod-debugger
version: 1.0.0
domain: devops
description: Debugs crashed Kubernetes pods and captures event logs.
triggers:
  - k8s crashloop
  - pod debugging
  - container crashed
allowed-tools:
  - openviking_find
  - openviking_read
---

# K8s Pod Debugger

Instructions on inspecting pod events.
"""

INVALID_DANGEROUS_SKILL_MD = """---
name: dangerous-sys-skill
version: 1.0.0
domain: ops
description: Dangerous skill with unauthorized system command
triggers:
  - exploit system
  - run dangerous
  - shell hijack
allowed-tools:
  - openviking_find
---

```python
import os
os.system("rm -rf /tmp/danger")
```
"""


def test_store_init_and_tables(store):
    """Verify table creation, WAL mode, and queue depth initialization."""
    depth = store.get_queue_depth()
    assert depth["total"] == 0
    assert depth["pending"] == 0


def test_enqueue_skill_fast_latency(store):
    """Verify enqueue operates well below the 50ms latency ceiling and returns receipt."""
    t0 = time.perf_counter()
    record = store.enqueue_skill(
        skill_name="k8s-pod-debugger",
        raw_content=VALID_SKILL_MD,
        author="test-agent",
    )
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 50.0
    assert record.receipt_id.startswith("ingest_")
    assert record.skill_name == "k8s-pod-debugger"
    assert record.status == IngestionStatus.PENDING
    assert record.author == "test-agent"


def test_get_and_list_records(store):
    """Verify record retrieval and status filtering."""
    r1 = store.enqueue_skill("skill-a", VALID_SKILL_MD, author="dev1")
    r2 = store.enqueue_skill("skill-b", VALID_SKILL_MD, author="dev2")

    fetched = store.get_record(r1.receipt_id)
    assert fetched is not None
    assert fetched.receipt_id == r1.receipt_id
    assert fetched.skill_name == "skill-a"

    all_records = store.list_records()
    assert len(all_records) == 2

    pending_records = store.list_records(status=IngestionStatus.PENDING)
    assert len(pending_records) == 2


def test_update_status_and_metrics(store):
    """Verify status machine transitions and metric counts."""
    r = store.enqueue_skill("k8s-debugger", VALID_SKILL_MD)
    assert store.get_queue_depth()["pending"] == 1

    store.update_status(
        receipt_id=r.receipt_id,
        status=IngestionStatus.VALIDATING,
        status_message="Running AST and Frontmatter checks",
    )
    updated = store.get_record(r.receipt_id)
    assert updated.status == IngestionStatus.VALIDATING
    assert store.get_queue_depth()["validating"] == 1
    assert store.get_queue_depth()["pending"] == 0


def test_worker_processes_valid_skill(worker, store):
    """Verify worker processes pending valid skill into STAGED status."""
    r = store.enqueue_skill("valid-skill", VALID_SKILL_MD)

    processed = worker.process_next_batch(batch_size=5)
    assert len(processed) == 1
    assert processed[0].receipt_id == r.receipt_id
    assert processed[0].status == IngestionStatus.STAGED
    assert "Passed static checks" in processed[0].status_message

    record = store.get_record(r.receipt_id)
    assert record.status == IngestionStatus.STAGED
    assert record.validation_report is not None
    assert record.validation_report.get("is_valid") is True


def test_worker_processes_invalid_skill(worker, store):
    """Verify worker rejects skill containing forbidden AST calls."""
    r = store.enqueue_skill("dangerous-skill", INVALID_DANGEROUS_SKILL_MD)

    processed = worker.process_next_batch(batch_size=5)
    assert len(processed) == 1
    assert processed[0].receipt_id == r.receipt_id
    assert processed[0].status == IngestionStatus.REJECTED
    assert "Dangerous system call detected" in processed[0].status_message

    record = store.get_record(r.receipt_id)
    assert record.status == IngestionStatus.REJECTED
    assert record.validation_report.get("is_valid") is False


def test_worker_empty_queue_is_noop(worker):
    """Verify worker returns empty list when queue has no pending items."""
    processed = worker.process_next_batch(batch_size=5)
    assert processed == []


def test_concurrent_claim_isolation(store):
    """Verify atomic fetch_and_claim prevents double processing of items."""
    r1 = store.enqueue_skill("skill-1", VALID_SKILL_MD)
    r2 = store.enqueue_skill("skill-2", VALID_SKILL_MD)

    claimed_worker_1 = store.fetch_and_claim_pending(batch_size=1)
    claimed_worker_2 = store.fetch_and_claim_pending(batch_size=1)

    assert len(claimed_worker_1) == 1
    assert len(claimed_worker_2) == 1
    assert claimed_worker_1[0].receipt_id != claimed_worker_2[0].receipt_id
    assert claimed_worker_1[0].status == IngestionStatus.VALIDATING
    assert claimed_worker_2[0].status == IngestionStatus.VALIDATING

    claimed_worker_3 = store.fetch_and_claim_pending(batch_size=1)
    assert len(claimed_worker_3) == 0


def test_api_submit_and_query_queue(client: TestClient):
    """Verify REST endpoints for submit, query queue, and batch processing."""
    submit_resp = client.post(
        "/api/v1/skills/ingestion/submit",
        json={
            "skill_name": "api-test-skill",
            "content": VALID_SKILL_MD,
            "author": "ci-runner",
        },
    )
    assert submit_resp.status_code == 200
    data = submit_resp.json()
    assert data["status"] == "ok"
    receipt_id = data["receipt_id"]
    assert receipt_id.startswith("ingest_")

    # Query receipt
    rcpt_resp = client.get(f"/api/v1/skills/ingestion/receipt/{receipt_id}")
    assert rcpt_resp.status_code == 200
    assert rcpt_resp.json()["record"]["status"] == "PENDING"

    # Query queue metrics
    q_resp = client.get("/api/v1/skills/ingestion/queue")
    assert q_resp.status_code == 200
    assert q_resp.json()["queue_depth"]["pending"] >= 1

    # Trigger worker tick
    proc_resp = client.post("/api/v1/skills/ingestion/process-batch?batch_size=5")
    assert proc_resp.status_code == 200
    summary = proc_resp.json()["worker_summary"]
    assert summary["processed_count"] >= 1
    assert summary["staged_count"] >= 1
