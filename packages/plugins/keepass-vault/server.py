#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeePass Vault FastMCP Server (keepass-vault v1.2.1)
基于官方 keepassxc-cli 打造的本地安全凭据管理与自动化中枢。
支持本地私有 config.json 与环境变量多级解耦，杜绝路径与密码硬编码。
严格遵循第一性原理、Disaster Recovery First (写前必备份) 与严格类型契约。
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from fastmcp import FastMCP

# SECTION: Windows UTF-8 Stdio Safeguard
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

mcp = FastMCP("keepass-vault")

# 1. 优先从本插件私有受保护 config.json 加载
_PLUGIN_DIR = Path(__file__).resolve().parent
_CONFIG_FILE = _PLUGIN_DIR / "config.json"
_LOCAL_CFG: Dict[str, Any] = {}

if _CONFIG_FILE.exists():
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            _LOCAL_CFG = json.load(f)
    except Exception:
        pass


def _get_default_db_candidate() -> str:
    """智能嗅探本地数据库路径：环境变量 > 私有 config.json > 桌面 Key.kdbx > 用户目录 vault.kdbx"""
    env_p = os.environ.get("KPXC_DB_PATH")
    if env_p and os.path.isfile(env_p):
        return env_p

    cfg_p = _LOCAL_CFG.get("kdbx_path") or _LOCAL_CFG.get("db_path")
    if cfg_p and os.path.isfile(os.path.expanduser(cfg_p)):
        return os.path.expanduser(cfg_p)

    desktop_kdbx = Path.home() / "Desktop" / "Key.kdbx"
    if desktop_kdbx.is_file():
        return str(desktop_kdbx)

    return os.path.expanduser("~/vault.kdbx")


DEFAULT_DB_PATH = _get_default_db_candidate()
DEFAULT_KEY_FILE = os.environ.get("KPXC_KEYFILE", _LOCAL_CFG.get("key_file", None))

_pwd_env_name = _LOCAL_CFG.get("password_env", "KPXC_MASTER_KEY")
DEFAULT_MASTER_KEY = (
    os.environ.get(_pwd_env_name, "")
    or _LOCAL_CFG.get("master_key", "")
    or _LOCAL_CFG.get("password", "")
    or os.environ.get("KPXC_MASTER_KEY", "")
    or os.environ.get("KEEPASS_VAULT_PASSWORD", "")
)


def _get_target_db(db_path: Optional[str] = None) -> str:
    path = db_path or DEFAULT_DB_PATH
    return os.path.expanduser(path)


def _auto_backup(db_path: str, max_backups: int = 10) -> Optional[str]:
    """写前物理备份：防止任何写入/修改/删除损坏数据库"""
    if not os.path.isfile(db_path):
        return None
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.{timestamp}.bak"
        shutil.copy2(db_path, backup_path)

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


def _ensure_parent_group(db_path: str, entry_path: str) -> None:
    """如果条目包含多级路径（如 Group/SubGroup/Title），自动递归创建缺失的父级分组"""
    parts = entry_path.strip("/").split("/")
    if len(parts) <= 1:
        return
    current = ""
    for group in parts[:-1]:
        current = f"{current}/{group}" if current else group
        _run_cli(["mkdir", "-q", db_path, current])


