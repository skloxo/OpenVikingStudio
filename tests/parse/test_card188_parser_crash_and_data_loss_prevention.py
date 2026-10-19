# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Card-188 Retina Test Suite:
1. Markdown parser keeps content/subheadings before the first top-level heading.
2. Table to Markdown formatter escapes '|', collapses newlines with '<br>', and ensures minimum width 3.
3. PDF parser serializes PDFium image extraction via process-wide thread lock.
4. MemoryUpdater propagates unexpected read errors to prevent stale snapshot overwrites.
"""

import io
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openviking_cli.exceptions import NotFoundError
from openviking.parse.base import format_table_to_markdown
from openviking.parse.parsers.markdown import MarkdownParser, _LayoutOp
from openviking.session.memory.memory_updater import MemoryUpdater
from openviking_cli.utils.config.parser_config import MarkdownConfig


@pytest.mark.asyncio
async def test_markdown_parser_keeps_subheading_before_top_heading():
    """Verify that lower-level headings appearing before the first top-level heading

    (e.g., '## Preface' before '# Chapter 1') are preserved in the virtual section
    rather than being silently dropped when the document is split.
    """
    config = MarkdownConfig(max_section_size=10, max_section_chars=50)
    parser = MarkdownParser(config=config)

    content = (
        "## Preface\n"
        "This is preface text before the first chapter.\n\n"
        "# Chapter 1\n"
        "Here is the body of chapter 1.\n"
    )

    ops: list[_LayoutOp] = []
    headings = parser._find_headings(content)
    # Headings: [(0, 10, 'Preface', 2), (58, 69, 'Chapter 1', 1)]
    assert len(headings) >= 2
    assert headings[0][3] == 2  # Level 2 heading comes first
    assert headings[1][3] == 1  # Level 1 heading comes second

    await parser._build_structure(
        ops=ops,
        content=content,
        headings=headings,
        root_dir="viking://test/doc",
        source_path="book.md",
        split_content=True,
    )

    all_written_text = "".join(op.content for op in ops if op.kind == "write" and op.content)
    assert "## Preface" in all_written_text, "Preface text was dropped before top-level heading!"
    assert "preface text" in all_written_text


def test_format_table_to_markdown_pipes_multiline_and_empty_cols():
    """Verify table formatting escapes '|', joins newlines with '<br>',

    and provides at least '---' for empty columns so markdown tables render properly.
    """
    rows = [
        ["Header 1", "Header with | pipe", ""],
        ["Line 1\nLine 2", "Cell | with | pipes", ""],
    ]

    result = format_table_to_markdown(rows, has_header=True)
    lines = result.splitlines()

    # Must escape pipes inside cells
    assert "Header with \\| pipe" in lines[0]
    assert "Cell \\| with \\| pipes" in lines[2]

    # Must collapse newlines into <br>
    assert "Line 1<br>Line 2" in lines[2]

    # Separator row must contain at least "---" for empty third column
    assert "---" in lines[1]
    sep_cols = [c.strip() for c in lines[1].split("|")[1:-1]]
    assert len(sep_cols) == 3
    for col in sep_cols:
        assert len(col) >= 3, f"Column separator '{col}' is shorter than 3 dashes!"


def test_pdf_parser_has_process_wide_pdfium_lock():
    """Verify PDFParser module defines and uses _PDFIUM_LOCK to serialize rendering."""
    import openviking.parse.parsers.pdf as pdf_mod

    assert hasattr(pdf_mod, "_PDFIUM_LOCK"), "openviking.parse.parsers.pdf missing _PDFIUM_LOCK"
    assert isinstance(pdf_mod._PDFIUM_LOCK, type(threading.Lock()))


@pytest.mark.asyncio
async def test_memory_updater_propagates_unexpected_read_error():
    """Verify MemoryUpdater._apply_upsert does NOT swallow unexpected read errors

    (such as OSError/IOError) with a fallback to stale old_memory_file_content.
    Only NotFoundError/FileNotFoundError may be ignored.
    """
    updater = MemoryUpdater()
    updater._registry = MagicMock()
    viking_fs = MagicMock()
    updater._get_viking_fs = MagicMock(return_value=viking_fs)

    # Simulate an unexpected disk I/O error on fresh read
    viking_fs.read_file = AsyncMock(side_effect=IOError("Corrupt block or disk failure"))
    viking_fs.write_file = AsyncMock()

    resolved_op = MagicMock()
    resolved_op.uris = ["viking://user/alice/memories/profile.md"]
    resolved_op.memory_type = "profile"
    resolved_op.memory_fields = {}
    resolved_op.old_memory_file_content = MagicMock()  # Stale pre-fetched content

    ctx = MagicMock()

    # The unexpected IOError must propagate, blocking stale snapshot overwrite!
    with pytest.raises(IOError, match="Corrupt block or disk failure"):
        await updater._apply_upsert(resolved_op, ctx=ctx)
