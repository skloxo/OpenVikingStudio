# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Compatibility shim resolving account memory registry to deployment defaults."""

from __future__ import annotations

from typing import Any

from openviking.session.memory.memory_type_registry import MemoryTypeRegistry


async def resolve_account_memory_registry(
    viking_fs: Any, account_id: str, registry: MemoryTypeRegistry
) -> MemoryTypeRegistry:
    del viking_fs, account_id
    return registry
