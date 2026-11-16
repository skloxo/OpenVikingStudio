# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Mask and detect routes retained from fork for stateless regex/lexicon privacy detection."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from openviking.privacy.privacy_masker import get_privacy_masker
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.server.models import Response

mask_router = APIRouter(tags=["privacy-configs"])


class MaskTextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = ""


class DetectSensitiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = ""


@mask_router.post("/mask")
async def mask_sensitive_text(
    request: MaskTextRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    masker = get_privacy_masker()
    sanitized = masker.mask_text(request.text)
    has_sensitive = masker.contains_sensitive(request.text)
    return Response(
        status="ok",
        result={
            "sanitized_text": sanitized,
            "contained_sensitive": has_sensitive,
            "length_diff": len(request.text) - len(sanitized),
        },
    )


@mask_router.post("/detect")
async def detect_sensitive_text(
    request: DetectSensitiveRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    masker = get_privacy_masker()
    return Response(
        status="ok",
        result={"contains_sensitive": masker.contains_sensitive(request.text)},
    )
