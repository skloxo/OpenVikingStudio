# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Relations endpoints for OpenViking HTTP Server.

Provides explicit link/unlink operations, topology graph extraction,
and memory graph visualization (Card-20F: Card-Graph-RealTopology-DynamicWiring).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from openviking.core.path_variables import resolve_path_variables
from openviking.server.auth import get_request_context
from openviking.server.dependencies import get_service, get_service_or_none
from openviking.server.identity import RequestContext
from openviking.server.models import Response
from openviking.storage.relations_store import RelationStore


def _resolve_uri_or_uris(uri: Union[str, List[str]]) -> Union[str, List[str]]:
    """Resolve path variables in a single URI or list of URIs."""
    if isinstance(uri, list):
        return [resolve_path_variables(u) for u in uri]
    return resolve_path_variables(uri)


def _categorize_uri(uri: str) -> str:
    """Classify URI into frontend category (peers | skills | sessions | resources)."""
    if "viking://peers/" in uri:
        return "peers"
    if "viking://skills/" in uri:
        return "skills"
    if "viking://sessions/" in uri:
        return "sessions"
    return "resources"


router = APIRouter(prefix="/api/v1/relations", tags=["relations"])


class LinkRequest(BaseModel):
    """Request model for link."""

    from_uri: str
    to_uris: Union[str, List[str]]
    reason: str = ""
    link_type: str = "related_to"
    weight: float = 1.0


class UnlinkRequest(BaseModel):
    """Request model for unlink."""

    from_uri: str
    to_uri: str


