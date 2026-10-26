#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeePass Vault 物理级生命周期守卫 (VaultGuard Hook v1.2.1)
严格遵循芒格逆向避坑铁律：
1. 纯标准库隔离 (-X utf8 -E -s -S)，零第三方依赖，冷启动 <= 40ms；
2. sys.stdin.readline() 单行流式读取，杜绝父子进程管道死锁；
3. sys.stdout.buffer 原生直写 UTF-8 字节，封闭 stderr；
4. 全流程 BaseException 捕获兜底，退出码恒为 0 (Fail-Open)。
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def _safe_stdout(payload: Dict[str, Any]) -> None:
    try:
        raw_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        sys.stdout.buffer.write(raw_bytes + b"\n")
        sys.stdout.buffer.flush()
    except Exception:
        pass


def _resolve_kdbx_path(tool_args: Dict[str, Any]) -> str:
    # 1. 显式入参优先
    if tool_args.get("db_path"):
        return str(tool_args["db_path"])

    # 2. 环境变量
    env_path = os.environ.get("KPXC_DB_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # 3. 私有 config.json 探测
    home_cfg = Path.home() / ".gemini" / "config" / "plugins" / "keepass-vault" / "config.json"
    if home_cfg.is_file():
        try:
            data = json.loads(home_cfg.read_text(encoding="utf-8"))
            cfg_p = data.get("kdbx_path") or data.get("db_path")
            if cfg_p and os.path.isfile(cfg_p):
                return cfg_p
        except Exception:
            pass

    # 4. 默认桌面路径探测
    desktop_key = Path.home() / "Desktop" / "Key.kdbx"
    if desktop_key.is_file():
        return str(desktop_key)

    return ""


def _perform_pre_write_backup(db_path: str, max_backups: int = 10) -> Optional[str]:
    """写前防抖物理快照：任何写入、修改、删除前强制备份，滚动保留最近 10 份。"""
    if not db_path or not os.path.isfile(db_path):
        return None

    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.{ts}.bak"
        shutil.copy2(db_path, backup_path)

        # 滚动清理超额备份
        backups = sorted(glob.glob(f"{db_path}.*.bak"))
        if len(backups) > max_backups:
            for old in backups[:-max_backups]:
                try:
                    os.remove(old)
                except OSError:
                    pass
        return backup_path
    except Exception:
        return None


def main() -> None:
    # 彻底封闭 stderr 避免控制台 GBK 异常引发宿主 Go 引擎推流白屏
    try:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass

    action = sys.argv[1].lower() if len(sys.argv) > 1 else "pre-tool"

    try:
        # 单行流式读取，严禁无脑 sys.stdin.read() 导致死锁
        line = sys.stdin.readline()
        if not line:
            _safe_stdout({"decision": "allow"})
            return

        payload = json.loads(line)
        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("arguments", {})

        # 针对写操作（add, edit, rm）执行写前物理快照
        if action == "pre-tool" and any(k in tool_name for k in ("add", "edit", "rm", "delete")):
            db_path = _resolve_kdbx_path(tool_args)
            if db_path:
                _perform_pre_write_backup(db_path)

        _safe_stdout({"decision": "allow"})
    except BaseException:
        # 绝对 Fail-Open，恒定放行，保障心流零中断
        _safe_stdout({"decision": "allow"})
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
