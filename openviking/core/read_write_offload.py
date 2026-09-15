# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Read/Write Dual-Sided Offload and Anti-Lazy Code Guard (Card-Harness-ReadWriteOffload-HookGuard - v1.5.05)

Absorbed from Tencent DECO Data Warehouse Agent Guardrails:
1. Write Guard (AntiLazyCodeGuard):
   Intercepts tool write payloads, scanning for lazy code omissions (e.g. '/* 省略若干行 */',
   '# ... rest of code unchanged ...', '// ... existing code ...').
   Physically blocks partial or truncated code overwrite to prevent silent codebase damage.
2. Read Guard (ReadOffloadManager):
   Intercepts large read outputs (> 300 lines or > 12KB).
   Offloads full text into cache and issues a lightweight FileRefHandle with head/tail snippets,
   reducing prompt token load by up to 90% and protecting LLM working memory.
"""

from dataclasses import dataclass, field
import hashlib
import logging
import re
import time
from typing import Any, Dict, List, Optional

from openviking.core.hook_aspects import AspectContext, AspectDecision, HookAspect

logger = logging.getLogger(__name__)

# Precompiled regex patterns for lazy omission detection across languages
LAZY_CODE_PATTERNS = [
    re.compile(r"/\*[\s\S]*?(?:省略|unchanged|existing|remain|rest of|同上)[\s\S]*?\*/", re.IGNORECASE),
    re.compile(r"//[^\n]*(?:省略|unchanged|existing|remain|rest of|同上|keep as is|TODO|FIXME)", re.IGNORECASE),
    re.compile(r"#[^\n]*(?:省略|unchanged|existing|remain|rest of|同上|keep as is|TODO|FIXME)", re.IGNORECASE),
    re.compile(r"<!--[\s\S]*?(?:省略|unchanged|existing|remain)[\s\S]*?-->", re.IGNORECASE),
    re.compile(r"\.\.\.\s*(?:rest of code|existing code|keep unchanged|省略若干行|同上)", re.IGNORECASE),
    re.compile(r"/\*\s*\.\.\.\s*\*/"),
    re.compile(r"^\s*pass\s*(?:#.*)?$", re.MULTILINE),
    re.compile(r"^\s*\.\.\.\s*$", re.MULTILINE),
    re.compile(r"raise\s+NotImplementedError", re.IGNORECASE),
]


class LazyCodeOmissionError(ValueError):
    """Raised when a write action contains lazy omission placeholders."""
    pass


@dataclass
class FileRefHandle:
    """Strongly typed lightweight reference handle for offloaded large reads."""
    ref_id: str
    target_path: str
    total_lines: int
    total_bytes: int
    content_hash: str
    head_preview: str
    tail_preview: str
    notice: str = (
        "[DECO 读护栏提示] 原文过长已自动 Offload。模型请使用切片参数 (StartLine/EndLine) 精准阅读。"
    )

    def to_formatted_str(self) -> str:
        return (
            f"=== 📁 FileRefHandle ({self.ref_id}) ===\n"
            f"Target: {self.target_path} | Total Lines: {self.total_lines} | Size: {self.total_bytes}B\n"
            f"SHA256: {self.content_hash[:16]}...\n"
            f"{self.notice}\n"
            f"--- [Head Preview: Lines 1~{min(20, self.total_lines)}] ---\n{self.head_preview}\n"
            f"--- [Tail Preview: Last {min(15, self.total_lines)} Lines] ---\n{self.tail_preview}\n"
            f"=========================================="
        )


class AntiLazyCodeGuard(HookAspect):
    """
    Write-side guard: Inspects tool arguments before execution to catch and reject
    lazy omission placeholders in generated code.
    """

    name: str = "anti_lazy_code_guard"
    priority: int = 20  # High priority before actual execution

    def __init__(self, target_tools: Optional[List[str]] = None) -> None:
        self.target_tools = set(
            target_tools
            or [
                "write_to_file",
                "replace_file_content",
                "multi_replace_file_content",
                "create_file",
                "edit_file",
                "openviking_write",
            ]
        )

    def _extract_text_payloads(self, args: Dict[str, Any]) -> List[str]:
        """Extract all candidate code payloads from tool arguments."""
        payloads: List[str] = []
        for key in ["CodeContent", "code", "content", "ReplacementContent", "text"]:
            val = args.get(key)
            if isinstance(val, str):
                payloads.append(val)

        chunks = args.get("ReplacementChunks")
        if isinstance(chunks, list):
            for chunk in chunks:
                if isinstance(chunk, dict) and "ReplacementContent" in chunk:
                    payloads.append(str(chunk["ReplacementContent"]))

        return payloads

    def scan_for_lazy_omissions(self, text: str) -> Optional[str]:
        """Check if code text contains prohibited lazy omission patterns."""
        for pattern in LAZY_CODE_PATTERNS:
            match = pattern.search(text)
            if match:
                matched_snippet = match.group(0).strip()
                if len(matched_snippet) > 60:
                    matched_snippet = matched_snippet[:57] + "..."
                return matched_snippet
        return None

    def before_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        ctx: AspectContext,
    ) -> AspectDecision:
        if tool_name not in self.target_tools:
            return AspectDecision.allow()

        payloads = self._extract_text_payloads(args)
        for payload in payloads:
            matched = self.scan_for_lazy_omissions(payload)
            if matched:
                reason = (
                    f"检测到偷懒代码省略占位符 '{matched}'！"
                    f"根据腾讯 DECO 生产护栏规则，严禁向文件写入省略代码。请提供完整实现或精准增量 Patch。"
                )
                logger.error(f"[AntiLazyCodeGuard] Prohibited write blocked: {reason}")
                return AspectDecision.block(
                    reason=reason,
                    override_output=f"🚨 [物理阻断: 防偷懒省略护栏] {reason}",
                )

        return AspectDecision.allow()


class ReadOffloadManager(HookAspect):
    """
    Read-side guard: Intercepts oversized text outputs from read/view tools,
    caches the full payload in memory/sandbox, and returns a compact FileRefHandle.
    """

    name: str = "read_offload_manager"
    priority: int = 80

    def __init__(
        self,
        max_lines: int = 300,
        max_bytes: int = 12_000,
        target_tools: Optional[List[str]] = None,
    ) -> None:
        self.max_lines = max_lines
        self.max_bytes = max_bytes
        self.target_tools = set(
            target_tools or ["view_file", "read_file", "cat", "openviking_read"]
        )
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_cached_content(self, ref_id: str) -> Optional[str]:
        item = self._cache.get(ref_id)
        return item["content"] if item else None

    def slice_cached_content(self, ref_id: str, start_line: int, end_line: int) -> Optional[str]:
        content = self.get_cached_content(ref_id)
        if content is None:
            return None
        lines = content.splitlines()
        start = max(0, start_line - 1)
        end = min(len(lines), end_line)
        return "\n".join(lines[start:end])

    def after_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        output: Any,
        ctx: AspectContext,
    ) -> Any:
        if tool_name not in self.target_tools or not isinstance(output, str):
            return output

        lines = output.splitlines()
        total_lines = len(lines)
        total_bytes = len(output.encode("utf-8"))

        if total_lines <= self.max_lines and total_bytes <= self.max_bytes:
            return output

        # Offload trigger
        target_path = str(args.get("AbsolutePath", args.get("path", args.get("TargetFile", "unknown_file"))))
        content_hash = hashlib.sha256(output.encode("utf-8")).hexdigest()
        ref_id = f"ref_{content_hash[:8]}"

        self._cache[ref_id] = {
            "target_path": target_path,
            "content": output,
            "total_lines": total_lines,
            "total_bytes": total_bytes,
            "created_at": time.time(),
        }

        head_preview = "\n".join(lines[:20])
        tail_preview = "\n".join(lines[-15:])

        handle = FileRefHandle(
            ref_id=ref_id,
            target_path=target_path,
            total_lines=total_lines,
            total_bytes=total_bytes,
            content_hash=content_hash,
            head_preview=head_preview,
            tail_preview=tail_preview,
        )

        logger.info(
            f"[ReadOffloadManager] Offloaded {target_path} ({total_lines} lines, {total_bytes}B) -> {ref_id}"
        )
        return handle.to_formatted_str()
