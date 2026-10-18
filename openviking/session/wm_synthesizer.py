# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Working Memory v2 synthesizer and anti-regression state machine engine.

Pure domain engine for 7-section Working Memory document parsing, section-level
merge operations, and per-section anti-bloat/anti-regression guards.
Strictly maintained within the 100-300 lines sweet spot.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

from openviking.session.models import WM_SEVEN_SECTIONS
from openviking.utils.token_estimation import estimate_text_tokens

logger = logging.getLogger("openviking.session.wm_synthesizer")


def _wm_debug(msg: str) -> None:
    logger.debug("wm_v2: %s", msg)


class WorkingMemorySynthesizer:
    """Pure algorithm engine for Working Memory document synthesis and state machine guards."""

    _WM_SECTION_BULLET_THRESHOLD = 25
    _WM_SECTION_TOKEN_THRESHOLD = 1500
    _WM_OVERSIZED_APPEND_CAP = 5
    _WM_CONSOLIDATION_SENTINEL = (
        "[⚠ CONSOLIDATION REQUIRED: Key Facts exceeds size limit. "
        "You MUST use UPDATE to merge and compress existing bullets before adding new facts.]"
    )
    _WM_APPEND_ONLY_SECTIONS = frozenset({"Errors & Corrections"})

    _WM_PATH_LIKE_RE = re.compile(
        r"(?:[\w./\\-]+\.(?:py|ts|tsx|js|jsx|md|yaml|yml|json|sh|ps1|cmd|bat|toml|ini|cfg|rs|go))"
        r"|(?:[a-zA-Z_][\w\-]*(?:/[a-zA-Z_][\w\-]*){1,})",
        re.IGNORECASE,
    )
    _WM_TITLE_STOPWORDS = frozenset(
        "the a an and or of to in on for with by at from session title working memory plan plans notes note".split()
    )
    _WM_KEY_FACTS_MIN_BULLET_RATIO = 0.15
    _WM_KEY_FACTS_MIN_ANCHOR_COVERAGE = 0.70

    _WM_ANCHOR_DATE_RE = re.compile(
        r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
        re.IGNORECASE,
    )
    _WM_ANCHOR_NUMBER_RE = re.compile(
        r"\b\d+\s+(?:years?|months?|weeks?|days?|kids?|children|hours?|miles?|times?|sessions?|rounds?|visits?|dollars?|euros?|pounds?|bedrooms?|paintings?|people|persons?)\b|\$\d[\d,]*|\b\d+\s+(?:AM|PM)\b",
        re.IGNORECASE,
    )
    _WM_ANCHOR_DECISION_RE = re.compile(r"\b(?:because|decided|chose|committed|agreed|resolved)\b", re.IGNORECASE)
    _WM_ANCHOR_STOPWORDS = frozenset(
        "the a an and or of to in on for with by at from is are was were has have had been be "
        "will would could should may might shall this that these those not no but if then so as "
        "it its they their them she her he him his we our us you your who which what when where "
        "why all each every both few more most other some such than too very also just about "
        "after before between into through during again further once here there over under out "
        "up down off own same only new old key facts decisions session working memory".split()
    )

    @classmethod
    def parse_wm_sections(cls, text: str) -> Dict[str, str]:
        """Parse an existing WM markdown document into {header_line: body_text}."""
        sections: Dict[str, str] = {}
        cur, buf = None, []
        for line in (text or "").splitlines():
            s = line.strip()
            if s.startswith("## "):
                if cur:
                    sections[cur] = "\n".join(buf).strip()
                cur, buf = s, []
            elif cur:
                buf.append(line)
        if cur:
            sections[cur] = "\n".join(buf).strip()
        return sections

    @classmethod
    def build_wm_section_reminders(cls, overview: str) -> str:
        """Compute dynamic section-size warnings for the WM update prompt."""
        if not overview:
            return ""
        warnings = []
        for hdr, body in cls.parse_wm_sections(overview).items():
            name = hdr.lstrip("#").strip()
            if name in cls._WM_APPEND_ONLY_SECTIONS:
                continue
            n_items, est_tok = len(cls.extract_bullet_items(body)), estimate_text_tokens(body)
            if n_items > cls._WM_SECTION_BULLET_THRESHOLD or est_tok > cls._WM_SECTION_TOKEN_THRESHOLD:
                warnings.append(
                    f'WARNING: "{name}" has {n_items} bullets (~{est_tok} tokens).\n'
                    f"This section MUST be consolidated via UPDATE. Group related facts by topic into category summaries.\n"
                    f"Target: <={cls._WM_SECTION_BULLET_THRESHOLD} bullets, <={cls._WM_SECTION_TOKEN_THRESHOLD} tokens."
                )
        return f"<section_size_warnings>\n{chr(10).join(warnings)}\n</section_size_warnings>" if warnings else ""

    @classmethod
    def recover_ops_from_raw(cls, raw: str) -> Dict[str, Any]:
        """Best-effort regex recovery of per-section ops from malformed tool_call string."""
        if not raw:
            return {}
        ops: Dict[str, Any] = {}
        sec_alt = "|".join(re.escape(n) for n in WM_SEVEN_SECTIONS)
        for m in re.finditer(rf'"({sec_alt})"\s*:\s*\{{\s*"op"\s*:\s*"KEEP"\s*\}}', raw):
            ops.setdefault(m.group(1), {"op": "KEEP"})
        for m in re.finditer(rf'"({sec_alt})"\s*:\s*\{{\s*"op"\s*:\s*"UPDATE"\s*,\s*"content"\s*:\s*"((?:[^"\\]|\\.)*?)"', raw, re.DOTALL):
            if m.group(1) not in ops:
                try:
                    c = json.loads(f'"{m.group(2)}"')
                except Exception:
                    c = m.group(2)
                ops[m.group(1)] = {"op": "UPDATE", "content": c}
        for m in re.finditer(rf'"({sec_alt})"\s*:\s*\{{\s*"op"\s*:\s*"APPEND"\s*,\s*"items"\s*:\s*\[([\s\S]*?)(?:\]|$)', raw):
            if m.group(1) not in ops:
                items = []
                for im in re.finditer(r'"((?:[^"\\]|\\.)*)"', m.group(2), re.DOTALL):
                    try:
                        items.append(json.loads(f'"{im.group(1)}"'))
                    except Exception:
                        items.append(im.group(1))
                ops[m.group(1)] = {"op": "APPEND", "items": items}
        return ops

    @classmethod
    def extract_bullet_items(cls, text: str) -> List[str]:
        """Extract bullet-like items from a markdown section body."""
        items = []
        for line in (text or "").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            m = re.match(r"^(?:[-*]|\d+[\.)])\s+(.*)$", s)
            item = m.group(1).strip() if m else s
            if item:
                items.append(item)
        return items

    @classmethod
    def extract_lexical_anchors(cls, text: str) -> Set[str]:
        """Extract fact-preserving anchors: dates, numbers, proper nouns, decision markers."""
        anchors = {m.group().lower().strip() for r in (cls._WM_ANCHOR_DATE_RE, cls._WM_ANCHOR_NUMBER_RE, cls._WM_ANCHOR_DECISION_RE) for m in r.finditer(text)}
        anchors.update(tok.lower() for tok in re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", text) if tok.lower() not in cls._WM_ANCHOR_STOPWORDS)
        return anchors

    @classmethod
    def salvage_new_items_from_rejected_update(cls, new_content: str, old_content: str) -> Dict[str, Any]:
        """Salvage genuinely new items from rejected UPDATE via APPEND."""
        old_lower = (old_content or "").lower()
        fresh = [it for it in cls.extract_bullet_items(new_content) if it.strip("_* `").lower() and it.strip("_* `").lower() not in old_lower]
        return {"op": "APPEND", "items": fresh} if fresh else {"op": "KEEP"}

    @classmethod
    def enforce_append_only(cls, header: str, op: Any, old_content: str) -> Dict[str, Any]:
        """Guard: force KEEP/APPEND semantics on APPEND-only sections."""
        if not isinstance(op, dict):
            return {"op": "KEEP"}
        op_name = (op.get("op") or "").upper()
        if op_name in ("KEEP", "APPEND"):
            return op
        return cls.salvage_new_items_from_rejected_update(op.get("content") or "", old_content) if op_name == "UPDATE" else {"op": "KEEP"}

    @classmethod
    def enforce_key_facts_consolidation(cls, op: Any, old_content: str) -> Dict[str, Any]:
        """Guard: allow controlled consolidation for Key Facts & Decisions with anti-bloat."""
        if not isinstance(op, dict):
            return {"op": "KEEP"}
        op_name = (op.get("op") or "").upper()
        if op_name == "KEEP":
            return op

        old_items = cls.extract_bullet_items(old_content or "")
        est_tokens = estimate_text_tokens(old_content or "")
        is_emergency = len(old_items) > cls._WM_SECTION_BULLET_THRESHOLD * 2 or est_tokens > cls._WM_SECTION_TOKEN_THRESHOLD * 2

        if op_name == "APPEND":
            if len(old_items) <= cls._WM_SECTION_BULLET_THRESHOLD and est_tokens <= cls._WM_SECTION_TOKEN_THRESHOLD:
                return op
            items = op.get("items") or cls.extract_bullet_items((op.get("content") or "").strip())
            old_lower = (old_content or "").lower()
            fresh = [str(it) for it in items if str(it).strip("_* `").lower() not in old_lower]
            if is_emergency:
                return {"op": "KEEP"} if cls._WM_CONSOLIDATION_SENTINEL.lower() in old_lower else {"op": "APPEND", "items": [cls._WM_CONSOLIDATION_SENTINEL]}
            accepted = fresh[: cls._WM_OVERSIZED_APPEND_CAP]
            return {"op": "APPEND", "items": accepted} if accepted else {"op": "KEEP"}

        if op_name != "UPDATE":
            return {"op": "KEEP"}
        if not old_items:
            return op

        new_content = (op.get("content") or "").strip()
        new_items = cls.extract_bullet_items(new_content)
        ratio = len(new_items) / len(old_items) if old_items else 1.0
        if ratio < cls._WM_KEY_FACTS_MIN_BULLET_RATIO:
            salvaged = cls.salvage_new_items_from_rejected_update(new_content, old_content)
            return {"op": "KEEP"} if (is_emergency and salvaged.get("op") == "APPEND") else salvaged

        old_anchors = cls.extract_lexical_anchors(old_content or "")
        if old_anchors:
            coverage = len(old_anchors & cls.extract_lexical_anchors(new_content)) / len(old_anchors)
            if coverage < cls._WM_KEY_FACTS_MIN_ANCHOR_COVERAGE:
                salvaged = cls.salvage_new_items_from_rejected_update(new_content, old_content)
                return {"op": "KEEP"} if (is_emergency and salvaged.get("op") == "APPEND") else salvaged
        return op

    @classmethod
    def enforce_files_no_regression(cls, op: Any, old_content: str) -> Dict[str, Any]:
        """Guard: don't let a 'Files & Context' UPDATE drop file paths."""
        if not isinstance(op, dict) or (op.get("op") or "").upper() != "UPDATE":
            return op if isinstance(op, dict) else {"op": "KEEP"}
        new_content = (op.get("content") or "").strip()
        old_paths = set(cls._WM_PATH_LIKE_RE.findall(old_content or ""))
        new_paths = set(cls._WM_PATH_LIKE_RE.findall(new_content))
        if old_paths.issubset(new_paths):
            return op
        added = new_paths - old_paths
        if added:
            new_items = [
                next((line.strip().lstrip("-*").strip() for line in new_content.splitlines() if p in line), f"{p} (newly referenced)")
                for p in sorted(added)
            ]
            return {"op": "APPEND", "items": new_items}
        return {"op": "KEEP"}

    @classmethod
    def enforce_title_stability(cls, op: Any, old_content: str) -> Dict[str, Any]:
        """Guard: reject Session Title UPDATE when semantic keywords drift completely."""
        if not isinstance(op, dict) or (op.get("op") or "").upper() != "UPDATE":
            return op if isinstance(op, dict) else {"op": "KEEP"}
        new_content = (op.get("content") or "").strip()
        words = lambda t: {tok.lower() for tok in re.findall(r"[A-Za-z][A-Za-z0-9\.]{2,}|[\d\.]+", t or "") if tok.lower() not in cls._WM_TITLE_STOPWORDS}
        old_w, new_w = words(old_content), words(new_content)
        return op if (not old_w or (old_w & new_w)) else {"op": "KEEP"}

    @classmethod
    def enforce_open_issues_resolved(cls, op: Any, old_content: str) -> Dict[str, Any]:
        """Guard: don't let an Open Issues UPDATE silently drop unaddressed items."""
        if not isinstance(op, dict) or (op.get("op") or "").upper() != "UPDATE":
            return op if isinstance(op, dict) else {"op": "KEEP"}
        new_content = (op.get("content") or "").strip()
        new_lower = new_content.lower()
        dropped = [
            it for it in cls.extract_bullet_items(old_content or "")
            if "[silently dropped, restored]" not in it and it[:40].lower().strip("_* `").strip() not in new_lower
        ]
        if not dropped:
            return op
        restored = "\n".join(f"- [silently dropped, restored] {it}" for it in dropped)
        return {"op": "UPDATE", "content": (new_content + ("\n" if new_content else "") + restored).strip()}

    @classmethod
    def merge_wm_sections(cls, old_wm: str, ops: Dict[str, Any]) -> str:
        """Merge LLM per-section ops into a clean 7-section Working Memory document."""
        old_sections = cls.parse_wm_sections(old_wm)
        parts = ["# Working Memory", ""]
        for header in WM_SEVEN_SECTIONS:
            full_header = f"## {header}"
            op = (ops or {}).get(header)
            old_c = old_sections.get(full_header, "").rstrip()

            if old_c:
                if header == "Session Title":
                    op = cls.enforce_title_stability(op, old_c)
                elif header == "Key Facts & Decisions":
                    op = cls.enforce_key_facts_consolidation(op, old_c)
                elif header in cls._WM_APPEND_ONLY_SECTIONS:
                    op = cls.enforce_append_only(header, op, old_c)
                elif header == "Files & Context":
                    op = cls.enforce_files_no_regression(op, old_c)
                elif header == "Open Issues":
                    op = cls.enforce_open_issues_resolved(op, old_c)

            op_name = (op.get("op") or "").upper() if isinstance(op, dict) else ""
            if op is None or op_name in ("", "KEEP"):
                new_c = old_c
            elif op_name == "UPDATE":
                new_c = (op.get("content") or "").strip()
            elif op_name == "APPEND":
                items = [str(s).strip() for s in (op.get("items") or []) if str(s).strip()]
                appended = "\n".join(f"- {s}" for s in items)
                new_c = f"{old_c}\n{appended}" if old_c and appended else (old_c or appended)
            else:
                new_c = old_c

            parts.append(full_header)
            if new_c:
                parts.append(new_c)
            parts.append("")
        return "\n".join(parts).rstrip() + "\n"
