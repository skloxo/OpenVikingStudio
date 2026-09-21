"""
FUSE Overlay Shield — Card 10 (v1.5.67)

三层内存防护机制，增强 FUSE 只读挂载对编辑器临时文件的鲁棒性：

1. TempFileShield: 拦截 .swp / ~ / .DS_Store / .Trash 等临时文件请求
   - readdir 过滤：不在目录列表中呈现垃圾文件
   - getattr 拦截：对垃圾文件路径返回 ENOENT
2. OverlayWriteBuffer: 内存模拟写缓冲区
   - 仅针对屏蔽文件集里的临时文件，模拟写成功（让 Vim/VS Code 正常保存交换文件但不真正写）
   - 对真实知识库文件依旧返回 EROFS
3. InodeDentryLRU: O(1) 热点 LRU 缓存
   - 缓存 getattr 结果，避免频繁轮询时反复穿透到 VikingFS HTTP 接口
"""

from __future__ import annotations

import fnmatch
import re
import time
from collections import OrderedDict
from typing import Any, Dict, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# 1. 临时文件屏蔽模式集 (TempFileShield)
# ---------------------------------------------------------------------------

#: 完整名称匹配（无通配符），O(1) 集合查询
_BLOCKED_EXACT_NAMES: Set[str] = frozenset(
    {
        ".DS_Store",
        ".Trash",
        ".Trashes",
        ".fseventsd",
        ".Spotlight-V100",
        "desktop.ini",
        "Thumbs.db",
        ".dropbox",
        ".dropbox.cache",
        ".localized",
        ".VolumeIcon.icns",
    }
)

#: 后缀匹配（小写化后比较）
_BLOCKED_SUFFIXES: Tuple[str, ...] = (
    ".swp",    # Vim 交换文件
    ".swo",    # Vim 次级交换文件
    ".swn",    # Vim 三级交换文件
    ".tmp",    # 通用临时文件
    ".bak",    # 备份文件
    ".orig",   # 原始文件备份
    ".rej",    # Patch 拒绝文件
    "~",       # Emacs / gedit 备份 (file~)
)

#: 正则模式匹配（预编译，用于前缀 . 开头的隐藏 IDE 元文件）
_BLOCKED_REGEX_PATTERNS = [
    re.compile(r"^\.[^/]*\.swp$"),          # .filename.swp
    re.compile(r"^\.~lock\..*#$"),          # LibreOffice 锁文件
    re.compile(r"^~\$"),                    # Office 临时文件 ~$xxx
    re.compile(r"^4913$"),                  # Vim 原子写测试文件
    re.compile(r"^\._"),                    # macOS AppleDouble 文件
    re.compile(r"^__pycache__$"),           # Python 缓存目录
    re.compile(r"^\.git$"),                 # Git 目录（不应暴露）
    re.compile(r"^\.idea$"),               # JetBrains IDE 目录
    re.compile(r"^\.vscode$"),             # VS Code 工作区目录
]


class TempFileShield:
    """
    临时文件屏蔽层 — 决策核心。

    所有 FUSE 入口点在处理前先通过 should_block() 进行门禁：
    - readdir 过滤：不在目录列表中呈现这些文件
    - getattr 过滤：返回 ENOENT 而非错误，避免编辑器反复重试
    """

    def should_block(self, name: str) -> bool:
        """
        判断文件名是否应被屏蔽。

        Args:
            name: 文件或目录名（不含路径前缀）

        Returns:
            True 表示应屏蔽此条目
        """
        if not name or name in (".", ".."):
            return False

        # 精确名称匹配 O(1)
        if name in _BLOCKED_EXACT_NAMES:
            return True

        # 后缀匹配（小写化）
        lower = name.lower()
        if lower.endswith(_BLOCKED_SUFFIXES):
            return True

        # 正则模式匹配
        for pattern in _BLOCKED_REGEX_PATTERNS:
            if pattern.match(name):
                return True

        return False

    def filter_entries(self, entries: list[str]) -> list[str]:
        """
        过滤目录条目列表，移除所有被屏蔽的名称。

        Args:
            entries: readdir 原始条目列表

        Returns:
            过滤后的干净条目列表
        """
        return [e for e in entries if not self.should_block(e)]


# ---------------------------------------------------------------------------
# 2. 内存 Overlay 写缓冲区 (OverlayWriteBuffer)
# ---------------------------------------------------------------------------

#: 单个内存 Buffer 最大字节数（防止被恶意写爆内存）
_MAX_BUFFER_SIZE = 4 * 1024 * 1024  # 4 MB

#: 最多缓存多少个临时文件 fd（超过后 LRU 淘汰）
_MAX_OVERLAY_FDS = 64


