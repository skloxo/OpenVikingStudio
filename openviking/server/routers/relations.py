# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Relations endpoints for OpenViking HTTP Server."""

from typing import Any, List, Optional, Union

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from openviking.core.path_variables import resolve_path_variables
from openviking.server.auth import get_request_context
from openviking.server.dependencies import get_service, get_service_or_none
from openviking.server.identity import RequestContext
from openviking.server.models import Response


def _resolve_uri_or_uris(uri: Union[str, List[str]]) -> Union[str, List[str]]:
    """Resolve path variables in a single URI or list of URIs."""
    if isinstance(uri, list):
        return [resolve_path_variables(u) for u in uri]
    return resolve_path_variables(uri)


router = APIRouter(prefix="/api/v1/relations", tags=["relations"])


class LinkRequest(BaseModel):
    """Request model for link."""

    from_uri: str
    to_uris: Union[str, List[str]]
    reason: str = ""


class UnlinkRequest(BaseModel):
    """Request model for unlink."""

    from_uri: str
    to_uri: str


@router.get("")
async def relations(
    uri: str = Query(..., description="Viking URI"),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Get relations for a resource."""
    service = get_service()
    uri = resolve_path_variables(uri)
    result = await service.relations.relations(uri, ctx=_ctx)
    return Response(status="ok", result=result)


@router.post("/link")
async def link(
    request: LinkRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Create link between resources."""
    service = get_service()
    from_uri = resolve_path_variables(request.from_uri)
    to_uris = _resolve_uri_or_uris(request.to_uris)
    await service.relations.link(from_uri, to_uris, ctx=_ctx, reason=request.reason)
    return Response(status="ok", result={"from": from_uri, "to": to_uris})


@router.delete("/link")
async def unlink(
    request: UnlinkRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Remove link between resources."""
    service = get_service()
    from_uri = resolve_path_variables(request.from_uri)
    to_uri = resolve_path_variables(request.to_uri)
    await service.relations.unlink(from_uri, to_uri, ctx=_ctx)
    return Response(status="ok", result={"from": from_uri, "to": to_uri})


class BuildGraphRequest(BaseModel):
    """Request model for build_graph."""

    space_uris: List[str]
    output_uri: str


@router.post("/build_graph")
async def build_graph(
    request: BuildGraphRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Generate a self-contained HTML graph from multiple memory roots into one output file."""
    from openviking.session.memory.graph_view import MemoryGraph

    service = get_service()
    space_uris = [resolve_path_variables(uri) for uri in request.space_uris]
    output_uri = resolve_path_variables(request.output_uri)
    graph = MemoryGraph(viking_fs=service.viking_fs)
    graph_path = await graph.build_graph(space_uris, output_uri, ctx=_ctx)
    return Response(status="ok", result={"graph_uri": graph_path})


@router.get("/topology")
async def get_topology(
    limit: int = Query(300, description="Max node limit", le=1000),
    service: Optional[Any] = Depends(get_service_or_none),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Get live topology nodes and relations across peers, skills, sessions, and memory resources."""
    if service is None:
        service = get_service_or_none()

    peers = [
        {"id": "viking://peers/antigravity@2080ti", "label": "Peer: 2080Ti Antigravity", "category": "peers", "role": "本地坐镇主控"},
        {"id": "viking://peers/antigravity@rtx3070", "label": "Peer: RTX3070 Antigravity", "category": "peers", "role": "远程哨兵代理"},
        {"id": "viking://peers/openclaw@2080ti", "label": "Peer: 2080Ti OpenClaw", "category": "peers", "role": "集群协同总线"},
        {"id": "viking://peers/workbuddy@rtx3070", "label": "Peer: RTX3070 WorkBuddy", "category": "peers", "role": "远程协同助手"},
        {"id": "viking://peers/macstudio", "label": "Peer: Mac Studio M3", "category": "peers", "role": "集群算力中心"},
        {"id": "viking://peers/xiaomimo@2080ti", "label": "Peer: 2080Ti XiaomiMo", "category": "peers", "role": "终端接入客户端"},
        {"id": "viking://peers/hermes@2080ti", "label": "Peer: 2080Ti Hermes", "category": "peers", "role": "通信网关服务"},
    ]
    edges = []
    for peer in peers[1:]:
        edges.append({"source": peers[0]["id"], "target": peer["id"], "link_type": "orchestrates"})

    skills = []
    try:
        if service and hasattr(service, "skills") and service.skills:
            from openviking.server.routers.skills import _list_skills_from_root, canonical_user_root
            user_root = f"{canonical_user_root(_ctx)}/skills"
            user_skills = await _list_skills_from_root(service, _ctx, user_root)
            for s in user_skills[:min(limit // 3, 100)]:
                name = s.get("name") if isinstance(s, dict) else getattr(s, "name", "")
                if name and not name.startswith("."):
                    skill_id = f"viking://skills/{name}"
                    skills.append({
                        "id": skill_id,
                        "label": f"Skill: {name}",
                        "category": "skills",
                    })
                    # Link skill to relevant peer
                    low = name.lower()
                    if any(k in low for k in ["mac", "studio", "mlx", "metal", "llm"]):
                        target_peer = "viking://peers/macstudio"
                    elif any(k in low for k in ["remote", "3070", "workbuddy"]):
                        target_peer = "viking://peers/antigravity@rtx3070"
                    elif any(k in low for k in ["claw", "bus", "cluster", "fleet"]):
                        target_peer = "viking://peers/openclaw@2080ti"
                    elif any(k in low for k in ["gateway", "hermes"]):
                        target_peer = "viking://peers/hermes@2080ti"
                    elif any(k in low for k in ["mimo", "xiaomi"]):
                        target_peer = "viking://peers/xiaomimo@2080ti"
                    else:
                        target_peer = "viking://peers/antigravity@2080ti"
                    edges.append({"source": target_peer, "target": skill_id, "link_type": "applies"})
    except Exception:
        pass

    sessions = []
    try:
        if service and hasattr(service, "sessions") and service.sessions:
            sess_list = await service.sessions.sessions(_ctx)
            for s in sess_list[:min(limit // 3, 100)]:
                sid = s.get("session_id") if isinstance(s, dict) else getattr(s, "session_id", "")
                if sid:
                    sess_id = f"viking://sessions/{sid}"
                    sessions.append({
                        "id": sess_id,
                        "label": f"Session: {sid[:8]}",
                        "category": "sessions",
                    })
                    edges.append({"source": "viking://peers/antigravity@2080ti", "target": sess_id, "link_type": "interacts"})
    except Exception:
        pass

    resources = []
    try:
        if service and hasattr(service, "viking_fs") and service.viking_fs:
            max_res = min(limit // 3, 50)
            res_entries = await service.viking_fs.ls("viking://resources", limit=max_res, ctx=_ctx)
            for entry in res_entries[:max_res]:
                uri = entry.get("uri") if isinstance(entry, dict) else getattr(entry, "uri", "")
                if uri:
                    label = uri.split("/")[-1]
                    resources.append({
                        "id": uri,
                        "label": f"Resource: {label}",
                        "category": "resources",
                    })
                    edges.append({
                        "source": "viking://peers/antigravity@2080ti",
                        "target": uri,
                        "link_type": "indexes",
                    })
    except Exception:
        pass

    nodes = peers + skills + sessions + resources
    return Response(status="ok", result={"nodes": nodes, "edges": edges})

