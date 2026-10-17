# -*- coding: utf-8 -*-
"""Adaptive prompt segmenter for Context Router Pipeline.

Scans heterogeneous prompt texts and cleanly isolates:
1. CODE_BLOCK: Fenced code blocks (Python, TS, JS, JSON, SQL, Shell);
2. SKILL_CONTRACT: YAML frontmatter and procedural skill definitions;
3. STATIC_HEADER: System prompts, role definitions, and immutable instructions;
4. DIALOGUE_HISTORY: Multi-turn user/assistant exchanges;
5. NATURAL_LANGUAGE: General markdown prose and wiki documentation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from openviking.service.context_router_types import RouteEngine, SegmentType

RE_FENCED_CODE = re.compile(
    r"(?P<fence>```|~~~)(?P<lang>[a-zA-Z0-9_\-\+]*)\r?\n(?P<code>[\s\S]*?)(?P=fence)",
    re.MULTILINE,
)

RE_YAML_HEADER = re.compile(
    r"^---\s*\r?\n(?P<yaml>[\s\S]*?)\r?\n---\s*\r?\n?",
    re.MULTILINE,
)

RE_SKILL_PROCEDURE = re.compile(
    r"(?P<skill>#+\s*(?:Skill|Rules|Actions|SOP|Workflow)[\s\S]*?(?=(?:\n#+\s+[^\n]+)|\Z))",
    re.IGNORECASE,
)

RE_DIALOGUE_TURNS = re.compile(
    r"(?P<dialogue>(?:(?:User|Assistant|Human|AI):\s+[^\n]+\r?\n?){3,})",
    re.IGNORECASE,
)

RE_STATIC_HEADER = re.compile(
    r"^(?P<static><(?:identity|system|role)>[\s\S]*?</(?:identity|system|role)>\s*|SYSTEM:[^\n]*\r?\n\s*|#+\s*System[^\n]*\r?\n\s*|You are[^\n]*\r?\n\s*)",
    re.IGNORECASE,
)


@dataclass
class RawSegment:
    """Pre-processed slice ready for engine dispatch."""
    segment_type: SegmentType
    engine: RouteEngine
    content: str
    language: Optional[str] = None
    fence_prefix: str = ""
    fence_suffix: str = ""
    start_pos: int = 0
    end_pos: int = 0


def estimate_tokens(text: str) -> int:
    """Heuristic token estimator (~3.5 chars per token for general mixture)."""
    if not text.strip():
        return 0
    return max(1, int(len(text) / 3.5))


def segment_prompt(content: str, preserve_static_header: bool = True) -> List[RawSegment]:
    """Split heterogeneous prompt into an ordered sequence of typed raw segments.
    
    Guarantees that re-combining segments preserves 100% of the original prompt
    ordering and structure.
    """
    if not content or not content.strip():
        return []

    spans: List[RawSegment] = []

    # 0. Match leading static header
    if preserve_static_header:
        m_static = RE_STATIC_HEADER.search(content)
        if m_static and m_static.start() == 0:
            spans.append(
                RawSegment(
                    segment_type=SegmentType.STATIC_HEADER,
                    engine=RouteEngine.NATIVE_CACHING,
                    content=m_static.group(0),
                    start_pos=m_static.start(),
                    end_pos=m_static.end(),
                )
            )

    # 1. Match fenced code blocks
    for m in RE_FENCED_CODE.finditer(content):
        lang = m.group("lang").strip().lower() or "python"
        inner_code = m.group("code")
        spans.append(
            RawSegment(
                segment_type=SegmentType.CODE_BLOCK,
                engine=RouteEngine.TOKENSHIFT,
                content=inner_code,
                language=lang,
                fence_prefix=f"{m.group('fence')}{m.group('lang')}\n",
                fence_suffix=f"\n{m.group('fence')}",
                start_pos=m.start(),
                end_pos=m.end(),
            )
        )

    # 2. Match YAML frontmatter (Skill contracts)
    for m in RE_YAML_HEADER.finditer(content):
        # Do not overlap with existing spans
        if any(s.start_pos <= m.start() < s.end_pos or s.start_pos < m.end() <= s.end_pos for s in spans):
            continue
        spans.append(
            RawSegment(
                segment_type=SegmentType.SKILL_CONTRACT,
                engine=RouteEngine.SKILLZIP,
                content=m.group(0),
                start_pos=m.start(),
                end_pos=m.end(),
            )
        )

    # 3. Match dialogue history blocks
    for m in RE_DIALOGUE_TURNS.finditer(content):
        if any(s.start_pos <= m.start() < s.end_pos or s.start_pos < m.end() <= s.end_pos for s in spans):
            continue
        spans.append(
            RawSegment(
                segment_type=SegmentType.DIALOGUE_HISTORY,
                engine=RouteEngine.ACTIVE_NOTES,
                content=m.group("dialogue"),
                start_pos=m.start(),
                end_pos=m.end(),
            )
        )

    # Sort spans chronologically by start position
    spans.sort(key=lambda s: s.start_pos)

    # 4. Fill gaps between specialized spans with prose / headers
    final_segments: List[RawSegment] = []
    cursor = 0

    for s in spans:
        if s.start_pos > cursor:
            gap_text = content[cursor:s.start_pos]
            if gap_text.strip():
                # Check if this leading gap is a static header
                is_static = (
                    cursor == 0
                    and preserve_static_header
                    and bool(RE_STATIC_HEADER.match(gap_text.strip()))
                )
                final_segments.append(
                    RawSegment(
                        segment_type=SegmentType.STATIC_HEADER if is_static else SegmentType.NATURAL_LANGUAGE,
                        engine=RouteEngine.NATIVE_CACHING if is_static else RouteEngine.LLMLINGUA2,
                        content=gap_text,
                        start_pos=cursor,
                        end_pos=s.start_pos,
                    )
                )
            elif gap_text:
                # Retain pure whitespace in previous or next segment if needed
                if final_segments:
                    final_segments[-1].content += gap_text
                else:
                    s.fence_prefix = gap_text + s.fence_prefix
        final_segments.append(s)
        cursor = s.end_pos

    if cursor < len(content):
        trailing = content[cursor:]
        if trailing.strip():
            is_static = (
                cursor == 0
                and preserve_static_header
                and bool(RE_STATIC_HEADER.match(trailing.strip()))
            )
            final_segments.append(
                RawSegment(
                    segment_type=SegmentType.STATIC_HEADER if is_static else SegmentType.NATURAL_LANGUAGE,
                    engine=RouteEngine.NATIVE_CACHING if is_static else RouteEngine.LLMLINGUA2,
                    content=trailing,
                    start_pos=cursor,
                    end_pos=len(content),
                )
            )
        elif trailing and final_segments:
            final_segments[-1].content += trailing

    # If no spans found at all, treat whole text
    if not final_segments and content.strip():
        is_static = preserve_static_header and bool(RE_STATIC_HEADER.match(content.strip()))
        final_segments.append(
            RawSegment(
                segment_type=SegmentType.STATIC_HEADER if is_static else SegmentType.NATURAL_LANGUAGE,
                engine=RouteEngine.NATIVE_CACHING if is_static else RouteEngine.LLMLINGUA2,
                content=content,
                start_pos=0,
                end_pos=len(content),
            )
        )

    return final_segments
