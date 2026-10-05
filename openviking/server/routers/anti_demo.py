# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Anti-Demo & Anti-Dangling Automated Retina Gate Router (Card-103 / v1.7.57).

Endpoints:
  GET /api/v1/system/anti-demo-audit  <- Query real-time or cached anti-demo audit report
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.anti_demo_service import (
    AntiDemoAuditReport,
    AntiDemoGateService,
)

anti_demo_router = APIRouter(prefix="/api/v1/system", tags=["anti-demo"])


@anti_demo_router.get("/anti-demo-audit", response_model=AntiDemoAuditReport)
async def get_anti_demo_audit(
    force: bool = Query(default=False, description="Force re-scan bypassing snapshot cache"),
    ctx: RequestContext = Depends(get_request_context),
) -> AntiDemoAuditReport:
    """Run or fetch cached anti-demo & anti-dangling automated retina audit."""
    service = AntiDemoGateService.get_instance()
    return service.audit(force_refresh=force)
