# -*- coding: utf-8 -*-
"""TokenShift AST transformers and multi-language parsers.

Provides specialized AST-level compression transformers for Python and structural
scanning for TypeScript, JavaScript, JSON, SQL, and Shell.
"""

import ast
import json
import re
from typing import List, Optional, Tuple

from openviking.service.tokenshift_types import (
    SyntaxValidationResult,
    TokenShiftLanguage,
    TokenShiftMode,
)


def detect_language(code: str, hint: TokenShiftLanguage) -> TokenShiftLanguage:
    """Auto-detect language if not explicitly specified."""
    if hint != TokenShiftLanguage.AUTO:
        return hint
    stripped = code.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            json.loads(stripped)
            return TokenShiftLanguage.JSON
        except Exception:
            pass
    if re.search(r"\b(interface|type|const|export|import\s+type)\b", code):
        return TokenShiftLanguage.TYPESCRIPT
    if re.search(r"\b(def\s+\w+|class\s+\w+|import\s+\w+|from\s+\w+\s+import)\b", code):
        return TokenShiftLanguage.PYTHON
    if re.search(r"\b(SELECT\s+.*?\s+FROM|CREATE\s+TABLE|INSERT\s+INTO)\b", code, re.IGNORECASE):
        return TokenShiftLanguage.SQL
    if stripped.startswith("#!/") or re.search(r"\b(echo\s+|fi\b|done\b|export\s+\w+=)", code):
        return TokenShiftLanguage.SHELL
    return TokenShiftLanguage.PYTHON


class PythonOutlineTransformer(ast.NodeTransformer):
    """L0 Outline: Preserves signatures, type hints, docstrings, folds bodies to ..."""

    def __init__(self, preserve_docstrings: bool = True):
        self.preserve_docstrings = preserve_docstrings
        self.protected_count = 0

    def _make_folded_body(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> List[ast.stmt]:
        self.protected_count += 1
        new_body: List[ast.stmt] = []
        doc = ast.get_docstring(node) if self.preserve_docstrings else None
        if doc:
            new_body.append(ast.Expr(value=ast.Constant(value=doc)))
        new_body.append(ast.Expr(value=ast.Constant(value=Ellipsis)))
        return new_body

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.body = self._make_folded_body(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        node.body = self._make_folded_body(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        self.protected_count += 1
        doc = ast.get_docstring(node) if self.preserve_docstrings else None
        filtered_body: List[ast.stmt] = []
        if doc:
            filtered_body.append(ast.Expr(value=ast.Constant(value=doc)))
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.AnnAssign)):
                transformed = self.visit(stmt)
                if transformed:
                    filtered_body.append(transformed)
        node.body = filtered_body or [ast.Pass()]
        return node


class PythonSkeletonTransformer(ast.NodeTransformer):
    """L1 Skeleton: Preserves signatures, docstrings, and control-flow (if/try/for/return)."""

    def __init__(self, preserve_docstrings: bool = True):
        self.preserve_docstrings = preserve_docstrings
        self.protected_count = 0

    def _transform_block(self, stmts: List[ast.stmt], doc: Optional[str] = None) -> List[ast.stmt]:
        new_stmts: List[ast.stmt] = []
        if doc and self.preserve_docstrings:
            new_stmts.append(ast.Expr(value=ast.Constant(value=doc)))

        for s in stmts:
            if isinstance(s, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.Return, ast.Yield, ast.YieldFrom, ast.Raise)):
                self.protected_count += 1
                transformed = self.visit(s)
                if isinstance(transformed, list):
                    new_stmts.extend(transformed)
                elif transformed:
                    new_stmts.append(transformed)
            elif isinstance(s, ast.AnnAssign):
                self.protected_count += 1
                new_stmts.append(s)

        if not new_stmts or (len(new_stmts) == 1 and doc):
            new_stmts.append(ast.Expr(value=ast.Constant(value=Ellipsis)))
        return new_stmts

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        doc = ast.get_docstring(node)
        node.body = self._transform_block(node.body, doc)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        doc = ast.get_docstring(node)
        node.body = self._transform_block(node.body, doc)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        self.protected_count += 1
        node.body = [self.visit(s) for s in node.body]
        return node

    def visit_If(self, node: ast.If) -> ast.AST:
        node.body = self._transform_block(node.body)
        if node.orelse:
            node.orelse = self._transform_block(node.orelse)
        return node

    def visit_For(self, node: ast.For) -> ast.AST:
        node.body = self._transform_block(node.body)
        if node.orelse:
            node.orelse = self._transform_block(node.orelse)
        return node

    def visit_AsyncFor(self, node: ast.AsyncFor) -> ast.AST:
        node.body = self._transform_block(node.body)
        if node.orelse:
            node.orelse = self._transform_block(node.orelse)
        return node

    def visit_While(self, node: ast.While) -> ast.AST:
        node.body = self._transform_block(node.body)
        if node.orelse:
            node.orelse = self._transform_block(node.orelse)
        return node

    def visit_Try(self, node: ast.Try) -> ast.AST:
        node.body = self._transform_block(node.body)
        for h in node.handlers:
            h.body = self._transform_block(h.body)
        if node.orelse:
            node.orelse = self._transform_block(node.orelse)
        if node.finalbody:
            node.finalbody = self._transform_block(node.finalbody)
        return node


