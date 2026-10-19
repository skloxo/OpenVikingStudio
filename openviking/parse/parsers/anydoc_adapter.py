# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Dedicated AnyDoc adapter with universal Office extraction and robust Fail-Open fallback."""

from __future__ import annotations

import asyncio
import csv
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

from openviking_cli.utils.config.parser_config import AnydocConfig
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AnyDocAdaptedContent:
    markdown: str
    source_format: str
    images_saved: int = 0
    assets_referenced: int = 0
    warnings: list[str] = field(default_factory=list)
    is_fallback: bool = False
    fallback_reason: Optional[str] = None
    extracted_tables: int = 0


def is_anydoc_installed() -> bool:
    """Check if the native anydoc library is importable."""
    try:
        import anydoc  # type: ignore # noqa: F401
        return True
    except (ImportError, ModuleNotFoundError):
        return False
    except Exception as exc:
        logger.debug(f"[AnyDocAdapter] Native anydoc probe error: {exc}")
        return False


class AnyDocAdapter:
    """Dedicated adapter for AnyDoc document extraction with Fail-Open fallback."""

    def __init__(self, anydoc_config: Optional[AnydocConfig] = None):
        self.anydoc_config = anydoc_config or AnydocConfig()

    def is_engine_available(self) -> bool:
        return is_anydoc_installed()

    async def parse_file(
        self,
        path: Union[str, Path],
        resource_name: Optional[str] = None,
        storage: Any = None,
        max_table_rows: int = 1000,
    ) -> AnyDocAdaptedContent:
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"Document file not found: {path}")

        name = resource_name or path.stem

        if self.anydoc_config.enabled and self.is_engine_available():
            try:
                return await asyncio.to_thread(
                    self._parse_with_engine,
                    path,
                    resource_name=name,
                    storage=storage,
                    max_table_rows=max_table_rows,
                )
            except Exception as exc:
                reason = f"Native AnyDoc parsing failed: {exc}"
                logger.warning(f"[AnyDocAdapter] {reason}; falling back to Fail-Open parser.")
                return self._fallback_parse(path, reason=reason)

        reason = (
            "AnyDoc parser is disabled"
            if not self.anydoc_config.enabled
            else "Native anydoc library is not installed"
        )
        return self._fallback_parse(path, reason=reason)

    def _parse_with_engine(
        self,
        path: Path,
        resource_name: str,
        storage: Any,
        max_table_rows: int,
    ) -> AnyDocAdaptedContent:
        from openviking.parse.parsers.anydoc_converter import AnyDocConverter
        from openviking_cli.utils.storage import get_storage

        conv_storage = storage or get_storage()
        conversion = AnyDocConverter().convert(
            path,
            resource_name=resource_name,
            storage=conv_storage,
            max_table_rows=max_table_rows,
        )
        return AnyDocAdaptedContent(
            markdown=conversion.markdown,
            source_format=conversion.source_format,
            images_saved=conversion.images_saved,
            assets_referenced=getattr(conversion, "assets_referenced", 0),
            warnings=list(getattr(conversion, "warnings", ())),
            is_fallback=False,
        )

    def _fallback_parse(self, path: Path, reason: str) -> AnyDocAdaptedContent:
        ext = path.suffix.lstrip(".").lower() or "unknown"
        warnings = [f"Fail-Open fallback activated: {reason}"]

        try:
            if ext == "csv":
                return self._parse_csv_fallback(path, ext, warnings, reason)
            elif ext in {"docx", "docm", "odt"}:
                return self._parse_docx_fallback(path, ext, warnings, reason)
            elif ext in {"xlsx", "xlsm", "xlsb", "ods"}:
                return self._parse_xlsx_fallback(path, ext, warnings, reason)
            elif ext in {"pptx", "pptm", "pot", "odp"}:
                return self._parse_pptx_fallback(path, ext, warnings, reason)
            else:
                return self._parse_raw_text_fallback(path, ext, warnings, reason)
        except Exception as exc:
            logger.warning(f"[AnyDocAdapter] Secondary fallback error on {path}: {exc}")
            warnings.append(f"Secondary fallback error: {exc}")
            return self._parse_raw_text_fallback(path, ext, warnings, reason)

    def _parse_csv_fallback(
        self, path: Path, ext: str, warnings: list[str], reason: str
    ) -> AnyDocAdaptedContent:
        content = path.read_text(encoding="utf-8", errors="replace")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            return AnyDocAdaptedContent(
                markdown="", source_format=ext, warnings=warnings, is_fallback=True, fallback_reason=reason
            )

        header = rows[0]
        md_lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * len(header)) + " |",
        ]
        for row in rows[1:]:
            padded = row + [""] * (len(header) - len(row))
            md_lines.append("| " + " | ".join(padded[: len(header)]) + " |")

        return AnyDocAdaptedContent(
            markdown="\n".join(md_lines) + "\n",
            source_format=ext,
            warnings=warnings,
            is_fallback=True,
            fallback_reason=reason,
            extracted_tables=1,
        )

    def _parse_docx_fallback(
        self, path: Path, ext: str, warnings: list[str], reason: str
    ) -> AnyDocAdaptedContent:
        lines: list[str] = []
        table_count = 0
        with zipfile.ZipFile(path, "r") as zf:
            xml_names = [n for n in zf.namelist() if n.endswith("document.xml")]
            for name in xml_names:
                root = ET.fromstring(zf.read(name))
                for child in root.iter():
                    tag = child.tag.split("}")[-1]
                    if tag == "p":
                        text = "".join(child.itertext()).strip()
                        if text:
                            lines.append(text + "\n")
                    elif tag == "tbl":
                        table_count += 1
                        tbl_rows: list[list[str]] = []
                        for tr in child.findall("{*}tr"):
                            row_vals = [
                                "".join(tc.itertext()).strip() for tc in tr.findall("{*}tc")
                            ]
                            tbl_rows.append(row_vals)
                        if tbl_rows:
                            col_count = max(len(r) for r in tbl_rows)
                            hdr = tbl_rows[0] + [""] * (col_count - len(tbl_rows[0]))
                            lines.append("| " + " | ".join(hdr) + " |")
                            lines.append("| " + " | ".join(["---"] * col_count) + " |")
                            for r in tbl_rows[1:]:
                                padded = r + [""] * (col_count - len(r))
                                lines.append("| " + " | ".join(padded) + " |")
                            lines.append("")

        return AnyDocAdaptedContent(
            markdown="\n".join(lines).strip() + "\n",
            source_format=ext,
            warnings=warnings,
            is_fallback=True,
            fallback_reason=reason,
            extracted_tables=table_count,
        )

    def _parse_xlsx_fallback(
        self, path: Path, ext: str, warnings: list[str], reason: str
    ) -> AnyDocAdaptedContent:
        shared_strings: list[str] = []
        md_lines: list[str] = []
        with zipfile.ZipFile(path, "r") as zf:
            if "xl/sharedStrings.xml" in zf.namelist():
                root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                for si in [el for el in root.iter() if el.tag.split("}")[-1] == "si"]:
                    shared_strings.append("".join(si.itertext()))

            sheet_names = sorted(
                [n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
            )
            for sname in sheet_names:
                root = ET.fromstring(zf.read(sname))
                rows: list[list[str]] = []
                for row_el in [el for el in root.iter() if el.tag.split("}")[-1] == "row"]:
                    row_data: list[str] = []
                    for c in [el for el in row_el.iter() if el.tag.split("}")[-1] == "c"]:
                        cell_type = c.attrib.get("t")
                        v_el = next((el for el in c.iter() if el.tag.split("}")[-1] == "v"), None)
                        val = v_el.text if v_el is not None and v_el.text else ""
                        if cell_type == "s" and val.isdigit():
                            idx = int(val)
                            val = shared_strings[idx] if idx < len(shared_strings) else val
                        row_data.append(val)
                    if row_data:
                        rows.append(row_data)

                if rows:
                    col_count = max(len(r) for r in rows)
                    hdr = rows[0] + [""] * (col_count - len(rows[0]))
                    md_lines.append("| " + " | ".join(hdr) + " |")
                    md_lines.append("| " + " | ".join(["---"] * col_count) + " |")
                    for r in rows[1:]:
                        padded = r + [""] * (col_count - len(r))
                        md_lines.append("| " + " | ".join(padded) + " |")
                    md_lines.append("")

        return AnyDocAdaptedContent(
            markdown="\n".join(md_lines).strip() + "\n",
            source_format=ext,
            warnings=warnings,
            is_fallback=True,
            fallback_reason=reason,
            extracted_tables=1 if md_lines else 0,
        )

    def _parse_pptx_fallback(
        self, path: Path, ext: str, warnings: list[str], reason: str
    ) -> AnyDocAdaptedContent:
        lines: list[str] = []
        with zipfile.ZipFile(path, "r") as zf:
            slide_names = sorted(
                [n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
            )
            for idx, sname in enumerate(slide_names, start=1):
                root = ET.fromstring(zf.read(sname))
                slide_texts = [
                    "".join(el.itertext()).strip()
                    for el in root.iter()
                    if el.tag.endswith("}p") and "".join(el.itertext()).strip()
                ]
                if slide_texts:
                    lines.append(f"## Slide {idx}\n")
                    lines.extend(slide_texts)
                    lines.append("")

        return AnyDocAdaptedContent(
            markdown="\n".join(lines).strip() + "\n",
            source_format=ext,
            warnings=warnings,
            is_fallback=True,
            fallback_reason=reason,
        )

    def _parse_raw_text_fallback(
        self, path: Path, ext: str, warnings: list[str], reason: str
    ) -> AnyDocAdaptedContent:
        try:
            raw_text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            raw_text = path.read_bytes().decode("latin1", errors="replace")

        # Extract printable sequences to avoid binary garbage
        clean_text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", raw_text)
        return AnyDocAdaptedContent(
            markdown=f"```text\n{clean_text[:4000]}\n```" if ext not in {"txt", "md"} else clean_text,
            source_format=ext,
            warnings=warnings,
            is_fallback=True,
            fallback_reason=reason,
        )
