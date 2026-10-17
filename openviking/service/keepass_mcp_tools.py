# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
KeePass Vault MCP Tools Hub (keepass-vault v1.1.0).
SSOT: docs/architecture/ATOMIC_TASK_CARDS_MATRIX.md -> TASK-PLUG-VAULT-MCP

First Principles:
1. "Credential SSOT": All agent operations access credentials through KeePassXC Vault.
2. "Disaster Recovery First": Write operations automatically create a pre-write backup (.bak).
3. "Defensive Parameter Binding": Flexibly accepts query/queries, path/entry_path for diverse LLM calling styles.
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from openviking_cli.utils import get_logger

logger = get_logger(__name__)


def _load_env_fallback():
    candidates = [
        os.path.expanduser("~/.config/keepass-vault/vault.env"),
        os.path.expanduser("~/.openviking/vault.env"),
    ]
    for env_file in candidates:
        if os.path.isfile(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            if k.strip() not in os.environ:
                                os.environ[k.strip()] = v.strip()
            except Exception:
                pass


_load_env_fallback()

DEFAULT_DB_PATH = os.environ.get("KPXC_DB_PATH", os.path.expanduser("~/vault.kdbx"))
DEFAULT_KEY_FILE = os.environ.get("KPXC_KEYFILE", None)
DEFAULT_MASTER_KEY = os.environ.get("KPXC_MASTER_KEY", "")


def _get_target_db(db_path: Optional[str] = None) -> str:
    path = db_path or os.environ.get("KPXC_DB_PATH") or DEFAULT_DB_PATH
    return os.path.expanduser(path)


def _auto_backup(db_path: str, max_backups: int = 10) -> Optional[str]:
    """写前物理备份：防止任何写入/修改/删除损坏数据库"""
    if not os.path.isfile(db_path):
        return None
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


def _ensure_parent_group(db_path: str, entry_path: str) -> None:
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
    master_key = password if password is not None else os.environ.get("KPXC_MASTER_KEY", DEFAULT_MASTER_KEY)
    k_file = key_file or os.environ.get("KPXC_KEYFILE", DEFAULT_KEY_FILE)

    full_cmd = ["keepassxc-cli"] + cmd_args
    if k_file and os.path.isfile(k_file):
        full_cmd.extend(["-k", k_file])

    try:
        proc = subprocess.Popen(
            full_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(input=f"{master_key}\n" if master_key else None, timeout=timeout)
        return {
            "success": proc.returncode == 0,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "returncode": proc.returncode,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
        }


def register_keepass_mcp_tools(mcp: Any, annotations: Any = None) -> None:
    """向 FastMCP 端点注入 keepass-vault 插件的标准原子 MCP 工具。"""
    tool_kw = {"annotations": annotations} if annotations is not None else {}

    # 1. keepass_status: 状态探针
    @mcp.tool(**tool_kw)
    async def keepass_status(db_path: Optional[str] = None) -> str:
        """检查凭据保险箱状态、数据库连通性、主密钥配置与物理备份记录。"""
        path = _get_target_db(db_path)
        exists = os.path.isfile(path)
        size_bytes = os.path.getsize(path) if exists else 0
        backups = glob.glob(f"{path}.*.bak")
        master_configured = bool(os.environ.get("KPXC_MASTER_KEY", DEFAULT_MASTER_KEY))

        unlocked = False
        info_str = ""
        if exists and master_configured:
            res = _run_cli(["db-info", "-q", path])
            unlocked = res["success"]
            info_str = res["stdout"] if res["success"] else res["stderr"]

        res_dict = {
            "db_path": path,
            "exists": exists,
            "size_bytes": size_bytes,
            "backup_count": len(backups),
            "auth_configured": master_configured,
            "unlocked": unlocked,
            "info": info_str[:300] if info_str else ("Database ready" if unlocked else "Locked/Unconfigured"),
        }
        return json.dumps(res_dict, ensure_ascii=False, indent=2)

    # 2. keepass_search: 模糊搜索条目
    @mcp.tool(**tool_kw)
    async def keepass_search(
        query: Optional[Union[str, List[str]]] = None,
        queries: Optional[Union[str, List[str]]] = None,
        db_path: Optional[str] = None,
    ) -> str:
        """全局搜索凭据库条目（支持服务名、域名、用户名或分组模糊匹配）。返回匹配的条目路径列表。"""
        target_q = ""
        for candidate in (query, queries):
            if isinstance(candidate, str) and candidate.strip():
                target_q = candidate.strip()
                break
            elif isinstance(candidate, (list, tuple)) and candidate:
                val = candidate[0]
                first = val.strip() if isinstance(val, str) else str(val).strip()
                if first:
                    target_q = first
                    break

        if not target_q:
            return "=== KeePass Search: No query provided ==="

        path = _get_target_db(db_path)
        res = _run_cli(["search", "-q", path, target_q])
        if not res["success"]:
            return f"=== KeePass Search Failed ===\nError: {res['stderr']}"

        entries = [line.strip() for line in res["stdout"].splitlines() if line.strip()]
        if not entries:
            return f"=== KeePass Search: 0 entries found for '{target_q}' ==="

        lines = [f"=== KeePass Search Results ({len(entries)} entries found for '{target_q}') ==="]
        for idx, entry in enumerate(entries, 1):
            lines.append(f"[{idx}] {entry}")
        lines.append("\n💡 提示：使用 keepass_get(entry_path=\"<条目路径>\") 获取该条目的账号密码明文。")
        return "\n".join(lines)

    # 3. keepass_get: 获取条目凭据详情
    @mcp.tool(**tool_kw)
    async def keepass_get(
        entry_path: Optional[str] = None,
        path: Optional[str] = None,
        show_password: bool = True,
        get_totp: bool = False,
        db_path: Optional[str] = None,
    ) -> str:
        """安全读取指定条目的凭据明文（包含用户名、密码、URL、完整备注 Notes 以及 TOTP 动态码）。"""
        target_entry = (entry_path or path or "").strip()
        if not target_entry:
            return "=== KeePass Get: entry_path is required ==="

        db = _get_target_db(db_path)
        cmd = ["show", "-q", "--all"]
        if show_password:
            cmd.append("-s")
        cmd.extend([db, target_entry])

        res = _run_cli(cmd)
        if not res["success"]:
            return f"=== KeePass Get Failed for '{target_entry}' ===\nError: {res['stderr']}"

        attrs: Dict[str, str] = {}
        for line in res["stdout"].splitlines():
            if ": " in line:
                k, v = line.split(": ", 1)
                attrs[k.strip()] = v.strip()

        # 针对 Notes、UserName、Password、URL 原生精准提取
        notes_res = _run_cli(["show", "-q", "-s", "-a", "Notes", db, target_entry])
        full_notes = notes_res["stdout"] if notes_res["success"] else attrs.get("Notes", attrs.get("notes", ""))

        username = attrs.get("UserName", attrs.get("username", ""))
        if not username:
            u_res = _run_cli(["show", "-q", "-a", "UserName", db, target_entry])
            if u_res["success"]:
                username = u_res["stdout"].strip()

        password = "******"
        if show_password:
            p_res = _run_cli(["show", "-q", "-s", "-a", "Password", db, target_entry])
            password = p_res["stdout"].strip() if p_res["success"] else attrs.get("Password", attrs.get("password", ""))

        url = attrs.get("URL", attrs.get("url", ""))
        if not url:
            url_res = _run_cli(["show", "-q", "-a", "URL", db, target_entry])
            if url_res["success"]:
                url = url_res["stdout"].strip()

        totp_code = None
        if get_totp:
            totp_res = _run_cli(["show", "-q", "-t", db, target_entry])
            if totp_res["success"]:
                totp_code = totp_res["stdout"].strip()

        result_payload = {
            "success": True,
            "entry_path": target_entry,
            "username": username,
            "password": password,
            "url": url,
            "notes": full_notes,
            "totp": totp_code,
        }
        return json.dumps(result_payload, ensure_ascii=False, indent=2)

    # 4. keepass_add: 新增条目
    @mcp.tool(**tool_kw)
    async def keepass_add(
        entry_path: str,
        username: str,
        password: Optional[str] = None,
        url: Optional[str] = None,
        notes: Optional[str] = None,
        auto_generate: bool = False,
        password_length: int = 24,
        db_path: Optional[str] = None,
    ) -> str:
        """新增凭据条目（支持自动生成 >=20 位高熵密码，写前自动触发物理备份）。"""
        target_db = _get_target_db(db_path)
        backup_file = _auto_backup(target_db)
        _ensure_parent_group(target_db, entry_path)

        cmd = ["add", "-q", "-u", username]
        if url:
            cmd.extend(["--url", url])
        if notes:
            cmd.extend(["--notes", notes])

        if auto_generate or not password:
            cmd.extend(["-g", "-L", str(password_length), "-l", "-U", "-n", "-s"])
        else:
            cmd.append("-p")

        cmd.extend([target_db, entry_path])

        pass_input = None
        if not auto_generate and password:
            master_key = os.environ.get("KPXC_MASTER_KEY", DEFAULT_MASTER_KEY)
            pass_input = f"{master_key}\n{password}\n{password}"

        res = _run_cli(cmd, password=pass_input)
        if not res["success"]:
            return json.dumps({"success": False, "error": res["stderr"], "backup": backup_file}, ensure_ascii=False)

        return json.dumps({
            "success": True,
            "entry_path": entry_path,
            "username": username,
            "backup_created": backup_file,
            "message": "Entry created successfully",
        }, ensure_ascii=False, indent=2)

    # 5. keepass_edit: 修改条目
    @mcp.tool(**tool_kw)
    async def keepass_edit(
        entry_path: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        url: Optional[str] = None,
        notes: Optional[str] = None,
        db_path: Optional[str] = None,
    ) -> str:
        """修改已有条目属性（写前自动触发物理备份）。"""
        target_db = _get_target_db(db_path)
        backup_file = _auto_backup(target_db)

        cmd = ["edit", "-q"]
        if username is not None:
            cmd.extend(["-u", username])
        if url is not None:
            cmd.extend(["--url", url])
        if notes is not None:
            cmd.extend(["--notes", notes])
        if password is not None:
            cmd.append("-p")
        cmd.extend([target_db, entry_path])

        pass_input = None
        if password is not None:
            master_key = os.environ.get("KPXC_MASTER_KEY", DEFAULT_MASTER_KEY)
            pass_input = f"{master_key}\n{password}\n{password}"

        res = _run_cli(cmd, password=pass_input)
        return json.dumps({
            "success": res["success"],
            "error": res["stderr"] if not res["success"] else None,
            "backup_created": backup_file,
        }, ensure_ascii=False, indent=2)

    # 6. keepass_rm: 删除条目
    @mcp.tool(**tool_kw)
    async def keepass_rm(entry_path: str, db_path: Optional[str] = None) -> str:
        """删除指定凭据条目（写前自动触发物理备份）。"""
        target_db = _get_target_db(db_path)
        backup_file = _auto_backup(target_db)
        res = _run_cli(["rm", "-q", target_db, entry_path])
        return json.dumps({
            "success": res["success"],
            "error": res["stderr"] if not res["success"] else None,
            "backup_created": backup_file,
        }, ensure_ascii=False, indent=2)

    # 7. keepass_list_tree: 查看层级树
    @mcp.tool(**tool_kw)
    async def keepass_list_tree(group: str = "/", db_path: Optional[str] = None) -> str:
        """列出指定分组或根目录下的条目拓扑树。"""
        target_db = _get_target_db(db_path)
        target_group = group.strip("/")
        cmd = ["ls", "-q", "-R", target_db]
        if target_group:
            cmd.append(target_group)

        res = _run_cli(cmd)
        if not res["success"]:
            return json.dumps({"success": False, "error": res["stderr"], "items": []}, ensure_ascii=False)

        items = [line.strip() for line in res["stdout"].splitlines() if line.strip()]
        return json.dumps({"success": True, "group": group, "count": len(items), "items": items}, ensure_ascii=False, indent=2)

    # 8. keepass_analyze: 弱密审计
    @mcp.tool(**tool_kw)
    async def keepass_analyze(hibp_file: Optional[str] = None, db_path: Optional[str] = None) -> str:
        """安全审计：检测数据库中的弱密码、重复密码及安全隐患。"""
        target_db = _get_target_db(db_path)
        h_file = os.path.expanduser(hibp_file) if hibp_file else "/dev/null"
        res = _run_cli(["analyze", "-q", "-H", h_file, target_db])
        return res["stdout"] if res["success"] else f"KeePass Analyze Error: {res['stderr']}"

    logger.info("Successfully registered 8 keepass-vault MCP tools into FastMCP endpoint")
