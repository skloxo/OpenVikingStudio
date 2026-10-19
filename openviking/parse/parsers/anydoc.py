# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unified AnyDoc parser for Office documents and EPUB files."""

import asyncio
import time
from pathlib import Path
from typing import List, Optional, Union

from openviking.parse.base import ParseResult
from openviking.parse.parsers.base_parser import BaseParser
from openviking_cli.utils.config.parser_config import AnydocConfig, ParserConfig

_SUPPORTED_EXTENSIONS = [
    ".doc",
    ".docx",
    ".docm",
    ".odt",
    ".rtf",
    ".pptx",
    ".ppt",
    ".pptm",
    ".pps",
    ".ppsx",
    ".ppsm",
    ".pot",
    ".odp",
    ".xlsx",
    ".xls",
    ".xlsm",
    ".xlsb",
    ".ods",
    ".csv",
    ".epub",
]


class AnyDocParser(BaseParser):
    """Parse Office and EPUB files through AnyDoc."""

    def __init__(
        self,
        config: Optional[ParserConfig] = None,
        anydoc_config: Optional[AnydocConfig] = None,
    ):
        from openviking.parse.parsers.markdown import MarkdownParser

        self.config = config or ParserConfig()
        self.anydoc_config = anydoc_config or AnydocConfig()
        self._md_parser = MarkdownParser(config=self.config)

    @property
    def supported_extensions(self) -> List[str]:
        return list(_SUPPORTED_EXTENSIONS)

    async def parse(self, source: Union[str, Path], instruction: str = "", **kwargs) -> ParseResult:
        started = time.time()
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"Document file not found: {path}")

        from openviking.parse.parsers.anydoc_adapter import AnyDocAdapter
        from openviking_cli.utils.storage import get_storage

        storage = get_storage()
        resource_name = kwargs.get("resource_name") or kwargs.get("source_name") or path.stem
        adapter = AnyDocAdapter(self.anydoc_config)
        conversion = await adapter.parse_file(
            path,
            resource_name=resource_name,
            storage=storage,
            max_table_rows=self.anydoc_config.max_table_rows,
        )

        markdown_kwargs = dict(kwargs)
        allowed_media_dirs = list(markdown_kwargs.get("allowed_media_dirs") or [])
        if storage.media_dir not in allowed_media_dirs:
            allowed_media_dirs.append(storage.media_dir)
        markdown_kwargs.update(
            source_path=str(path),
            base_dir=path.parent,
            allowed_media_dirs=allowed_media_dirs,
        )
        result = await self._md_parser.parse_content(
            conversion.markdown,
            instruction=instruction,
            **markdown_kwargs,
        )
        result.source_format = conversion.source_format or path.suffix.lstrip(".").lower()
        result.parser_name = "AnyDocParser"
        result.parser_version = "1.0"
        result.parse_time = time.time() - started
        result.meta.update(
            {
                "converter": "anydoc-adapter",
                "intermediate_markdown_length": len(conversion.markdown),
                "images_extracted": conversion.images_saved,
                "assets_referenced": getattr(conversion, "assets_referenced", 0),
                "fail_open_fallback": conversion.is_fallback,
                "fallback_reason": conversion.fallback_reason,
                "extracted_tables": conversion.extracted_tables,
            }
        )
        if not self.anydoc_config.enabled:
            result.warnings.append("AnyDoc parser is disabled; fell back to Fail-Open adapter")
        result.warnings.extend(getattr(conversion, "warnings", ()))
        return result

    async def parse_content(
        self,
        content: str,
        source_path: Optional[str] = None,
        instruction: str = "",
        **kwargs,
    ) -> ParseResult:
        result = await self._md_parser.parse_content(
            content,
            source_path=source_path,
            instruction=instruction,
            **kwargs,
        )
        suffix = Path(source_path).suffix.lstrip(".").lower() if source_path else ""
        result.source_format = suffix or "anydoc"
        result.parser_name = "AnyDocParser"
        result.parser_version = "1.0"
        return result
