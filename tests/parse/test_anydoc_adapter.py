import io
import zipfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from openviking.parse.parsers.base_parser import BaseParser
from openviking.parse.parsers.anydoc_adapter import (
    AnyDocAdapter,
    AnyDocAdaptedContent,
)
from openviking.parse.parsers.anydoc import AnyDocParser
from openviking_cli.utils.config.parser_config import AnydocConfig, ParserConfig


class FakeVikingFS:
    def __init__(self):
        self.files = {}
        self._temp_counter = 0

    async def mkdir(self, uri, exist_ok=False, **kw):
        pass

    async def write(self, uri, data):
        self.files[uri] = data

    async def write_file(self, uri, content, **kw):
        self.files[uri] = content

    async def glob(self, pattern, uri="", **kw):
        return {"matches": []}

    def create_temp_uri(self):
        self._temp_counter += 1
        return f"viking://temp/fake_{self._temp_counter}"


@pytest.fixture(autouse=True)
def mock_viking_fs(monkeypatch):
    fake_fs = FakeVikingFS()
    monkeypatch.setattr(BaseParser, "_get_viking_fs", lambda self: fake_fs)
    return fake_fs


def _create_mock_docx(text: str = "Test Heading\nSample paragraph in docx.") -> bytes:
    """Create a minimal valid docx in-memory zip."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        xml_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Header1</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Header2</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Val1</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Val2</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
  </w:body>
</w:document>"""
        zf.writestr("word/document.xml", xml_content.encode("utf-8"))
    return buf.getvalue()


def _create_mock_xlsx() -> bytes:
    """Create a minimal valid xlsx in-memory zip."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        shared_strings = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="4" uniqueCount="4">
  <si><t>Item</t></si>
  <si><t>Price</t></si>
  <si><t>Apple</t></si>
  <si><t>10</t></si>
</sst>"""
        sheet = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">
      <c r="A1" t="s"><v>0</v></c>
      <c r="B1" t="s"><v>1</v></c>
    </row>
    <row r="2">
      <c r="A2" t="s"><v>2</v></c>
      <c r="B2" t="s"><v>3</v></c>
    </row>
  </sheetData>
</worksheet>"""
        zf.writestr("xl/sharedStrings.xml", shared_strings.encode("utf-8"))
        zf.writestr("xl/worksheets/sheet1.xml", sheet.encode("utf-8"))
    return buf.getvalue()


def test_is_engine_available():
    adapter = AnyDocAdapter()
    assert isinstance(adapter.is_engine_available(), bool)


@pytest.mark.asyncio
async def test_adapter_fallback_csv(tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("Name,Age,Role\nAlice,30,Engineer\nBob,25,Designer", encoding="utf-8")

    adapter = AnyDocAdapter(AnydocConfig(enabled=False))
    result = await adapter.parse_file(csv_file)

    assert isinstance(result, AnyDocAdaptedContent)
    assert "| Name | Age | Role |" in result.markdown
    assert "| Alice | 30 | Engineer |" in result.markdown
    assert result.source_format == "csv"
    assert result.is_fallback is True
    assert result.extracted_tables >= 1


@pytest.mark.asyncio
async def test_adapter_fallback_docx(tmp_path):
    docx_file = tmp_path / "sample.docx"
    docx_file.write_bytes(_create_mock_docx("Overview Document"))

    adapter = AnyDocAdapter(AnydocConfig(enabled=False))
    result = await adapter.parse_file(docx_file)

    assert isinstance(result, AnyDocAdaptedContent)
    assert "Overview Document" in result.markdown
    assert "| Header1 | Header2 |" in result.markdown
    assert result.source_format == "docx"
    assert result.is_fallback is True
    assert result.extracted_tables >= 1


@pytest.mark.asyncio
async def test_adapter_fallback_xlsx(tmp_path):
    xlsx_file = tmp_path / "table.xlsx"
    xlsx_file.write_bytes(_create_mock_xlsx())

    adapter = AnyDocAdapter(AnydocConfig(enabled=False))
    result = await adapter.parse_file(xlsx_file)

    assert isinstance(result, AnyDocAdaptedContent)
    assert "| Item | Price |" in result.markdown
    assert "| Apple | 10 |" in result.markdown
    assert result.source_format == "xlsx"
    assert result.is_fallback is True


@pytest.mark.asyncio
async def test_adapter_fallback_corrupted_file(tmp_path):
    bad_file = tmp_path / "broken.docx"
    bad_file.write_bytes(b"\x00\x01\x02CORRUPTED_BIN_DATA\x03\x04")

    adapter = AnyDocAdapter(AnydocConfig(enabled=False))
    # Must NOT raise unhandled exception! Must fail-open safely
    result = await adapter.parse_file(bad_file)

    assert isinstance(result, AnyDocAdaptedContent)
    assert result.is_fallback is True
    assert len(result.warnings) > 0
    assert result.source_format == "docx"


@pytest.mark.asyncio
async def test_anydoc_parser_integration(tmp_path):
    docx_file = tmp_path / "doc.docx"
    docx_file.write_bytes(_create_mock_docx("Integration Test Document"))

    parser = AnyDocParser(anydoc_config=AnydocConfig(enabled=False))
    result = await parser.parse(docx_file)

    assert result.parser_name == "AnyDocParser"
    assert result.source_format == "docx"
    assert result.meta.get("fail_open_fallback") is True
    nodes = result.get_all_nodes()
    assert len(nodes) > 0


@pytest.mark.asyncio
async def test_anydoc_parser_disabled_fail_open(tmp_path):
    csv_file = tmp_path / "report.csv"
    csv_file.write_text("Year,Revenue\n2025,100M\n2026,200M", encoding="utf-8")

    # Previously this raised RuntimeError("AnyDoc parser is disabled...")
    parser = AnyDocParser(anydoc_config=AnydocConfig(enabled=False))
    result = await parser.parse(csv_file)

    assert result.parser_name == "AnyDocParser"
    assert result.source_format == "csv"
    assert any("AnyDoc parser is disabled" in w for w in result.warnings)
    assert len(result.get_all_nodes()) > 0


@pytest.mark.asyncio
async def test_adapter_preserves_images_and_assets(tmp_path):
    docx_file = tmp_path / "media.docx"
    docx_file.write_bytes(_create_mock_docx("With Assets"))

    adapter = AnyDocAdapter()
    with patch.object(adapter, "_parse_with_engine") as mock_engine:
        mock_engine.return_value = AnyDocAdaptedContent(
            markdown="# Document\n![img](media/img1.png)",
            source_format="docx",
            images_saved=3,
            assets_referenced=5,
            warnings=["Mocked image warning"],
        )
        result = await adapter.parse_file(docx_file)
        assert result.images_saved == 3
        assert result.assets_referenced == 5
        assert "Mocked image warning" in result.warnings
