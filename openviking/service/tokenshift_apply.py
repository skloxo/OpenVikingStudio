# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""TokenShift AST-Aware Code File Scanner & Physical Persistence Service.

Provides project code file discovery, syntax validation gate, quarantine snapshotting,
and dual persistence modes (skeleton mirror file vs in-place overwrite) for TokenShift (Card-102 / v1.7.56).
"""

from __future__ import annotations

import ast
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

CODE_EXTENSIONS = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".json": "json",
}

IGNORED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    ".agents",
    "quarantine",
    ".next",
}


class CodeFileItem(BaseModel):
    """Catalog item for real project code file picker."""
    rel_path: str
    filename: str
    language: str
    size_bytes: int
    line_count: int
    preview: str


class ApplyTokenShiftRequest(BaseModel):
    """Request payload for applying compressed code."""
    rel_path: str = Field(..., description="Project-relative path of the code file")
    compressed_code: str = Field(..., description="AST compressed source code")
    mode: str = Field(default="skeleton_file", description="'skeleton_file' (.skeleton.<ext>) or 'in_place' (overwrite)")
    operator: str = Field(default="tokenshift", description="Operator identity for audit trail")


class ApplyTokenShiftResult(BaseModel):
    """Result payload after physical persistence and snapshotting."""
    success: bool
    mode: str
    target_path: str
    snapshot_path: str
    original_chars: int
    compressed_chars: int
    saved_chars: int
    syntax_valid: bool
    message: str


class TokenShiftApplyService:
    """Orchestrates codebase source file discovery, AST validation, quarantine snapshots, and writes."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        backup_root: Optional[Path] = None,
    ) -> None:
        self.project_root = (
            project_root.resolve()
            if project_root
            else Path(__file__).resolve().parents[2]
        )
        self.backup_root = backup_root or (
            Path.home() / ".openviking" / "data" / "quarantine" / "tokenshift_pre_apply"
        )
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, rel_path: str) -> Path:
        """Resolve project-relative path and verify it stays inside project root."""
        clean = rel_path.lstrip("/\\")
        candidate = (self.project_root / clean).resolve()
        if not str(candidate).startswith(str(self.project_root)):
            raise ValueError(f"Path traversal detected: {rel_path} escapes project root")
        return candidate

    def list_code_files(
        self,
        search: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 50,
    ) -> List[CodeFileItem]:
        """Scan project repository for real source code files."""
        results: List[CodeFileItem] = []
        limit = max(1, min(limit, 200))
        search_lower = search.lower().strip() if search else ""
        target_lang = language.lower().strip() if language else ""

        # Scan primary code directories
        scan_dirs = ["openviking", "src", "tests", "scripts"]
        for dir_name in scan_dirs:
            base_dir = self.project_root / dir_name
            if not base_dir.exists():
                continue

            for file_path in base_dir.rglob("*"):
                if not file_path.is_file():
                    continue

                # Skip ignored directory parts
                parts = file_path.relative_to(self.project_root).parts
                if any(ignored in parts for ignored in IGNORED_DIRS):
                    continue

                ext = file_path.suffix.lower()
                detected_lang = CODE_EXTENSIONS.get(ext)
                if not detected_lang:
                    continue

                if target_lang and target_lang != "auto" and detected_lang != target_lang:
                    continue

                rel_str = str(file_path.relative_to(self.project_root))
                if search_lower and search_lower not in rel_str.lower():
                    continue

                try:
                    stat = file_path.stat()
                    # Skip huge binary or generated files (> 500 KB)
                    if stat.st_size > 512 * 1024:
                        continue

                    # Read preview
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = [f.readline() for _ in range(6)]
                    preview = "".join(lines).strip()
                    line_count = sum(1 for _ in open(file_path, "r", encoding="utf-8", errors="replace"))

                    results.append(
                        CodeFileItem(
                            rel_path=rel_str,
                            filename=file_path.name,
                            language=detected_lang,
                            size_bytes=stat.st_size,
                            line_count=line_count,
                            preview=preview[:300],
                        )
                    )
                    if len(results) >= limit:
                        break
                except Exception as exc:
                    logger.debug(f"Failed to index code file {file_path}: {exc}")

            if len(results) >= limit:
                break

        results.sort(key=lambda x: x.rel_path)
        return results

    def read_code_file(self, rel_path: str) -> Dict[str, Any]:
        """Read source code file and return content and metadata."""
        abs_path = self._resolve_safe_path(rel_path)
        if not abs_path.is_file():
            raise FileNotFoundError(f"Source file not found: {rel_path}")

        ext = abs_path.suffix.lower()
        detected_lang = CODE_EXTENSIONS.get(ext, "text")

        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        line_count = len(content.splitlines())
        return {
            "rel_path": rel_path,
            "filename": abs_path.name,
            "language": detected_lang,
            "line_count": line_count,
            "size_bytes": len(content.encode("utf-8")),
            "content": content,
        }

    def apply_compression(self, req: ApplyTokenShiftRequest) -> ApplyTokenShiftResult:
        """Apply compressed code to disk with AST syntax validation and quarantine snapshotting."""
        orig_file = self._resolve_safe_path(req.rel_path)
        if not orig_file.is_file():
            raise FileNotFoundError(f"Original source file not found: {req.rel_path}")

        with open(orig_file, "r", encoding="utf-8", errors="replace") as f:
            original_content = f.read()

        # AST Syntax gate for Python
        ext = orig_file.suffix.lower()
        syntax_valid = True
        if ext == ".py":
            try:
                ast.parse(req.compressed_code)
            except SyntaxError as e:
                syntax_valid = False
                raise ValueError(f"AST Syntax Gate Rejected: Compressed Python code has syntax error: {e}")

        # Quarantine Snapshot (Lossless backup)
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_name = orig_file.name.replace(".", "_")
        snapshot_file = self.backup_root / f"{now_str}_{safe_name}.bak"
        with open(snapshot_file, "w", encoding="utf-8") as f:
            f.write(original_content)

        # Write Target
        if req.mode == "in_place":
            target_file = orig_file
        else:
            # Skeleton mirror file: e.g. script.py -> script.skeleton.py
            stem = orig_file.stem
            target_name = f"{stem}.skeleton{ext}"
            target_file = orig_file.parent / target_name

        with open(target_file, "w", encoding="utf-8") as f:
            f.write(req.compressed_code)

        orig_len = len(original_content)
        comp_len = len(req.compressed_code)
        saved = max(0, orig_len - comp_len)

        return ApplyTokenShiftResult(
            success=True,
            mode=req.mode,
            target_path=str(target_file.relative_to(self.project_root)),
            snapshot_path=str(snapshot_file),
            original_chars=orig_len,
            compressed_chars=comp_len,
            saved_chars=saved,
            syntax_valid=syntax_valid,
            message=(
                f"Successfully persisted compressed code ({req.mode}) to "
                f"{target_file.relative_to(self.project_root)} with backup snapshot"
            ),
        )
