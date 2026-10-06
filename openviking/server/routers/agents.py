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
    connection_mode: str = Field("apiClient", description="realtimeApi | apiClient")


def _generate_bootstrap_payload(
    agent_id: str,
    user_id: str,
    host_url: str = "https://vk.tide.red",
) -> Dict[str, Any]:
    """
    Generate safe onboarding snippets and system prompt instructions.
    Munger Inversion Guard: Uses ${OPENVIKING_API_KEY} placeholder to prevent
    committing plaintext secrets to public repositories!
    """
    mcp_config = {
        "mcpServers": {
            "openviking": {
                "command": "npx",
                "args": [
                    "-y",
                    "openviking-bridge",
                    "--server",
                    f"{host_url}/mcp",
                    "--agent-id",
                    agent_id,
                    "--key",
                    "${OPENVIKING_API_KEY}",
                ],
            }
        }
    }

    system_prompt = (
        f"# OpenViking 体外大脑专属接入指南\n"
        f"- 你的身份牌 (Agent ID): `{agent_id}`\n"
        f"- 归属用户 (User ID): `{user_id}`\n"
        f"- 专属工作空间: `viking://user/{user_id}/peers/{agent_id}/memories/`\n"
        f"- 演进公理: 遇到复杂工程疑难时，必须优先调用 `openviking_find` 召回历史经验；"
        f"解决重大技术突破后，必须调用 `openviking_record_evolution_lesson` 写入体外大脑沉淀资产。"
    )

    remote_mcp_url = f"{host_url}/mcp?agent_id={agent_id}&key=${{OPENVIKING_API_KEY}}"

    return {
        "mcp_config": mcp_config,
        "system_prompt": system_prompt,
        "remote_mcp_url": remote_mcp_url,
    }


@router.get("/{user_id}/agents")
async def list_user_agents(
    user_id: str,
    status: Optional[str] = Query("active", description="active | all | revoked"),
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
    bootstrap = _generate_bootstrap_payload(clean_id, user_id, host_url)

    return {
        "status": "ok",
        "result": {
            "agent": agent.model_dump(),
            "bootstrap": bootstrap,
        },
    }


@router.delete("/{user_id}/agents/{agent_id}")
async def revoke_user_agent(
    user_id: str,
    agent_id: str,
) -> Dict[str, Any]:
    """Revoke or delete an authorized agent identifier."""
    store = AgentPrincipalStore.get_instance()
    success = store.revoke_agent(agent_id.strip())
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    return {
        "status": "ok",
        "result": {"revoked": True, "agent_id": agent_id},
    }
