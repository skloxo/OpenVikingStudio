"""
Card 10 专属单测：FUSE Overlay Virtual Trash Shield (v1.5.67)

验证三层 Overlay 防护机制：
1. TempFileShield: 临时文件屏蔽 (readdir 过滤 + getattr ENOENT 拦截)
2. OverlayWriteBuffer: 内存虚拟写缓冲 (不卡死编辑器)
3. InodeDentryLRU: 热点 getattr LRU 缓存 (O(1) 命中)
"""

import errno
import os
import stat
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vikingbot.openviking_mount.fuse_overlay import (
    InodeDentryLRU,
    OverlayWriteBuffer,
    TempFileShield,
)
from vikingbot.openviking_mount.mount import MountConfig, MountScope, OpenVikingMount
from vikingbot.openviking_mount.viking_fuse import FuseOSError, OpenVikingFUSE


# ---------------------------------------------------------------------------
# 测试辅助：带垃圾文件的 mock 客户端
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ov_client_with_trash():
    """Mock 客户端，模拟包含真实文件 + 编辑器生成的垃圾文件的目录。"""
    client = MagicMock()

    def mock_ls(uri: str, **kwargs):
        clean_uri = uri.rstrip("/")
        if clean_uri in ("viking://resources", "viking://"):
            return [
                {"name": "README.md", "is_dir": False, "size": 20, "modified_at": 1700000000.0},
                {"name": "notes.txt", "is_dir": False, "size": 10, "modified_at": 1700000000.0},
                # 垃圾文件 —— 应被屏蔽
                {"name": ".DS_Store", "is_dir": False, "size": 6148, "modified_at": 1700000000.0},
                {"name": ".README.md.swp", "is_dir": False, "size": 4096, "modified_at": 1700000000.0},
                {"name": "notes.txt~", "is_dir": False, "size": 10, "modified_at": 1700000000.0},
                {"name": "4913", "is_dir": False, "size": 0, "modified_at": 1700000000.0},
            ]
        raise RuntimeError(f"URI not found: {uri}")

    def mock_read(uri: str, **kwargs):
        if uri.endswith("README.md"):
            return "# Hello OpenViking!\n"
        raise FileNotFoundError(f"File not found: {uri}")

    client.ls.side_effect = mock_ls
    client.read.side_effect = mock_read
    return client


@pytest.fixture
def trash_fuse(tmp_path: Path, mock_ov_client_with_trash):
    """创建集成三层 Overlay 的 OpenVikingFUSE 实例。"""
    config = MountConfig(
        mount_point=tmp_path / "mount",
        openviking_data_path=tmp_path / "cache",
        scope=MountScope.RESOURCES,
        auto_init=False,
        read_only=True,
    )
    mount = OpenVikingMount(config)
    mount._client = mock_ov_client_with_trash
    mount._initialized = True
    return OpenVikingFUSE(mount)


# ---------------------------------------------------------------------------
# 1. TempFileShield 单元测试
# ---------------------------------------------------------------------------


class TestTempFileShield:
    """验证 TempFileShield 的临时文件识别与过滤逻辑。"""

    def setup_method(self):
        self.shield = TempFileShield()

    def test_exact_name_blocked(self):
        """精确名称匹配的垃圾文件应被屏蔽。"""
        assert self.shield.should_block(".DS_Store")
        assert self.shield.should_block(".Trash")
        assert self.shield.should_block("desktop.ini")
        assert self.shield.should_block("Thumbs.db")

    def test_suffix_blocked(self):
        """常见临时文件后缀应被屏蔽。"""
        assert self.shield.should_block("notes.txt~")
        assert self.shield.should_block("file.swp")
        assert self.shield.should_block("file.swo")
        assert self.shield.should_block("backup.bak")
        assert self.shield.should_block("old.orig")

    def test_regex_pattern_blocked(self):
        """正则模式匹配的垃圾文件应被屏蔽。"""
        assert self.shield.should_block(".README.md.swp")  # Vim .filename.swp
        assert self.shield.should_block("4913")              # Vim 原子写测试
        assert self.shield.should_block("._resource")        # macOS AppleDouble
        assert self.shield.should_block(".git")              # Git 目录
        assert self.shield.should_block(".vscode")           # VS Code 配置目录

    def test_legitimate_files_not_blocked(self):
        """正常文件和目录不应被屏蔽。"""
        assert not self.shield.should_block("README.md")
        assert not self.shield.should_block("architecture.md")
        assert not self.shield.should_block("docs")
        assert not self.shield.should_block(".")
        assert not self.shield.should_block("..")

    def test_filter_entries_removes_trash(self):
        """filter_entries 应从列表中移除所有被屏蔽项，保留合法项。"""
        raw = [".", "..", "README.md", ".DS_Store", ".file.swp", "notes.txt", "notes.txt~", "4913"]
        filtered = self.shield.filter_entries(raw)
        assert "." in filtered
        assert ".." in filtered
        assert "README.md" in filtered
        assert "notes.txt" in filtered
        # 垃圾文件必须被清除
        assert ".DS_Store" not in filtered
        assert ".file.swp" not in filtered
        assert "notes.txt~" not in filtered
        assert "4913" not in filtered


