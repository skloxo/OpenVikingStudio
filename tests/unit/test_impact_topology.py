# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test suite for Reverse Impact Topology (Card-46).

Validates:
1. Skills-to-tools inverted index (which skills depend on a given tool).
2. Skill trigger collision detection (which skills share overlapping triggers).
3. SQLite table reader/writer impact topology from AST/SQL statements.
4. Output Markdown view format for zero-hallucination refactoring safeguards.
"""

from __future__ import annotations

import pytest

from openviking.service.skill_fact_compiler import SkillFactRecord
from openviking.service.code_fact_compiler import McpToolFactRecord, RouteFactRecord
from openviking.service.impact_topology import (
    ImpactTopologyBuilder,
    TableImpactRecord,
    SkillConflictGroup,
)


def test_skills_inverted_and_collision_topology():
    """Test building inverted index from tools to skills, and detecting trigger collisions."""
    skills = [
        SkillFactRecord(
            name="skill-debugger",
            description="Diagnose bugs",
            allowed_tools=["run_command", "view_file"],
            triggers=["diagnose", "bug", "error"],
        ),
        SkillFactRecord(
            name="skill-trace",
            description="Trace bug execution",
            allowed_tools=["view_file", "grep_search"],
            triggers=["trace", "bug", "callstack"],
        ),
        SkillFactRecord(
            name="skill-deployer",
            description="Deploy services",
            allowed_tools=["run_command"],
            triggers=["deploy", "release"],
        ),
    ]

    topology = ImpactTopologyBuilder.build_skills_topology(skills)

    # 1. Tool to skills inverted index
    tool_map = topology["tools_to_skills"]
    assert "run_command" in tool_map
    assert set(tool_map["run_command"]) == {"skill-debugger", "skill-deployer"}
    assert set(tool_map["view_file"]) == {"skill-debugger", "skill-trace"}

    # 2. Trigger collision detection: "bug" is shared by debugger and trace
    conflicts = topology["trigger_conflicts"]
    bug_conflict = next((c for c in conflicts if c.trigger == "bug"), None)
    assert bug_conflict is not None
    assert set(bug_conflict.conflicting_skills) == {"skill-debugger", "skill-trace"}


def test_sqlite_table_impact_extraction():
    """Test extracting reader and writer files from SQL queries in Python source."""
    sample_writer_code = '''
def update_status(cursor, uri: str, status: str):
    cursor.execute(
        "UPDATE vector_sync_state SET status = ? WHERE uri = ?",
        (status, uri)
    )
    cursor.execute(
        "INSERT INTO queue_dead_letters (id, payload) VALUES (?, ?)",
        ("msg-1", "{}")
    )
'''
    sample_reader_code = '''
def query_pending(cursor):
    cursor.execute("SELECT uri, status FROM vector_sync_state WHERE status = 'PENDING'")
    return cursor.fetchall()
'''

    builder = ImpactTopologyBuilder()
    builder.analyze_source_sql("service/writer.py", sample_writer_code)
    builder.analyze_source_sql("service/reader.py", sample_reader_code)

    impact_map = builder.get_table_impact_map()

    # 1. vector_sync_state impact
    assert "vector_sync_state" in impact_map
    v_rec = impact_map["vector_sync_state"]
    assert "service/writer.py" in v_rec.writers
    assert "service/reader.py" in v_rec.readers

    # 2. queue_dead_letters impact
    assert "queue_dead_letters" in impact_map
    q_rec = impact_map["queue_dead_letters"]
    assert "service/writer.py" in q_rec.writers
    assert len(q_rec.readers) == 0


def test_views_markdown_rendering():
    """Test rendering deterministic Markdown views from topology records."""
    table_records = {
        "vector_sync_state": TableImpactRecord(
            table_name="vector_sync_state",
            writers=["service/vector_sync_tracker.py", "storage/content_write.py"],
            readers=["server/routers/dlq.py", "service/offline_dreamer.py"],
            description="Tracks index synchronization state machine.",
        )
    }

    markdown = ImpactTopologyBuilder.render_storage_views_markdown(table_records)
    assert "# 🗄️ SQLite Storage Tables Impact Topology (`views/storage_tables.md`)" in markdown
    assert "vector_sync_state" in markdown
    assert "service/vector_sync_tracker.py" in markdown
    assert "server/routers/dlq.py" in markdown


def test_views_rest_api_endpoints():
    """Verify FastAPI endpoints for reverse impact views via TestClient."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from openviking.server.routers.code_catalog import router as code_catalog_router

    app = FastAPI()
    app.include_router(code_catalog_router)
    client = TestClient(app)

    # 1. Test /api/v1/catalog/views/storage
    resp = client.get("/api/v1/catalog/views/storage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["total_tables"] > 0
    assert "views/storage_tables.md" in data["markdown_view"]

    # 2. Test /api/v1/catalog/views/skills
    skills_resp = client.get("/api/v1/catalog/views/skills")
    assert skills_resp.status_code == 200
    s_data = skills_resp.json()
    assert s_data["status"] == "ok"
    assert "tools_to_skills" in s_data

