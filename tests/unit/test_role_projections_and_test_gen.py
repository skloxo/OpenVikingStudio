# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test suite for Role Projections and Test Retina Generator (Card-47).

Validates:
1. Multi-role projection from unified facts (dev, test, ops views).
2. Automated pytest code generation from route contracts (syntactically valid via AST).
3. Test scaffold generation for FastMCP tools.
"""

from __future__ import annotations

import ast
import pytest

from openviking.service.code_fact_compiler import McpToolFactRecord, RouteFactRecord
from openviking.service.skill_fact_compiler import SkillFactRecord
from openviking.service.role_projector import RoleProjector
from openviking.service.test_retina_generator import TestRetinaGenerator


def test_role_projections_multi_perspective():
    """Test generating distinct views for dev, test, and ops from the same underlying facts."""
    skills = [
        SkillFactRecord(
            name="skill-eval",
            description="Evaluate models",
            allowed_tools=["run_command"],
            triggers=["eval", "benchmark"],
        )
    ]
    routes = [
        RouteFactRecord(
            method="GET",
            path="/api/v1/catalog/summary",
            handler_name="get_catalog_summary",
            is_async=True,
            summary="Get high-level knowledge catalog metric summary",
            source_file="routers/code_catalog.py",
            line_number=72,
        ),
        RouteFactRecord(
            method="POST",
            path="/api/v1/task-cards/file",
            handler_name="file_task_card",
            is_async=True,
            summary="File a new autonomous task card",
            source_file="routers/task_cards.py",
            line_number=25,
        ),
    ]
    tools = [
        McpToolFactRecord(
            name="openviking_search",
            handler_name="search_memory",
            is_async=True,
            parameters_signature="query: str, limit: int = 5",
            return_type="Dict[str, Any]",
            docstring="Search memories.",
            source_file="server/mcp.py",
            line_number=10,
        )
    ]

    # 1. Dev projection: Focus on signatures and seams
    dev_view = RoleProjector.project_dev(skills, routes, tools)
    assert dev_view["role"] == "dev"
    assert "openviking_search" in dev_view["mcp_contracts"][0]["name"]
    assert "query: str" in dev_view["mcp_contracts"][0]["parameters_signature"]

    # 2. Test projection: Focus on endpoints and verification targets
    test_view = RoleProjector.project_test(routes, tools)
    assert test_view["role"] == "test"
    assert test_view["total_testable_endpoints"] == 2
    assert test_view["routes_to_test"][0]["method"] == "GET"

    # 3. Ops projection: Focus on ports and HTTP distribution
    ops_view = RoleProjector.project_ops(routes)
    assert ops_view["role"] == "ops"
    assert ops_view["methods_distribution"]["GET"] == 1
    assert ops_view["methods_distribution"]["POST"] == 1


def test_test_retina_code_generator_for_route():
    """Test generating syntactically valid pytest test functions from route facts."""
    route = RouteFactRecord(
        method="GET",
        path="/api/v1/catalog/summary",
        handler_name="get_catalog_summary",
        is_async=True,
        summary="Get high-level knowledge catalog metric summary",
        source_file="routers/code_catalog.py",
        line_number=72,
    )

    code_snippet = TestRetinaGenerator.generate_pytest_for_route(route)
    assert "def test_get_api_v1_catalog_summary_contract(" in code_snippet
    assert 'client.get("/api/v1/catalog/summary")' in code_snippet
    assert "assert resp.status_code in (200, 201, 400, 422)" in code_snippet

    # Crucial gatekeeper: AST parse verification ensures zero syntax error!
    parsed_tree = ast.parse(code_snippet)
    assert parsed_tree is not None


def test_test_retina_code_generator_for_tool():
    """Test generating pytest scaffold for a FastMCP tool contract."""
    tool = McpToolFactRecord(
        name="openviking_search",
        handler_name="search_memory",
        is_async=True,
        parameters_signature="query: str, limit: int = 5",
        return_type="Dict[str, Any]",
        docstring="Search memories.",
        source_file="server/mcp.py",
        line_number=10,
    )

    tool_code = TestRetinaGenerator.generate_pytest_for_mcp_tool(tool)
    assert "def test_openviking_search_contract(" in tool_code
    assert '"query": "test_query"' in tool_code

    parsed_tree = ast.parse(tool_code)
    assert parsed_tree is not None


def test_projections_and_gen_tests_api():
    """Verify FastAPI endpoints for role projections and test generation via TestClient."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from openviking.server.routers.code_catalog import router as code_catalog_router

    app = FastAPI()
    app.include_router(code_catalog_router)
    client = TestClient(app)

    # 1. Test /api/v1/catalog/projections/dev
    dev_resp = client.get("/api/v1/catalog/projections/dev")
    assert dev_resp.status_code == 200
    d_data = dev_resp.json()
    assert d_data["status"] == "ok"
    assert d_data["role"] == "dev"
    assert "mcp_contracts" in d_data["projection"]

    # 2. Test /api/v1/catalog/projections/ops
    ops_resp = client.get("/api/v1/catalog/projections/ops")
    assert ops_resp.status_code == 200
    o_data = ops_resp.json()
    assert o_data["status"] == "ok"
    assert o_data["projection"]["primary_service_port"] == 1933

    # 3. Test /api/v1/catalog/generate-tests
    gen_resp = client.get("/api/v1/catalog/generate-tests?limit=3")
    assert gen_resp.status_code == 200
    g_data = gen_resp.json()
    assert g_data["status"] == "ok"
    assert g_data["total_routes_covered"] > 0
    assert "def test_" in g_data["generated_test_code"]
    # Check that generated code parses without syntax errors
    assert ast.parse(g_data["generated_test_code"]) is not None