def _run_cli(
    cmd_args: List[str],
    password: Optional[str] = None,
    key_file: Optional[str] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """执行 keepassxc-cli 封装并处理安全标准输入 (stdin) 传递主密码"""
    full_args = ["keepassxc-cli"] + cmd_args
    kf = key_file or DEFAULT_KEY_FILE
    if kf and "-k" not in cmd_args and "--key-file" not in cmd_args:
        full_args.extend(["-k", os.path.expanduser(kf)])

    pass_to_send = (password if password is not None else DEFAULT_MASTER_KEY) + "\n"

    try:
        proc = subprocess.Popen(
            full_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout, stderr = proc.communicate(input=pass_to_send, timeout=timeout)
        success = proc.returncode == 0
        return {
            "success": success,
            "returncode": proc.returncode,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
        }
    except FileNotFoundError:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "keepassxc-cli 未安装或未加入系统 PATH。请先安装 KeePassXC 并配置环境变量。",
        }
    except subprocess.TimeoutExpired:
        proc.kill()
        return {
            "success": False,
            "returncode": -2,
            "stdout": "",
            "stderr": f"keepassxc-cli 命令执行超时 ({timeout}s)",
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -3,
            "stdout": "",
            "stderr": f"执行异常: {str(e)}",
        }


# SECTION: 9 大核心 MCP 工具算子

@mcp.tool()
def keepass_status(db_path: Optional[str] = None) -> Dict[str, Any]:
    """检查 KeePass 数据库状态、文件是否存在、cli 是否可用以及主密钥解锁状态。"""
    target = _get_target_db(db_path)
    exists = os.path.isfile(target)
    cli_check = shutil.which("keepassxc-cli") is not None

    status = {
        "db_path": target,
        "db_exists": exists,
        "cli_available": cli_check,
        "has_master_key_configured": bool(DEFAULT_MASTER_KEY),
        "key_file": DEFAULT_KEY_FILE or "None",
        "can_unlock": False,
    }

    if exists and cli_check:
        res = _run_cli(["ls", "-q", target])
        status["can_unlock"] = res["success"]
        if not res["success"]:
            status["unlock_error"] = res["stderr"]
        else:
            # 统计条目总数
            lines = [l for l in res["stdout"].splitlines() if l.strip()]
            status["total_root_entries"] = len(lines)

    return status


@mcp.tool()
def keepass_search(query: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """按标题、URL 或关键词模糊/精确检索数据库条目，返回匹配的条目路径列表。"""
    target = _get_target_db(db_path)
    res = _run_cli(["search", "-q", target, query])
    if not res["success"]:
        return {"error": res["stderr"]}
    lines = [line.strip() for line in res["stdout"].splitlines() if line.strip()]
    return {"query": query, "count": len(lines), "matches": lines}


@mcp.tool()
def keepass_get(
    entry_path: str,
    attributes: Optional[List[str]] = None,
    show_protected: bool = False,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """读取指定条目的详情。默认隐藏受保护属性，显式声明 show_protected=True 时方输出明文密码。"""
    target = _get_target_db(db_path)
    cmd = ["show", target, entry_path]
    if show_protected:
        cmd.append("-s")
    if attributes:
        for attr in attributes:
            cmd.extend(["-a", attr])

    res = _run_cli(cmd)
    if not res["success"]:
        return {"error": res["stderr"]}

    parsed_data: Dict[str, Any] = {}
    for line in res["stdout"].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            parsed_data[k.strip()] = v.strip()
        else:
            if "Raw" not in parsed_data:
                parsed_data["Raw"] = []
            parsed_data["Raw"].append(line.strip())

    return {"entry": entry_path, "attributes": parsed_data}


@mcp.tool()
def keepass_add(
    entry_path: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    url: Optional[str] = None,
    notes: Optional[str] = None,
    generate_password_length: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """在数据库中新增凭据条目。自动递归创建缺失分组，并在写入前自动执行物理安全备份。"""
    target = _get_target_db(db_path)
    backup = _auto_backup(target)
    _ensure_parent_group(target, entry_path)

    cmd = ["add", "-q", target, entry_path]
    if username:
        cmd.extend(["-u", username])
    if url:
        cmd.extend(["--url", url])
    if generate_password_length:
        cmd.extend(["-g", "-L", str(generate_password_length)])
    elif password:
        cmd.extend(["-p"])

    input_text = DEFAULT_MASTER_KEY + "\n"
    if not generate_password_length and password:
        input_text += password + "\n"

    try:
        proc = subprocess.Popen(
            ["keepassxc-cli"] + cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout, stderr = proc.communicate(input=input_text, timeout=15)
        if proc.returncode != 0:
            return {"error": stderr.strip(), "backup": backup}

        if notes:
            _run_cli(["edit", "-q", target, entry_path, "--notes", notes])

        return {"status": "success", "entry": entry_path, "backup": backup}
    except Exception as e:
        return {"error": str(e), "backup": backup}


@mcp.tool()
def keepass_edit(
    entry_path: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    url: Optional[str] = None,
    notes: Optional[str] = None,
    title: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """更新已存在的凭据条目。写入前自动执行物理安全备份。"""
    target = _get_target_db(db_path)
    backup = _auto_backup(target)

    cmd = ["edit", "-q", target, entry_path]
    if username is not None:
        cmd.extend(["-u", username])
    if url is not None:
        cmd.extend(["--url", url])
    if notes is not None:
        cmd.extend(["--notes", notes])
    if title is not None:
        cmd.extend(["-t", title])

    input_text = DEFAULT_MASTER_KEY + "\n"
    if password is not None:
        cmd.extend(["-p"])
        input_text += password + "\n"

    try:
        proc = subprocess.Popen(
            ["keepassxc-cli"] + cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout, stderr = proc.communicate(input=input_text, timeout=15)
        if proc.returncode != 0:
            return {"error": stderr.strip(), "backup": backup}
        return {"status": "success", "entry": entry_path, "backup": backup}
    except Exception as e:
        return {"error": str(e), "backup": backup}


@mcp.tool()
def keepass_rm(entry_path: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """安全删除指定条目或分组。删除前强制执行物理安全备份。"""
    target = _get_target_db(db_path)
    backup = _auto_backup(target)
    res = _run_cli(["rm", "-q", target, entry_path])
    if not res["success"]:
        return {"error": res["stderr"], "backup": backup}
    return {"status": "deleted", "entry": entry_path, "backup": backup}


@mcp.tool()
def keepass_list_tree(group: str = "/", recursive: bool = True, db_path: Optional[str] = None) -> Dict[str, Any]:
    """以树状或扁平结构列出指定分组下的所有子分组与条目。"""
    target = _get_target_db(db_path)
    cmd = ["ls", "-q"]
    if recursive:
        cmd.append("-R")
    cmd.extend([target, group])

    res = _run_cli(cmd)
    if not res["success"]:
        return {"error": res["stderr"]}
    lines = [line.strip() for line in res["stdout"].splitlines() if line.strip()]
    return {"group": group, "count": len(lines), "items": lines}


@mcp.tool()
def keepass_analyze(db_path: Optional[str] = None) -> Dict[str, Any]:
    """数据库健康度体检：审计密码安全强度、检测重复弱口令与过期待办。"""
    target = _get_target_db(db_path)
    res = _run_cli(["analyze", "-q", target])
    if not res["success"]:
        return {"error": res["stderr"]}
    return {"status": "ok", "report": res["stdout"]}


@mcp.tool()
def keepass_export_attachment(
    entry_path: str,
    attachment_name: str,
    output_dir: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """导出存放在条目附件中的私钥文件、证书或配置文件至本地隔离目录。"""
    target = _get_target_db(db_path)
    out_path = Path(output_dir).expanduser().resolve()
    out_path.mkdir(parents=True, exist_ok=True)
    target_file = out_path / attachment_name

    cmd = ["attachment-export", target, entry_path, attachment_name, str(target_file)]
    res = _run_cli(cmd)
    if not res["success"]:
        return {"error": res["stderr"]}
    return {"status": "exported", "entry": entry_path, "attachment": attachment_name, "file_path": str(target_file)}


if __name__ == "__main__":
    mcp.run()
