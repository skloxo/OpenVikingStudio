# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill Playground REST Router (Card-167 / Tududi #155).

Exposes zero-side-effect developer endpoints for:
1. Interactive intent hit-testing, KNN margin routing, alias trace, and collision detection
2. Six-Tuple contractual compression simulation and gate checking
3. Six-section standardized SKILL.md scaffolding with inline format validation
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from openviking.core.skill_loader import validate_skill_format
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.skill_aliasing_router import SkillAliasingRouter
from openviking.service.skill_intent_matcher import SkillIntentMatcher
from openviking.service.skill_package_router import SkillPackageRouter
from openviking.service.skill_path_resolver import resolve_skills_root
from openviking.service.skill_zip_engine import SkillZipEngine

router = APIRouter(prefix="/api/v1/skills/playground", tags=["skill-playground"])


class HitTestRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    query: str = Field(..., min_length=1, description="Natural language prompt to test")
    candidate_name: str = Field(default="", description="Optional candidate skill slug")
    candidate_triggers: List[str] = Field(default_factory=list, description="Optional trigger phrases")
    candidate_content: str = Field(default="", description="Optional SKILL.md draft content")
    threshold: float = Field(default=0.60, ge=0.0, le=1.0)
    collision_threshold: float = Field(default=0.80, ge=0.0, le=1.0)


class CompressSimulateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    skill_content: str = Field(..., min_length=1, description="Raw SKILL.md content to compress")
    seed_length: int = Field(default=400, ge=1, description="Seed baseline length for multiplier check")


class PlaygroundScaffoldRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(..., min_length=1, description="Skill identifier (kebab-case)")
    description: str = Field(..., min_length=1, description="Skill purpose and triggering summary")
    domain: str = Field(default="general", description="Target domain")
    triggers: List[str] = Field(default_factory=list, description="Trigger phrases")
    role: str = Field(default="Autonomous Engineering Specialist", description="Agent role persona")
    constraints: List[str] = Field(default_factory=list, description="Hard engineering guardrails")
    tags: List[str] = Field(default_factory=list, description="Classification tags")


def _extract_frontmatter_and_triggers(raw_text: str) -> tuple[Dict[str, Any], List[str]]:
    meta: Dict[str, Any] = {}
    lines = raw_text.splitlines()
    if lines and lines[0].strip() == "---":
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                try:
                    parsed = yaml.safe_load("\n".join(lines[1:idx]))
                    if isinstance(parsed, dict):
                        meta = parsed
                except yaml.YAMLError:
                    meta = {}
                break
    triggers_raw = meta.get("triggers")
    triggers: List[str] = []
    if isinstance(triggers_raw, list):
        triggers = [str(item).strip() for item in triggers_raw if str(item).strip()]
    elif isinstance(triggers_raw, str) and triggers_raw.strip():
        triggers = [t.strip() for t in triggers_raw.split(",") if t.strip()]
    if not triggers:
        desc = str(meta.get("description") or "").strip()
        if desc:
            triggers = [desc]
    return meta, triggers


