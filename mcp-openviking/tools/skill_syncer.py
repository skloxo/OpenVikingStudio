# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: tools.skill_syncer ──────────────────────────────────────────────
"""
用途: 智能体技能自动扫描、JSON资产导出与 VikingFS 缺失技能常态化自动补齐入库守护
依赖: _core.config
被调用: tools.skills, mcp_openviking_server.py
"""

import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict

from _core.config import (
    _get_skill_base_sources,
    _infer_skill_source,
    _parse_skill_description,
    http_client,
)

logger = logging.getLogger("openviking-mcp")

_ingest_lock = threading.Lock()


def _desensitize_text(text: str) -> str:
    if not text:
        return ""
    try:
        from openviking.privacy.privacy_masker import mask_text

        text = mask_text(text)
    except Exception:
        text = re.sub(r"sk-[a-zA-Z0-9_-]{24,}", "sk-[REDACTED_API_KEY]", text)
        text = re.sub(r"ghp_[a-zA-Z0-9_-]{24,}", "ghp_[REDACTED_TOKEN]", text)
    # Mask arbitrary sensitive credential fragments dynamically
    secret_pat = os.environ.get("OV_TEST_SECRET_PATTERN", "")
    if secret_pat:
        text = text.replace(secret_pat, "[REDACTED_PASSWORD]")
    return text


def _extract_frontmatter_metadata(content: str) -> tuple[list[str], list[str]]:
    tags: list[str] = []
    allowed_tools: list[str] = []
    if not content.startswith("---"):
        return tags, allowed_tools
    parts = content.split("---", 2)
    if len(parts) < 3:
        return tags, allowed_tools

    fm = parts[1]
    in_tags = False
    in_tools = False
    for line in fm.splitlines():
        sline = line.strip()
        if sline.startswith("tags:"):
            in_tags = True
            in_tools = False
        elif sline.startswith("allowed-tools:") or sline.startswith("allowed_tools:"):
            in_tools = True
            in_tags = False
        elif sline.startswith("- ") and in_tags:
            tags.append(sline[2:].strip().strip("\"'"))
        elif sline.startswith("- ") and in_tools:
            allowed_tools.append(sline[2:].strip().strip("\"'"))
        elif ":" in sline:
            in_tags = False
            in_tools = False
    return tags, allowed_tools


def _scan_skill_directory_files(root: str) -> list[dict[str, Any]]:
    skill_files: list[dict[str, Any]] = []
    for r_sub, _, filenames in os.walk(root):
        rel_root = os.path.relpath(r_sub, root)
        if rel_root != ".":
            skill_files.append({
                "name": os.path.basename(r_sub),
                "path": rel_root,
                "is_dir": True,
                "kind": "directory"
            })
        for fn in sorted(filenames):
            if fn.startswith("."):
                continue
            file_rel_path = os.path.join(rel_root, fn) if rel_root != "." else fn
            kind = "definition" if fn == "SKILL.md" else (
                "auxiliary" if fn.endswith((".md", ".sh", ".py")) else "file"
            )
            skill_files.append({
                "name": fn,
                "path": file_rel_path,
                "is_dir": False,
                "kind": kind
            })
    return skill_files


def _auto_ingest_missing_to_vikingfs(found_skills: Dict[str, Dict[str, Any]]):
    """检测本地合规技能是否已收录入 VikingFS，如缺失则后台原子补齐入库"""
    if not _ingest_lock.acquire(blocking=False):
        return

    try:
        res = http_client.get("/api/v1/skills")
        if not isinstance(res, dict) or res.get("status") != "ok":
            return
        viking_skills = {
            s["name"] for s in res.get("result", {}).get("skills", [])
            if isinstance(s, dict) and "name" in s
        }

        # 仅对已合规、具备非空 description 且未收录的技能发起补齐
        missing: list[tuple[str, str]] = []
        for name, item in found_skills.items():
            if name in viking_skills:
                continue
            if name.startswith(".") or name in ("skills", "scripts", "bin", "lib", "src", "public", "__pycache__"):
                continue
            desc = item.get("description", "").strip()
            if not desc or desc == "暂无简介":
                continue
            content = item.get("content", "").strip()
            if not content:
                continue
            missing.append((name, content))

        if not missing:
            return

        logger.info("发现 %d 个本地技能未收录至 Wiki 技能中心，正在自动补齐入库...", len(missing))
        for name, content in missing:
            try:
                payload = {
                    "data": content,
                    "target_uri": "viking://agent/skills"
                }
                sub_res = http_client.post("/api/v1/skills", payload)
                if isinstance(sub_res, dict) and sub_res.get("status") == "ok":
                    logger.info("已自动补齐技能收录至 Wiki 技能中心: %s", name)
                else:
                    logger.warning("自动收录技能返回异常 (%s): %s", name, sub_res)
            except Exception as item_err:
                logger.warning("自动收录技能失败 (%s): %s", name, item_err)
            time.sleep(1.0)
    except Exception as e:
        logger.debug("比对并入库缺失技能异常: %s", e)
    finally:
        _ingest_lock.release()