# ---------------------------------------------------------------------------
# 2. OverlayWriteBuffer 单元测试
# ---------------------------------------------------------------------------


class TestOverlayWriteBuffer:
    """验证 OverlayWriteBuffer 虚拟写缓冲的完整生命周期。"""

    def setup_method(self):
        self.overlay = OverlayWriteBuffer()

    def test_create_and_write_virtual_file(self):
        """create + write 应正常将数据存入内存缓冲区。"""
        fd = self.overlay.create_virtual_file("/tmp/.file.swp", 0o100644)
        assert fd > 0
        assert self.overlay.is_virtual_fd(fd)

        written = self.overlay.write_virtual(fd, b"hello world", offset=0)
        assert written == 11

    def test_read_virtual_file(self):
        """write 后 read 应能读回正确内容。"""
        fd = self.overlay.create_virtual_file("/tmp/.swp_test", 0o100644)
        self.overlay.write_virtual(fd, b"VikingFS Overlay Test\n", offset=0)
        data = self.overlay.read_virtual(fd, size=100, offset=0)
        assert data == b"VikingFS Overlay Test\n"

    def test_partial_read_offset(self):
        """验证 offset 切片读取正确性。"""
        fd = self.overlay.create_virtual_file("/test.swp", 0o100644)
        self.overlay.write_virtual(fd, b"ABCDEFGHIJ", offset=0)
        data = self.overlay.read_virtual(fd, size=4, offset=3)
        assert data == b"DEFG"

    def test_release_virtual_fd(self):
        """release 后 fd 应从缓冲区中移除。"""
        fd = self.overlay.create_virtual_file("/tmp/.released.swp", 0o100644)
        assert self.overlay.is_virtual_fd(fd)
        self.overlay.release_virtual(fd)
        assert not self.overlay.is_virtual_fd(fd)

    def test_virtual_attr_update_on_write(self):
        """write 后 vattr size 应自动更新为实际写入大小。"""
        fd = self.overlay.create_virtual_file("/test.swp", 0o100644)
        self.overlay.write_virtual(fd, b"X" * 128, offset=0)
        attr = self.overlay.get_virtual_attr("/test.swp")
        assert attr is not None
        assert attr["st_size"] == 128


# ---------------------------------------------------------------------------
# 3. InodeDentryLRU 单元测试
# ---------------------------------------------------------------------------


class TestInodeDentryLRU:
    """验证 InodeDentryLRU 缓存的存取、TTL 过期与 LRU 淘汰。"""

    def test_get_miss_on_empty_cache(self):
        """空缓存中查询任何路径应返回 None。"""
        lru = InodeDentryLRU()
        assert lru.get("/README.md") is None

    def test_put_and_get(self):
        """put 后立即 get 应命中缓存并返回原始属性字典。"""
        lru = InodeDentryLRU()
        attrs = {"st_mode": 0o100444, "st_size": 100}
        lru.put("/README.md", attrs)
        result = lru.get("/README.md")
        assert result is not None
        assert result["st_size"] == 100

    def test_ttl_expiry(self):
        """TTL 过期后缓存条目应自动失效。"""
        lru = InodeDentryLRU(ttl=0.05)  # 50ms TTL
        lru.put("/notes.txt", {"st_size": 50})
        time.sleep(0.1)  # 等待 TTL 过期
        assert lru.get("/notes.txt") is None

    def test_lru_eviction(self):
        """超出容量后，最旧的条目应被 LRU 淘汰。"""
        lru = InodeDentryLRU(capacity=3)
        for i in range(3):
            lru.put(f"/file{i}.md", {"st_size": i})
        # 再插入第 4 个，应淘汰 file0
        lru.put("/file3.md", {"st_size": 3})
        assert lru.get("/file0.md") is None
        assert lru.get("/file3.md") is not None

    def test_invalidate(self):
        """invalidate 应精准使单条路径的缓存失效。"""
        lru = InodeDentryLRU()
        lru.put("/README.md", {"st_size": 20})
        lru.put("/notes.txt", {"st_size": 10})
        lru.invalidate("/README.md")
        assert lru.get("/README.md") is None
        assert lru.get("/notes.txt") is not None


