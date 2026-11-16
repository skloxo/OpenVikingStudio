# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Resource monitoring and management module."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openviking.resource.watch_manager import WatchManager, WatchTask

__all__ = ["WatchManager", "WatchTask"]


def __getattr__(name: str) -> Any:
    if name in ("WatchManager", "WatchTask"):
        from openviking.resource import watch_manager

        return getattr(watch_manager, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
