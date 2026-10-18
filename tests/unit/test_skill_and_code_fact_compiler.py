# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test suite for Skill and Code Fact Compiler (Card-45).

Validates:
1. Pure static extraction of YAML Frontmatter, triggers, and allowed-tools for skills.
2. Honest omission (unverified fields remain blank, zero hallucination).
3. Python AST extraction for FastMCP Tools and FastAPI Routes.
4. L0/L1 output format compliance with OKF / VikingFS standards.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from openviking.service.skill_fact_compiler import (
    SkillFactCompiler,
    SkillFactRecord,
)
from openviking.service.code_fact_compiler import (
    CodeFactCompiler,
    McpToolFactRecord,
    RouteFactRecord,
)


def test_skill_fact_compiler_basic():
    """Test standard SKILL.md fact compilation with complete frontmatter."""
    sample_skill_content = """---
name: sample-debugger
description: "排查 bug 与诊断内存泄露的专家技能。触发词：排查, 诊断, 内存泄露, 报错。"
allowed-tools:
  - run_command
  - view_file
tags:
  - debug
  - diagnostic
---

# Sample Debugger

## 核心公理
1. 第一性原理排查。
2. 零手动干预。
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "sample-debugger"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(sample_skill_content, encoding="utf-8")

        record = SkillFactCompiler.compile_skill_file(skill_file)

        assert record is not None
        assert record.name == "sample-debugger"
        assert record.allowed_tools == ["run_command", "view_file"]
        assert "debug" in record.tags
        assert "排查" in record.triggers
        assert "诊断" in record.triggers
        assert "内存泄露" in record.triggers
        assert record.l0_summary.startswith("sample-debugger")
        assert len(record.unverified_fields) == 0


def test_skill_fact_compiler_honesty_unverified_fields():
    """Test honesty principle: missing/unprovable fields are kept blank, never hallucinated."""
    incomplete_skill_content = """---
name: minimal-tool
description: "A minimal skill without explicit triggers or tool declarations."
---

# Minimal Tool

Just some generic text here.
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "minimal-tool"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(incomplete_skill_content, encoding="utf-8")

        record = SkillFactCompiler.compile_skill_file(skill_file)

        assert record is not None
        assert record.name == "minimal-tool"
        assert record.allowed_tools == []
        assert "allowed_tools" in record.unverified_fields
        assert "triggers" in record.unverified_fields
        # Must not hallucinate tools or triggers
        assert len(record.triggers) == 0


def test_code_fact_compiler_mcp_tools():
    """Test AST extraction of @mcp.tool decorated functions without runtime import."""
    sample_code = '''
"""Sample MCP module."""

@mcp.tool()
async def openviking_calculate(expression: str, precision: int = 4) -> float:
    """Evaluate a mathematical expression.
    
    Args:
        expression: The math formula to evaluate.
        precision: Decimal precision.
    """
    return 42.0

def internal_helper(x: int) -> int:
    return x * 2

@router.tool(name="openviking_lookup")
def lookup_key(key: str) -> str:
    """Lookup a key in the registry."""
    return "val"
'''
    tools = CodeFactCompiler.extract_mcp_tools_from_source(sample_code, source_file="sample_mcp.py")
    assert len(tools) == 2

    t1 = next(t for t in tools if t.name == "openviking_calculate")
    assert t1.is_async is True
    assert "expression: str" in t1.parameters_signature
    assert "precision: int = 4" in t1.parameters_signature
    assert t1.return_type == "float"
    assert "Evaluate a mathematical expression" in t1.docstring

    t2 = next(t for t in tools if t.name == "openviking_lookup")
    assert t2.is_async is False
    assert "key: str" in t2.parameters_signature


def test_code_fact_compiler_fastapi_routes():
    """Test AST extraction of FastAPI route decorators (@router.get, @router.post)."""
    sample_code = '''
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/catalog")

@router.get("/skills", summary="List compiled skills")
async def list_skills(limit: int = 50, offset: int = 0):
    return {"status": "ok"}

@router.post("/refresh")
def refresh_catalog():
    return {"status": "ok"}
'''
    routes = CodeFactCompiler.extract_routes_from_source(sample_code, source_file="routers/catalog.py")
    assert len(routes) == 2

    r_get = next(r for r in routes if r.method == "GET")
    assert r_get.path == "/skills"
    assert r_get.handler_name == "list_skills"
    assert r_get.is_async is True

    r_post = next(r for r in routes if r.method == "POST")
    assert r_post.path == "/refresh"
    assert r_post.handler_name == "refresh_catalog"
    assert r_post.is_async is False


def test_batch_compile_and_markdown_catalog():
    """Test batch compilation and standard Markdown catalog generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_root = Path(tmpdir) / "skills"
        skills_root.mkdir()

        s1 = skills_root / "skill-alpha"
        s1.mkdir()
        (s1 / "SKILL.md").write_text("""---
name: skill-alpha
description: "Alpha test skill"
allowed-tools: ["run_command"]
---
# Alpha
""", encoding="utf-8")

        compiler = SkillFactCompiler()
        records = compiler.compile_directory(skills_root)
        assert len(records) == 1
        assert records[0].name == "skill-alpha"

        markdown_catalog = compiler.generate_markdown_catalog(records)
        assert "# 🛠️ Agent Skills Fact Catalog" in markdown_catalog
        assert "skill-alpha" in markdown_catalog
        assert "run_command" in markdown_catalog


def test_code_catalog_http_api_endpoints():
    """Verify FastAPI endpoints for code and skill facts catalog via TestClient."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from openviking.server.routers.code_catalog import router as code_catalog_router

    app = FastAPI()
    app.include_router(code_catalog_router)
    client = TestClient(app)

    # 1. Test /api/v1/catalog/code
    code_resp = client.get("/api/v1/catalog/code")
    assert code_resp.status_code == 200
    code_data = code_resp.json()
    assert code_data["status"] == "ok"
    assert code_data["total_tools"] > 0
    assert code_data["total_routes"] > 0
    assert any("openviking" in t["name"] for t in code_data["tools"])

    # 2. Test /api/v1/catalog/summary
    sum_resp = client.get("/api/v1/catalog/summary")
    assert sum_resp.status_code == 200
    sum_data = sum_resp.json()
    assert sum_data["status"] == "ok"
    assert sum_data["summary"]["mcp_tools_detected"] > 0
    assert sum_data["summary"]["hallucination_rate"] == 0.0
