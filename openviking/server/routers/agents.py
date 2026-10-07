# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
User-Scoped Agent Identifier Management Router (Card-112 / Card-117).

First Principles:
1. "Immutable Identity vs Mutable Display Name":
   - `agent_id`: Permanent system-generated identity (e.g. ag_a7b9c1d3e5f2).
   - `agent_name`: Human-friendly customizable name, modifiable at any time.
2. "Soft Deletion Fail-Fast":
   - Deletions are soft. When a deleted agent attempts MCP access, it fails fast.
3. "Dynamic Tool ACL":
   - Agent permissions driven by `allowed_tools` list.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from openviking.storage.agent_principal_store import (
    AgentPrincipal,
    AgentPrincipalStore,
    DEFAULT_ALLOWED_TOOLS,
    generate_agent_id,
)

logger = logging.getLogger("openviking.server.routers.agents")

router = APIRouter(prefix="/api/v1/users", tags=["agents"])


class CreateAgentRequest(BaseModel):
    agent_name: str = Field(..., description="Human-friendly agent name e.g. 前端结对专家")
    agent_id: Optional[str] = Field(None, description="Optional custom unique ID; auto-generated if omitted")
    role_desc: str = Field("智能体助手", description="Human-readable role description")
    icon: str = Field("terminal", description="Lucide icon name")
    connection_mode: str = Field("apiClient", description="realtimeApi (本地直连) | apiClient (网络远程)")
    allowed_tools: Optional[List[str]] = Field(None, description="Tool names authorized for this agent")
    plugin_grants: Optional[Dict[str, List[str]]] = Field(None, description="Plugin-scoped tool grants e.g. {'openviking-memory': ['openviking_find']}")


class UpdateAgentRequest(BaseModel):
    agent_name: Optional[str] = Field(None, description="Updated display name")
    role_desc: Optional[str] = Field(None, description="Updated role description")
    connection_mode: Optional[str] = Field(None, description="realtimeApi | apiClient")
    allowed_tools: Optional[List[str]] = Field(None, description="Updated tool list")
    plugin_grants: Optional[Dict[str, List[str]]] = Field(None, description="Updated plugin grants mapping")
    status: Optional[str] = Field(None, description="active | suspended | revoked")