def compress_python(code: str, mode: TokenShiftMode, preserve_docstrings: bool) -> Tuple[str, int, SyntaxValidationResult]:
    """Compress Python code with guaranteed AST syntax validity."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return code, 0, SyntaxValidationResult(valid=False, parser="python_ast", error=str(e))

    protected_count = 0
    if mode == TokenShiftMode.OUTLINE:
        transformer = PythonOutlineTransformer(preserve_docstrings)
        tree = transformer.visit(tree)
        ast.fix_missing_locations(tree)
        compressed = ast.unparse(tree)
        protected_count = transformer.protected_count
    elif mode == TokenShiftMode.SKELETON:
        transformer = PythonSkeletonTransformer(preserve_docstrings)
        tree = transformer.visit(tree)
        ast.fix_missing_locations(tree)
        compressed = ast.unparse(tree)
        protected_count = transformer.protected_count
    else:  # COMPACT
        compressed = ast.unparse(tree)
        protected_count = sum(1 for _ in ast.walk(tree) if isinstance(_, (ast.FunctionDef, ast.ClassDef)))

    # Gate: Validate produced code with ast.parse
    try:
        ast.parse(compressed)
        val = SyntaxValidationResult(valid=True, parser="python_ast")
    except SyntaxError as e:
        val = SyntaxValidationResult(valid=False, parser="python_ast", error=f"Regenerated AST failed validation: {e}")
        compressed = code  # Safe fallback

    return compressed, protected_count, val


def compress_typescript(code: str, mode: TokenShiftMode) -> Tuple[str, int, SyntaxValidationResult]:
    """Compress TypeScript/JavaScript preserving interfaces and function signatures."""
    lines = code.splitlines()
    compressed_lines: List[str] = []
    protected_count = 0
    in_interface_or_type = False
    in_function_skip = False
    func_brace_depth = 0

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue

        # If skipping a folded function body in OUTLINE mode
        if in_function_skip:
            func_brace_depth += trimmed.count("{") - trimmed.count("}")
            if func_brace_depth <= 0:
                in_function_skip = False
            continue

        # Check start of interface or type alias
        if re.match(r"^(export\s+)?(interface|type)\b", trimmed):
            compressed_lines.append(line)
            protected_count += 1
            if "{" in trimmed and "}" not in trimmed:
                in_interface_or_type = True
            continue

        # If inside interface or type block, preserve property declarations and closing brace
        if in_interface_or_type:
            compressed_lines.append(line)
            if "}" in trimmed:
                in_interface_or_type = False
            continue

        # Imports
        if re.match(r"^(export\s+)?import\b", trimmed):
            compressed_lines.append(line)
            protected_count += 1
            continue

        # Top-level Functions / classes / exported arrows
        if re.match(r"^(export\s+)?(class|function|async\s+function)\b", trimmed) or \
           re.match(r"^export\s+const\s+\w+\s*=\s*(async\s*)?\(", trimmed):
            protected_count += 1
            if mode == TokenShiftMode.OUTLINE:
                if "{" in line:
                    compressed_lines.append(re.sub(r"\{.*$", "{ /* ... */ }", line))
                    open_cnt = line.count("{") - line.count("}")
                    if open_cnt > 0:
                        in_function_skip = True
                        func_brace_depth = open_cnt
                else:
                    compressed_lines.append(line + " { /* ... */ }")
            else:
                compressed_lines.append(line)
            continue

        if mode == TokenShiftMode.OUTLINE:
            continue
        elif mode == TokenShiftMode.SKELETON:
            if re.match(r"^\s*(if|else|for|while|try|catch|finally|return|throw|switch|case)\b", trimmed):
                compressed_lines.append(line)
                protected_count += 1
        else:  # COMPACT
            if trimmed.startswith("//") and not any(k in trimmed for k in ("TODO", "FIXME", "NOTE")):
                continue
            compressed_lines.append(line)

    res = "\n".join(compressed_lines)
    # Check brace/bracket balance
    valid = res.count("{") == res.count("}") and res.count("(") == res.count(")")
    val = SyntaxValidationResult(valid=valid, parser="ts_balance_gate", error=None if valid else "Brace count mismatch")
    return res, protected_count, val


def compress_json(code: str, mode: TokenShiftMode) -> Tuple[str, int, SyntaxValidationResult]:
    """Compress JSON data safely."""
    try:
        data = json.loads(code)
    except Exception as e:
        return code, 0, SyntaxValidationResult(valid=False, parser="json", error=str(e))

    if mode == TokenShiftMode.OUTLINE:
        if isinstance(data, dict):
            compact_dict = {k: f"<{type(v).__name__}>" for k, v in list(data.items())[:15]}
            res = json.dumps(compact_dict, indent=2)
        elif isinstance(data, list):
            res = json.dumps([f"<Array of {len(data)} items>"], indent=2)
        else:
            res = json.dumps(data)
    else:
        res = json.dumps(data, separators=(",", ":"))
    return res, 1, SyntaxValidationResult(valid=True, parser="json")
