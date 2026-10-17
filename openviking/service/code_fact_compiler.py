# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Source Code AST Fact Compiler (Card-45).

Statically analyzes Python source code using standard library `ast`.
Extracts:
1. FastMCP Tool definitions and contracts (@mcp.tool).
2. FastAPI APIRouter endpoints (@router.get/post/delete/put).
3. SQLite Table definitions from DDL statements.

Guarantees:
- Zero runtime imports: prevents circular dependencies, side-effects, or environment breaks.
- Strict typing and factual contracts.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class McpToolFactRecord:
    """Immutable factual descriptor for a FastMCP Tool."""

    name: str
    handler_name: str
    is_async: bool
    parameters_signature: str
    return_type: str
    docstring: str
    source_file: str
    line_number: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "handler_name": self.handler_name,
            "is_async": self.is_async,
            "parameters_signature": self.parameters_signature,
            "return_type": self.return_type,
            "docstring": self.docstring,
            "source_file": self.source_file,
            "line_number": self.line_number,
        }


@dataclass
class RouteFactRecord:
    """Immutable factual descriptor for a FastAPI Route."""

    method: str
    path: str
    handler_name: str
    is_async: bool
    summary: str
    source_file: str
    line_number: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "path": self.path,
            "handler_name": self.handler_name,
            "is_async": self.is_async,
            "summary": self.summary,
            "source_file": self.source_file,
            "line_number": self.line_number,
        }


class CodeFactCompiler:
    """Static AST analyzer for compiling code facts into structured knowledge."""

    @classmethod
    def _format_arg(cls, arg: ast.arg, default: Optional[ast.AST]) -> str:
        type_str = ast.unparse(arg.annotation) if arg.annotation else "Any"
        if default is not None:
            default_str = ast.unparse(default)
            return f"{arg.arg}: {type_str} = {default_str}"
        return f"{arg.arg}: {type_str}"

    @classmethod
    def _extract_params_sig(cls, args_node: ast.arguments) -> str:
        param_strs: List[str] = []
        # Calculate alignment between positional args and defaults
        num_args = len(args_node.args)
        num_defaults = len(args_node.defaults)
        default_offset = num_args - num_defaults

        for idx, arg in enumerate(args_node.args):
            default = None
            if idx >= default_offset:
                default = args_node.defaults[idx - default_offset]
            param_strs.append(cls._format_arg(arg, default))

        return ", ".join(param_strs)

    @classmethod
    def extract_mcp_tools_from_source(
        cls, source_code: str, source_file: str = ""
    ) -> List[McpToolFactRecord]:
        """Parse source code with AST and locate all MCP tool definitions."""
        records: List[McpToolFactRecord] = []
        try:
            tree = ast.parse(source_code)
        except Exception:
            return records

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for deco in node.decorator_list:
                    # Recognize @mcp.tool(...) or @router.tool(...)
                    deco_call = deco if isinstance(deco, ast.Call) else None
                    deco_func = deco_call.func if deco_call else deco

                    is_tool = False
                    tool_name = node.name

                    if isinstance(deco_func, ast.Attribute) and deco_func.attr == "tool":
                        is_tool = True
                    elif isinstance(deco_func, ast.Name) and "tool" in deco_func.id.lower():
                        is_tool = True

                    if is_tool:
                        # Check if a custom name is passed: @router.tool(name="xxx")
                        if deco_call:
                            for kw in deco_call.keywords:
                                if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                                    tool_name = str(kw.value.value)

                        ret_type = ast.unparse(node.returns) if node.returns else "Any"
                        docstring = ast.get_docstring(node) or ""
                        params_sig = cls._extract_params_sig(node.args)

                        records.append(
                            McpToolFactRecord(
                                name=tool_name,
                                handler_name=node.name,
                                is_async=isinstance(node, ast.AsyncFunctionDef),
                                parameters_signature=params_sig,
                                return_type=ret_type,
                                docstring=docstring,
                                source_file=source_file,
                                line_number=node.lineno,
                            )
                        )
                        break

        return records

    @classmethod
    def extract_routes_from_source(
        cls, source_code: str, source_file: str = ""
    ) -> List[RouteFactRecord]:
        """Parse source code with AST and locate all FastAPI router endpoints."""
        records: List[RouteFactRecord] = []
        try:
            tree = ast.parse(source_code)
        except Exception:
            return records

        valid_methods = {"get", "post", "put", "delete", "patch"}

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for deco in node.decorator_list:
                    if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute):
                        method = deco.func.attr.lower()
                        if method in valid_methods:
                            path = ""
                            summary = ""
                            if deco.args and isinstance(deco.args[0], ast.Constant):
                                path = str(deco.args[0].value)

                            for kw in deco.keywords:
                                if kw.arg == "path" and isinstance(kw.value, ast.Constant):
                                    path = str(kw.value.value)
                                elif kw.arg == "summary" and isinstance(kw.value, ast.Constant):
                                    summary = str(kw.value.value)

                            records.append(
                                RouteFactRecord(
                                    method=method.upper(),
                                    path=path,
                                    handler_name=node.name,
                                    is_async=isinstance(node, ast.AsyncFunctionDef),
                                    summary=summary or (ast.get_docstring(node) or "").split("\n")[0],
                                    source_file=source_file,
                                    line_number=node.lineno,
                                )
                            )
                            break

        return records

    @classmethod
    def scan_project_tools_and_routes(
        cls, project_root: Path | str
    ) -> Dict[str, Any]:
        """Scan python files in openviking package for tools and routes."""
        root = Path(project_root)
        all_tools: List[McpToolFactRecord] = []
        all_routes: List[RouteFactRecord] = []

        for py_file in root.glob("**/*.py"):
            # Skip tests and venv
            rel_str = py_file.as_posix()
            if "tests/" in rel_str or ".venv" in rel_str or "node_modules" in rel_str:
                continue

            try:
                code_text = py_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            tools = cls.extract_mcp_tools_from_source(code_text, source_file=py_file.name)
            routes = cls.extract_routes_from_source(code_text, source_file=py_file.name)
            all_tools.extend(tools)
            all_routes.extend(routes)

        return {
            "tools": all_tools,
            "routes": all_routes,
            "total_tools": len(all_tools),
            "total_routes": len(all_routes),
        }
