# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Extract sensitive values from skill content."""

from dataclasses import dataclass, field
from typing import Any, Optional

try:
    from openviking.config.vlm import VLMHandle
except ImportError:  # pragma: no cover - decoupled config package pending #183
    VLMHandle = Any  # type: ignore[assignment,misc]

from openviking.privacy.skill_placeholder import placeholderize_skill_content_with_blocks
from openviking.prompts import render_prompt
from openviking_cli.utils.config import get_openviking_config
from openviking_cli.utils.llm import parse_json_from_response


@dataclass
class SkillPrivacyExtractionResult:
    values: dict[str, str]
    original_content: str
    sanitized_content: str
    original_content_blocks: list[str] = field(default_factory=list)
    replacement_content_blocks: list[str] = field(default_factory=list)


async def extract_skill_privacy_values(
    *,
    skill_name: str,
    skill_description: str,
    content: str,
    vlm: Optional[VLMHandle] = None,
) -> SkillPrivacyExtractionResult:
    resolved_vlm = vlm if vlm is not None else get_openviking_config().vlm
    if resolved_vlm is None or (hasattr(resolved_vlm, "is_available") and not resolved_vlm.is_available()):
        raise ValueError("Skill privacy extraction requires an available VLM")
    prompt = render_prompt(
        "skill.privacy_extraction",
        {
            "skill_name": skill_name,
            "skill_description": skill_description,
            "skill_content": content,
        },
    )
    response = await resolved_vlm.get_completion_async(prompt)
    data = parse_json_from_response(response) or {}

    values: dict[str, str] = {}
    if isinstance(data, dict):
        raw_values = data.get("values", {})
        if isinstance(raw_values, dict):
            values = {
                str(key): "" if value is None else str(value)
                for key, value in raw_values.items()
                if str(key).strip()
            }

    placeholder_result = placeholderize_skill_content_with_blocks(content, skill_name, values)
    return SkillPrivacyExtractionResult(
        values=placeholder_result.replaced_values,
        original_content=content,
        sanitized_content=placeholder_result.sanitized_content,
        original_content_blocks=placeholder_result.original_content_blocks,
        replacement_content_blocks=placeholder_result.replacement_content_blocks,
    )
