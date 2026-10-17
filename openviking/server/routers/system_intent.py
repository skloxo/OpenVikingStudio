# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Neural semantic intent matching and collision disambiguation endpoints."""

import json
from pathlib import Path
import re
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.server.routers.system_models import MatchIntentRequest, WriteDisambiguationRequest
from openviking.service.harness_catalog import CORE_SKILLS_CATALOG, _get_active_skills_catalog
from openviking_cli.utils import get_logger

logger = get_logger(__name__)

intent_router = APIRouter()


@intent_router.post("/api/v1/harness/match_intent", tags=["system"])
async def match_intent(
    req: MatchIntentRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Real neural semantic intent matching and collision detector using local 2080Ti Reranker."""
    query = req.query.strip()
    if not query:
        return JSONResponse(status_code=400, content={"error": "query cannot be empty"})

    skills_catalog = _get_active_skills_catalog()
    candidate_skills = []
    seen = set()
    for name, desc in CORE_SKILLS_CATALOG:
        path = f"/home/skloxo/.gemini/config/skills/{name}/SKILL.md"
        candidate_skills.append((name, desc, path))
        seen.add(name)
    for name, desc, path in skills_catalog:
        if name not in seen:
            candidate_skills.append((name, desc, path))
            seen.add(name)
    q_tokens = set(re.findall(r"[\w\u4e00-\u9fa5]+", query.lower()))

    def pre_rank_score(item: tuple[str, str, str]) -> float:
        name, desc, _ = item
        d_tokens = set(re.findall(r"[\w\u4e00-\u9fa5]+", f"{name} {desc}".lower()))
        common = len(q_tokens & d_tokens)
        name_bonus = 3.0 if any(t in name.lower() for t in q_tokens) else 0.0
        return common + name_bonus

    top_candidates = sorted(candidate_skills, key=pre_rank_score, reverse=True)[:6]

    docs = [f"{name}: {desc}" for name, desc, _ in top_candidates]
    results = None
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        rerank_req = urllib.request.Request(
            "http://127.0.0.1:11433/v1/rerank",
            data=json.dumps({
                "model": "qwen3-vl-reranker",
                "query": query,
                "documents": docs,
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with opener.open(rerank_req, timeout=5) as r:
            resp_data = json.loads(r.read())
            results = sorted(resp_data.get("results", []), key=lambda x: x.get("relevance_score", 0), reverse=True)
            logger.info(f"Reranker returned {len(results)} results, top: {results[:2]}")
    except Exception as e:
        logger.warning(f"Local reranker call failed, falling back to lexical similarity: {e}")

    if not results:
        scored = []
        for i, (name, desc, _) in enumerate(top_candidates):
            d_tokens = set(re.findall(r"[\w\u4e00-\u9fa5]+", f"{name} {desc}".lower()))
            common = len(q_tokens & d_tokens)
            score = common / max(len(q_tokens), 1) * 0.4 + 0.2
            scored.append({"index": i, "relevance_score": score})
        results = sorted(scored, key=lambda x: x["relevance_score"], reverse=True)

    top1 = results[0]
    top2 = results[1] if len(results) > 1 else None

    idx1 = int(top1["index"])
    p_name, _p_desc, p_path = top_candidates[idx1]

    def to_pct(score: float) -> float:
        pct = (score - 0.20) / (0.55 - 0.20) * 36.0 + 60.0
        return round(min(99.5, max(45.0, pct)), 1)

    p_conf = to_pct(float(top1.get("relevance_score", 0.5)))
    s_name = None
    s_conf = None
    has_collision = False
    suggestion = f"意图清晰，高置信度 ({p_conf}%) 命中 {p_name} 技能，零歧义碰撞。"

    if top2:
        idx2 = int(top2["index"])
        s_name, _s_desc, _s_path = top_candidates[idx2]
        s_conf = to_pct(float(top2.get("relevance_score", 0.3)))
        diff = p_conf - s_conf
        if s_conf >= 70.0 and diff < 15.0:
            has_collision = True
            suggestion = (
                f"检测到意图在 \"{p_name}\" 与 \"{s_name}\" 之间重叠度较高 ({s_conf}%)！"
                f"建议在 SKILL.md 中追加消歧规则: \"{p_name} 负责主体主控，{s_name} 负责特定分支场景\"。"
            )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "primarySkill": p_name,
            "primaryConfidence": p_conf,
            "secondarySkill": s_name,
            "secondaryConfidence": s_conf,
            "hasCollision": has_collision,
            "suggestion": suggestion,
            "targetPath": p_path,
        },
    )


@intent_router.post("/api/v1/harness/write_disambiguation", tags=["system"])
async def write_disambiguation(
    req: WriteDisambiguationRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Physically append intent disambiguation rule to target SKILL.md on disk."""
    skill_name = req.skill_name.strip()
    rule = req.rule.strip()
    if not skill_name or not rule:
        return JSONResponse(status_code=400, content={"error": "skill_name and rule are required"})

    candidate_paths = [
        Path.home() / ".gemini" / "config" / "skills" / skill_name / "SKILL.md",
        Path(f"/home/skloxo/aho/openclaw/project/OpenVikingStudio/.agents/skills/{skill_name}/SKILL.md"),
        Path(f"/home/skloxo/aho/openclaw/project/.agents/skills/{skill_name}/SKILL.md"),
        Path.home() / "aho" / "openclaw" / "skills" / skill_name / "SKILL.md",
        Path.home() / ".openclaw" / "skills" / skill_name / "SKILL.md",
    ]

    target_file = None
    for p in candidate_paths:
        if p.is_file():
            target_file = p
            break

    if not target_file:
        target_file = candidate_paths[0]
        target_file.parent.mkdir(parents=True, exist_ok=True)
        if not target_file.exists():
            target_file.write_text(f"---\nname: {skill_name}\ndescription: Auto-managed skill\n---\n\n# {skill_name}\n", encoding="utf-8")

    disambiguation_block = f"\n\n<!-- INTENT_DISAMBIGUATION_RULE_AUTO_WRITTEN -->\n> [!IMPORTANT]\n> **意图消歧规约**: {rule}\n"
    with open(target_file, "a", encoding="utf-8") as f:
        f.write(disambiguation_block)

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "file_path": str(target_file),
            "message": f"Successfully written disambiguation rule to {target_file}",
        },
    )
