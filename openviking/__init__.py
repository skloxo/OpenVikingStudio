# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking - An Agent-native context database

Data in, Context out.
"""

__version__ = "1.3.17"

try:
    from ._version import version as _v

    if _v and not _v.startswith("0."):
        __version__ = _v
except Exception:
    try:
        from importlib.metadata import version

        __version__ = version("openviking")
    except Exception:
        pass


def __getattr__(name: str):
    if name == "__version__":
        return __version__
    if name == "AsyncHTTPClient":
        from openviking_cli.client.http import AsyncHTTPClient

        return AsyncHTTPClient
    if name == "SyncHTTPClient":
        from openviking_cli.client.sync_http import SyncHTTPClient

        return SyncHTTPClient
    if name == "AsyncOpenViking":
        from openviking.async_client import AsyncOpenViking

        return AsyncOpenViking
    if name == "OpenViking":
        from openviking.client import OpenViking

        return OpenViking
    raise AttributeError(name)


__all__ = [
    "__version__",
    "SyncHTTPClient",
    "AsyncHTTPClient",
    "AsyncOpenViking",
    "OpenViking",
]

