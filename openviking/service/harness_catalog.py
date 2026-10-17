# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Catalog discovery of active skills and evolution lessons for System Harness."""

import json
from pathlib import Path
import re

from openviking_cli.utils import get_logger

logger = get_logger(__name__)

CORE_SKILLS_CATALOG = [
    ("diagnosing-bugs", "Diagnosis loop for hard bugs, performance regressions, crashes, exceptions, errors, memory leaks, slow performance, deadlocks"),
    ("tdd", "Test-driven development, red-green-refactor, write unit tests, integration tests, failing test first"),
    ("to-spec", "Turn conversation and requirements into spec and publish to tracker, PRD, specification, roadmap, requirements"),
    ("to-tickets", "Break a plan or spec into tracer-bullet tickets, task cards, workboard tickets"),
    ("codebase-design", "Shared vocabulary for designing deep modules, seam placement, architecture decisions, domain modeling"),
    ("code-review", "Review changes along standards and spec, pull request review, inspect diff, code review"),
    ("resolving-merge-conflicts", "Resolve in-progress git merge or rebase conflicts, git branch conflicts"),
    ("research", "Investigate questions against high-trust primary sources, documentation, technical research"),
    ("prototype", "Build throwaway prototype or demo to answer design question, test UI logic"),
    ("openviking-studio-dev", "OpenViking Studio frontend and backend development, SSOT, NO GREEN EVER, fastmcp, monitoring"),
    ("master-dev", "General code development, refactoring, architecture design, and standards enforcement"),
    ("auto-pr", "Automated PR creation, testing, conflict resolution, git tags, and release SOP"),
    ("triage", "Move issues and external PRs through a state machine of triage roles, categorize, verify"),
    ("improve-codebase-architecture", "Scan a codebase for deepening opportunities, architectural report"),
    ("openviking-memory-benchmark", "Benchmark telemetry and recall rate evaluation for OpenViking memory"),
    ("openviking-model-evaluator", "Model evaluation and admission benchmarking in thinking separation mode"),
    ("skill-state-fsm", "Deterministic finite state machine protocol for agent long-horizon execution"),
    ("wikiskill-evolution", "Knowledge distillation and lessons learned persistence protocol into master memory"),
]


def _load_all_evolution_lessons() -> list[dict]:
    lessons = []
    next_id = 1

    mem_dir = Path.home() / ".openviking" / "data" / "viking" / "default" / "resources" / "master_memory" / "evolution_lessons"
    if mem_dir.is_dir():
        for f in sorted(mem_dir.glob("**/*.md")):
            if f.name.startswith("."):
                continue
            try:
                content = f.read_text(encoding="utf-8")
                title = f.stem
                context = ""
                reflection = ""
                lesson = ""

                m_title = re.search(r"^#\s*(?:Evolution Lesson:\s*)?(.+)$", content, re.MULTILINE)
                if m_title:
                    title = m_title.group(1).strip()

                m_ctx = re.search(r"-\s*\*\*Context\*\*:\s*(.+)", content, re.IGNORECASE)
                if m_ctx:
                    context = m_ctx.group(1).strip()

                m_ref = re.search(r"##\s*🔍\s*Reflection.*?\n([\s\S]*?)(?=##|$)", content)
                if m_ref:
                    reflection = m_ref.group(1).strip()

                m_les = re.search(r"##\s*📜\s*Permanent Guidelines.*?\n([\s\S]*?)(?=##|$)", content)
                if m_les:
                    lesson = m_les.group(1).strip()

                lessons.append({
                    "id": next_id,
                    "title": title,
                    "context": context or f"Recorded from master memory: {f.name}",
                    "reflection": reflection or "Master Memory snapshot evolution.",
                    "lesson": lesson or content[:200],
                    "source": f"master_memory/{f.name}",
                })
                next_id += 1
            except Exception as e:
                logger.debug(f"Failed to parse lesson file {f}: {e}")

    skill_files = [
        Path.home() / ".gemini" / "config" / "skills" / "openviking-studio-dev" / "SKILL.md",
        Path("/home/skloxo/aho/openclaw/project/OpenVikingStudio/.agents/skills/openviking-studio-dev/SKILL.md"),
        Path("/home/skloxo/aho/openclaw/project/.agents/skills/openviking-studio-dev/SKILL.md"),
    ]
    for sf in skill_files:
        if sf.is_file():
            try:
                text = sf.read_text(encoding="utf-8")
                pattern = r"####\s*📌\s*Lesson\s+([^\n]+)\n([\s\S]*?)(?=####\s*📌\s*Lesson|$)"
                for m in re.finditer(pattern, text):
                    raw_title = m.group(1).strip()
                    block = m.group(2)

                    ctx = ""
                    ref = ""
                    les = ""
                    m_c = re.search(r"-\s*\*\*CONTEXT\*\*[:：]\s*(.+)", block)
                    if m_c:
                        ctx = m_c.group(1).strip()
                    m_r = re.search(r"-\s*\*\*REFLECTION\*\*[:：]\s*(.+)", block)
                    if m_r:
                        ref = m_r.group(1).strip()
                    m_l = re.search(r"-\s*\*\*LESSON\*\*[:：]\s*(.+)", block)
                    if m_l:
                        les = m_l.group(1).strip()

                    t_clean = re.sub(r"^\d{4}-\d{2}-\d{2}\s*(?:#\d+)?[:：]?\s*", "", raw_title)

                    lessons.append({
                        "id": next_id,
                        "title": t_clean or raw_title,
                        "context": ctx or f"From {sf.parent.name}",
                        "reflection": ref or "Reflexion continuous evolution.",
                        "lesson": les or "Clean and faithful execution.",
                        "source": str(sf),
                    })
                    next_id += 1
                break
            except Exception as e:
                logger.debug(f"Failed to parse skill lessons {sf}: {e}")

    return lessons


