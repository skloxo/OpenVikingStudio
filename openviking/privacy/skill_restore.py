# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Restore configured privacy values when reading skill content."""

from __future__ import annotations

import re

from openviking.core.namespace import uri_parts
from openviking.privacy.restore import PrivacyRestorer
from openviking.privacy.service import UserPrivacyConfigService
from openviking.privacy.skill_placeholder import build_placeholder
from openviking.server.identity import RequestContext


def get_skill_name_from_uri(uri: str) -> str | None:
    """Return skill name if uri targets a skill file inside user skills root."""
    parts = uri_parts(uri)
    if "skills" not in parts:
        return None
    idx = parts.index("skills")
    if idx + 1 >= len(parts):
        return None
    return parts[idx + 1] or None


def _extract_placeholder_keys(content: str, skill_name: str) -> list[str]:
    pattern = re.compile(r"\{\{ov_privacy:skill:" + re.escape(skill_name) + r":([^}:]+)\}\}")
    keys: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(content):
        key = match.group(1)
        if key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


def restore_skill_content(content: str, skill_name: str, values: dict[str, str]) -> str:
    """Synchronously restore {{ov_privacy:skill:<name>:<key>}} placeholders for fs_service callers."""
    restored = content
    unresolved_entries: list[str] = []
    placeholder_keys = _extract_placeholder_keys(content, skill_name)
    placeholder_key_set = set(placeholder_keys)

    for key in placeholder_keys:
        raw_value = values.get(key)
        if raw_value is None or raw_value == "":
            shown_value = "<missing>" if raw_value is None else '""'
            unresolved_entries.append(f"{key}={shown_value}")
            continue
        restored = restored.replace(build_placeholder(skill_name, key), raw_value)

    extra_config_entries = [
        f"{key}={value}"
        for key, value in values.items()
        if key not in placeholder_key_set and value is not None and value != ""
    ]

    if unresolved_entries or extra_config_entries:
        restored += "\n\n[Privacy Config Notice]\n"
        if unresolved_entries:
            restored += "Missing config: " + ", ".join(unresolved_entries) + "\n"
        if extra_config_entries:
            restored += (
                "Configured but not referenced in content: "
                + ", ".join(extra_config_entries)
                + "\n"
            )
    return restored


async def restore_skill_content_async(
    privacy: UserPrivacyConfigService,
    content: str,
    ctx: RequestContext,
    *,
    skill_name: str,
) -> str:
    """Asynchronously restore owner-bound privacy references for a skill file."""
    restorer = PrivacyRestorer(privacy, ctx, category="skill", target_key=skill_name)
    restorer.collect_text(content)
    await restorer.load_values()
    current = await restorer.get_current("skill", skill_name)
    values = current.values if current else {}
    unresolved_entries: list[str] = []

    for placeholder, location in restorer.fields.items():
        if placeholder == build_placeholder(skill_name, location.field):
            raw_value = values.get(location.field)
            if raw_value is None or raw_value == "":
                shown_value = "<missing>" if raw_value is None else '""'
                unresolved_entries.append(f"{location.field}={shown_value}")

    extra_config_entries = [
        f"{key}={value}"
        for key, value in values.items()
        if build_placeholder(skill_name, key) not in restorer.fields
        and value is not None
        and value != ""
    ]

    restored = restorer.restore_text(content)
    if current and (unresolved_entries or extra_config_entries):
        restored += "\n\n[Privacy Config Notice]\n"
        if unresolved_entries:
            restored += "Missing config: " + ", ".join(unresolved_entries) + "\n"
        if extra_config_entries:
            restored += (
                "Configured but not referenced in content: "
                + ", ".join(extra_config_entries)
                + "\n"
            )
    return restored
