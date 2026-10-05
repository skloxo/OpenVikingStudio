# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Wiki Dehydration Apply & Mirror Persistence Service.

Provides physical persistence, structural gate validation, and quarantine snapshotting
for LLMLingua-2 dehydrated Wiki/Markdown documents (Card-101 / v1.7.55).
"""

from __future__ import annotations

import datetime
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from openviking.service.skill_provenance_tracker import (
    ProvenanceAction,
    SkillProvenanceTracker,
)
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

RE_YAML_HEADER = re.compile(r"^---\s*\n[\s\S]*?\n---\s*\n?", re.MULTILINE)
RE_FENCED_CODE = re.compile(r"(```[\s\S]*?```|~~~[\s\S]*?~~~)", re.MULTILINE)


class WikiDocumentItem(BaseModel):
    """Catalog item for real Wiki document picker."""
    uri: str
    name: str
    category: str
    size_bytes: int
    mod_time: str
    preview: str


class ApplyDehydrationRequest(BaseModel):
    """Request payload for applying dehydrated wiki document."""
    uri: str = Field(..., description="Viking URI or document relative path")
    dehydrated_content: str = Field(..., description="Dehydrated text content")
    mode: str = Field(default="mirror", description="'mirror' (.dehydrated.md) or 'in_place' (overwrite)")
    operator: str = Field(default="wiki_dehydrate", description="Operator identity for audit trail")


class ApplyDehydrationResult(BaseModel):
    """Result payload after physical persistence and snapshotting."""
    success: bool
    mode: str
    target_uri: str
    target_path: str
    snapshot_path: str
    original_chars: int
    dehydrated_chars: int
    saved_chars: int
    provenance_event_id: str


class WikiDehydrateApplyService:
    """Orchestrates real Wiki document discovery, quarantine snapshotting, and atomic write-back."""

    def __init__(
        self,
        backup_root: Optional[Path] = None,
        candidate_dirs: Optional[List[Path]] = None,
    ) -> None:
        self.backup_root = backup_root or (
            Path.home() / ".openviking" / "data" / "quarantine" / "wiki_dehydration_pre_apply"
        )
        self.backup_root.mkdir(parents=True, exist_ok=True)

        if candidate_dirs:
            self.candidate_dirs = [d for d in candidate_dirs if d.exists()]
        else:
            base_home = Path.home() / ".openviking" / "data"
            self.candidate_dirs = [
                d for d in [
                    base_home / "viking" / "default" / "resources" / "master_memory",
                    base_home / "resources" / "master_memory",
                    base_home / "viking" / "default" / "resources",
                    base_home / "resources",
                ] if d.exists()
            ]

    def list_documents(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 150,
    ) -> List[WikiDocumentItem]:
        """List real Wiki documents from the knowledge base."""
        items: List[WikiDocumentItem] = []
        seen_uris = set()
        search_lower = search.strip().lower() if search else None

        for root in self.candidate_dirs:
            if not root.exists():
                continue
            for fpath in root.rglob("*.md"):
                if not fpath.is_file() or fpath.name.startswith("."):
                    continue
                # Skip quarantine or compact/dehydrated mirror files when listing source catalog
                if ".dehydrated." in fpath.name or "quarantine" in str(fpath):
                    continue

                rel = fpath.relative_to(root)
                cat = rel.parts[0] if len(rel.parts) > 1 else "root"
                uri = f"viking://resources/master_memory/{rel.as_posix()}"

                if uri in seen_uris:
                    continue
                seen_uris.add(uri)

                if category and category != "all" and cat != category:
                    continue

                if search_lower and (search_lower not in fpath.name.lower() and search_lower not in str(rel).lower()):
                    continue

                try:
                    stat = fpath.stat()
                    # Read preview
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        preview = f.read(180).strip().replace("\n", " ")
                    items.append(
                        WikiDocumentItem(
                            uri=uri,
                            name=fpath.name,
                            category=cat,
                            size_bytes=stat.st_size,
                            mod_time=datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            preview=preview,
                        )
                    )
                except Exception as err:
                    logger.debug("Failed to stat wiki doc %s: %s", fpath, err)

                if len(items) >= limit:
                    break
            if len(items) >= limit:
                break

        return sorted(items, key=lambda x: x.name)

    def find_file_by_uri(self, uri: str) -> Optional[Path]:
        """Resolve a Viking URI or relative path to a local physical file."""
        clean_rel = uri.replace("viking://resources/master_memory/", "").replace("viking://resources/", "")
        clean_rel = clean_rel.lstrip("/")

        # Check direct path if absolute
        p = Path(uri)
        if p.is_file():
            return p

        for root in self.candidate_dirs:
            candidate = root / clean_rel
            if candidate.is_file():
                return candidate
            # Try searching by basename if nested structure differs
            for match in root.rglob(Path(clean_rel).name):
                if match.is_file():
                    return match
        return None

    def read_document(self, uri: str) -> str:
        """Read content of a Wiki document by URI."""
        fpath = self.find_file_by_uri(uri)
        if not fpath:
            raise FileNotFoundError(f"Wiki document not found for URI: {uri}")
        return fpath.read_text(encoding="utf-8", errors="replace")

    def apply_dehydration(self, req: ApplyDehydrationRequest) -> ApplyDehydrationResult:
        """Atomically persist dehydrated content with quarantine snapshot and Provenance audit."""
        orig_file = self.find_file_by_uri(req.uri)
        if not orig_file:
            raise FileNotFoundError(f"Source Wiki document not found: {req.uri}")

        orig_content = orig_file.read_text(encoding="utf-8", errors="replace")
        new_content = req.dehydrated_content.strip() + "\n"

        # Structural Gate: verify YAML frontmatter & code block preservation
        orig_yaml = RE_YAML_HEADER.search(orig_content)
        if orig_yaml and not RE_YAML_HEADER.search(new_content):
            raise ValueError("Structural Gate Rejected: YAML frontmatter was removed during dehydration.")

        orig_code_count = len(RE_FENCED_CODE.findall(orig_content))
        new_code_count = len(RE_FENCED_CODE.findall(new_content))
        if orig_code_count > 0 and new_code_count != orig_code_count:
            raise ValueError(
                f"Structural Gate Rejected: Fenced code block count mismatch (orig: {orig_code_count}, new: {new_code_count})."
            )

        # Step 1: Create quarantine snapshot
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        snapshot_filename = f"{timestamp_str}_{orig_file.name}.bak"
        snapshot_path = self.backup_root / snapshot_filename
        snapshot_path.write_text(orig_content, encoding="utf-8")

        # Step 2: Determine target file path
        if req.mode == "in_place":
            target_file = orig_file
            target_uri = req.uri
        else:
            # mirror mode: save as .dehydrated.md
            stem = orig_file.stem
            target_file = orig_file.parent / f"{stem}.dehydrated.md"
            target_uri = f"{req.uri.removesuffix('.md')}.dehydrated.md"

        # Step 3: Atomic write
        tmp_target = target_file.parent / f".tmp_{timestamp_str}_{target_file.name}"
        tmp_target.write_text(new_content, encoding="utf-8")
        tmp_target.replace(target_file)

        # Step 4: Record Provenance event
        saved_chars = len(orig_content) - len(new_content)
        event = SkillProvenanceTracker.get_instance().record_event(
            action=ProvenanceAction.OPTIMIZE,
            skill_name=orig_file.name,
            operator=req.operator,
            snapshot_path=str(snapshot_path),
            details={
                "operation": "wiki_dehydration",
                "mode": req.mode,
                "target_uri": target_uri,
                "target_path": str(target_file),
                "original_chars": len(orig_content),
                "dehydrated_chars": len(new_content),
                "saved_chars": saved_chars,
            },
        )

        return ApplyDehydrationResult(
            success=True,
            mode=req.mode,
            target_uri=target_uri,
            target_path=str(target_file),
            snapshot_path=str(snapshot_path),
            original_chars=len(orig_content),
            dehydrated_chars=len(new_content),
            saved_chars=saved_chars,
            provenance_event_id=event.event_id,
        )
