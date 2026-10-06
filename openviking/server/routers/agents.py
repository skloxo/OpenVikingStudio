# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
User-Scoped Agent Identifier Management Router (Card-112 / v1.7.66).

First Principles:
1. "Zero Guesswork": Explicit Agent Principals created under a tenant user (e.g. default).
2. "Instant Bootstrap Payload": Creating an agent immediately returns copy-pasteable
   safe MCP configs and System Prompt templates.
3. "O(1) Data Sourcing": Pure SQLite-driven operations, never traversing the disk.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from openviking.storage.agent_principal_store import (
    AgentPrincipal,
    AgentPrincipalStore,
)

logger = logging.getLogger("openviking.server.routers.agents")

router = APIRouter(prefix="/api/v1/users", tags=["agents"])


class CreateAgentRequest(BaseModel):
    agent_id: str = Field(..., description="Unique agent identifier e.g. cursor@macbook")
    role_desc: str = Field("远程智能体助手", description="Human-readable role description")
    icon: str = Field("terminal", description="Lucide icon name")
    connection_mode: str = Field("apiClient", description="realtimeApi (本地直连) | apiClient (网络远程)")


def _generate_bootstrap_payload(
    agent_id: str,
    user_id: str,
    host_url: str = "https://vk.tide.red",
    connection_mode: str = "apiClient",
) -> Dict[str, Any]:
    """
    Generate topology-aware safe onboarding snippets and system prompt instructions.
    - Local (realtimeApi): Direct localhost endpoint (http://127.0.0.1:1933/mcp), zero public overhead.
    - Remote (apiClient): Public gateway endpoint (https://vk.tide.red/mcp) with ${OPENVIKING_API_KEY} placeholder.
    """
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

    topology_desc = "本地宿主直连 (Localhost In-Host)" if is_local else "网络远程卫星 (Remote Gateway)"
    system_prompt = (
        f"# OpenViking 体外大脑专属接入指南 ({topology_desc})\n"
        f"- 你的身份牌 (Agent ID): `{agent_id}`\n"
        f"- 归属用户 (User ID): `{user_id}`\n"
        f"- 拓扑接入模式: `{'本地进程直连' if is_local else '公网卫星远程'}`\n"
        f"- 专属工作空间: `viking://user/{user_id}/peers/{agent_id}/memories/`\n"
        f"- 演进公理: 遇到复杂工程疑难时，必须优先调用 `openviking_find` 召回历史经验；"
        f"解决重大技术突破后，必须调用 `openviking_record_evolution_lesson` 写入体外大脑沉淀资产。"
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


@router.get("/{user_id}/agents")
async def list_user_agents(
    user_id: str,
    status: Optional[str] = Query("all", description="active | all | revoked"),
) -> Dict[str, Any]:
    """List all authorized agents under a specific user."""
    store = AgentPrincipalStore.get_instance()
    filter_status = None if status == "all" else status
    agents = store.list_agents(user_id=user_id, status=filter_status)
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
    """Create or register an authorized agent identifier under a user."""
    clean_id = req.agent_id.strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="agent_id cannot be empty")

    store = AgentPrincipalStore.get_instance()
    agent = store.register_agent(
        agent_id=clean_id,
        user_id=user_id,
        role_desc=req.role_desc,
        icon=req.icon,
        connection_mode=req.connection_mode,
    )

    # Infer base host URL for bootstrap payload
    host_url = str(request.base_url).rstrip("/")
    bootstrap = _generate_bootstrap_payload(
        clean_id, user_id, host_url, connection_mode=req.connection_mode
    )

    return {
        "status": "ok",
        "result": {
            "agent": agent.model_dump(),
            "bootstrap": bootstrap,
        },
    }


@router.post("/{user_id}/agents/{agent_id}/activate")
async def activate_user_agent(
    user_id: str,
    agent_id: str,
) -> Dict[str, Any]:
    """Reactivate a revoked agent identifier."""
    store = AgentPrincipalStore.get_instance()
    agent = store.get_agent(agent_id.strip())
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    store.record_activity(agent_id=agent.agent_id, user_id=user_id, increment=0)
    return {
        "status": "ok",
        "result": {"activated": True, "agent_id": agent_id},
    }


@router.delete("/{user_id}/agents/{agent_id}")
async def revoke_or_delete_user_agent(
    user_id: str,
    agent_id: str,
    purge: bool = Query(False, description="Permanently delete from database if true"),
) -> Dict[str, Any]:
    """Revoke or permanently delete an authorized agent identifier."""
    store = AgentPrincipalStore.get_instance()
    clean_id = agent_id.strip()
    existing = store.get_agent(clean_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # If already revoked or explicit purge requested, permanently delete
    if purge or existing.status == "revoked":
        success = store.delete_agent(clean_id)
        return {
            "status": "ok",
            "result": {"deleted": success, "purged": True, "agent_id": agent_id},
        }

    # Otherwise mark as revoked
    success = store.revoke_agent(clean_id)
    return {
        "status": "ok",
        "result": {"revoked": success, "purged": False, "agent_id": agent_id},
    }