def _get_active_skills_catalog() -> list[tuple[str, str, str]]:
    skills = []
    all_skills_file = Path.home() / ".openviking" / "all_skills.json"
    if all_skills_file.is_file():
        try:
            with open(all_skills_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    name = item.get("name", "")
                    desc = item.get("description", "")
                    path = item.get("path", "")
                    if name and desc:
                        skills.append((name, desc, path))
        except Exception:
            pass
    if not skills:
        for name, desc in CORE_SKILLS_CATALOG:
            skills.append((name, desc, f"/home/skloxo/.gemini/config/skills/{name}/SKILL.md"))
    return skills


def get_harness_fsm_meta() -> dict:
    """Return runtime metadata for Harness State FSM."""
    from openviking.core.harness_fsm import HarnessFSM, HarnessState

    return {
        "states": [s.value for s in HarnessState],
        "current_state": "IDLE",
        "active_state": "IDLE",
        "transition_rules_count": sum(len(v) for v in HarnessFSM.TRANSITION_GRAPH.values()),
        "pipeline": [
            {"id": "SPEC_INGEST", "label": "规格摄取", "desc": "任务规格冻结与输入三元组校验 (Spec P Ingestion)", "role": "Orchestrator"},
            {"id": "DECOMPOSE", "label": "工单拆解", "desc": "Tracer-Bullet 工单拆解与 DAG 依赖编排", "role": "Orchestrator"},
            {"id": "DISPATCH", "label": "专业分发", "desc": "角色隔离沙箱分配 (Orchestrator != Specialist)", "role": "Orchestrator"},
            {"id": "RUNNING", "label": "执行生成", "desc": "沙箱代码生成与工具调用拦截", "role": "Specialist"},
            {"id": "VERIFY", "label": "物理验真", "desc": "真实物理 Diff + 测试视网膜执行门禁", "role": "MultiMetricGate"},
            {"id": "EVALUATE", "label": "独立评审", "desc": "生成者与评估者物理防串通 (Generator != Evaluator)", "role": "Independent Evaluator"},
            {"id": "CHECKPOINT", "label": "状态快照", "desc": "不可变 SHA-256 检查点落盘", "role": "Harness Trace"},
            {"id": "COMPLETED", "label": "交付归档", "desc": "版本回溯与 Git Tag 物理留痕", "role": "Release SOP"},
        ],
        "exceptions": [
            {"id": "BLOCKED", "label": "护栏拦截", "desc": "防偷懒省略 / 超大读取物理阻断", "type": "guard"},
            {"id": "RECOVERING", "label": "自愈重试", "desc": "三元故障恢复与预算自愈", "type": "retry"},
            {"id": "FAILED", "label": "熔断终止", "desc": "不可逆错误熔断阻断", "type": "terminal"},
        ],
    }


HARNESS_GATES_META = {
    "physical_diff": {
        "name": "物理增量代码门禁 (Physical Diff Gate)",
        "status": "active",
        "badge": "Active Invariant",
        "description": "严格剔除纯空格与纯注释伪变更，断言物理有效改动行 > 0",
        "rules": ["min_effective_lines >= 1", "comment_only_filtered", "whitespace_filtered", "git_tree_asserted"],
    },
    "test_retina": {
        "name": "测试视网膜反欺诈门禁 (Anti-Cheat Retina)",
        "status": "active",
        "badge": "Active Invariant",
        "description": "拦截 false exit 0 假绿灯，真实校验 passed > 0 且 failed == 0",
        "rules": ["real_process_execution", "test_report_parsed", "false_exit_zero_blocked", "duration_tracked"],
    },
    "anti_lazy": {
        "name": "防偷懒代码省略占位符护栏 (Anti-Lazy Code Guard)",
        "status": "active",
        "badge": "Active Invariant",
        "description": "AST 与正则实时扫描，物理封杀 pass、# TODO、...、NotImplementedError",
        "rules": ["prohibit_pass_stub", "prohibit_todo_stub", "prohibit_ellipsis", "zero_omission_tolerance"],
    },
    "role_separation": {
        "name": "生成与评估角色隔离 (Role Separation)",
        "status": "active",
        "badge": "Active Invariant",
        "description": "物理隔离生成者与评估者，防止智能体自问自答自批改作弊",
        "rules": ["generator_not_evaluator", "checkpoint_sha256_verified", "dual_axis_standards_spec"],
    },
    "cpa_teacher_guard": {
        "name": "CPA 教师模型守卫拦截器 (CPA Teacher Model Guard)",
        "status": "active",
        "badge": "Active Invariant",
        "description": "毫秒级物理拦截工兵任务/批量并发滥用昂贵教师模型 (GPT/Claude)，确保教师零泄漏、工兵高吞吐",
        "rules": [
            "teacher_models_restricted_to_deadlock_and_tradeoff",
            "worker_pool_unlimited_throughput",
            "pre_tool_interception_sub_2ms",
            "discovery_to_card_proposal_enforced",
        ],
    },
}

