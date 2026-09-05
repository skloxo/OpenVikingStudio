# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: tools.skills ──────────────────────────────────────────────────
"""
用途: 智能体技能生命周期治理、规范审计、自动收录与演进 Lesson 存盘
依赖: _core.config, tools.observability, tools.skill_onboarder
被调用: mcp_openviking_server.py
"""

# SECTION: Imports
import json
import logging
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List
from pydantic import Field
from mcp.server.fastmcp import FastMCP
from _core.config import (
    _get_skill_base_sources,
    _infer_skill_source,
    _parse_skill_description,
    _make_error,
    _format_result,
    http_client,
)
from .observability import HARNESS_METRICS, _record_harness_call
from .skill_onboarder import ONBOARDING_QUEUE, generate_ai_skill_md

logger = logging.getLogger("openviking-mcp")

# SECTION: Auto Sync Skills
def _auto_sync_skills():
    """自动探针：全量递归扫描 IDE/OpenClaw/Gemini/Project 技能目录，生成全量带简介的 ~/.openviking/all_skills.json"""
    try:
        target_base = os.path.expanduser("~/.openviking/skills")
        os.makedirs(target_base, exist_ok=True)

        base_sources = _get_skill_base_sources()
        found = {}
        for base in base_sources:
            if not os.path.exists(base):
                continue
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", ".git", ".cache", ".npm", "cleanup-backup", "fastapi", ".venv", "dist", "build", ".next", "__pycache__")]
                if "SKILL.md" in files:
                    skill_name = os.path.basename(root)
                    skill_md = os.path.join(root, "SKILL.md")
                    if skill_name not in found:
                        link_path = os.path.join(target_base, skill_name)
                        if not os.path.exists(link_path):
                            try:
                                os.symlink(root, link_path)
                            except Exception:
                                pass
                        desc = _parse_skill_description(skill_md)
                        source = _infer_skill_source(skill_name, root)
                        scope = "user" if "gemini" in root else "agent"
                        content = ""
                        try:
                            with open(skill_md, "r", encoding="utf-8", errors="ignore") as fp:
                                content = fp.read()
                        except Exception:
                            pass

                        skill_files = []
                        try:
                            for r_sub, d_sub, filenames in os.walk(root):
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
                                    kind = "definition" if fn == "SKILL.md" else ("auxiliary" if fn.endswith(".md") or fn.endswith(".sh") or fn.endswith(".py") else "file")
                                    skill_files.append({
                                        "name": fn,
                                        "path": file_rel_path,
                                        "is_dir": False,
                                        "kind": kind
                                    })
                        except Exception:
                            pass

                        found[skill_name] = {
                            "name": skill_name,
                            "description": desc,
                            "source": source,
                            "path": root,
                            "uri": f"viking://user/skills/{skill_name}/SKILL.md",
                            "scope": scope,
                            "content": content,
                            "files": skill_files
                        }

        all_skills = list(found.values())
        json_path = os.path.expanduser("~/.openviking/all_skills.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_skills, f, ensure_ascii=False, indent=2)

        cwd_public = Path.cwd() / "public" / "all_skills.json"
        if cwd_public.parent.exists():
            with open(cwd_public, "w", encoding="utf-8") as f:
                json.dump(all_skills, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"技能自动同步异常: {e}")


# 关联回调并启动守护线程
ONBOARDING_QUEUE.sync_callback = _auto_sync_skills
threading.Thread(target=_auto_sync_skills, daemon=True, name="skill-sync").start()

# SECTION: Tool Registration
def register_skills_tools(mcp: FastMCP, mcp_tool: Callable) -> Dict[str, Callable]:
    registered: Dict[str, Callable] = {}

    @mcp_tool()
    def openviking_record_evolution_lesson(
        skill_name: str = Field(description="目标演进技能名称（例如 diagnosing-bugs, tdd 等）"),
        lesson_title: str = Field(description="Lesson 简短标题（概括踩坑教训与物理原则）"),
        context: str = Field(default="", description="触发纠偏的上下文场景"),
        reflection: str = Field(default="", description="根因与物理逻辑分析"),
        lesson: str = Field(default="", description="提炼出的永久闭环规范"),
    ) -> str:
        """Harness Reflexion 隐式自演进钩子：自动写入本地 SKILL.md 归档 Lesson，并双写纯 Markdown 镜像至 OpenViking Master Memory 永久存盘"""
        try:
            mcp_mod = sys.modules.get("mcp_openviking_server")
            active_os = getattr(mcp_mod, "os", os)
            active_http = getattr(mcp_mod, "http_client", http_client) or http_client

            candidate_paths = []
            if active_os.path.exists(skill_name):
                candidate_paths.append(Path(skill_name))

            home = Path.home()
            cwd = Path.cwd()
            candidate_paths.extend([
                cwd / ".agents" / "skills" / skill_name / "SKILL.md",
                cwd / "skills" / skill_name / "SKILL.md",
                cwd / "openclaw" / "skills" / skill_name / "SKILL.md",
                home / ".agents" / "skills" / skill_name / "SKILL.md",
                home / ".gemini" / "config" / "skills" / skill_name / "SKILL.md",
                home / ".openclaw" / "skills" / skill_name / "SKILL.md",
            ])
            local_written_file = None
            lesson_entry = f"\n\n#### 📌 Lesson {time.strftime('%Y-%m-%d')}：{lesson_title}\n- **CONTEXT**：{context}\n- **REFLECTION**：{reflection}\n- **LESSON**：{lesson}\n"
            for p in candidate_paths:
                if p.exists() or active_os.path.exists(str(p)):
                    with open(p, "a", encoding="utf-8") as f:
                        f.write(lesson_entry)
                    local_written_file = str(p)
                    break

            clean_slug = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]+', '_', lesson_title).strip('_').lower()
            if not clean_slug:
                clean_slug = "lesson"
            date_str = time.strftime('%Y%m%d_%H%M%S')
            mirror_filename = f"{date_str}_{skill_name}_{clean_slug}.md"
            master_uri = f"viking://resources/master_memory/evolution_lessons/{mirror_filename}"

            mirror_content = f"""# Evolution Lesson: {lesson_title}
- **Skill**: `{skill_name}`
- **Recorded At**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Context**: {context}

## 🔍 Reflection & Root Cause Analysis
{reflection}

## 📜 Permanent Guidelines & Lesson
{lesson}
"""
            mirror_status = "skipped"
            try:
                res = active_http.post("/api/v1/content/write", {
                    "uri": master_uri,
                    "content": mirror_content,
                    "mode": "create"
                })
                if isinstance(res, dict) and (res.get("status") == "ok" or "result" in res):
                    mirror_status = "synced"
                else:
                    mirror_status = f"response: {res}"
            except Exception as write_err:
                mirror_status = f"error: {str(write_err)}"

            HARNESS_METRICS["lessons_count"] = HARNESS_METRICS.get("lessons_count", 0) + 1
            HARNESS_METRICS["most_evolved_skill"] = skill_name
            _record_harness_call("store", actor_peer="antigravity")

            return _format_result({
                "status": "ok",
                "message": f"成功归档 Lesson '{lesson_title}' 至 {skill_name} 并镜像入脑 Master Memory",
                "lessons_count": HARNESS_METRICS["lessons_count"],
                "most_evolved_skill": skill_name,
                "local_written_file": local_written_file,
                "master_memory_uri": master_uri,
                "mirror_status": mirror_status,
            })
        except Exception as e:
            return _format_result({"status": "error", "error": str(e)})
    registered["openviking_record_evolution_lesson"] = openviking_record_evolution_lesson

    @mcp_tool()
    def openviking_skills(
        action: str = Field(description="操作：list（列出）/ add（添加）"),
        name: str = Field(default="", description="技能名称（add 时必填）"),
        description: str = Field(default="", description="技能描述（add 时必填）"),
        content: str = Field(default="", description="技能内容（Markdown）"),
        tags: str = Field(default="", description="标签（逗号分隔）"),
    ) -> str:
        """技能管理：列出或添加技能"""
        if action == "list":
            result = http_client.get("/api/v1/skills")
            return _format_result(result)
        elif action == "add":
            if not name or not description:
                return _make_error("添加技能需要 name 和 description")
            body: Dict[str, Any] = {"name": name, "description": description}
            if content:
                body["content"] = content
            if tags:
                body["tags"] = [t.strip() for t in tags.split(",")]
            result = http_client.post("/api/v1/skills", body)
            return _format_result(result)
        else:
            return _make_error(f"无效操作: {action}。可选: list, add")
    registered["openviking_skills"] = openviking_skills

    @mcp_tool()
    def openviking_audit_skills() -> str:
        """物理白盒审计本地技能与模型目录：透视符合 Wiki 规范技能与待规范模型/技能，标识来源 Agent (v1.1.24)"""
        try:
            base_sources = _get_skill_base_sources()
            compliant_dict = {}
            non_compliant_dict = {}

            for base in base_sources:
                if not os.path.exists(base):
                    continue
                for root, dirs, files in os.walk(base):
                    if any(skip in root for skip in ["node_modules", ".git", ".cache", ".npm", "cleanup-backup", "fastapi", ".venv"]):
                        continue
                    skill_name = os.path.basename(root)
                    source = _infer_skill_source(skill_name, root)
                    if "SKILL.md" in files:
                        skill_md = os.path.join(root, "SKILL.md")
                        desc = _parse_skill_description(skill_md)
                        is_valid_desc = bool(desc and desc.strip() and desc.strip() != "暂无简介")
                        if is_valid_desc:
                            if skill_name not in compliant_dict:
                                compliant_dict[skill_name] = {
                                    "name": skill_name,
                                    "path": root,
                                    "source": source,
                                    "description": desc,
                                    "status": "compliant"
                                }
                        else:
                            if skill_name not in compliant_dict and skill_name not in non_compliant_dict:
                                non_compliant_dict[skill_name] = {
                                    "name": skill_name,
                                    "path": root,
                                    "source": source,
                                    "description": "❌ 缺失或未填规范的 description 简介",
                                    "status": "non_compliant",
                                    "missing_reason": "❌ 缺失 description 头部元数据",
                                    "can_auto_fix": True
                                }
                    elif ("skills" in root.lower() or "agent" in root.lower()) and len(files) > 0:
                        if skill_name not in compliant_dict and skill_name not in non_compliant_dict and skill_name != "skills":
                            non_compliant_dict[skill_name] = {
                                "name": skill_name,
                                "path": root,
                                "source": source,
                                "description": "❌ 缺失 SKILL.md 规范文本",
                                "status": "non_compliant",
                                "missing_reason": "❌ 缺失 SKILL.md 规范文本",
                                "can_auto_fix": True
                            }

            compliant = list(compliant_dict.values())
            non_compliant = list(non_compliant_dict.values())

            return _format_result({
                "status": "ok",
                "total_scanned": len(compliant) + len(non_compliant),
                "compliant_count": len(compliant),
                "non_compliant_count": len(non_compliant),
                "compliant_skills": compliant,
                "non_compliant_skills": non_compliant
            })
        except Exception as e:
            return _make_error(str(e))
    registered["openviking_audit_skills"] = openviking_audit_skills

    @mcp_tool()
    def openviking_auto_onboard_skills(
        limit: int = Field(default=10, description="单批次自动规范上架的最大技能数量"),
        async_queue: bool = Field(default=True, description="是否使用限流队列后台异步处理（推荐 True 防止打爆接口与超时）"),
        rate_limit_delay_sec: float = Field(default=1.2, description="每个技能生成与上架之间的强制冷却秒数（防限流）"),
    ) -> str:
        """全自动发现新技能/模型，通过【单并发+强制冷却限流队列】调用 LLM 规范化生成 SKILL.md 并上架至 OpenViking (v1.1.26)"""
        try:
            base_sources = _get_skill_base_sources()
            non_compliant_dirs = []

            for base in base_sources:
                if not os.path.exists(base):
                    continue
                for root, dirs, files in os.walk(base):
                    if any(skip in root for skip in ["node_modules", ".git", ".cache", ".npm", "cleanup-backup", "fastapi", ".venv"]):
                        continue
                    skill_name = os.path.basename(root)
                    if ("skills" in root.lower() or "agent" in root.lower()) and len(files) > 0 and skill_name != "skills":
                        if "SKILL.md" not in files:
                            non_compliant_dirs.append(root)
                        else:
                            skill_md_p = os.path.join(root, "SKILL.md")
                            desc = _parse_skill_description(skill_md_p)
                            if not desc or desc.strip() == "" or desc.strip() == "暂无简介":
                                non_compliant_dirs.append(root)

            target_dirs = non_compliant_dirs[:limit]

            if async_queue:
                ONBOARDING_QUEUE.rate_limit_delay = rate_limit_delay_sec
                enqueued = ONBOARDING_QUEUE.enqueue_dirs(target_dirs)
                return _format_result({
                    "status": "ok",
                    "mode": "async_rate_limited_queue",
                    "message": f"已成功将 {len(enqueued)} 个待规范技能推入【限流保护队列】！正在后台逐一调用 LLM 生成规范并同步上架。",
                    "discovered_candidates_count": len(non_compliant_dirs),
                    "enqueued_count": len(enqueued),
                    "rate_limit_delay_sec": rate_limit_delay_sec,
                    "queue_status": {
                        "pending_items": ONBOARDING_QUEUE.task_queue.qsize(),
                        "worker_status": ONBOARDING_QUEUE.stats["status"]
                    }
                })
            else:
                onboarded = []
                for d in target_dirs:
                    skill_name = os.path.basename(d)
                    skill_md_path = os.path.join(d, "SKILL.md")
                    try:
                        spec_content = generate_ai_skill_md(d)
                        with open(skill_md_path, "w", encoding="utf-8") as f:
                            f.write(spec_content)
                        onboarded.append({
                            "name": skill_name,
                            "path": d,
                            "skill_md": skill_md_path,
                            "status": "onboarded_successfully"
                        })
                    except Exception as w_err:
                        logger.warning(f"写入 SKILL.md 失败 ({d}): {w_err}")
                    time.sleep(rate_limit_delay_sec)

                _auto_sync_skills()

                return _format_result({
                    "status": "ok",
                    "mode": "sync_sequential",
                    "message": f"已顺序完成 {len(onboarded)} 个新技能规范上架！",
                    "discovered_candidates_count": len(non_compliant_dirs),
                    "onboarded_count": len(onboarded),
                    "onboarded_skills": onboarded
                })
        except Exception as e:
            return _make_error(str(e))
    registered["openviking_auto_onboard_skills"] = openviking_auto_onboard_skills

    @mcp_tool()
    def openviking_get_onboard_queue_status() -> str:
        """获取技能自动上架限流队列的实时运行状态与进度 (v1.1.26)"""
        with ONBOARDING_QUEUE.lock:
            return _format_result({
                "status": "ok",
                "queue_worker_status": ONBOARDING_QUEUE.stats["status"],
                "pending_queue_size": ONBOARDING_QUEUE.task_queue.qsize(),
                "total_enqueued": ONBOARDING_QUEUE.stats["total_enqueued"],
                "processed_count": ONBOARDING_QUEUE.stats["processed_count"],
                "failed_count": ONBOARDING_QUEUE.stats["failed_count"],
                "current_item": ONBOARDING_QUEUE.stats["current_item"],
                "last_active_timestamp": ONBOARDING_QUEUE.stats["last_active_timestamp"],
                "rate_limit_delay_sec": ONBOARDING_QUEUE.rate_limit_delay
            })
    registered["openviking_get_onboard_queue_status"] = openviking_get_onboard_queue_status

    @mcp_tool()
    def openviking_fix_skill(skill_name: str = Field(description="要进行规范化修复上架的技能名称")) -> str:
        """一键规范化未完工技能并上架到 OpenViking 向量库 (v1.1.25)"""
        try:
            base_sources = _get_skill_base_sources()
            target_dir = None
            for base in base_sources:
                if not os.path.exists(base):
                    continue
                for root, dirs, files in os.walk(base):
                    if os.path.basename(root) == skill_name:
                        target_dir = root
                        break
                if target_dir:
                    break

            if not target_dir:
                return _make_error(f"找不到技能目录: {skill_name}")

            skill_md = os.path.join(target_dir, "SKILL.md")
            if not os.path.exists(skill_md):
                spec_content = generate_ai_skill_md(target_dir)
                with open(skill_md, "w", encoding="utf-8") as f:
                    f.write(spec_content)

            _auto_sync_skills()
            return _format_result({
                "status": "ok",
                "message": f"技能 {skill_name} 已成功规范化并同步上架至 OpenViking 存储池！",
                "skill_name": skill_name,
                "skill_md_path": skill_md
            })
        except Exception as e:
            return _make_error(str(e))
    registered["openviking_fix_skill"] = openviking_fix_skill

    return registered