def _auto_sync_skills():
    """自动探针：全量递归扫描技能目录，导出 JSON 并自动补齐收录至 VikingFS"""
    try:
        target_base = os.path.expanduser("~/.openviking/skills")
        os.makedirs(target_base, exist_ok=True)

        base_sources = _get_skill_base_sources()
        found: Dict[str, Dict[str, Any]] = {}

        for base in base_sources:
            if not os.path.exists(base):
                continue
            for root, dirs, files in os.walk(base):
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith(".") and d not in (
                        "node_modules", ".git", ".cache", ".npm",
                        "cleanup-backup", "fastapi", ".venv", "dist",
                        "build", ".next", "__pycache__"
                    )
                ]
                if "SKILL.md" in files:
                    dirs[:] = []
                    skill_name = os.path.basename(root)
                    skill_md = os.path.join(root, "SKILL.md")
                    if skill_name not in found:
                        link_path = os.path.join(target_base, skill_name)
                        if not os.path.exists(link_path):
                            try:
                                os.symlink(root, link_path)
                            except Exception:
                                pass
                        desc = _desensitize_text(_parse_skill_description(skill_md))
                        source = _infer_skill_source(skill_name, root)
                        scope = "user" if "gemini" in root else "agent"
                        content = ""
                        try:
                            with open(skill_md, "r", encoding="utf-8", errors="ignore") as fp:
                                content = _desensitize_text(fp.read())
                        except Exception:
                            pass

                        tags, allowed_tools = _extract_frontmatter_metadata(content)
                        skill_files = _scan_skill_directory_files(root)

                        found[skill_name] = {
                            "name": skill_name,
                            "description": desc,
                            "source": source,
                            "path": root,
                            "uri": f"viking://user/skills/{skill_name}/SKILL.md",
                            "scope": scope,
                            "content": content,
                            "files": skill_files,
                            "tags": tags,
                            "allowedTools": allowed_tools,
                        }

        all_skills = list(found.values())
        json_path = os.path.expanduser("~/.openviking/all_skills.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_skills, f, ensure_ascii=False, indent=2)

        cwd_public = Path.cwd() / "public" / "all_skills.json"
        if cwd_public.parent.exists():
            with open(cwd_public, "w", encoding="utf-8") as f:
                json.dump(all_skills, f, ensure_ascii=False, indent=2)

        # 启动后台异步线程执行差集比对与入库补齐，不阻塞主流程
        threading.Thread(
            target=_auto_ingest_missing_to_vikingfs,
            args=(found,),
            daemon=True,
            name="skill-auto-ingest"
        ).start()

    except Exception as e:
        logger.warning("技能自动同步异常: %s", e)


def _periodic_skill_sync_loop(interval_sec: int = 300):
    """周期性长效自愈守护循环：每 5 分钟巡检一次本地技能并自动收录"""
    while True:
        try:
            _auto_sync_skills()
        except Exception as e:
            logger.debug("周期性技能巡检异常: %s", e)
        time.sleep(interval_sec)


def start_skill_sync_worker():
    """启动技能同步与常驻守护后台线程"""
    threading.Thread(
        target=_auto_sync_skills,
        daemon=True,
        name="skill-sync-initial"
    ).start()
    threading.Thread(
        target=_periodic_skill_sync_loop,
        daemon=True,
        name="skill-sync-daemon"
    ).start()
