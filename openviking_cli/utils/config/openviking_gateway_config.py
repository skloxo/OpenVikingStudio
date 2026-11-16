# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Embedded gateway configuration stub compatible with fork Gateway 2.0."""

from __future__ import annotations

try:
    from openviking_gateway.config import EmbeddedGatewayConfig
except ImportError:
    from typing import Any, Dict, Literal
    from pydantic import BaseModel, Field

    class EmbeddedGatewayConfig(BaseModel):  # type: ignore[no-redef]
        """Configuration for embedded gateway mounting on the OpenViking server."""

        enabled: bool = False
        public_url: str = ""
        mcp_file_links: Literal["proxy", "direct"] = "proxy"
        storage_path: str = "~/.openviking/gateway"
        management_api: bool = True
        openviking_keys: bool = False
        tenancy: Literal["account", "key"] = "account"
        default_upstreams: Dict[str, Any] = Field(default_factory=dict, repr=False)
        model_config = {"extra": "ignore"}
