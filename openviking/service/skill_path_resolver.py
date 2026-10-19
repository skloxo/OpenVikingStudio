# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Adaptive Cross-Platform Skills & Storage Path Resolver (Card-195 - SSOT).

Eliminates developer-specific hardcoded paths across Windows, WSL2, Linux containers,
and cloud environments, establishing a unified, resilient single source of truth for
skill directories and master memory paths.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def resolve_skills_root(
    account_id: str = "default",
    explicit_override: Optional[Path | str] = None,
) -> Path:
    """Resolve the authoritative physical directory for agent skills across platforms."""
    # 1. Explicit override passed in constructor or config
    if explicit_override:
        p = Path(explicit_override)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # 2. Environment variable override
    env_dir = os.environ.get("OPENVIKING_SKILLS_DIR")
    if env_dir and env_dir.strip():
        p = Path(env_dir.strip())
        p.mkdir(parents=True, exist_ok=True)
        return p

    # 3. Detect relative to OPENVIKING_DATA_DIR or OPENVIKING_HOME
    data_home = os.environ.get("OPENVIKING_DATA_DIR") or os.environ.get("OPENVIKING_HOME")
    if data_home and data_home.strip():
        candidate = Path(data_home.strip()) / "viking" / account_id / "agent" / "skills"
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate

    # 4. Detect in current workspace / repo root if running locally
    local_candidate = Path.cwd() / "data" / "viking" / account_id / "agent" / "skills"
    if local_candidate.exists():
        return local_candidate

    # 5. Authoritative user home directory
    user_home_candidate = Path.home() / ".openviking" / "data" / "viking" / account_id / "agent" / "skills"
    try:
        user_home_candidate.mkdir(parents=True, exist_ok=True)
        return user_home_candidate
    except Exception:
        # Fallback to local working directory if home is read-only
        fallback = Path.cwd() / ".openviking_skills_fallback"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def resolve_master_memory_root(
    account_id: str = "default",
    explicit_override: Optional[Path | str] = None,
) -> Path:
    """Resolve physical master memory storage root across platforms."""
    if explicit_override:
        p = Path(explicit_override)
        p.mkdir(parents=True, exist_ok=True)
        return p

    env_dir = os.environ.get("OPENVIKING_MASTER_MEMORY_DIR")
    if env_dir and env_dir.strip():
        p = Path(env_dir.strip())
        p.mkdir(parents=True, exist_ok=True)
        return p

    user_home_candidate = Path.home() / ".openviking" / "data" / "viking" / account_id / "resources" / "master_memory"
    try:
        user_home_candidate.mkdir(parents=True, exist_ok=True)
        return user_home_candidate
    except Exception:
        fallback = Path.cwd() / ".openviking_memory_fallback"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
