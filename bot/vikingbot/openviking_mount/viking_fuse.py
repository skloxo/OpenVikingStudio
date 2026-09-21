"""
OpenViking FUSE 文件系统 - 只读挂载 MVP + Overlay 防护层 (v1.5.67)

提供将 OpenViking 知识库 (viking://) 挂载到本地目录的 FUSE 文件系统实现。
支持 standard POSIX 只读契约：getattr, readdir, open, read, statfs。
写操作严格返回 POSIX 标准 errno.EROFS (Read-only file system)。

Card 10 新增三层 Overlay 防护机制：
1. TempFileShield: 拦截 .swp / ~ / .DS_Store / .Trash 等临时文件
2. OverlayWriteBuffer: 内存虚拟写缓冲，吸收编辑器写请求不卡死
3. InodeDentryLRU: 热点 LRU 缓存，提升 getattr 遍历性能
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

from .fuse_overlay import InodeDentryLRU, OverlayWriteBuffer, TempFileShield
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

        # Card 10: 三层 Overlay 防护层实例
        self._shield = TempFileShield()
        self._overlay = OverlayWriteBuffer()
        self._lru = InodeDentryLRU()

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
        获取文件/目录属性 (Card 10: 加入 TempFileShield 拦截 + InodeDentryLRU 缓存)

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

        target_name = Path(path).name

        # Card 10 - Layer 1: TempFileShield 拦截 — 临时文件直接返回 ENOENT
        if self._shield.should_block(target_name):
            logger.debug(f"getattr: blocked temp file '{target_name}' at {path}")
            # 检查是否是 Overlay 内存虚拟文件
            vattr = self._overlay.get_virtual_attr(path)
            if vattr is not None:
                return {
                    "st_mode": vattr["st_mode"],
                    "st_nlink": 1,
                    "st_uid": uid,
                    "st_gid": gid,
                    "st_size": vattr["st_size"],
                    "st_atime": vattr["st_atime"],
                    "st_mtime": vattr["st_mtime"],
                    "st_ctime": vattr["st_ctime"],
                }
            raise FuseOSError(errno.ENOENT)

        # Card 10 - Layer 3: InodeDentryLRU 热点缓存查询
        cached = self._lru.get(path)
        if cached is not None:
            logger.debug(f"getattr: LRU hit for {path}")
            return cached

        parent_path = str(Path(path).parent) if Path(path).parent != Path(".") else "/"
        parent_uri = self._path_to_uri(parent_path)

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

                result = {
                    "st_mode": mode,
                    "st_nlink": nlink,
                    "st_uid": uid,
                    "st_gid": gid,
                    "st_size": file_size,
                    "st_atime": mtime,
                    "st_mtime": mtime,
                    "st_ctime": mtime,
                }
                # Card 10 - Layer 3: 写回 LRU 缓存
                self._lru.put(path, result)
                return result

        # 路径在父目录下不存在，抛出标准 POSIX 文件未找到错误
        raise FuseOSError(errno.ENOENT)

    def readdir(self, path: str, fh: Optional[int] = None) -> List[str]:
        """
        读取目录内容 (Card 10: TempFileShield 过滤垃圾文件)

        Args:
            path: 目录路径
            fh: 文件描述符

        Returns:
            目录项列表（已过滤临时/垃圾文件）
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

        # Card 10 - Layer 1: 过滤临时/垃圾文件，保持目录干净
        return self._shield.filter_entries(entries)

    def open(self, path: str, flags: int) -> int:
        """
        打开文件 (Card 10: 对屏蔽路径路由到 Overlay 虚拟写)

        Args:
            path: 文件路径
            flags: 打开标志

        Returns:
            文件描述符（真实 fd 或 Overlay 虚拟 fd）
        """
        logger.debug(f"open: {path} (flags={flags})")

        is_write = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND))
        target_name = Path(path).name

        # Card 10 - Layer 2: 对被屏蔽路径的写请求，路由到内存 Overlay（不卡死编辑器）
        if self.mount.config.read_only and is_write and self._shield.should_block(target_name):
            logger.debug(f"open: overlay virtual write for blocked path {path}")
            if self._overlay.has_virtual_path(path):
                return self._overlay.open_virtual(path)
            return self._overlay.create_virtual_file(path, 0o100644)

        # 对真实知识库文件，只读契约不变
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
        读取文件内容 (Card 10: Overlay 虚拟 fd 优先走内存缓冲)

        Args:
            path: 文件路径
            size: 读取大小
            offset: 偏移量
            fh: 文件描述符

        Returns:
            读取的字节
        """
        logger.debug(f"read: {path} (size={size}, offset={offset})")

        # Card 10 - Layer 2: Overlay 虚拟文件 fd 直接从内存缓冲读取
        if self._overlay.is_virtual_fd(fh):
            return self._overlay.read_virtual(fh, size, offset)

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

    # POSIX 修改类接口：对屏蔽路径路由 Overlay，对真实 VikingFS 路径拦截 EROFS
    def create(self, path: str, mode: int, fi: Any = None) -> int:
        target_name = Path(path).name
        # Card 10 - Layer 2: 屏蔽路径的 create 路由到内存 Overlay
        if self.mount.config.read_only and self._shield.should_block(target_name):
            logger.debug(f"create: overlay virtual file for {path}")
            return self._overlay.create_virtual_file(path, mode)
        if self.mount.config.read_only:
            raise FuseOSError(errno.EROFS)
        raise FuseOSError(errno.EPERM)

    def write(self, path: str, data: bytes, offset: int, fh: int) -> int:
        # Card 10 - Layer 2: Overlay 虚拟 fd 的写请求路由到内存缓冲
        if self._overlay.is_virtual_fd(fh):
            return self._overlay.write_virtual(fh, data, offset)
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
        target_name = Path(path).name
        # Card 10 - Layer 2: 屏蔽文件的 unlink 虚拟成功（让编辑器清理 swp）
        if self.mount.config.read_only and self._shield.should_block(target_name):
            self._overlay._vattrs.pop(path, None)
            return
        if self.mount.config.read_only:
            raise FuseOSError(errno.EROFS)
        raise FuseOSError(errno.EPERM)

    def rename(self, old: str, new: str) -> None:
        if self.mount.config.read_only:
            raise FuseOSError(errno.EROFS)
        raise FuseOSError(errno.EPERM)

    def truncate(self, path: str, length: int, fh: Optional[int] = None) -> None:
        target_name = Path(path).name
        # Card 10 - Layer 2: 屏蔽文件的 truncate 路由到 Overlay
        if self.mount.config.read_only and self._shield.should_block(target_name):
            self._overlay.truncate_virtual(path, length)
            return
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
        target_name = Path(path).name
        # Card 10 - Layer 2: 屏蔽文件的 utimens 虚拟成功
        if self.mount.config.read_only and self._shield.should_block(target_name):
            return
        if self.mount.config.read_only:
            raise FuseOSError(errno.EROFS)
        raise FuseOSError(errno.EPERM)

    def release(self, path: str, fh: int) -> None:
        logger.debug(f"release: {path} (fh={fh})")
        # Card 10 - Layer 2: 释放 Overlay 虚拟 fd
        if self._overlay.is_virtual_fd(fh):
            self._overlay.release_virtual(fh)
            return
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
