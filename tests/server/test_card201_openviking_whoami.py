# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-201 TDD Test Suite: openviking_whoami introspection tool and vk-sk- key privacy masking."""

import json
import pytest
from openviking.privacy.privacy_masker import PrivacyMasker
from openviking.service.builtin_plugins_core import BATTLEFIELD_34_TOOL_NAMES
from openviking.server.routers.client_caps_constants import BATTLEFIELD_34_TOOLS


def test_card201_whoami_contract_presence():
    """Verify openviking_whoami is formally registered in capability contracts."""
    assert "openviking_whoami" in BATTLEFIELD_34_TOOL_NAMES
    spec_ids = [t["id"] for t in BATTLEFIELD_34_TOOLS]
    assert "openviking_whoami" in spec_ids
    spec = next(t for t in BATTLEFIELD_34_TOOLS if t["id"] == "openviking_whoami")
    assert spec["name"] == "whoami"


def test_card201_privacy_masker_redacts_vk_sk():
    """Verify PrivacyMasker automatically masks OpenViking API keys (vk-sk-)."""
    masker = PrivacyMasker()
    prefix = "vk-s" + "k-"
    leaked_root = prefix + "96d39bdb670dbdfaaf9c1b19db4c1c2a860d141bc57dcbff4d7ec1044fd2d5e7"
    raw_text = f"Warning: root key was found: {leaked_root} in configuration"
    masked = masker.mask_text(raw_text)
    assert leaked_root not in masked
    assert "vk-sk-***[REDACTED_API_KEY]" in masked


@pytest.mark.asyncio
async def test_card201_whoami_fastmcp_invocation():
    """Verify openviking_whoami tool returns masked credentials and identity without leaking cleartext."""
    from openviking.server.mcp_endpoint import openviking_whoami, _mcp_ctx, RequestContext, UserIdentifier

    fake_key = "ZGVmYXVsdA.RFNIQFJUWDMwNzA.fe6c2193e72f7b19c16dc47a1b725059dffcfdcfaf4bcab91e4d6cd57d57e1d2"
    ctx = RequestContext(
        user=UserIdentifier("default", "DSH@RTX3070"),
        role="user",
        actor_peer_id="openviking-memory",
        from_oauth=False,
        api_key=fake_key,
    )

    token = _mcp_ctx.set(ctx)
    try:
        raw_res = await openviking_whoami()
        res = json.loads(raw_res)
        assert res["user"] == "DSH@RTX3070"
        assert res["account"] == "default"
        assert res["role"] == "user"
        assert res["authenticated"] is True
        assert res["masked_user_key"] == "ZGVmY...e1d2"
        # 严格铁律：全量明文绝对禁止出现在返回结果中
        assert fake_key not in raw_res
    finally:
        _mcp_ctx.reset(token)
