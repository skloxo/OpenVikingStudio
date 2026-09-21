"""
OpenViking FUSE 文件系统 - 只读挂载 MVP 与 POSIX 兼容实现

提供将 OpenViking 知识库 (viking://) 挂载到本地目录的 FUSE 文件系统实现。
支持 standard POSIX 只读契约：getattr, readdir, open, read, statfs。
写操作严格返回 POSIX 标准 errno.EROFS (Read-only file system)。
"""

from __future__ import annotations

import errno
import os
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .mount import MountConfig, OpenVikingMount

# 尝试导入 fusepy；如未安装则启用轻量纯 Python 抽象基类以保障在无 libfuse 环境下依然安全测试与调用
try:
    from fuse import FUSE, FuseOSError, Operations

    FUSE_AVAILABLE = True
except (ImportError, OSError):
    FUSE_AVAILABLE = False

    class Operations:
        """Fallback base class when fusepy is not installed."""

        pass

    class FuseOSError(OSError):
        """Fallback FuseOSError preserving errno when fusepy is not installed."""

        def __init__(self, err: int):
            super().__init__(err, os.strerror(err) if hasattr(os, "strerror") else str(err))
            self.errno = err

    FUSE = None


class OpenVikingFUSE(Operations):
    """
    OpenViking FUSE 操作类

    实现 FUSE 文件系统操作，将 OpenViking 的虚拟文件系统暴露为标准的 POSIX 文件系统。
    """

    def __init__(self, mount: OpenVikingMount):
        """
        初始化 FUSE 操作

        Args:
            mount: OpenVikingMount 实例
        """
        self.mount = mount
        self._fd = 0
        self._file_handles: Dict[int, str] = {}
        self._file_contents: Dict[str, str] = {}

        if not mount._initialized and mount.config.auto_init:
            mount.initialize()

    def _path_to_uri(self, path: str) -> str:
        """
        将 FUSE 路径转换为 OpenViking URI

        Args:
            path: FUSE 路径 (如 /resources/foo.md)

        Returns:
            OpenViking URI
        """
        clean_path = path.strip("/")
        if not clean_path:
            return self.mount._get_scope_root_uri()

        scope_root = self.mount._get_scope_root_uri().rstrip("/")
        return f"{scope_root}/{clean_path}"

    def getattr(self, path: str, fh: Optional[int] = None) -> Dict[str, Any]:
        """
        获取文件/目录属性

        Args:
            path: 文件路径
            fh: 文件描述符

        Returns:
            属性字典
        """
        logger.debug(f"getattr: {path}")
        now = datetime.now().timestamp()
        uid = os.getuid() if hasattr(os, "getuid") else 1000
        gid = os.getgid() if hasattr(os, "getgid") else 1000

        # 根目录直接返回
        if path in ("", "/"):
            dir_mode = stat.S_IFDIR | (0o555 if self.mount.config.read_only else 0o755)
            return {
                "st_mode": dir_mode,
                "st_nlink": 2,
                "st_uid": uid,
                "st_gid": gid,
                "st_size": 4096,
                "st_atime": now,
                "st_mtime": now,
                "st_ctime": now,
            }

        parent_path = str(Path(path).parent) if Path(path).parent != Path(".") else "/"
        parent_uri = self._path_to_uri(parent_path)
        target_name = Path(path).name

        items = []
        try:
            if self.mount._client:
                items = self.mount._client.ls(parent_uri)
        except Exception as e:
            logger.debug(f"getattr failed listing parent {parent_uri}: {e}")
            items = []

        for item in items:
            if isinstance(item, dict):
                item_name = item.get("name", "")
                is_dir = bool(item.get("isDir", item.get("is_dir", False)))
                size = int(item.get("size", 0))
                mtime = float(item.get("modified_at", item.get("updated_at", now)))
            else:
                item_name = str(item)
                is_dir = False
                size = 0
                mtime = now

            if item_name == target_name:
                if is_dir:
                    mode = stat.S_IFDIR | (0o555 if self.mount.config.read_only else 0o755)
                    nlink = 2
                    file_size = 4096
                else:
                    mode = stat.S_IFREG | (0o444 if self.mount.config.read_only else 0o644)
                    nlink = 1
                    file_size = size

                return {
                    "st_mode": mode,
                    "st_nlink": nlink,
                    "st_uid": uid,
                    "st_gid": gid,
                    "st_size": file_size,
                    "st_atime": mtime,
                    "st_mtime": mtime,
                    "st_ctime": mtime,
                }

        # 路径在父目录下不存在，抛出标准 POSIX 文件未找到错误
        raise FuseOSError(errno.ENOENT)

    def readdir(self, path: str, fh: Optional[int] = None) -> List[str]:
        """
        读取目录内容

        Args:
            path: 目录路径
            fh: 文件描述符

        Returns:
            目录项列表
        """
        logger.debug(f"readdir: {path}")
        uri = self._path_to_uri(path)

        try:
            items = self.mount._client.ls(uri) if self.mount._client else []
        except Exception as e:
            logger.warning(f"readdir error for {uri}: {e}")
            raise FuseOSError(errno.ENOENT)

        entries = [".", ".."]
        for item in items:
            if isinstance(item, dict):
                name = item.get("name", "")
            else:
                name = str(item)
            if name and name not in entries:
                entries.append(name)

        return entries

    def open(self, path: str, flags: int) -> int:
        """
        打开文件

        Args:
            path: 文件路径
            flags: 打开标志

        Returns:
            文件描述符
        """
        logger.debug(f"open: {path} (flags={flags})")

        # 检查只读文件系统写入拒绝
        is_write = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND))
        if self.mount.config.read_only and is_write:
            raise FuseOSError(errno.EROFS)

        # 验证文件是否存在
        self.getattr(path)

        uri = self._path_to_uri(path)
        self._fd += 1
        fd = self._fd
        self._file_handles[fd] = uri

        return fd

    def read(self, path: str, size: int, offset: int, fh: int) -> bytes:
        """
        读取文件内容

        Args:
            path: 文件路径
            size: 读取大小
            offset: 偏移量
            fh: 文件描述符

        Returns:
            读取的字节
        """
        logger.debug(f"read: {path} (size={size}, offset={offset})")

        uri = self._file_handles.get(fh) or self._path_to_uri(path)

        if uri in self._file_contents:
            content = self._file_contents[uri]
        else:
            try:
                content = self.mount._client.read(uri) if self.mount._client else ""
                self._file_contents[uri] = content
            except Exception as e:
                logger.error(f"read error for {uri}: {e}")
                raise FuseOSError(errno.EIO)

        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = bytes(content)

        return content_bytes[offset : offset + size]

    def statfs(self, path: str) -> Dict[str, Any]:
        """
        获取虚拟文件系统统计信息

        Args:
            path: 路径

        Returns:
            statfs 字典
        """
        logger.debug(f"statfs: {path}")
        return {
            "f_bsize": 4096,
            "f_frsize": 4096,
            "f_blocks": 1024 * 1024 * 100,  # 400 GB 虚拟总量
            "f_bfree": 1024 * 1024 * 50,  # 200 GB 虚拟可用
            "f_bavail": 1024 * 1024 * 50,
            "f_files": 1000000,
            "f_ffree": 500000,
            "f_favail": 500000,
            "f_flag": os.ST_RDONLY if self.mount.config.read_only else 0,
            "f_namemax": 255,
        }

    # POSIX 修改类接口在只读模式下统一拦截为 EROFS
    def create(self, path: str, mode: int, fi: Any = None) -> int:
        if self.mount.config.read_only:
            raise FuseOSError(errno.EROFS)
        raise FuseOSError(errno.EPERM)

    def write(self, path: str, data: bytes, offset: int, fh: int) -> int:
        if self.mount.config.read_only:
            raise FuseOSError(errno.EROFS)
        raise FuseOSError(errno.EROFS)

    def mkdir(self, path: str, mode: int) -> None:
        if self.mount.config.read_only:
            raise FuseOSError(errno.EROFS)
        raise FuseOSError(errno.EPERM)

    def rmdir(self, path: str) -> None:
        if self.mount.config.read_only:
            raise FuseOSError(errno.EROFS)
        raise FuseOSError(errno.EPERM)

    def unlink(self, path: str) -> None:
        if self.mount.config.read_only:
            raise FuseOSError(errno.EROFS)
        raise FuseOSError(errno.EPERM)

    def rename(self, old: str, new: str) -> None:
        if self.mount.config.read_only:
            raise FuseOSError(errno.EROFS)
        raise FuseOSError(errno.EPERM)

    def truncate(self, path: str, length: int, fh: Optional[int] = None) -> None:
        if self.mount.config.read_only:
            raise FuseOSError(errno.EROFS)
        raise FuseOSError(errno.EROFS)

    def chmod(self, path: str, mode: int) -> None:
        if self.mount.config.read_only:
            raise FuseOSError(errno.EROFS)
        raise FuseOSError(errno.EPERM)

    def chown(self, path: str, uid: int, gid: int) -> None:
        if self.mount.config.read_only:
            raise FuseOSError(errno.EROFS)
        raise FuseOSError(errno.EPERM)

    def utimens(self, path: str, times: Optional[tuple] = None) -> None:
        if self.mount.config.read_only:
            raise FuseOSError(errno.EROFS)
        raise FuseOSError(errno.EPERM)

    def release(self, path: str, fh: int) -> None:
        logger.debug(f"release: {path} (fh={fh})")
        self._file_handles.pop(fh, None)