# ---------------------------------------------------------------------------
# 4. 集成测试：三层 Overlay 与 OpenVikingFUSE 联动
# ---------------------------------------------------------------------------


class TestFUSEOverlayIntegration:
    """验证 OpenVikingFUSE 中三层 Overlay 防护的端到端行为。"""

    def test_readdir_filters_trash_files(self, trash_fuse):
        """readdir 应过滤垃圾文件，仅保留真实知识库条目。"""
        entries = trash_fuse.readdir("/")
        assert "README.md" in entries
        assert "notes.txt" in entries
        # 垃圾文件必须被过滤
        assert ".DS_Store" not in entries
        assert ".README.md.swp" not in entries
        assert "notes.txt~" not in entries
        assert "4913" not in entries

    def test_getattr_trash_returns_enoent(self, trash_fuse):
        """对垃圾文件路径调用 getattr 应返回 ENOENT（不暴露给工具）。"""
        with pytest.raises(FuseOSError) as exc_info:
            trash_fuse.getattr("/.DS_Store")
        assert exc_info.value.errno == errno.ENOENT

        with pytest.raises(FuseOSError) as exc_info:
            trash_fuse.getattr("/.README.md.swp")
        assert exc_info.value.errno == errno.ENOENT

    def test_overlay_create_write_read_release_lifecycle(self, trash_fuse):
        """Vim 完整写 .swp 生命周期：create -> write -> read -> release。"""
        # 1. create .swp 文件
        fd = trash_fuse.create("/.README.md.swp", 0o100644)
        assert isinstance(fd, int)
        assert fd > 0

        # 2. write 内容到内存 overlay
        written = trash_fuse.write("/.README.md.swp", b"vim swap content", offset=0, fh=fd)
        assert written == 16

        # 3. read 读回
        data = trash_fuse.read("/.README.md.swp", size=100, offset=0, fh=fd)
        assert data == b"vim swap content"

        # 4. release 释放 fd
        trash_fuse.release("/.README.md.swp", fd)
        # fd 释放后应不再是 overlay fd
        assert not trash_fuse._overlay.is_virtual_fd(fd)

    def test_overlay_unlink_virtual_succeeds(self, trash_fuse):
        """unlink 临时文件应虚拟成功（不抛 EROFS），让编辑器正常清理。"""
        # 先创建虚拟文件
        trash_fuse.create("/.vim_tmp.swp", 0o100644)
        # unlink 不应抛异常
        trash_fuse.unlink("/.vim_tmp.swp")

    def test_lru_cache_hit_on_second_getattr(self, trash_fuse):
        """同一路径的第二次 getattr 应命中 LRU 缓存（client.ls 仅调用一次）。"""
        # 第一次 getattr 触发 VikingFS 查询
        trash_fuse.getattr("/README.md")
        call_count_1 = trash_fuse.mount._client.ls.call_count

        # 第二次 getattr 应从 LRU 缓存命中，不再调用 ls
        trash_fuse.getattr("/README.md")
        call_count_2 = trash_fuse.mount._client.ls.call_count

        assert call_count_2 == call_count_1, (
            f"LRU 缓存未命中：ls 被调用了 {call_count_2 - call_count_1} 次额外调用"
        )

    def test_real_file_write_still_returns_erofs(self, trash_fuse):
        """真实知识库文件（非垃圾文件）的写操作仍然返回 EROFS。"""
        with pytest.raises(FuseOSError) as exc_info:
            trash_fuse.open("/README.md", os.O_WRONLY)
        assert exc_info.value.errno == errno.EROFS
