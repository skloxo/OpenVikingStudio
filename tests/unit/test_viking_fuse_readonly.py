"""
Unit tests for OpenViking FUSE Read-Only MVP operations and POSIX compliance.
Verifies getattr, readdir, open, read, statfs, and strict EROFS error handling for write operations.
"""

import errno
import os
import stat
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vikingbot.openviking_mount.mount import MountConfig, MountScope, OpenVikingMount
from vikingbot.openviking_mount.viking_fuse import (
    FUSEMountManager,
    FuseOSError,
    OpenVikingFUSE,
)


@pytest.fixture
def mock_ov_client():
    """Create a mock OpenViking SyncHTTPClient with simulated files and directories."""
    client = MagicMock()

    # Simulate directory listing
    def mock_ls(uri: str, **kwargs):
        clean_uri = uri.rstrip("/")
        if clean_uri in ("viking://resources", "viking://"):
            return [
                {"name": "docs", "is_dir": True, "size": 4096, "modified_at": 1700000000.0},
                {
                    "name": "README.md",
                    "is_dir": False,
                    "size": 25,
                    "modified_at": 1700000000.0,
                },
                {"name": "notes.txt", "is_dir": False, "size": 18, "modified_at": 1700000000.0},
            ]
        elif clean_uri in ("viking://resources/docs", "viking://docs"):
            return [
                {
                    "name": "architecture.md",
                    "is_dir": False,
                    "size": 32,
                    "modified_at": 1700000000.0,
                }
            ]
        else:
            raise RuntimeError(f"URI not found: {uri}")

    # Simulate file reading
    def mock_read(uri: str, **kwargs):
        clean_uri = uri.rstrip("/")
        if clean_uri.endswith("README.md"):
            return "# Welcome to OpenViking!\n"
        elif clean_uri.endswith("notes.txt"):
            return "Knowledge base MVP"
        elif clean_uri.endswith("architecture.md"):
            return "Detailed system architecture doc"
        raise FileNotFoundError(f"File not found: {uri}")

    client.ls.side_effect = mock_ls
    client.read.side_effect = mock_read
    return client


@pytest.fixture
def readonly_fuse(tmp_path: Path, mock_ov_client):
    """Create an OpenVikingFUSE instance in read-only mode backed by the mock client."""
    config = MountConfig(
        mount_point=tmp_path / "mount",
        openviking_data_path=tmp_path / "cache",
        scope=MountScope.RESOURCES,
        auto_init=False,
        read_only=True,
    )
    mount = OpenVikingMount(config)
    mount._client = mock_ov_client
    mount._initialized = True

    fuse_ops = OpenVikingFUSE(mount)
    return fuse_ops