def mount_fuse(config: MountConfig, foreground: bool = False, allow_other: bool = False) -> None:
    """
    挂载 OpenViking FUSE 文件系统

    Args:
        config: 挂载配置
        foreground: 是否在前台运行
        allow_other: 是否允许其他用户访问
    """
    if not FUSE_AVAILABLE or FUSE is None:
        raise ImportError(
            "fusepy and libfuse are required for system FUSE mounting. "
            "Install with: pip install fusepy and install system libfuse."
        )

    mount = OpenVikingMount(config)
    operations = OpenVikingFUSE(mount)

    fuse_opts = {}
    if allow_other:
        fuse_opts["allow_other"] = True

    logger.info(f"Mounting OpenViking FUSE at: {config.mount_point}")
    logger.info(f"  Scope: {config.scope.value}")
    logger.info(f"  Read-only: {config.read_only}")

    try:
        FUSE(
            operations,
            str(config.mount_point),
            foreground=foreground,
            nothreads=True,
            **fuse_opts,
        )
    except KeyboardInterrupt:
        logger.info("Unmounting FUSE on KeyboardInterrupt...")
    finally:
        mount.close()
        logger.info("FUSE mount closed.")


class FUSEMountManager:
    """
    FUSE 挂载管理器

    管理 FUSE 挂载进程的生命周期与状态查询
    """

    def __init__(self):
        self._mounts: Dict[str, Any] = {}

    def mount(self, mount_id: str, config: MountConfig, background: bool = True) -> None:
        """
        挂载 FUSE 文件系统

        Args:
            mount_id: 挂载 ID
            config: 挂载配置
            background: 是否在后台进程运行
        """
        if not FUSE_AVAILABLE:
            raise ImportError("fusepy and libfuse are required for FUSE mounting")

        if background:
            import multiprocessing

            def _mount_worker():
                mount_fuse(config, foreground=True)

            process = multiprocessing.Process(target=_mount_worker, daemon=True)
            process.start()
            self._mounts[mount_id] = process
            logger.info(f"Started FUSE mount '{mount_id}' in background (PID: {process.pid})")
        else:
            mount_fuse(config, foreground=True)

    def unmount(self, mount_id: str) -> None:
        """
        卸载 FUSE 文件系统

        Args:
            mount_id: 挂载 ID
        """
        if mount_id in self._mounts:
            process = self._mounts.pop(mount_id)
            if hasattr(process, "terminate"):
                process.terminate()
                process.join(timeout=5)
            logger.info(f"Unmounted FUSE mount '{mount_id}'")

    def unmount_all(self) -> None:
        """卸载所有 FUSE 文件系统"""
        for mount_id in list(self._mounts.keys()):
            self.unmount(mount_id)

    def is_mounted(self, mount_id: str) -> bool:
        """检查挂载点是否存活"""
        process = self._mounts.get(mount_id)
        if process is None:
            return False
        if hasattr(process, "is_alive"):
            return process.is_alive()
        return True

    def list_active_mounts(self) -> List[str]:
        """列出所有活跃的挂载 ID"""
        return [mid for mid in self._mounts if self.is_mounted(mid)]
