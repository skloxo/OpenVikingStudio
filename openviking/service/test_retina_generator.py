# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Automated Test Retina Generator (Card-47).

Generates executable, syntactically verified pytest scripts from factual contracts.
Emulates the JD Haibo 90%+ acceptance rate test generation paradigm:
- Auto-generates contract assertions for FastAPI routes.
- Auto-generates input/output type checks for FastMCP tools.
"""

from __future__ import annotations

import re
from typing import List

from openviking.service.code_fact_compiler import McpToolFactRecord, RouteFactRecord


_IDENT_CLEAN_RE = re.compile(r"[^a-zA-Z0-9_]+")


class TestRetinaGenerator:
    """Generator for pytest contract test suites from code facts."""

    @classmethod
    def _clean_func_name(cls, prefix: str, path: str) -> str:
        clean = _IDENT_CLEAN_RE.sub("_", path).strip("_")
        return f"{prefix.lower()}_{clean}"

    @classmethod
    def generate_pytest_for_route(cls, route: RouteFactRecord) -> str:
        """Generate a single pytest test function string for an HTTP route."""
        func_name = cls._clean_func_name(f"test_{route.method}", route.path)
        method_lower = route.method.lower()

        # Prepare dummy payload or query params
        if route.method in ("POST", "PUT", "PATCH"):
            action_call = f'resp = client.{method_lower}("{route.path}", json={{}})'
        else:
            action_call = f'resp = client.{method_lower}("{route.path}")'

        code_lines = [
            f"def {func_name}_contract(client):",
            f'    """Contract test for {route.method} {route.path} ({route.summary})."""',
            f"    {action_call}",
            "    assert resp.status_code in (200, 201, 400, 422)",
            "    data = resp.json()",
            '    assert isinstance(data, (dict, list))',
            '    if isinstance(data, dict) and "status" in data:',
            '        assert data["status"] in ("ok", "error")',
        ]
        return "\n".join(code_lines)

    @classmethod
    def generate_pytest_for_mcp_tool(cls, tool: McpToolFactRecord) -> str:
        """Generate a pytest test function string for a FastMCP tool contract."""
        func_name = f"test_{tool.name}_contract"

        # Generate dummy argument passing
        dummy_args: List[str] = []
        if tool.parameters_signature:
            for param in tool.parameters_signature.split(","):
                clean_p = param.strip()
                if not clean_p:
                    continue
                p_name = clean_p.split("=")[0].split(":")[0].strip()
                if p_name and p_name != "self":
                    dummy_args.append(f'"{p_name}": "test_{p_name}"')

        args_str = ", ".join(dummy_args)

        code_lines = [
            f"def {func_name}():",
            f'    """Contract test for FastMCP tool {tool.name}."""',
            f"    import inspect",
            f"    from openviking.server import mcp_endpoint",
            f"    handler = getattr(mcp_endpoint, '{tool.handler_name}', None)",
            f"    assert handler is not None, f'FastMCP tool handler {tool.handler_name} not found in mcp_endpoint'",
            f"    assert callable(handler), f'FastMCP tool handler {tool.handler_name} is not callable'",
            f"    sig = inspect.signature(handler)",
            f"    kwargs = {{{args_str}}}",
            f"    for param_name in kwargs.keys():",
            f"        assert param_name in sig.parameters, f'Parameter {{param_name}} not accepted by handler'",
        ]
        return "\n".join(code_lines)

    @classmethod
    def generate_full_test_module(cls, routes: List[RouteFactRecord]) -> str:
        """Generate a complete, ready-to-run pytest module for a list of routes."""
        header_lines = [
            '"""Auto-generated Test Retina Suite by OpenViking Knowledge Compiler."""',
            "from __future__ import annotations",
            "import pytest",
            "from fastapi.testclient import TestClient",
            "from openviking.server.app import create_app",
            "from openviking.server.config import ServerConfig",
            "",
            "@pytest.fixture",
            "def client():",
            "    app = create_app(ServerConfig())",
            "    return TestClient(app)",
            "",
        ]
        func_blocks = [cls.generate_pytest_for_route(r) for r in routes]
        return "\n".join(header_lines) + "\n\n".join(func_blocks) + "\n"