class TestOpenVikingFUSEReadOnly:
    """Test suite for POSIX read-only file system operations."""

    def test_root_getattr(self, readonly_fuse):
        """Root directory / should return valid directory attributes with read-only permissions."""
        st = readonly_fuse.getattr("/")
        assert stat.S_ISDIR(st["st_mode"])
        assert st["st_mode"] & 0o777 == 0o555
        assert st["st_nlink"] == 2
        assert st["st_size"] == 4096

    def test_existing_file_getattr(self, readonly_fuse):
        """Existing file should return valid regular file attributes and correct size."""
        st = readonly_fuse.getattr("/README.md")
        assert stat.S_ISREG(st["st_mode"])
        assert st["st_mode"] & 0o777 == 0o444
        assert st["st_nlink"] == 1
        assert st["st_size"] == 25

    def test_existing_directory_getattr(self, readonly_fuse):
        """Existing subdirectory should return directory attributes."""
        st = readonly_fuse.getattr("/docs")
        assert stat.S_ISDIR(st["st_mode"])
        assert st["st_mode"] & 0o777 == 0o555
        assert st["st_nlink"] == 2

    def test_nonexistent_path_getattr_raises_enoent(self, readonly_fuse):
        """Non-existent path must raise FuseOSError with errno.ENOENT, never return a fake directory."""
        with pytest.raises(FuseOSError) as exc_info:
            readonly_fuse.getattr("/missing_file.md")
        assert exc_info.value.errno == errno.ENOENT

    def test_readdir_root(self, readonly_fuse):
        """readdir on root directory must include '.' and '..' and list all children."""
        entries = readonly_fuse.readdir("/")
        assert "." in entries
        assert ".." in entries
        assert "docs" in entries
        assert "README.md" in entries
        assert "notes.txt" in entries

    def test_readdir_nonexistent_raises_enoent(self, readonly_fuse):
        """readdir on non-existent directory must raise FuseOSError(errno.ENOENT)."""
        with pytest.raises(FuseOSError) as exc_info:
            readonly_fuse.readdir("/invalid_folder")
        assert exc_info.value.errno == errno.ENOENT

    def test_open_read_only_success(self, readonly_fuse):
        """Opening an existing file with O_RDONLY should succeed and return integer fd."""
        fd = readonly_fuse.open("/README.md", os.O_RDONLY)
        assert isinstance(fd, int)
        assert fd > 0

    def test_open_write_mode_rejected_with_erofs(self, readonly_fuse):
        """Opening a file with O_WRONLY or O_RDWR or O_APPEND in read-only mount must raise EROFS."""
        with pytest.raises(FuseOSError) as exc_info:
            readonly_fuse.open("/README.md", os.O_WRONLY)
        assert exc_info.value.errno == errno.EROFS

        with pytest.raises(FuseOSError) as exc_info:
            readonly_fuse.open("/README.md", os.O_RDWR)
        assert exc_info.value.errno == errno.EROFS

    def test_open_nonexistent_raises_enoent(self, readonly_fuse):
        """Opening a non-existent file should raise FuseOSError(errno.ENOENT)."""
        with pytest.raises(FuseOSError) as exc_info:
            readonly_fuse.open("/ghost.txt", os.O_RDONLY)
        assert exc_info.value.errno == errno.ENOENT

    def test_read_slices_content_correctly(self, readonly_fuse):
        """read should return correct byte slices matching offset and size."""
        fd = readonly_fuse.open("/README.md", os.O_RDONLY)
        # "# Welcome to OpenViking!\n"
        data = readonly_fuse.read("/README.md", size=9, offset=2, fh=fd)
        assert data == b"Welcome t"

        # Read remaining portion
        data2 = readonly_fuse.read("/README.md", size=100, offset=0, fh=fd)
        assert data2 == b"# Welcome to OpenViking!\n"

    def test_statfs_returns_valid_posix_metrics(self, readonly_fuse):
        """statfs must return valid virtual filesystem block and free size metrics."""
        stat_dict = readonly_fuse.statfs("/")
        assert stat_dict["f_bsize"] == 4096
        assert stat_dict["f_blocks"] > 0
        assert stat_dict["f_bfree"] > 0
        assert stat_dict["f_flag"] == os.ST_RDONLY

    def test_write_operations_strictly_rejected_with_erofs(self, readonly_fuse):
        """All POSIX mutating operations must raise EROFS in read-only mode."""
        with pytest.raises(FuseOSError) as exc_info:
            readonly_fuse.create("/new.txt", 0o644)
        assert exc_info.value.errno == errno.EROFS

        with pytest.raises(FuseOSError) as exc_info:
            readonly_fuse.write("/README.md", b"malicious write", offset=0, fh=1)
        assert exc_info.value.errno == errno.EROFS

        with pytest.raises(FuseOSError) as exc_info:
            readonly_fuse.mkdir("/new_dir", 0o755)
        assert exc_info.value.errno == errno.EROFS

        with pytest.raises(FuseOSError) as exc_info:
            readonly_fuse.rmdir("/docs")
        assert exc_info.value.errno == errno.EROFS

        with pytest.raises(FuseOSError) as exc_info:
            readonly_fuse.unlink("/README.md")
        assert exc_info.value.errno == errno.EROFS

        with pytest.raises(FuseOSError) as exc_info:
            readonly_fuse.rename("/README.md", "/RENAMED.md")
        assert exc_info.value.errno == errno.EROFS

        with pytest.raises(FuseOSError) as exc_info:
            readonly_fuse.truncate("/README.md", 0)
        assert exc_info.value.errno == errno.EROFS

        with pytest.raises(FuseOSError) as exc_info:
            readonly_fuse.chmod("/README.md", 0o777)
        assert exc_info.value.errno == errno.EROFS

        with pytest.raises(FuseOSError) as exc_info:
            readonly_fuse.chown("/README.md", 0, 0)
        assert exc_info.value.errno == errno.EROFS

        with pytest.raises(FuseOSError) as exc_info:
            readonly_fuse.utimens("/README.md", None)
        assert exc_info.value.errno == errno.EROFS

    def test_mount_write_file_raises_permission_error(self, tmp_path):
        """OpenVikingMount.write_file should raise PermissionError in read-only configuration."""
        config = MountConfig(
            mount_point=tmp_path / "m",
            openviking_data_path=tmp_path / "c",
            read_only=True,
            auto_init=False,
        )
        mount = OpenVikingMount(config)
        with pytest.raises(PermissionError):
            mount.write_file("/file.txt", "content")

    def test_fuse_mount_manager_lifecycle(self):
        """FUSEMountManager should safely report status and clean unmounts."""
        manager = FUSEMountManager()
        assert not manager.is_mounted("non_existent_mount")
        assert manager.list_active_mounts() == []
        manager.unmount("non_existent_mount")
        manager.unmount_all()