def _generate_bootstrap_payload(
    agent_id: str,
    agent_name: str,
    user_id: str,
    host_url: str = "https://vk.tide.red",
    connection_mode: str = "apiClient",
    allowed_tools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    is_local = connection_mode == "realtimeApi"
    target_server = "http://127.0.0.1:1933/mcp" if is_local else f"{host_url}/mcp"

    args = [
        "-y",
        "openviking-bridge",
        "--server",
        target_server,
        "--agent-id",
        agent_id,
    ]
    if not is_local:
        args.extend(["--key", "${OPENVIKING_API_KEY}"])

    mcp_config = {
        "mcpServers": {
            "openviking": {
                "command": "npx",
                "args": args,
            }
        }
    }

    tools_summary = ", ".join(allowed_tools) if allowed_tools else "默认核心工具池"
    topology_desc = "本地宿主直连 (Localhost In-Host)" if is_local else "网络远程卫星 (Remote Gateway)"
    system_prompt = (
        f"# OpenViking 体外大脑专属接入指南 ({topology_desc})\n"
        f"- 你的身份标识 (Agent Name): `{agent_name}`\n"
        f"- 永久身份证号 (Agent ID): `{agent_id}`\n"
        f"- 归属租户用户 (User ID): `{user_id}`\n"
        f"- 已授权工具权限: `{tools_summary}`\n"
        f"- 专属工作空间: `viking://user/{user_id}/peers/{agent_id}/memories/`\n"
        f"- 演进公理: 遇到复杂工程疑难时优先调用 `openviking_find` 召回历史设计；"
        f"突破关键技术后调用 `openviking_record_evolution_lesson` 沉淀事实。"
    )

    remote_mcp_url = (
        f"http://127.0.0.1:1933/mcp?agent_id={agent_id}"
        if is_local
        else f"{host_url}/mcp?agent_id={agent_id}&key=${{OPENVIKING_API_KEY}}"
    )

    return {
        "topology": "local" if is_local else "remote",
        "target_server": target_server,
        "mcp_config": mcp_config,
        "system_prompt": system_prompt,
        "remote_mcp_url": remote_mcp_url,
    }


@router.get("/agent-counts")
async def get_all_user_agent_counts() -> Dict[str, Any]:
    """Get active in-record agent count for all users in O(1)."""
    store = AgentPrincipalStore.get_instance()
    counts = store.count_active_agents_by_user()
    return {"status": "ok", "result": counts}


@router.get("/{user_id}/agents")
async def list_user_agents(
    user_id: str,
    status: Optional[str] = Query("all", description="active | all | revoked"),
) -> Dict[str, Any]:
    """List all authorized agents under a specific user."""
    store = AgentPrincipalStore.get_instance()
    filter_status = None if status == "all" else status
    agents = store.list_agents(user_id=user_id, status=filter_status, include_deleted=False)
    return {
        "status": "ok",
        "result": [a.model_dump() for a in agents],
    }


@router.post("/{user_id}/agents")
async def create_user_agent(
    user_id: str,
    req: CreateAgentRequest,
    request: Request,
) -> Dict[str, Any]:
    """Create or register an authorized agent with system-generated ID."""
    clean_name = req.agent_name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="agent_name cannot be empty")

    final_id = req.agent_id.strip() if req.agent_id and req.agent_id.strip() else generate_agent_id()

    store = AgentPrincipalStore.get_instance()
    agent = store.register_agent(
        agent_id=final_id,
        agent_name=clean_name,
        user_id=user_id,
        role_desc=req.role_desc,
        icon=req.icon,
        connection_mode=req.connection_mode,
        allowed_tools=req.allowed_tools,
        plugin_grants=req.plugin_grants,
    )

    host_url = str(request.base_url).rstrip("/")
    bootstrap = _generate_bootstrap_payload(
        agent_id=agent.agent_id,
        agent_name=agent.agent_name,
        user_id=user_id,
        host_url=host_url,
        connection_mode=req.connection_mode,
        allowed_tools=agent.allowed_tools,
    )

    return {
        "status": "ok",
        "result": {
            "agent": agent.model_dump(),
            "bootstrap": bootstrap,
        },
    }


@router.patch("/{user_id}/agents/{agent_id}")
async def update_user_agent(
    user_id: str,
    agent_id: str,
    req: UpdateAgentRequest,
) -> Dict[str, Any]:
    """Update agent display name, role, connection mode, or allowed tools."""
    store = AgentPrincipalStore.get_instance()
    clean_id = agent_id.strip()
    existing = store.get_agent(clean_id, include_deleted=False)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found or invalid credential")

    updated = store.update_agent(
        agent_id=clean_id,
        agent_name=req.agent_name,
        role_desc=req.role_desc,
        connection_mode=req.connection_mode,
        allowed_tools=req.allowed_tools,
        plugin_grants=req.plugin_grants,
        status=req.status,
    )
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update agent")

    return {"status": "ok", "result": updated.model_dump()}


@router.post("/{user_id}/agents/{agent_id}/activate")
async def activate_user_agent(
    user_id: str,
    agent_id: str,
) -> Dict[str, Any]:
    """Restore or reactivate an agent identifier."""
    store = AgentPrincipalStore.get_instance()
    clean_id = agent_id.strip()
    success = store.restore_agent(clean_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    return {
        "status": "ok",
        "result": {"activated": True, "agent_id": agent_id},
    }


@router.delete("/{user_id}/agents/{agent_id}")
async def soft_delete_user_agent(
    user_id: str,
    agent_id: str,
) -> Dict[str, Any]:
    """Soft delete an authorized agent identifier. Record is preserved for audit trail."""
    store = AgentPrincipalStore.get_instance()
    clean_id = agent_id.strip()
    existing = store.get_agent(clean_id, include_deleted=False)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found or invalid credential")

    success = store.soft_delete_agent(clean_id)
    return {
        "status": "ok",
        "result": {"deleted": success, "soft_deleted": True, "agent_id": agent_id},
    }
