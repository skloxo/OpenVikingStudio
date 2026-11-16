# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Independent Account generation settings with legacy Cluster defaults."""

from __future__ import annotations

from typing import Any

from openviking_cli.utils.config import get_openviking_config
from openviking_cli.utils.config.open_viking_config import OpenVikingConfig


async def get_output_language_override(
    manager: Any,
    account_id: str,
    *,
    cluster_config: OpenVikingConfig | None = None,
) -> str:
    """Read Account output_language_override; fallback cleanly to Cluster."""
    if manager is not None and hasattr(manager, "get_account"):
        language = await manager.get_account(account_id, "output_language_override")
        if language is not None:
            return language
    config = cluster_config if cluster_config is not None else get_openviking_config()
    return config.output_language_override


async def get_memory_extraction_enabled(
    manager: Any,
    account_id: str,
    *,
    cluster_config: OpenVikingConfig | None = None,
) -> bool:
    """Read Account extraction switch; fallback cleanly to Cluster."""
    if manager is not None and hasattr(manager, "get_account"):
        memory = await manager.get_account(account_id, "memory")
        if memory is not None:
            return memory.extraction_enabled
    config = cluster_config if cluster_config is not None else get_openviking_config()
    return config.memory.extraction_enabled