class OverlayWriteBuffer:
    """
    内存 Overlay 虚拟写缓冲区。

    只针对被 TempFileShield 屏蔽的路径（例如 .swp 临时文件）：
    - 允许编辑器正常 create / write / truncate（返回成功）
    - 实际写入保留在进程内存中，不触及 VikingFS 后端
    - 释放文件（release）时自动丢弃内存缓冲

    对非屏蔽文件路径保持 EROFS 契约不变。
    """

    def __init__(self) -> None:
        # fd -> (path, bytearray)  — 活跃虚拟文件描述符
        self._buffers: "OrderedDict[int, Tuple[str, bytearray]]" = OrderedDict()
        # path -> vattr  — 虚拟文件元数据
        self._vattrs: Dict[str, Dict[str, Any]] = {}
        self._next_fd = 10000  # 从高位 fd 开始，与真实 fd 不冲突

    def create_virtual_file(self, path: str, mode: int) -> int:
        """
        为被屏蔽路径创建虚拟文件，返回虚拟 fd。

        Args:
            path: 文件路径（FUSE 视角）
            mode: 创建模式位

        Returns:
            虚拟文件描述符（正整数）
        """
        # LRU 淘汰最旧的 fd
        while len(self._buffers) >= _MAX_OVERLAY_FDS:
            self._buffers.popitem(last=False)

        fd = self._next_fd
        self._next_fd += 1
        self._buffers[fd] = (path, bytearray())
        self._vattrs[path] = {
            "st_mode": 0o100644,
            "st_size": 0,
            "st_atime": time.time(),
            "st_mtime": time.time(),
            "st_ctime": time.time(),
        }
        return fd

    def open_virtual(self, path: str) -> int:
        """
        打开一个已存在的虚拟文件（对编辑器重新打开 .swp 的响应）。

        Returns:
            虚拟 fd
        """
        fd = self._next_fd
        self._next_fd += 1
        # 复用已有缓冲或创建空缓冲
        existing_buf = None
        for _, (p, buf) in self._buffers.items():
            if p == path:
                existing_buf = buf
                break
        self._buffers[fd] = (path, existing_buf if existing_buf is not None else bytearray())
        return fd

    def is_virtual_fd(self, fd: int) -> bool:
        """判断给定 fd 是否属于虚拟 Overlay 文件。"""
        return fd in self._buffers

    def has_virtual_path(self, path: str) -> bool:
        """判断给定路径是否已有虚拟文件存在。"""
        return path in self._vattrs

    def write_virtual(self, fd: int, data: bytes, offset: int) -> int:
        """
        向虚拟缓冲区写入数据。

        Returns:
            实际写入字节数（满足 POSIX write 契约）
        """
        if fd not in self._buffers:
            return 0
        path, buf = self._buffers[fd]
        end = offset + len(data)
        if end > _MAX_BUFFER_SIZE:
            # 截断到上限，防止内存爆炸
            data = data[: _MAX_BUFFER_SIZE - offset]
            end = _MAX_BUFFER_SIZE
        if end > len(buf):
            buf.extend(b"\x00" * (end - len(buf)))
        buf[offset:end] = data
        # 更新 vattr size
        if path in self._vattrs:
            self._vattrs[path]["st_size"] = len(buf)
            self._vattrs[path]["st_mtime"] = time.time()
        return len(data)

    def read_virtual(self, fd: int, size: int, offset: int) -> bytes:
        """从虚拟缓冲区读取数据。"""
        if fd not in self._buffers:
            return b""
        _, buf = self._buffers[fd]
        return bytes(buf[offset: offset + size])

    def truncate_virtual(self, path: str, length: int) -> None:
        """截断虚拟文件到指定长度。"""
        for fd, (p, buf) in self._buffers.items():
            if p == path:
                if length < len(buf):
                    del buf[length:]
                else:
                    buf.extend(b"\x00" * (length - len(buf)))
                if path in self._vattrs:
                    self._vattrs[path]["st_size"] = length
                return

    def get_virtual_attr(self, path: str) -> Optional[Dict[str, Any]]:
        """获取虚拟文件属性，不存在时返回 None。"""
        return self._vattrs.get(path)

    def release_virtual(self, fd: int) -> None:
        """释放虚拟 fd，丢弃其内存缓冲。"""
        if fd in self._buffers:
            self._buffers.pop(fd)


# ---------------------------------------------------------------------------
# 3. Inode/Dentry LRU 缓存 (InodeDentryLRU)
# ---------------------------------------------------------------------------

#: 默认 LRU 最大容量（条目数）
_DEFAULT_LRU_CAPACITY = 1024

#: 默认缓存 TTL（秒）—— 与 models_observer 保持 5s 一致
_DEFAULT_TTL = 5.0


class InodeDentryLRU:
    """
    热点 Inode/Dentry LRU 缓存。

    缓存 getattr 结果，提升 FUSE 目录遍历性能：
    - capacity 条 LRU 驱逐最旧条目
    - TTL 过期后条目自动失效，强制穿透到 VikingFS 后端刷新
    """

    def __init__(self, capacity: int = _DEFAULT_LRU_CAPACITY, ttl: float = _DEFAULT_TTL) -> None:
        self._capacity = capacity
        self._ttl = ttl
        # key: path, value: (expire_monotonic, attr_dict)
        self._store: "OrderedDict[str, Tuple[float, Dict[str, Any]]]" = OrderedDict()

    def get(self, path: str) -> Optional[Dict[str, Any]]:
        """
        尝试从缓存获取 path 的 getattr 结果。

        Returns:
            属性字典 (有效) 或 None (缺失/已过期)
        """
        if path not in self._store:
            return None
        expire, attrs = self._store[path]
        if time.monotonic() > expire:
            # 已过期，惰性删除
            del self._store[path]
            return None
        # 移到末尾（LRU 更新）
        self._store.move_to_end(path)
        return attrs

    def put(self, path: str, attrs: Dict[str, Any]) -> None:
        """
        将 path 的 getattr 结果存入缓存。

        Args:
            path: FUSE 路径
            attrs: getattr 返回的属性字典
        """
        if path in self._store:
            self._store.move_to_end(path)
        elif len(self._store) >= self._capacity:
            # 淘汰最旧条目
            self._store.popitem(last=False)
        expire = time.monotonic() + self._ttl
        self._store[path] = (expire, attrs)

    def invalidate(self, path: str) -> None:
        """主动使给定路径的缓存条目失效。"""
        self._store.pop(path, None)

    def invalidate_all(self) -> None:
        """清空整个缓存（卸载或强制刷新时使用）。"""
        self._store.clear()

    @property
    def size(self) -> int:
        """当前缓存中的有效条目数（包含可能已过期未被惰性删除的）。"""
        return len(self._store)
