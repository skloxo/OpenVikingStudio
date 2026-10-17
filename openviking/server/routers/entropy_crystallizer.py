# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
REST Endpoints for Tri-Gate Memory Entropy Crystallization & SSOT Distillation.
(Card-Memory-EntropyCrystallizer-TriGate / v1.5.33)
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.entropy_crystallizer import (
    MemoryFragment,
    EntropyCrystallizer,
    TriGateRejectionError,
)
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/memory/crystallize", tags=["entropy-crystallizer"])


class EvaluateRequest(BaseModel):
    fragments: List[MemoryFragment] = Field(..., description="Candidate memory fragments to test against tri-gate")


class DistillRequest(BaseModel):
    fragments: List[MemoryFragment] = Field(..., description="Candidate memory fragments passing tri-gate")
    axiom: str = Field(..., description="L0: Core single declarative statement of truth")
    version_range: str = Field(">= v1.5.00", description="L1: Target applicable version range")
    deprecated_patterns: List[str] = Field(default_factory=list, description="L2: Deprecated patterns to repulse")
    forbidden_keywords: List[str] = Field(default_factory=list, description="L2: Forbidden keywords to repulse")
    distiller_id: Optional[str] = Field(None, description="Identifier of commander/distiller agent")


@router.post("/evaluate")
async def evaluate_fragments_tri_gate(
    req: EvaluateRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """
    Evaluate candidate fragments against the parallel tri-gate barrier:
    1. Cluster size >= 5
    2. Cosine similarity > 0.75
    3. Cooling period >= 24h
    """
    crystallizer = EntropyCrystallizer.get_instance()
    try:
        eval_result = crystallizer.evaluate_tri_gate(req.fragments)
        return {"status": "ok", "result": eval_result.model_dump()}
    except Exception as e:
        logger.error(f"Failed to evaluate tri-gate barrier: {e}")
        raise HTTPException(status_code=500, detail=f"Tri-gate evaluation error: {e}")


@router.post("/distill")
async def distill_immutable_crystal(
    req: DistillRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """
    Distill candidate fragments into a 3-tier immutable FactCrystal (L0 Axiom, L1 Bounds, L2 Repulsion),
    and atomically supersede source fragments to achieve net physical entropy reduction.
    """
    crystallizer = EntropyCrystallizer.get_instance()
    distiller = req.distiller_id or (ctx.user.user_id if ctx.user else "commander@antigravity")

    try:
        distill_result = crystallizer.distill_crystal(
            fragments=req.fragments,
            axiom=req.axiom,
            version_range=req.version_range,
            deprecated_patterns=req.deprecated_patterns,
            forbidden_keywords=req.forbidden_keywords,
            distiller_id=distiller,
        )
        return {"status": "ok", "result": distill_result.model_dump()}
    except TriGateRejectionError as e:
        logger.warning(f"Tri-gate barrier blocked distillation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to distill fact crystal: {e}")
        raise HTTPException(status_code=500, detail=f"Distillation internal error: {e}")


@router.get("/stats")
async def get_crystallization_stats(
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """
    Retrieve operational metrics for memory entropy crystallization and net node reduction.
    """
    crystallizer = EntropyCrystallizer.get_instance()
    return {"status": "ok", "result": crystallizer.get_stats()}


@router.get("/crystals")
async def list_fact_crystals(
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """
    List all distilled immutable fact crystals currently active (memory + disk).
    """
    from pathlib import Path
    import re
    crystallizer = EntropyCrystallizer.get_instance()
    crystals_map: Dict[str, Dict[str, Any]] = {c.uri: c.model_dump() for c in crystallizer.list_crystals()}

    # Scan disk directories to ensure complete persistence parity across server restarts
    crystals_dirs = [
        Path.home() / ".openviking" / "data" / "viking" / "default" / "resources" / "master_memory" / "crystals",
        Path.home() / ".openviking" / "data" / "viking" / "default" / "resources" / "crystals",
    ]
    for c_dir in crystals_dirs:
        if not c_dir.exists():
            continue
        for fpath in c_dir.glob("*.md"):
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                m_uri = re.search(r"^---[\s\S]*?uri:\s*[\"']?([^\"'\n\r]+)[\"']?[\s\S]*?---", content)
                uri = m_uri.group(1).strip() if m_uri else f"viking://resources/master_memory/crystals/{fpath.name}"
                if uri not in crystals_map:
                    m_title = re.search(r"^#\s+([^\n\r]+)", content, re.MULTILINE)
                    title = m_title.group(1).strip() if m_title else fpath.stem
                    m_distilled = re.search(r"distilled_at:\s*([0-9\.]+)", content)
                    distilled_at = float(m_distilled.group(1)) if m_distilled else fpath.stat().st_mtime
                    
                    # Extract axioms and boundaries
                    axioms = re.findall(r"## 💎[^\n]+\n\n((?:- [^\n]+\n?)+)", content)
                    parsed_axioms = [line.strip("- ").strip() for line in axioms[0].strip().splitlines()] if axioms else [title]
                    
                    bounds = re.findall(r"## 🚫[^\n]+\n\n((?:- [^\n]+\n?)+)", content)
                    parsed_bounds = [line.strip("- 🚫 ").strip() for line in bounds[0].strip().splitlines()] if bounds else []

                    sources = re.findall(r"## 🔗[^\n]+\n\n((?:- [^\n]+\n?)+)", content)
                    parsed_sources = [line.strip("- `").strip("`").strip() for line in sources[0].strip().splitlines()] if sources else []

                    crystals_map[uri] = {
                        "uri": uri,
                        "axiom": parsed_axioms[0] if parsed_axioms else title,
                        "context_bounds": {
                            "version_range": ">= v1.6.0",
                            "source_uris": parsed_sources,
                            "evidence_hashes": [],
                            "distilled_at": distilled_at,
                            "distiller_id": "dream_recipe_distiller",
                        },
                        "negative_boundary": {
                            "deprecated_patterns": parsed_bounds,
                            "forbidden_keywords": [],
                        },
                        "status": "active",
                        "created_at": distilled_at,
                    }
            except Exception as e:
                logger.debug(f"Failed to parse disk crystal {fpath}: {e}")

    return {"status": "ok", "result": list(crystals_map.values())}


@router.get("/detail")
async def get_fact_crystal_detail(
    uri: str,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """
    Retrieve full structured details of a single Fact Crystal or Master Knowledge Card.
    """
    res = await list_fact_crystals(ctx=ctx)
    all_crystals = res.get("result", [])
    
    target_clean = uri.strip()
    for c in all_crystals:
        if c.get("uri") == target_clean or c.get("uri", "").endswith(target_clean.split("/")[-1]):
            return {"status": "ok", "result": c}
            
    raise HTTPException(status_code=404, detail=f"Fact crystal not found for URI: {uri}")

