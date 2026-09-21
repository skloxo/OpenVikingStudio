# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Working Memory v2 synthesizer and anti-regression guard algorithms.

Extracts the 7-section Working Memory document parser, section-level merge engine,
and per-section anti-bloat / anti-regression validation guards into a standalone,
testable pure domain module.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from openviking.session.models import WM_SEVEN_SECTIONS
from openviking.utils.token_estimation import estimate_text_tokens

logger = logging.getLogger("openviking.session.wm_synthesizer")


def _wm_debug(msg: str) -> None:
    """Log a WM v2 debug message via the standard logger."""
    logger.debug("wm_v2: %s", msg)


class WorkingMemorySynthesizer:
    """Pure algorithm engine for Working Memory v2 document synthesis and guard evaluation."""

    _WM_SECTION_BULLET_THRESHOLD = 25
    _WM_SECTION_TOKEN_THRESHOLD = 1500
    _WM_OVERSIZED_APPEND_CAP = 5
    _WM_CONSOLIDATION_SENTINEL = (
        "[⚠ CONSOLIDATION REQUIRED: Key Facts exceeds size limit. "
        "You MUST use UPDATE to merge and compress existing bullets "
        "before adding new facts.]"
    )

    _WM_APPEND_ONLY_SECTIONS = frozenset(
        {
            "Errors & Corrections",
        }
    )

    _WM_PATH_LIKE_RE = re.compile(
        r"(?:[\w./\\-]+\.(?:py|ts|tsx|js|jsx|md|yaml|yml|json|sh|ps1|cmd|bat|toml|ini|cfg|rs|go))"
        r"|(?:[a-zA-Z_][\w\-]*(?:/[a-zA-Z_][\w\-]*){1,})",
        re.IGNORECASE,
    )

    _WM_TITLE_STOPWORDS = frozenset(
        {
            "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
            "by", "at", "from", "session", "title", "working", "memory", "plan",
            "plans", "notes", "note",
        }
    )

    _WM_KEY_FACTS_MIN_BULLET_RATIO = 0.15
    _WM_KEY_FACTS_MIN_ANCHOR_COVERAGE = 0.70

    _WM_ANCHOR_DATE_RE = re.compile(
        r"\b\d{4}-\d{2}-\d{2}\b"
        r"|\b\d{1,2}\s+(?:January|February|March|April|May|June"
        r"|July|August|September|October|November|December)\s+\d{4}\b",
        re.IGNORECASE,
    )
    _WM_ANCHOR_NUMBER_RE = re.compile(
        r"\b\d+\s+(?:years?|months?|weeks?|days?|kids?|children"
        r"|hours?|miles?|times?|sessions?|rounds?|visits?"
        r"|dollars?|euros?|pounds?|bedrooms?|paintings?"
        r"|people|persons?)\b"
        r"|\$\d[\d,]*"
        r"|\b\d+\s+(?:AM|PM)\b",
        re.IGNORECASE,
    )
    _WM_ANCHOR_DECISION_RE = re.compile(
        r"\b(?:because|decided|chose|committed|agreed|resolved)\b",
        re.IGNORECASE,
    )
    _WM_ANCHOR_STOPWORDS = frozenset(
        {
            "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
            "by", "at", "from", "is", "are", "was", "were", "has", "have", "had",
            "been", "be", "will", "would", "could", "should", "may", "might",
            "shall", "this", "that", "these", "those", "not", "no", "but", "if",
            "then", "so", "as", "it", "its", "they", "their", "them", "she",
            "her", "he", "him", "his", "we", "our", "us", "you", "your", "who",
            "which", "what", "when", "where", "why", "all", "each", "every",
            "both", "few", "more", "most", "other", "some", "such", "than",
            "too", "very", "also", "just", "about", "after", "before", "between",
            "into", "through", "during", "again", "further", "once", "here",
            "there", "over", "under", "out", "up", "down", "off", "own", "same",
            "only", "new", "old", "key", "facts", "decisions", "session",
            "working", "memory",
        }
    )

    @classmethod
    def parse_wm_sections(cls, text: str) -> Dict[str, str]:
        """Parse an existing WM markdown into {header_line: body_text}."""
        sections: Dict[str, str] = {}
        current: Optional[str] = None
        buf: List[str] = []
        for line in (text or "").splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                if current is not None:
                    sections[current] = "\n".join(buf).strip()
                current = stripped
                buf = []
            elif current is not None:
                buf.append(line)
        if current is not None:
            sections[current] = "\n".join(buf).strip()
        return sections

    @classmethod
    def build_wm_section_reminders(cls, overview: str) -> str:
        """Compute dynamic section-size warnings for the WM update prompt."""
        if not overview:
            return ""
        sections = cls.parse_wm_sections(overview)
        warnings: List[str] = []
        for header, body in sections.items():
            name = header.lstrip("#").strip()
            if name in cls._WM_APPEND_ONLY_SECTIONS:
                continue
            items = cls.extract_bullet_items(body)
            est_tokens = estimate_text_tokens(body)
            if (
                len(items) > cls._WM_SECTION_BULLET_THRESHOLD
                or est_tokens > cls._WM_SECTION_TOKEN_THRESHOLD
            ):
                warnings.append(
                    f'WARNING: "{name}" has {len(items)} bullets '
                    f"(~{est_tokens} tokens).\n"
                    f"This section MUST be consolidated via UPDATE. Group "
                    f"related facts by topic into category summaries. "
                    f"Preserve names, dates, and exact values but merge "
                    f"repetitive events into patterns.\n"
                    f"Target: <={cls._WM_SECTION_BULLET_THRESHOLD} "
                    f"bullets, <={cls._WM_SECTION_TOKEN_THRESHOLD} tokens."
                )
        if not warnings:
            return ""
        return "<section_size_warnings>\n" + "\n\n".join(warnings) + "\n</section_size_warnings>"

    @classmethod
    def recover_ops_from_raw(cls, raw_str: str) -> Dict[str, Any]:
        """Best-effort regex recovery of per-section ops from a malformed tool_call string."""
        if not raw_str:
            return {}

        ops: Dict[str, Any] = {}
        names_alt = "|".join(re.escape(n) for n in WM_SEVEN_SECTIONS)

        # KEEP
        keep_re = re.compile(rf'"({names_alt})"\s*:\s*\{{\s*"op"\s*:\s*"KEEP"\s*\}}')
        for m in keep_re.finditer(raw_str):
            ops.setdefault(m.group(1), {"op": "KEEP"})

        # UPDATE
        update_re = re.compile(
            rf'"({names_alt})"\s*:\s*\{{\s*"op"\s*:\s*"UPDATE"\s*,\s*"content"\s*:\s*"'
            rf'((?:[^"\\]|\\.)*?)'
            rf'(?:"\s*\}}|(?="\s*,\s*"(?:' + names_alt + r')"))',
            re.DOTALL,
        )
        for m in update_re.finditer(raw_str):
            header = m.group(1)
            if header in ops:
                continue
            captured = m.group(2)
            try:
                content = json.loads('"' + captured + '"')
            except Exception:
                content = captured
            ops[header] = {"op": "UPDATE", "content": content}

        # APPEND
        append_re = re.compile(
            rf'"({names_alt})"\s*:\s*\{{\s*"op"\s*:\s*"APPEND"\s*,\s*"items"\s*:\s*\['
            rf"([\s\S]*?)(?:\]|$)",
        )
        item_re = re.compile(r'"((?:[^"\\]|\\.)*)"', re.DOTALL)
        for m in append_re.finditer(raw_str):
            header = m.group(1)
            if header in ops:
                continue
            items_raw = m.group(2)
            items: List[str] = []
            for im in item_re.finditer(items_raw):
                captured = im.group(1)
                try:
                    items.append(json.loads('"' + captured + '"'))
                except Exception:
                    items.append(captured)
            ops[header] = {"op": "APPEND", "items": items}

        return ops

    @classmethod
    def extract_bullet_items(cls, text: str) -> List[str]:
        """Extract bullet-like items from a markdown section body."""
        items: List[str] = []
        for line in (text or "").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            m = re.match(r"^(?:[-*]|\d+[\.)])\s+(.*)$", stripped)
            if m:
                item = m.group(1).strip()
            else:
                item = stripped
            if item:
                items.append(item)
        return items

    @classmethod
    def enforce_append_only(cls, header: str, op: Any, old_content: str) -> Dict[str, Any]:
        """Guard: force KEEP/APPEND semantics on APPEND-only sections."""
        if not isinstance(op, dict):
            return {"op": "KEEP"}
        op_name = (op.get("op") or "").upper()
        if op_name in ("KEEP", "APPEND"):
            return op
        if op_name != "UPDATE":
            return {"op": "KEEP"}

        new_content = (op.get("content") or "").strip()
        new_items = cls.extract_bullet_items(new_content)
        old_lower = (old_content or "").lower()
        fresh_items = []
        for it in new_items:
            key = it.strip("_* `").lower()
            if key and key not in old_lower:
                fresh_items.append(it)
        _wm_debug(
            f"guard: section {header!r} UPDATE -> forced APPEND "
            f"(llm_items={len(new_items)}, fresh_after_dedup={len(fresh_items)})"
        )
        if not fresh_items:
            return {"op": "KEEP"}
        return {"op": "APPEND", "items": fresh_items}

    @classmethod
    def extract_lexical_anchors(cls, text: str) -> set:
        """Extract fact-preserving anchors: dates, numbers, proper nouns, decision markers."""
        anchors: set = set()
        for m in cls._WM_ANCHOR_DATE_RE.finditer(text):
            anchors.add(m.group().lower().strip())
        for m in cls._WM_ANCHOR_NUMBER_RE.finditer(text):
            anchors.add(m.group().lower().strip())
        for m in cls._WM_ANCHOR_DECISION_RE.finditer(text):
            anchors.add(m.group().lower().strip())
        for token in re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", text):
            if token.lower() not in cls._WM_ANCHOR_STOPWORDS:
                anchors.add(token.lower())
        return anchors

    @classmethod
    def salvage_new_items_from_rejected_update(
        cls, new_content: str, old_content: str
    ) -> Dict[str, Any]:
        """Salvage genuinely new items from rejected UPDATE via APPEND."""
        new_items = cls.extract_bullet_items(new_content)
        old_lower = (old_content or "").lower()
        fresh_items = []
        for it in new_items:
            key = it.strip("_* `").lower()
            if key and key not in old_lower:
                fresh_items.append(it)
        if fresh_items:
            _wm_debug(f"guard: salvaged {len(fresh_items)} new items from rejected UPDATE")
            return {"op": "APPEND", "items": fresh_items}
        return {"op": "KEEP"}

    @classmethod
    def enforce_key_facts_consolidation(cls, op: Any, old_content: str) -> Dict[str, Any]:
        """Guard: allow controlled consolidation for Key Facts & Decisions with anti-bloat."""
        if not isinstance(op, dict):
            return {"op": "KEEP"}
        op_name = (op.get("op") or "").upper()
        if op_name == "KEEP":
            return op
        if op_name == "APPEND":
            old_items = cls.extract_bullet_items(old_content or "")
            est_tokens = estimate_text_tokens(old_content or "")
            bullet_over = len(old_items) > cls._WM_SECTION_BULLET_THRESHOLD
            token_over = est_tokens > cls._WM_SECTION_TOKEN_THRESHOLD
            if not bullet_over and not token_over:
                return op
            append_items = op.get("items") or []
            if not append_items:
                raw = (op.get("content") or "").strip()
                append_items = cls.extract_bullet_items(raw)
            append_items = [str(it) for it in append_items if it]
            old_lower = (old_content or "").lower()
            fresh = [it for it in append_items if it.strip("_* `").lower() not in old_lower]
            emergency = (
                len(old_items) > cls._WM_SECTION_BULLET_THRESHOLD * 2
                or est_tokens > cls._WM_SECTION_TOKEN_THRESHOLD * 2
            )
            if emergency:
                sentinel = cls._WM_CONSOLIDATION_SENTINEL
                if sentinel.lower() in old_lower:
                    _wm_debug(
                        f"guard: Key Facts APPEND blocked (emergency, "
                        f"sentinel already present): "
                        f"bullets={len(old_items)} est_tok={est_tokens} — "
                        f"dropped {len(fresh)} new item(s)"
                    )
                    return {"op": "KEEP"}
                _wm_debug(
                    f"guard: Key Facts APPEND blocked (emergency, "
                    f"inserting sentinel): "
                    f"bullets={len(old_items)} est_tok={est_tokens} — "
                    f"dropped {len(fresh)} new item(s)"
                )
                return {"op": "APPEND", "items": [sentinel]}
            cap = cls._WM_OVERSIZED_APPEND_CAP
            accepted = fresh[:cap]
            _wm_debug(
                f"guard: Key Facts APPEND throttled (oversized): "
                f"bullets={len(old_items)} est_tok={est_tokens} — "
                f"input={len(append_items)} deduped={len(fresh)} "
                f"accepted={len(accepted)} (cap={cap})"
            )
            if not accepted:
                return {"op": "KEEP"}
            return {"op": "APPEND", "items": accepted}
        if op_name != "UPDATE":
            return {"op": "KEEP"}

        new_content = (op.get("content") or "").strip()
        old_items = cls.extract_bullet_items(old_content or "")
        new_items = cls.extract_bullet_items(new_content)

        if not old_items:
            return op

        est_tokens = estimate_text_tokens(old_content or "")
        is_emergency = (
            len(old_items) > cls._WM_SECTION_BULLET_THRESHOLD * 2
            or est_tokens > cls._WM_SECTION_TOKEN_THRESHOLD * 2
        )

        # Layer 1
        ratio = len(new_items) / len(old_items) if old_items else 1.0
        if ratio < cls._WM_KEY_FACTS_MIN_BULLET_RATIO:
            _wm_debug(
                f"guard: Key Facts consolidation REJECTED (layer1): "
                f"new={len(new_items)} / old={len(old_items)} = "
                f"{ratio:.2%} < {cls._WM_KEY_FACTS_MIN_BULLET_RATIO:.0%}"
            )
            salvaged = cls.salvage_new_items_from_rejected_update(new_content, old_content)
            if is_emergency and salvaged.get("op") == "APPEND":
                _wm_debug("guard: suppressing salvage APPEND (emergency level)")
                return {"op": "KEEP"}
            return salvaged

        # Layer 2
        old_anchors = cls.extract_lexical_anchors(old_content or "")
        if old_anchors:
            new_anchors = cls.extract_lexical_anchors(new_content)
            covered = len(old_anchors & new_anchors)
            coverage = covered / len(old_anchors)
            if coverage < cls._WM_KEY_FACTS_MIN_ANCHOR_COVERAGE:
                _wm_debug(
                    f"guard: Key Facts consolidation REJECTED (layer2): "
                    f"anchor coverage={coverage:.2%} "
                    f"({covered}/{len(old_anchors)}) < "
                    f"{cls._WM_KEY_FACTS_MIN_ANCHOR_COVERAGE:.0%}"
                )
                salvaged = cls.salvage_new_items_from_rejected_update(new_content, old_content)
                if is_emergency and salvaged.get("op") == "APPEND":
                    _wm_debug("guard: suppressing salvage APPEND (emergency level)")
                    return {"op": "KEEP"}
                return salvaged
            _wm_debug(
                f"guard: Key Facts consolidation ACCEPTED: "
                f"bullets {len(old_items)}->{len(new_items)} "
                f"({ratio:.1%}), "
                f"anchors={coverage:.1%} ({covered}/{len(old_anchors)})"
            )
        else:
            _wm_debug(
                f"guard: Key Facts consolidation ACCEPTED (no old anchors): "
                f"bullets {len(old_items)}->{len(new_items)}"
            )

        return op

    @classmethod
    def enforce_files_no_regression(cls, op: Any, old_content: str) -> Dict[str, Any]:
        """Guard: don't let a 'Files & Context' UPDATE drop file paths."""
        if not isinstance(op, dict):
            return {"op": "KEEP"}
        op_name = (op.get("op") or "").upper()
        if op_name != "UPDATE":
            return op

        new_content = (op.get("content") or "").strip()
        old_paths = set(cls._WM_PATH_LIKE_RE.findall(old_content or ""))
        new_paths = set(cls._WM_PATH_LIKE_RE.findall(new_content))
        missing = {p for p in old_paths if p not in new_paths}
        if not missing:
            return op

        added_paths = new_paths - old_paths
        _wm_debug(
            f"guard: 'Files & Context' UPDATE drops {len(missing)} paths "
            f"{sorted(missing)[:5]}; forcing KEEP (+ APPEND new paths="
            f"{len(added_paths)})"
        )
        if added_paths:
            new_items: List[str] = []
            for path in sorted(added_paths):
                for line in new_content.splitlines():
                    if path in line:
                        new_items.append(line.strip().lstrip("-*").strip())
                        break
                else:
                    new_items.append(f"{path} (newly referenced)")
            return {"op": "APPEND", "items": new_items}
        return {"op": "KEEP"}

    @classmethod
    def enforce_title_stability(cls, op: Any, old_content: str) -> Dict[str, Any]:
        """Guard: reject Session Title UPDATE when it drifts too far."""
        if not isinstance(op, dict):
            return {"op": "KEEP"}
        op_name = (op.get("op") or "").upper()
        if op_name != "UPDATE":
            return op

        new_content = (op.get("content") or "").strip()

        def meaningful_words(text: str) -> set:
            tokens = re.findall(r"[A-Za-z][A-Za-z0-9\.]{2,}|[\d\.]+", text or "")
            return {t.lower() for t in tokens if t.lower() not in cls._WM_TITLE_STOPWORDS}

        old_w = meaningful_words(old_content)
        new_w = meaningful_words(new_content)

        if not old_w:
            return op
        if len(old_w & new_w) >= 1:
            return op
        _wm_debug(
            f"guard: Session Title drift rejected "
            f"(old={old_content[:80]!r}, new={new_content[:80]!r}); KEEP"
        )
        return {"op": "KEEP"}

    @classmethod
    def enforce_open_issues_resolved(cls, op: Any, old_content: str) -> Dict[str, Any]:
        """Guard: don't let an Open Issues UPDATE silently drop items."""
        if not isinstance(op, dict):
            return op
        op_name = (op.get("op") or "").upper()
        if op_name != "UPDATE":
            return op

        new_content = (op.get("content") or "").strip()
        new_lower = new_content.lower()
        old_items = cls.extract_bullet_items(old_content or "")
        dropped: List[str] = []
        for it in old_items:
            if "[silently dropped, restored]" in it:
                continue
            snippet = it[:40].lower().strip("_* `").strip()
            if snippet and snippet not in new_lower:
                dropped.append(it)
        if not dropped:
            return op

        _wm_debug(
            f"guard: Open Issues UPDATE silently dropped {len(dropped)} "
            f"items; restoring once (will not restore again if re-dropped)"
        )
        restored = "\n".join(f"- [silently dropped, restored] {it}" for it in dropped)
        merged = (new_content + ("\n" if new_content else "") + restored).strip()
        return {"op": "UPDATE", "content": merged}

    @classmethod
    def merge_wm_sections(cls, old_wm: str, ops: Dict[str, Any]) -> str:
        """Merge LLM per-section ops into a new Working Memory document."""
        _wm_debug(
            f"_merge_wm_sections entry old_wm={len(old_wm or '')}B "
            f"sections={list((ops or {}).keys())[:7]}"
        )
        old_sections = cls.parse_wm_sections(old_wm)

        parts: List[str] = ["# Working Memory", ""]
        for header in WM_SEVEN_SECTIONS:
            full_header = f"## {header}"
            op = (ops or {}).get(header)
            old_content = old_sections.get(full_header, "").rstrip()

            # ---------- per-section guards ----------
            if old_content:
                if header == "Session Title":
                    op = cls.enforce_title_stability(op, old_content)
                elif header == "Key Facts & Decisions":
                    op = cls.enforce_key_facts_consolidation(op, old_content)
                elif header in cls._WM_APPEND_ONLY_SECTIONS:
                    op = cls.enforce_append_only(header, op, old_content)
                elif header == "Files & Context":
                    op = cls.enforce_files_no_regression(op, old_content)
                elif header == "Open Issues":
                    op = cls.enforce_open_issues_resolved(op, old_content)
            # ----------------------------------------

            if op is None:
                new_content = old_content
            else:
                op_name = (op.get("op") or "").upper() if isinstance(op, dict) else ""
                if op_name == "KEEP":
                    new_content = old_content
                elif op_name == "UPDATE":
                    new_content = (op.get("content") or "").strip()
                elif op_name == "APPEND":
                    items = op.get("items") or []
                    bad_items = [s for s in items if not isinstance(s, str)]
                    if bad_items:
                        logger.warning(
                            "wm_v2: dropped %d non-string APPEND item(s) in section %r: %s",
                            len(bad_items),
                            header,
                            [type(s).__name__ for s in bad_items],
                        )
                    appended = "\n".join(
                        f"- {s.strip()}" for s in items if isinstance(s, str) and s.strip()
                    )
                    if old_content and appended:
                        new_content = f"{old_content}\n{appended}"
                    else:
                        new_content = old_content or appended
                else:
                    logger.warning(
                        "WM update: unknown op %r for section %r; keeping old content",
                        op,
                        header,
                    )
                    new_content = old_content

            parts.append(full_header)
            if new_content:
                parts.append(new_content)
            parts.append("")

        return "\n".join(parts).rstrip() + "\n"
