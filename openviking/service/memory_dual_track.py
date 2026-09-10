# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Dual-Track Memory Storage & Manifold Separation Service.

Implements 'Dual-Track Write, Single-Track Read' (双轨写入，单轨读取):
- Track 1: semantic_anchor (causal attribution, scenario, trigger conditions, rules)
  -> Dedicated to vector embedding and similarity retrieval;
- Track 2: delta (concrete 3~5 line Git Diff, code snippet, error fingerprint)
  -> Stored in raw text body for deterministic agent code replay.

Cures:
- Raw Diff semantic blindness (vector manifold dilution);
- Vacuous sentimental reflections causing negative transfer.
"""

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Tuple

DIFF_BLOCK_PATTERN = re.compile(
    r"```(?:diff|patch)?\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE
)
GIT_DIFF_HEADER_PATTERN = re.compile(
    r"(?:^|\n)(diff --git\s+.*|--- [ab]/.*|\+\+\+ [ab]/.*|@@\s+-\d+.*?\s+@@)",
    re.MULTILINE,
)
SEMANTIC_ANCHOR_HEADER = re.compile(
    r"##\s+(?:🎯\s*)?Semantic Anchor[^\n]*\n(.*?)(?=\n##|\Z)", re.DOTALL | re.IGNORECASE
)
DELTA_HEADER = re.compile(
    r"##\s+(?:⚡\s*)?Delta(?:\s+Replay)?[^\n]*\n(.*?)(?=\n##|\Z)", re.DOTALL | re.IGNORECASE
)
MEMORY_FIELDS_RE = re.compile(
    r"<!--\s*MEMORY_FIELDS\s*\n(.*?)\n-->", re.DOTALL
)


@dataclass(frozen=True)
class DualTrackMemory:
    """Immutable Typed DTO representing a dual-track memory unit."""

    semantic_anchor: str
    delta: str
    raw_content: str
    is_dual_track: bool = False
    title: str = ""
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def format_dual_track_markdown(
    title: str,
    semantic_anchor: str,
    delta: str = "",
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Format dual-track memory into standardized markdown with MEMORY_FIELDS comment."""
    clean_title = (title or "Dual-Track Memory").strip()
    clean_anchor = (semantic_anchor or "").strip()
    clean_delta = (delta or "").strip()

    metadata = dict(extra_metadata or {})
    metadata["dual_track"] = True
    metadata["has_delta"] = bool(clean_delta)
    if clean_anchor:
        metadata["semantic_anchor"] = clean_anchor[:300]

    lines = [f"# {clean_title}", ""]
    if clean_anchor:
        lines.extend([
            "## 🎯 Semantic Anchor (因果归因与检索场景)",
            clean_anchor,
            "",
        ])

    if clean_delta:
        diff_body = clean_delta
        if not (diff_body.startswith("```") and diff_body.endswith("```")):
            diff_body = f"```diff\n{clean_delta}\n```"
        lines.extend([
            "## ⚡ Delta Replay (代码重放轨)",
            diff_body,
            "",
        ])

    meta_json = json.dumps(metadata, ensure_ascii=False, indent=2)
    lines.extend([
        f"<!-- MEMORY_FIELDS\n{meta_json}\n-->",
        "",
    ])

    return "\n".join(lines).strip() + "\n"


def _extract_diff_hunks_and_files(diff_text: str) -> Tuple[list[str], list[str]]:
    """Extract modified filenames and hunk headers from raw git diff text."""
    files = []
    hunks = []
    for line in diff_text.splitlines():
        line_str = line.strip()
        if line_str.startswith("diff --git"):
            parts = line_str.split()
            if len(parts) >= 4:
                files.append(parts[-1].lstrip("b/"))
        elif line_str.startswith("+++ b/"):
            files.append(line_str[6:])
        elif line_str.startswith("@@"):
            hunks.append(line_str)
    # Deduplicate preserving order
    seen_files = set()
    uniq_files = [f for f in files if not (f in seen_files or seen_files.add(f))]
    return uniq_files, hunks[:5]


