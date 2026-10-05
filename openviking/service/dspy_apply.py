# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""DSPy MIPO Prompt Template Scanner & Compilation Persistence Service.

Provides real prompt template catalog discovery, quarantine snapshotting,
and dual persistence modes (compiled template file vs in-place update) for DSPy (Card-102 / v1.7.56).
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field

from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)


class PromptTemplateItem(BaseModel):
    """Catalog item for real system prompt template picker."""
    id: str
    rel_path: str
    name: str
    category: str
    description: str
    version: str
    variables_count: int
    template_chars: int
    preview: str


class ApplyDSPyRequest(BaseModel):
    """Request payload for applying compiled prompt."""
    rel_path: str = Field(..., description="Relative path of prompt template under prompts/templates/")
    compiled_prompt: str = Field(..., description="Compiled prompt text with strict schema")
    signature_name: Optional[str] = Field(default=None, description="Extracted signature name")
    task_objective: Optional[str] = Field(default=None, description="Task objective statement")
    mode: str = Field(default="compiled_file", description="'compiled_file' (.compiled.yaml) or 'in_place' (overwrite)")
    operator: str = Field(default="dspy_compiler", description="Operator identity for audit trail")


class ApplyDSPyResult(BaseModel):
    """Result payload after physical persistence and snapshotting."""
    success: bool
    mode: str
    target_path: str
    snapshot_path: str
    original_chars: int
    compiled_chars: int
    message: str


class DSPyApplyService:
    """Orchestrates system prompt template discovery, quarantine snapshots, and compilation writes."""

    def __init__(
        self,
        templates_dir: Optional[Path] = None,
        compiled_dir: Optional[Path] = None,
        backup_root: Optional[Path] = None,
    ) -> None:
        base_prompts = Path(__file__).resolve().parent.parent / "prompts"
        self.templates_dir = templates_dir.resolve() if templates_dir else (base_prompts / "templates")
        self.compiled_dir = compiled_dir.resolve() if compiled_dir else (base_prompts / "compiled")
        self.backup_root = backup_root or (
            Path.home() / ".openviking" / "data" / "quarantine" / "dspy_pre_apply"
        )
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.compiled_dir.mkdir(parents=True, exist_ok=True)
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def _resolve_template_path(self, rel_path: str) -> Path:
        """Resolve template relative path and verify safety."""
        clean = rel_path.lstrip("/\\")
        candidate = (self.templates_dir / clean).resolve()
        if not str(candidate).startswith(str(self.templates_dir)):
            raise ValueError(f"Path traversal detected: {rel_path} escapes templates directory")
        return candidate

    def list_prompt_templates(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[PromptTemplateItem]:
        """Scan openviking/prompts/templates for real YAML prompt templates."""
        results: List[PromptTemplateItem] = []
        limit = max(1, min(limit, 200))
        search_lower = search.lower().strip() if search else ""
        target_cat = category.lower().strip() if category else ""

        for file_path in sorted(self.templates_dir.rglob("*.yaml")):
            if not file_path.is_file():
                continue

            rel_str = str(file_path.relative_to(self.templates_dir))
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    continue

                metadata = data.get("metadata", {})
                template_str = str(data.get("template", ""))
                variables = data.get("variables", [])

                item_id = str(metadata.get("id", rel_str))
                item_name = str(metadata.get("name", file_path.stem))
                item_cat = str(metadata.get("category", file_path.parent.name))
                item_desc = str(metadata.get("description", ""))
                item_ver = str(metadata.get("version", "1.0.0"))

                if target_cat and target_cat != "all" and item_cat.lower() != target_cat:
                    continue

                combined_search_text = f"{item_id} {item_name} {item_cat} {item_desc} {rel_str}".lower()
                if search_lower and search_lower not in combined_search_text:
                    continue

                preview = template_str.strip()[:200]
                results.append(
                    PromptTemplateItem(
                        id=item_id,
                        rel_path=rel_str,
                        name=item_name,
                        category=item_cat,
                        description=item_desc,
                        version=item_ver,
                        variables_count=len(variables) if isinstance(variables, list) else 0,
                        template_chars=len(template_str),
                        preview=preview,
                    )
                )
                if len(results) >= limit:
                    break
            except Exception as exc:
                logger.debug(f"Failed to parse prompt template {file_path}: {exc}")

        return results

    def read_prompt_template(self, rel_path: str) -> Dict[str, Any]:
        """Read prompt template YAML and return parsed metadata and template content."""
        abs_path = self._resolve_template_path(rel_path)
        if not abs_path.is_file():
            raise FileNotFoundError(f"Prompt template file not found: {rel_path}")

        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            raw_yaml = f.read()

        data = yaml.safe_load(raw_yaml) or {}
        metadata = data.get("metadata", {})
        template_str = str(data.get("template", ""))
        variables = data.get("variables", [])

        return {
            "rel_path": rel_path,
            "filename": abs_path.name,
            "id": metadata.get("id", rel_path),
            "name": metadata.get("name", abs_path.stem),
            "category": metadata.get("category", abs_path.parent.name),
            "description": metadata.get("description", ""),
            "version": metadata.get("version", "1.0.0"),
            "variables": variables,
            "template": template_str,
            "raw_yaml": raw_yaml,
        }

    def apply_compiled_prompt(self, req: ApplyDSPyRequest) -> ApplyDSPyResult:
        """Persist compiled prompt to disk with quarantine snapshotting."""
        orig_file = self._resolve_template_path(req.rel_path)
        if not orig_file.is_file():
            raise FileNotFoundError(f"Original template file not found: {req.rel_path}")

        with open(orig_file, "r", encoding="utf-8", errors="replace") as f:
            original_content = f.read()

        # Lossless Quarantine Snapshot
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_name = orig_file.name.replace(".", "_")
        snapshot_file = self.backup_root / f"{now_str}_{safe_name}.bak"
        with open(snapshot_file, "w", encoding="utf-8") as f:
            f.write(original_content)

        # Parse original data to merge or rewrite
        try:
            data = yaml.safe_load(original_content) or {}
        except Exception:
            data = {}

        if req.mode == "in_place":
            # In-place update of template string while preserving metadata
            data["template"] = req.compiled_prompt
            if "metadata" in data and isinstance(data["metadata"], dict):
                data["metadata"]["dspy_compiled_at"] = datetime.datetime.now().isoformat()
            target_file = orig_file
            content_to_write = yaml.dump(data, allow_unicode=True, sort_keys=False)
        else:
            # Save into compiled templates directory: compiled/{category}/{stem}.compiled.yaml
            category = data.get("metadata", {}).get("category", orig_file.parent.name)
            target_dir = self.compiled_dir / category
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / f"{orig_file.stem}.compiled.yaml"

            compiled_doc = {
                "metadata": {
                    "source_template_id": data.get("metadata", {}).get("id", req.rel_path),
                    "signature_name": req.signature_name or "DSPyCompiledSignature",
                    "task_objective": req.task_objective or "",
                    "compiled_at": datetime.datetime.now().isoformat(),
                    "compiler": "DSPy-MIPO",
                },
                "variables": data.get("variables", []),
                "compiled_template": req.compiled_prompt,
            }
            content_to_write = yaml.dump(compiled_doc, allow_unicode=True, sort_keys=False)

        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content_to_write)

        return ApplyDSPyResult(
            success=True,
            mode=req.mode,
            target_path=str(target_file),
            snapshot_path=str(snapshot_file),
            original_chars=len(original_content),
            compiled_chars=len(content_to_write),
            message=(
                f"Successfully saved compiled prompt ({req.mode}) to "
                f"{target_file.name} with backup snapshot"
            ),
        )
