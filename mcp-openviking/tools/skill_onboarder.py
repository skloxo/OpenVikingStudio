# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: tools.skill_onboarder ─────────────────────────────────────────
"""
用途: 技能 AI 规约生成器与单并发限流保护队列 (Rate-Limited Queue)
依赖: 标准库, urllib
被调用: tools.skills
"""

# SECTION: Imports
import json
import logging
import os
import queue
import threading
import time
from typing import Callable, List, Optional
import urllib.request
from urllib.request import Request, urlopen

logger = logging.getLogger("openviking-mcp")

# SECTION: AI Skill Spec Generator
def generate_ai_skill_md(dir_path: str) -> str:
    """使用 LLM (gpt-oss-120b) 深度分析目录代码与文档，自动生成符合 Wiki 规范的 SKILL.md 规约"""
    skill_name = os.path.basename(dir_path)
    sample_texts = []
    files = []
    try:
        for root, dirs, fnames in os.walk(dir_path):
            if any(skip in root for skip in ["node_modules", ".git", ".cache", ".npm", "cleanup-backup", ".venv"]):
                continue
            for fn in fnames:
                if fn.startswith("."):
                    continue
                rel = os.path.relpath(os.path.join(root, fn), dir_path)
                files.append(rel)
                if fn.endswith((".md", ".py", ".ts", ".js", ".json", ".sh")) and len(sample_texts) < 3:
                    try:
                        with open(os.path.join(root, fn), "r", encoding="utf-8", errors="ignore") as f:
                            sample_texts.append(f"{rel}:\n" + f.read(500))
                    except Exception:
                        pass
    except Exception:
        pass

    context = "\n".join(sample_texts)
    prompt = f"""请为 AI Agent 技能模块 "{skill_name}" 生成一份符合 OpenViking Wiki 规范的 SKILL.md 文件。
文件最开头必须包含 YAML frontmatter (包含 name 和 description 两个必填字段)。
目录中的文件包括: {files[:10]}
文件内容片段:
{context[:1000]}

请输出完整的 SKILL.md 内容，仅输出 Markdown 代码，不要输出额外沟通文字。"""

    vlm_key = "sk-fbb21afbe35d09986ac6f66ca91f66f4dee6b2536319be7347759f02de8f6227"
    try:
        req_data = json.dumps({
            "model": "gpt-oss-120b",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 600,
        }).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {vlm_key}",
        }
        req = Request("http://127.0.0.1:8317/v1/chat/completions", data=req_data, headers=headers, method="POST")
        with urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices", [])
            if choices and isinstance(choices[0], dict):
                msg = choices[0].get("message", {})
                content = (msg.get("content", "") if isinstance(msg, dict) else str(msg)).strip()
                if content.startswith("```markdown"):
                    content = content.split("```markdown", 1)[1].rsplit("```", 1)[0].strip()
                elif content.startswith("```"):
                    content = content.split("```", 1)[1].rsplit("```", 1)[0].strip()
                if content and "name:" in content:
                    return content
                elif content:
                    return f"---\nname: {skill_name}\ndescription: {skill_name} module specification.\n---\n\n# {skill_name.replace('-', ' ').title()} SOP\n\n{content}\n"
    except Exception as e:
        logger.warning(f"AI 生成 SKILL.md 失败，使用基础模板 fallback: {e}")

    return f"""---
name: {skill_name}
description: Standardized SOP and execution guidelines for {skill_name} module.
---

# {skill_name.replace('-', ' ').title()} SOP

本文档为 {skill_name} 模块的标准化技能规约。当用户提及相关功能或操作时自动触发。
"""

# SECTION: Rate-Limited Asynchronous Skill Onboarding Queue
class SkillOnboardingQueue:
    def __init__(self, rate_limit_delay: float = 1.2, sync_callback: Optional[Callable] = None):
        self.task_queue = queue.Queue()
        self.rate_limit_delay = rate_limit_delay
        self.sync_callback = sync_callback
        self.lock = threading.Lock()
        self.is_running = False
        self.worker_thread = None
        self.stats = {
            "total_enqueued": 0,
            "processed_count": 0,
            "failed_count": 0,
            "current_item": None,
            "status": "idle",
            "last_active_timestamp": 0.0,
            "last_error": None,
        }

    def start_worker_if_needed(self):
        with self.lock:
            if not self.is_running:
                self.is_running = True
                self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
                self.worker_thread.start()

    def enqueue_dirs(self, dir_paths: List[str]) -> List[str]:
        enqueued = []
        with self.lock:
            for d in dir_paths:
                self.task_queue.put(d)
                self.stats["total_enqueued"] += 1
                enqueued.append(d)
        self.start_worker_if_needed()
        return enqueued

    def _worker_loop(self):
        logger.info("限流技能上架队列 Worker 启动 (Rate-limited Queue Worker)...")
        while True:
            try:
                dir_path = self.task_queue.get(timeout=20)
            except queue.Empty:
                with self.lock:
                    self.is_running = False
                    self.stats["status"] = "idle"
                    self.stats["current_item"] = None
                logger.info("限流技能上架队列已空，Worker 恢复空闲。")
                break

            skill_name = os.path.basename(dir_path)
            with self.lock:
                self.stats["status"] = "processing"
                self.stats["current_item"] = skill_name
                self.stats["last_active_timestamp"] = time.time()

            try:
                skill_md_path = os.path.join(dir_path, "SKILL.md")
                if not os.path.exists(skill_md_path):
                    spec_content = generate_ai_skill_md(dir_path)
                    with open(skill_md_path, "w", encoding="utf-8") as f:
                        f.write(spec_content)

                if self.sync_callback:
                    self.sync_callback()

                with self.lock:
                    self.stats["processed_count"] += 1
            except Exception as e:
                logger.warning(f"队列处理技能失败 ({skill_name}): {e}")
                with self.lock:
                    self.stats["failed_count"] += 1
                    self.stats["last_error"] = str(e)
            finally:
                self.task_queue.task_done()
                time.sleep(self.rate_limit_delay)


ONBOARDING_QUEUE = SkillOnboardingQueue(rate_limit_delay=1.2)
