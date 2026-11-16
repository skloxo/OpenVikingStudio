# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

from __future__ import annotations

from datetime import datetime, timezone

from openviking.observability.events import ObservabilityEvent
from openviking.observability.usage_audit.projection import (
    context_write_operation_for_http,
    project_events,
)


def test_context_write_operation_for_http_covers_legacy_and_new_write_routes():
    expected = [
        ("/api/v1/resources", "add_resource"),
        ("/api/v1/resources/cp", "add_resource"),
        ("/api/v1/resources/mv", "add_resource"),
        ("/api/v1/content/write", "add_resource"),
        ("/api/v1/content/batch-write", "add_resource"),
        ("/api/v1/content/set_tags", "add_resource"),
        ("/api/v1/fs/mkdir", "add_resource"),
        ("/api/v1/fs/cp", "add_resource"),
        ("/api/v1/fs/mv", "add_resource"),
        ("/api/v1/fs/attrs/set_tags", "add_resource"),
        ("/api/v1/valet/handover", "add_resource"),
        ("/api/v1/valet/batch", "add_resource"),
        ("/api/v1/skills", "add_skill"),
        ("/api/v1/skills/ingestion/submit", "add_skill"),
        ("/api/v1/skills/ingestion/process-batch", "add_skill"),
        ("/api/v1/sessions/{session_id}/messages", "session.add_message"),
        ("/api/v1/sessions/{session_id}/messages/batch", "session.add_message"),
        ("/api/v1/sessions/{session_id}/commit", "session.commit"),
        ("/api/v1/task-cards/file", "session.commit"),
        ("/api/v1/task-cards/{card_id}/resolve", "session.commit"),
    ]
    for route, operation in expected:
        assert context_write_operation_for_http("POST", route, 200) == operation
        assert context_write_operation_for_http("POST", route, 202) == operation
        assert context_write_operation_for_http("POST", route, 400) is None
        assert context_write_operation_for_http("GET", route, 200) is None

    for non_write in (
        "/api/v1/content/read",
        "/api/v1/fs/ls",
        "/api/v1/fs/tree",
        "/api/v1/skills/find",
        "/api/v1/skills/ingestion/rollback",
        "/api/v1/resources/temp_upload",
    ):
        assert context_write_operation_for_http("POST", non_write, 200) is None


def test_project_events_aggregates_context_write_and_http_request():
    ts = datetime(2026, 11, 16, 10, 15, 0, tzinfo=timezone.utc)
    events = [
        ObservabilityEvent(
            event_name="context.write",
            payload={
                "operation": "session.commit",
                "tool_name": "record_evolution_lesson",
                "status": "success",
            },
            timestamp=ts,
            account_id="acct-1",
            user_id="alice",
        ),
        ObservabilityEvent(
            event_name="context.write",
            payload={
                "operation": "session.commit",
                "tool_name": "remember",
                "status": "success",
                "count": 2,
            },
            timestamp=ts,
            account_id="acct-1",
            user_id="alice",
        ),
        ObservabilityEvent(
            event_name="context.write",
            payload={"operation": "session.commit", "status": "error"},
            timestamp=ts,
            account_id="acct-1",
            user_id="alice",
        ),
        ObservabilityEvent(
            event_name="context.write",
            payload={"operation": "unknown_op", "status": "success"},
            timestamp=ts,
            account_id="acct-1",
            user_id="alice",
        ),
        ObservabilityEvent(
            event_name="http.request",
            payload={
                "method": "POST",
                "route": "/api/v1/skills/ingestion/submit",
                "status": 200,
                "duration_ms": 12.0,
            },
            timestamp=ts,
            account_id="acct-1",
            user_id="alice",
        ),
    ]

    proj = project_events(events)
    assert proj.context_rows == {
        ("acct-1", "alice", "2026-11-16", 10, "session.commit"): 3,
        ("acct-1", "alice", "2026-11-16", 10, "add_skill"): 1,
    }
