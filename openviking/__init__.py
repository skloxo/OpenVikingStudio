# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking - An Agent-native context database

Data in, Context out.
"""

__version__ = "1.4.16"

try:
    from ._version import version as _v

    __version__ = _v
except Exception:
    try:
        from importlib.metadata import version

        __version__ = version("openviking")
    except Exception:
        pass

# Namespace package and shadow path integrity guard
import os
import sys
import warnings

def _verify_package_integrity():
    """Detect and alert if openviking is contaminated by shadow site-packages or namespace paths."""
    mod = sys.modules.get(__name__)
    if mod is not None and getattr(mod, "__file__", None) is None:
        raise RuntimeError(
            "\n[CRITICAL] 'openviking' was imported as a degenerate PEP 420 namespace package!\n"
            "Cause: An orphan site-packages directory or shadow path lacks __init__.py and masked the real package.\n"
            "Remedy: Check and clean orphan site-packages: rm -rf ~/.local/lib/python*/site-packages/openviking*"
        )
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if hasattr(mod, "__path__"):
        extra_paths = [os.path.abspath(p) for p in mod.__path__ if os.path.abspath(p) != current_dir]
        if extra_paths:
            warnings.warn(
                f"\n[WARNING] Multiple conflicting paths detected in openviking.__path__:\n"
                f"  Primary: {current_dir}\n"
                f"  Conflicting: {extra_paths}\n"
                f"Please remove stale site-packages shadow paths to prevent symbol masking.",
                RuntimeWarning,
                stacklevel=2,
            )

_verify_package_integrity()


def __getattr__(name: str):
    if name == "AsyncHTTPClient":
        from openviking_cli.client.http import AsyncHTTPClient

        return AsyncHTTPClient
    if name == "SyncHTTPClient":
        from openviking_cli.client.sync_http import SyncHTTPClient

        return SyncHTTPClient
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "__version__",
    "SyncHTTPClient",
    "AsyncHTTPClient",
]
