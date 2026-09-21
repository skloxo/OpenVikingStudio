# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unified OpenViking server endpoint resolver.

Provides a robust Single Source of Truth (SSOT) to resolve the active server
URL across services, background watchdogs, and client tools.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("openviking.service.endpoint_resolver")

DEFAULT_OPENVIKING_ENDPOINT = "http://127.0.0.1:1933"


def get_openviking_endpoint(default: str = DEFAULT_OPENVIKING_ENDPOINT) -> str:
    """Resolve active OpenViking server endpoint URL.

    Resolution order:
    1. Direct URL environment variables:
       - OPENVIKING_ENDPOINT
       - OPENVIKING_URL
       - OPENVIKING_API
    2. Port override environment variable:
       - OPENVIKING_PORT (assembled as http://127.0.0.1:{port})
    3. Configuration file (~/.openviking/ov.conf):
       - Inspects [server] or server.port configuration
    4. Default fallback: http://127.0.0.1:1933
    """
    # 1. Direct URL environment variables
    for var_name in ("OPENVIKING_ENDPOINT", "OPENVIKING_URL", "OPENVIKING_API"):
        val = os.environ.get(var_name, "").strip()
        if val:
            return val.rstrip("/")

    # 2. Port override
    port = os.environ.get("OPENVIKING_PORT", "").strip()
    if port:
        return f"http://127.0.0.1:{port}"

    # 3. Inspect ov.conf if exists
    ov_conf = Path.home() / ".openviking" / "ov.conf"
    if ov_conf.exists():
        try:
            with open(ov_conf, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("server_url") or stripped.startswith("endpoint"):
                        parts = stripped.split("=", 1)
                        if len(parts) == 2:
                            endpoint = parts[1].strip().strip('"').strip("'")
                            if endpoint:
                                return endpoint.rstrip("/")
                    elif stripped.startswith("port") and not port:
                        parts = stripped.split("=", 1)
                        if len(parts) == 2:
                            cfg_port = parts[1].strip().strip('"').strip("'")
                            if cfg_port.isdigit():
                                return f"http://127.0.0.1:{cfg_port}"
        except Exception as e:
            logger.debug("[EndpointResolver] Failed reading ov.conf: %s", e)

    return default.rstrip("/")
