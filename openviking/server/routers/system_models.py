# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Request and response models for system and harness routers."""

from typing import Optional
from pydantic import BaseModel


class MatchIntentRequest(BaseModel):
    query: str
    top_k: int = 5


class WriteDisambiguationRequest(BaseModel):
    skill_name: str
    rule: str


class VerifyProbeRequest(BaseModel):
    test_command: Optional[str] = None
    diff_text: Optional[str] = None


class TestGuardRequest(BaseModel):
    code: str


class AgentLoopProbeRequest(BaseModel):
    action: str = "inject_interjection"
    count: Optional[int] = 1
    tool_name: Optional[str] = "multi_metric_gate"
    steps: Optional[int] = 3
    exhausted: Optional[bool] = False


class BisectionHealProbeRequest(BaseModel):
    scenario: str = "long_dialogue_truncation"


class WaitRequest(BaseModel):
    """Request model for wait."""

    timeout: Optional[float] = None


class ConsistencyRequest(BaseModel):
    """Request model for filesystem/vector-index consistency checks and optional pruning."""

    uri: str
    prune: bool = False


class BackendSyncRequest(BaseModel):
    """Request model for backend sync status and retry operations."""

    uri: str