def extract_dual_track(content: str) -> DualTrackMemory:
    """Parse raw content and decouple into semantic_anchor and delta tracks.

    Zero-breakage contract:
    - If explicit dual-track headers or MEMORY_FIELDS exist, parse directly.
    - If content embeds ```diff ... ``` or git diff, separate prose from diff code.
    - If content is pure raw diff, synthesize a semantic anchor from diff headers to prevent vector blindness.
    - If content is plain prose without diff, semantic_anchor is content, delta is empty.
    """
    if not content:
        return DualTrackMemory(semantic_anchor="", delta="", raw_content="", is_dual_track=False)

    raw = content.strip()
    extra_fields: Dict[str, Any] = {}

    # 1. Parse MEMORY_FIELDS if present
    mf_match = MEMORY_FIELDS_RE.search(raw)
    if mf_match:
        try:
            extra_fields = json.loads(mf_match.group(1).strip())
        except Exception:
            pass

    # 2. Check for explicit section headers
    anchor_match = SEMANTIC_ANCHOR_HEADER.search(raw)
    delta_match = DELTA_HEADER.search(raw)

    if anchor_match or delta_match or extra_fields.get("dual_track"):
        extracted_anchor = ""
        extracted_delta = ""

        if anchor_match:
            extracted_anchor = anchor_match.group(1).strip()
        elif extra_fields.get("semantic_anchor"):
            extracted_anchor = str(extra_fields.get("semantic_anchor")).strip()

        if delta_match:
            raw_delta_sec = delta_match.group(1).strip()
            # Strip code fence if present
            fence_match = DIFF_BLOCK_PATTERN.search(raw_delta_sec)
            extracted_delta = fence_match.group(1).strip() if fence_match else raw_delta_sec
        elif extra_fields.get("delta"):
            extracted_delta = str(extra_fields.get("delta")).strip()

        title = ""
        first_line = raw.splitlines()[0].strip() if raw.splitlines() else ""
        if first_line.startswith("# "):
            title = first_line[2:].strip()

        return DualTrackMemory(
            semantic_anchor=extracted_anchor,
            delta=extracted_delta,
            raw_content=raw,
            is_dual_track=True,
            title=title,
            extra_fields=extra_fields,
        )

    # 3. Check for embedded code diff blocks (```diff ... ```)
    code_block_match = DIFF_BLOCK_PATTERN.search(raw)
    if code_block_match:
        delta_code = code_block_match.group(1).strip()
        prose_anchor = DIFF_BLOCK_PATTERN.sub("", raw).strip()
        prose_anchor = MEMORY_FIELDS_RE.sub("", prose_anchor).strip()

        # If prose is empty or purely title, extract diff context
        if len(prose_anchor) < 10:
            files, hunks = _extract_diff_hunks_and_files(delta_code)
            file_desc = f"Files: {', '.join(files)}" if files else "Code patch"
            hunk_desc = f" (Hunks: {'; '.join(hunks)})" if hunks else ""
            prose_anchor = f"{file_desc}{hunk_desc}. Code modification diff."

        return DualTrackMemory(
            semantic_anchor=prose_anchor,
            delta=delta_code,
            raw_content=raw,
            is_dual_track=True,
            title="Embedded Diff Memory",
            extra_fields=extra_fields,
        )

    # 4. Check for naked git diff (starts with diff --git or contains --- a/ +++ b/)
    if GIT_DIFF_HEADER_PATTERN.search(raw):
        files, hunks = _extract_diff_hunks_and_files(raw)
        file_desc = f"Files: {', '.join(files)}" if files else "Raw git diff patch"
        hunk_desc = f" ({'; '.join(hunks)})" if hunks else ""
        synthetic_anchor = f"[Git Diff Delta] {file_desc}{hunk_desc}. Physical code patch replay."

        return DualTrackMemory(
            semantic_anchor=synthetic_anchor,
            delta=raw,
            raw_content=raw,
            is_dual_track=True,
            title=f"Patch for {', '.join(files[:2])}" if files else "Git Patch",
            extra_fields={"synthetic_anchor": True},
        )

    # 5. Plain prose knowledge
    clean_prose = MEMORY_FIELDS_RE.sub("", raw).strip()
    return DualTrackMemory(
        semantic_anchor=clean_prose,
        delta="",
        raw_content=raw,
        is_dual_track=False,
        title="",
        extra_fields=extra_fields,
    )


def get_embedding_text_for_content(content: str) -> str:
    """Return high-signal text for vector embedding, shedding raw code diff noise."""
    dt = extract_dual_track(content)
    if dt.is_dual_track and dt.semantic_anchor:
        return dt.semantic_anchor
    return content