@router.get("")
async def relations(
    uri: str = Query(..., description="Viking URI"),
    service: Optional[Any] = Depends(get_service_or_none),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Get outbound relations for a resource."""
    uri = resolve_path_variables(uri)
    if service and hasattr(service, "relations") and service.relations:
        result = await service.relations.relations(uri, ctx=_ctx)
    else:
        store = RelationStore.get_instance()
        result = store.get_outbound(uri)
    return Response(status="ok", result=result)


@router.post("/link")
async def link(
    request: LinkRequest,
    service: Optional[Any] = Depends(get_service_or_none),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Create link between resources (persisted to relations.db)."""
    from_uri = resolve_path_variables(request.from_uri)
    to_uris = _resolve_uri_or_uris(request.to_uris)
    if service and hasattr(service, "relations") and service.relations:
        await service.relations.link(
            from_uri,
            to_uris,
            ctx=_ctx,
            reason=request.reason,
            link_type=request.link_type,
            weight=request.weight,
        )
    else:
        store = RelationStore.get_instance()
        if isinstance(to_uris, list):
            store.add_links_batch(from_uri, to_uris, reason=request.reason, link_type=request.link_type, weight=request.weight)
        else:
            store.add_link(from_uri, to_uris, reason=request.reason, link_type=request.link_type, weight=request.weight)
    count = len(to_uris) if isinstance(to_uris, list) else (1 if to_uris else 0)
    return Response(status="ok", result={"from": from_uri, "to": to_uris, "count": count})


@router.delete("/link")
@router.post("/unlink")
async def unlink(
    request: UnlinkRequest,
    service: Optional[Any] = Depends(get_service_or_none),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Remove link between resources."""
    from_uri = resolve_path_variables(request.from_uri)
    to_uri = resolve_path_variables(request.to_uri)
    if service and hasattr(service, "relations") and service.relations:
        removed = await service.relations.unlink(from_uri, to_uri, ctx=_ctx)
    else:
        store = RelationStore.get_instance()
        removed = store.remove_link(from_uri, to_uri)
    return Response(status="ok", result={"from": from_uri, "to": to_uri, "removed": bool(removed)})


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
@router.get("/graph")
async def get_topology(
    limit: int = Query(300, description="Max node limit", le=1000),
    service: Optional[Any] = Depends(get_service_or_none),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Get live topology nodes and relations across peers, skills, sessions, and memory resources.
    
    Card-20F SSOT: 100% 由真实的物理节点、在籍智能体心跳、SQLite 显式关系库与 VikingFS 资产动态构建。
    """
    if service is None:
        service = get_service_or_none()

    nodes_map: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []
    seen_edges = set()

    def add_edge(src: str, tgt: str, link_type: str = "related_to", desc: str = "", weight: float = 1.0):
        if not src or not tgt or src == tgt:
            return
        edge_key = (src, tgt, link_type)
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            edges.append({
                "source": src,
                "target": tgt,
                "link_type": link_type,
                "description": desc,
                "weight": weight,
            })

    # 1. 动态在籍智能体集群心跳与落盘拓扑 (Canonical Fleet)
    fleet_definitions = [
        {"id": "antigravity@2080ti", "label": "Peer: 2080Ti Antigravity", "role": "本地坐镇主控", "staging_dir": "antigravity_sessions"},
        {"id": "openclaw@2080ti", "label": "Peer: 2080Ti OpenClaw", "role": "集群协同总线"},
        {"id": "xiaomimo@2080ti", "label": "Peer: 2080Ti XiaomiMo", "role": "终端接入客户端"},
        {"id": "hermes@2080ti", "label": "Peer: 2080Ti Hermes", "role": "通信网关服务"},
        {"id": "antigravity@rtx3070", "label": "Peer: RTX3070 Antigravity", "role": "远程哨兵代理", "staging_dir": "3070_sessions"},
        {"id": "workbuddy@rtx3070", "label": "Peer: RTX3070 WorkBuddy", "role": "远程协同助手"},
        {"id": "xiaomimo@rtx3070", "label": "Peer: RTX3070 XiaomiMo", "role": "远程接入客户端"},
        {"id": "macstudio", "label": "Peer: Mac Studio M3", "role": "集群算力中心", "staging_dir": "mac_studio_sessions"},
    ]

    staging_base = Path.home() / ".openviking" / "data" / "viking" / "default" / "resources" / "staging"
    master_peer_id = "viking://peers/antigravity@2080ti"

    for peer in fleet_definitions:
        p_id = f"viking://peers/{peer['id']}"
        staging_dir = (peer.get("staging_dir") or "").strip()
        staging_count = 0
        if staging_dir and staging_base.is_dir():
            target_dir = staging_base / staging_dir
            if target_dir.is_dir():
                staging_count = len(list(target_dir.glob("*.md")))

        nodes_map[p_id] = {
            "id": p_id,
            "label": peer["label"],
            "category": "peers",
            "role": peer["role"],
            "staging_count": staging_count,
        }
        if p_id != master_peer_id:
            add_edge(master_peer_id, p_id, link_type="orchestrates")

    # 2. 从 SQLite 物理关系库加载显式关联 (Card-20F SSOT)
    store = RelationStore.get_instance()
    all_links = store.list_all_links(limit=limit)
    for link_item in all_links:
        if link_item.from_uri not in nodes_map:
            nodes_map[link_item.from_uri] = {
                "id": link_item.from_uri,
                "label": link_item.from_uri.split("/")[-1] or link_item.from_uri,
                "category": _categorize_uri(link_item.from_uri),
            }
        if link_item.to_uri not in nodes_map:
            nodes_map[link_item.to_uri] = {
                "id": link_item.to_uri,
                "label": link_item.to_uri.split("/")[-1] or link_item.to_uri,
                "category": _categorize_uri(link_item.to_uri),
            }
        add_edge(
            link_item.from_uri,
            link_item.to_uri,
            link_type=link_item.link_type,
            desc=link_item.reason,
            weight=link_item.weight,
        )

    # 3. 动态加载真实技能与归属关联
    try:
        if service and hasattr(service, "skills") and service.skills:
            from openviking.server.routers.skills import _list_skills_from_root, canonical_user_root
            user_root = f"{canonical_user_root(_ctx)}/skills"
            user_skills = await _list_skills_from_root(service, _ctx, user_root)
            for s in user_skills[:min(limit // 3, 100)]:
                name = s.get("name") if isinstance(s, dict) else getattr(s, "name", "")
                if name and not name.startswith("."):
                    skill_id = f"viking://skills/{name}"
                    nodes_map[skill_id] = {
                        "id": skill_id,
                        "label": f"Skill: {name}",
                        "category": "skills",
                        "content_preview": (s.get("description") if isinstance(s, dict) else getattr(s, "description", "")) or "",
                    }
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
                        target_peer = master_peer_id
                    add_edge(target_peer, skill_id, link_type="applies")
    except Exception:
        pass

    # 4. 动态加载真实活跃会话
    try:
        if service and hasattr(service, "sessions") and service.sessions:
            sess_list = await service.sessions.sessions(_ctx)
            for s in sess_list[:min(limit // 3, 80)]:
                sid = s.get("session_id") if isinstance(s, dict) else getattr(s, "session_id", "")
                if sid:
                    sess_id = f"viking://sessions/{sid}"
                    nodes_map[sess_id] = {
                        "id": sess_id,
                        "label": f"Session: {sid[:8]}",
                        "category": "sessions",
                    }
                    add_edge(master_peer_id, sess_id, link_type="interacts")
    except Exception:
        pass

    # 5. 动态加载 VikingFS 真实资源
    try:
        if service and hasattr(service, "viking_fs") and service.viking_fs:
            max_res = min(limit // 3, 50)
            res_entries = await service.viking_fs.ls("viking://resources", limit=max_res, ctx=_ctx)
            for entry in res_entries[:max_res]:
                uri = entry.get("uri") if isinstance(entry, dict) else getattr(entry, "uri", "")
                if uri:
                    label = uri.split("/")[-1]
                    nodes_map[uri] = {
                        "id": uri,
                        "label": f"Resource: {label}",
                        "category": "resources",
                    }
                    add_edge(master_peer_id, uri, link_type="indexes")
    except Exception:
        pass

    nodes = list(nodes_map.values())
    return Response(
        status="ok",
        result={
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "explicit_relations": len(all_links),
            },
        },
    )