def _load_skill_catalog(skills_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    root = skills_root or resolve_skills_root()
    if not root.is_dir():
        return []
    catalog: List[Dict[str, Any]] = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        skill_md = entry / "SKILL.md"
        if not entry.is_dir() or not skill_md.is_file():
            continue
        try:
            content = skill_md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        meta, triggers = _extract_frontmatter_and_triggers(content)
        catalog.append(
            {
                "name": str(meta.get("name") or entry.name),
                "dir_name": entry.name,
                "domain": str(meta.get("domain") or entry.name),
                "description": str(meta.get("description") or ""),
                "triggers": triggers or [entry.name],
                "content": content,
            }
        )
    return catalog


@router.post("/hit-test")
async def playground_hit_test(
    req: HitTestRequest,
    _ctx: RequestContext = Depends(get_request_context),
    skills_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run intent match, KNN margin routing, alias projection, and collision checks."""
    del _ctx
    root = skills_root or resolve_skills_root()
    catalog = _load_skill_catalog(root)

    matches: List[Dict[str, Any]] = []
    triggers_by_skill: Dict[str, List[str]] = {}
    for item in catalog:
        triggers = list(item["triggers"])
        triggers_by_skill[item["name"]] = triggers
        res = SkillIntentMatcher.match_intent(req.query, triggers, threshold=req.threshold)
        matches.append(
            {
                "skill_name": item["name"],
                "domain": item["domain"],
                "matched": res.matched,
                "score": round(res.score, 4),
                "best_trigger": res.best_trigger,
                "matched_triggers": res.matched_triggers[:5],
                "reason": res.reason,
            }
        )

    matches.sort(key=lambda m: m["score"], reverse=True)
    top_matches = matches[:5]
    top1_score = top_matches[0]["score"] if top_matches else 0.0
    top2_score = top_matches[1]["score"] if len(top_matches) > 1 else 0.0
    intent_margin = round(max(0.0, top1_score - top2_score), 4)

    candidate_match = None
    if req.candidate_triggers:
        c_res = SkillIntentMatcher.match_intent(
            req.query, req.candidate_triggers, threshold=req.threshold
        )
        candidate_match = c_res.to_dict()

    collision_triggers = req.candidate_triggers or (
        top_matches[0]["matched_triggers"] and [top_matches[0]["best_trigger"]] or []
    )
    peers_for_collision = {
        k: v for k, v in triggers_by_skill.items() if k != req.candidate_name
    }
    collision_report = SkillIntentMatcher.detect_collisions(
        [str(t) for t in collision_triggers if t],
        peers_for_collision,
        threshold=req.collision_threshold,
    )

    pkg_router = SkillPackageRouter(vault_root=root)
    route_target = req.candidate_name.strip() or (
        top_matches[0]["skill_name"] if top_matches else "candidate-skill"
    )
    route_content = req.candidate_content.strip() or f"domain: {route_target}\n{req.query}"
    routing_decision = pkg_router.analyze_routing(route_target, route_content, catalog)

    alias_router = SkillAliasingRouter(skills_root=root)
    alias_lookup_name = req.candidate_name.strip() or (
        top_matches[0]["skill_name"] if top_matches else ""
    )
    alias_resolved = alias_router.resolve(alias_lookup_name) if alias_lookup_name else None
    if alias_resolved and "file_path" in alias_resolved:
        alias_resolved["file_path"] = str(alias_resolved["file_path"])

    return {
        "status": "ok",
        "query": req.query,
        "catalog_size": len(catalog),
        "top1_score": top1_score,
        "top2_score": top2_score,
        "margin": intent_margin,
        "candidate_match": candidate_match,
        "matches": top_matches,
        "collisions": collision_report.to_dict(),
        "routing_decision": {
            "action": routing_decision.action.value,
            "target_package": routing_decision.target_package,
            "top1_candidate": routing_decision.top1_candidate,
            "top1_score": routing_decision.top1_score,
            "top2_candidate": routing_decision.top2_candidate,
            "top2_score": routing_decision.top2_score,
            "margin": routing_decision.margin,
            "rationale": routing_decision.rationale,
        },
        "alias_resolution": alias_resolved,
    }


@router.post("/compress-simulate")
async def playground_compress_simulate(
    req: CompressSimulateRequest,
    _ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Simulate zero-rollout Six-Tuple contractual compression without writing to disk."""
    del _ctx
    engine = SkillZipEngine.get_instance()
    compression = engine.compress(req.skill_content)
    gate = engine.check_gate(req.skill_content, seed_length=req.seed_length)
    return {
        "status": "ok",
        "compression": compression.model_dump(),
        "gate": gate.model_dump(),
    }


@router.post("/scaffold")
async def playground_scaffold(
    req: PlaygroundScaffoldRequest,
    _ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Generate a compliant 6-section Six-Tuple SKILL.md scaffold and run format gate."""
    del _ctx
    slug = req.name.strip().lower().replace(" ", "-")
    triggers_yaml = "\n".join(f"  - \"{t.strip()}\"" for t in req.triggers if t.strip()) or f"  - \"{slug}\""
    tags_yaml = "\n".join(f"  - \"{t.strip()}\"" for t in req.tags if t.strip()) or f"  - \"{req.domain.strip() or 'general'}\""
    constraints = [c.strip() for c in req.constraints if c.strip()] or [
        "单文件代码严格控制在 100~300 行，绝对上限 <= 500 行",
        "NO GREEN EVER：所有 UI 与报告禁止使用绿色系，正常态统一使用 cyan-500",
    ]
    rules_bullets = "\n".join(f"- {c}" for c in constraints)

    sections = [
        "Interface",
        "Workflow",
        "Protocol",
        "Rules",
        "Contracts",
        "Evidence",
    ]
    content = (
        f"---\n"
        f"name: {slug}\n"
        f"description: \"{req.description.strip()}\"\n"
        f"domain: {req.domain.strip() or 'general'}\n"
        f"role: \"{req.role.strip()}\"\n"
        f"tags:\n{tags_yaml}\n"
        f"triggers:\n{triggers_yaml}\n"
        f"---\n\n"
        f"# {slug}\n\n"
        f"> **Role**: {req.role.strip()} — {req.description.strip()}\n\n"
        f"## 1. Interface (接口与入出参)\n"
        f"- **Inputs**: 明确任务上下文、目标 URI 与约束参数\n"
        f"- **Outputs**: 可验证变更产物与结构化验收摘要\n\n"
        f"## 2. Workflow (标准执行工作流)\n"
        f"1. 读取目标上下文与历史决策记录，禁止重复踩坑；\n"
        f"2. 执行规划与隔离校验后再落盘实施；\n"
        f"3. 运行靶向单测与线上探活并交棒验收。\n\n"
        f"## 3. Protocol (状态流转与异常处理协议)\n"
        f"- 发现连续两次同类报错立即熔断止损，输出三行物理事实与互斥选项；\n"
        f"- 外部探针统一绑定短超时，禁止无超时挂死。\n\n"
        f"## 4. Rules (行为红线与负向防御)\n"
        f"{rules_bullets}\n\n"
        f"## 5. Contracts (不变量与规模上限契约)\n"
        f"- 必须保留现有向后兼容接口并确保无明文凭据写入仓库或日志。\n\n"
        f"## 6. Evidence (自动化验证与验收证据)\n"
        f"- 提交靶向 pytest / Vitest 真实执行通过结果与端到端 HTTP 状态证据。\n"
    )
    validation = validate_skill_format(content, strict=True, skill_dir_name=slug)
    return {
        "status": "ok",
        "name": slug,
        "sections": sections,
        "content": content,
        "validation": validation,
    }
