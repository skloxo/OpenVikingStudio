# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
AST-Aware Code Symbol Chunker.
Parses Python source code into callable units (functions, classes, methods) with line spans.
(Card-Retrieval-LocalFirst-zgSemanticSearch / v1.5.17)
"""

import ast
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CodeSymbolChunk(BaseModel):
    """Discrete callable code unit extracted via AST."""
    uri: str
    file_path: str
    symbol_name: str
    symbol_type: str  # "function" | "async_function" | "class" | "method"
    parent_class: Optional[str] = None
    start_line: int
    end_line: int
    signature: str
    docstring: str = ""
    fingerprint: str
    line_count: int = 0
    lines: List[str] = Field(default_factory=list)

    def to_index_dict(self) -> Dict[str, Any]:
        """Convert chunk to a searchable representation for BM25/FTS5."""
        display_name = f"{self.parent_class}.{self.symbol_name}" if self.parent_class else self.symbol_name
        search_text = f"{display_name}\n{self.signature}\n{self.docstring}\n" + "\n".join(self.lines[:10])
        return {
            "uri": self.uri,
            "title": f"{self.symbol_type} {display_name}",
            "content": search_text,
            "level": 2,
            "context_type": "code_symbol",
            "file_path": self.file_path,
            "symbol_name": self.symbol_name,
            "symbol_type": self.symbol_type,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "fingerprint": self.fingerprint,
        }


class ASTChunker:
    """Extracts discrete functions, classes, and methods from codebases."""

    @staticmethod
    def _compute_fingerprint(signature: str, docstring: str) -> str:
        """Compute 8-character deterministic anchor hash."""
        raw = f"{signature.strip()}:{docstring.strip()}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:8]

    @classmethod
    def parse_python(cls, code: str, file_path: str = "") -> List[CodeSymbolChunk]:
        """
        Parse Python source code into structured CodeSymbolChunks using native ast.
        """
        if not code.strip():
            return []

        try:
            tree = ast.parse(code, filename=file_path or "<string>")
        except SyntaxError:
            # Skip invalid syntax without breaking search pipeline
            return []

        source_lines = code.splitlines()
        chunks: List[CodeSymbolChunk] = []

        def get_lines_slice(start: int, end: int) -> List[str]:
            s_idx = max(0, start - 1)
            e_idx = min(len(source_lines), end)
            return source_lines[s_idx:e_idx]

        def extract_signature(node: ast.AST, start: int) -> str:
            # Header line of the def or class
            idx = max(0, start - 1)
            if idx < len(source_lines):
                sig_line = source_lines[idx].strip()
                # Multi-line signature support: read until ':'
                curr_idx = idx
                accum = []
                while curr_idx < len(source_lines) and curr_idx < idx + 5:
                    line = source_lines[curr_idx].strip()
                    accum.append(line)
                    if line.endswith(":"):
                        break
                    curr_idx += 1
                return " ".join(accum)
            return getattr(node, "name", "")

        for node in tree.body:
            # Top-level functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_type = "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
                start = node.lineno
                end = getattr(node, "end_lineno", node.lineno)
                doc = ast.get_docstring(node) or ""
                sig = extract_signature(node, start)
                fp = cls._compute_fingerprint(sig, doc)
                chunks.append(
                    CodeSymbolChunk(
                        uri=f"code://{file_path}#{node.name}:{start}",
                        file_path=file_path,
                        symbol_name=node.name,
                        symbol_type=fn_type,
                        parent_class=None,
                        start_line=start,
                        end_line=end,
                        signature=sig,
                        docstring=doc,
                        fingerprint=fp,
                        line_count=max(1, end - start + 1),
                        lines=get_lines_slice(start, end),
                    )
                )

            # Classes and nested methods
            elif isinstance(node, ast.ClassDef):
                c_start = node.lineno
                c_end = getattr(node, "end_lineno", node.lineno)
                c_doc = ast.get_docstring(node) or ""
                c_sig = extract_signature(node, c_start)
                c_fp = cls._compute_fingerprint(c_sig, c_doc)

                # Record Class definition itself
                chunks.append(
                    CodeSymbolChunk(
                        uri=f"code://{file_path}#{node.name}:{c_start}",
                        file_path=file_path,
                        symbol_name=node.name,
                        symbol_type="class",
                        parent_class=None,
                        start_line=c_start,
                        end_line=c_end,
                        signature=c_sig,
                        docstring=c_doc,
                        fingerprint=c_fp,
                        line_count=max(1, c_end - c_start + 1),
                        lines=get_lines_slice(c_start, c_end),
                    )
                )

                # Methods inside class
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        m_type = "async_method" if isinstance(sub, ast.AsyncFunctionDef) else "method"
                        m_start = sub.lineno
                        m_end = getattr(sub, "end_lineno", sub.lineno)
                        m_doc = ast.get_docstring(sub) or ""
                        m_sig = extract_signature(sub, m_start)
                        m_fp = cls._compute_fingerprint(m_sig, m_doc)
                        chunks.append(
                            CodeSymbolChunk(
                                uri=f"code://{file_path}#{node.name}.{sub.name}:{m_start}",
                                file_path=file_path,
                                symbol_name=sub.name,
                                symbol_type=m_type,
                                parent_class=node.name,
                                start_line=m_start,
                                end_line=m_end,
                                signature=m_sig,
                                docstring=m_doc,
                                fingerprint=m_fp,
                                line_count=max(1, m_end - m_start + 1),
                                lines=get_lines_slice(m_start, m_end),
                            )
                        )

        return chunks

    @classmethod
    def parse_file(cls, file_path: Path, base_dir: Optional[Path] = None) -> List[CodeSymbolChunk]:
        """Parse a single file on disk."""
        if not file_path.is_file() or file_path.suffix != ".py":
            return []
        try:
            code = file_path.read_text(encoding="utf-8", errors="ignore")
            rel_path = str(file_path.relative_to(base_dir)) if base_dir else str(file_path)
            return cls.parse_python(code, file_path=rel_path)
        except Exception:
            return []

    @classmethod
    def parse_directory(
        cls,
        dir_path: Path,
        max_files: int = 500,
        exclude_patterns: Optional[List[str]] = None,
    ) -> List[CodeSymbolChunk]:
        """Walk a directory and extract all symbol chunks."""
        excludes = exclude_patterns or [".git", "node_modules", ".venv", "__pycache__", "dist", "build"]
        all_chunks: List[CodeSymbolChunk] = []
        files_scanned = 0

        for py_path in sorted(dir_path.rglob("*.py")):
            if any(exc in py_path.parts for exc in excludes):
                continue
            chunks = cls.parse_file(py_path, base_dir=dir_path)
            all_chunks.extend(chunks)
            files_scanned += 1
            if files_scanned >= max_files:
                break

        return all_chunks
