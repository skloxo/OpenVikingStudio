"""
Unit tests for Feishu task status markdown conversion and CodeRepositoryParser/GitAccessor remote zip extraction.
"""

import io
import os
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openviking.parse.accessors.feishu_accessor import FeishuAccessor
from openviking.parse.accessors.git_accessor import GitAccessor
from openviking.parse.parsers.code.code import CodeRepositoryParser


class TestFeishuTaskStatusParsing:
    """Test Feishu task status parsing into checkbox markdown."""

    def setup_method(self):
        self.accessor = FeishuAccessor()

    def test_feishu_task_completed_via_style(self):
        """Task block with style.done=True should render as '- [x] text'."""
        block = SimpleNamespace(
            block_type=999,
            parent_id=None,
            task=SimpleNamespace(
                elements=[SimpleNamespace(text_run=SimpleNamespace(content="Deploy to production"))],
                style=SimpleNamespace(done=True),
            ),
        )
        res = self.accessor._block_to_markdown(block, block_map={}, ordered_counter={})
        assert res == "- [x] Deploy to production"

    def test_feishu_task_pending_via_style(self):
        """Task block with style.done=False should render as '- [ ] text'."""
        block = SimpleNamespace(
            block_type=999,
            parent_id=None,
            task=SimpleNamespace(
                elements=[SimpleNamespace(text_run=SimpleNamespace(content="Write unit tests"))],
                style=SimpleNamespace(done=False),
            ),
        )
        res = self.accessor._block_to_markdown(block, block_map={}, ordered_counter={})
        assert res == "- [ ] Write unit tests"

    def test_feishu_task_completed_via_task_completed(self):
        """Task block with task.completed=True should render as '- [x] text'."""
        block = SimpleNamespace(
            block_type=999,
            parent_id=None,
            task=SimpleNamespace(
                elements=[SimpleNamespace(text_run=SimpleNamespace(content="Refactor SQLite WAL"))],
                task=SimpleNamespace(completed=True),
            ),
        )
        res = self.accessor._block_to_markdown(block, block_map={}, ordered_counter={})
        assert res == "- [x] Refactor SQLite WAL"

    def test_feishu_task_completed_via_top_level_completed(self):
        """Task block with completed=True attribute should render as '- [x] text'."""
        block = SimpleNamespace(
            block_type=999,
            parent_id=None,
            task=SimpleNamespace(
                elements=[SimpleNamespace(text_run=SimpleNamespace(content="Benchmark LLMLingua-2"))],
                completed=True,
            ),
        )
        res = self.accessor._block_to_markdown(block, block_map={}, ordered_counter={})
        assert res == "- [x] Benchmark LLMLingua-2"

    def test_feishu_todo_status_parity(self):
        """Standard todo block should continue to parse correctly."""
        block_done = SimpleNamespace(
            block_type=17,
            parent_id=None,
            todo=SimpleNamespace(
                elements=[SimpleNamespace(text_run=SimpleNamespace(content="Done item"))],
                style=SimpleNamespace(done=True),
            ),
        )
        block_pending = SimpleNamespace(
            block_type=17,
            parent_id=None,
            todo=SimpleNamespace(
                elements=[SimpleNamespace(text_run=SimpleNamespace(content="Pending item"))],
                style=SimpleNamespace(done=False),
            ),
        )
        assert self.accessor._block_to_markdown(block_done, block_map={}, ordered_counter={}) == "- [x] Done item"
        assert self.accessor._block_to_markdown(block_pending, block_map={}, ordered_counter={}) == "- [ ] Pending item"


class TestCodeRepositoryParserZipDownload:
    """Test local and remote zip extraction in CodeRepositoryParser and GitAccessor."""

    @pytest.fixture
    def sample_zip(self, tmp_path: Path) -> Path:
        """Create a valid zip archive with code files."""
        zip_path = tmp_path / "my_project.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("main.py", "print('hello from main')\n")
            zf.writestr("utils/helper.py", "def help(): pass\n")
        return zip_path

    @pytest.mark.asyncio
    async def test_code_parser_extract_local_zip(self, sample_zip: Path, tmp_path: Path):
        """CodeRepositoryParser should extract local zip archive into target directory."""
        parser = CodeRepositoryParser()
        target_dir = tmp_path / "extracted"
        target_dir.mkdir(parents=True, exist_ok=True)

        repo_name = await parser._extract_zip(str(sample_zip), str(target_dir))
        assert repo_name == "my_project"
        assert (target_dir / "main.py").exists()
        assert (target_dir / "main.py").read_text() == "print('hello from main')\n"
        assert (target_dir / "utils" / "helper.py").exists()

    @pytest.mark.asyncio
    async def test_code_parser_extract_remote_zip(self, sample_zip: Path, tmp_path: Path):
        """CodeRepositoryParser should download remote zip over HTTP and extract cleanly."""
        parser = CodeRepositoryParser()
        target_dir = tmp_path / "remote_extracted"
        target_dir.mkdir(parents=True, exist_ok=True)

        zip_bytes = sample_zip.read_bytes()

        # Mock httpx AsyncClient
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = zip_bytes
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            repo_name = await parser._extract_zip("https://github.com/example/repo/archive/main.zip", str(target_dir))
            assert repo_name == "main"
            assert (target_dir / "main.py").exists()
            assert (target_dir / "main.py").read_text() == "print('hello from main')\n"

    @pytest.mark.asyncio
    async def test_git_accessor_extract_remote_zip(self, sample_zip: Path, tmp_path: Path):
        """GitAccessor should also download remote zip and extract properly."""
        accessor = GitAccessor()
        target_dir = tmp_path / "git_remote_extracted"
        target_dir.mkdir(parents=True, exist_ok=True)

        zip_bytes = sample_zip.read_bytes()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = zip_bytes
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            repo_name = await accessor._extract_zip("https://gitlab.com/group/repo/-/archive/v1.0.zip", str(target_dir))
            assert repo_name == "v1.0"
            assert (target_dir / "main.py").exists()
