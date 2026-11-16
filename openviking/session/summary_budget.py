# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Working Memory summary output budget, rolling batching, and retry helpers (#6771)."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import replace
from typing import Any, Callable, Dict, List, Optional

from openviking.message import Message
from openviking.message.part import TextPart
from openviking.utils.token_estimation import estimate_text_tokens, truncate_text_to_token_budget
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)


def limit_summary_output_tokens(vlm: Any, output_budget: int) -> int:
    """Clamp summary output_budget against configured VLM max_tokens (incl. FailoverVLM)."""
    sub_vlms = getattr(vlm, "_vlm_instances", None)
    if sub_vlms:
        return min(limit_summary_output_tokens(sub, output_budget) for sub in sub_vlms)
    primary = getattr(vlm, "primary", None)
    backup = getattr(vlm, "backup", None)
    if primary is not None and backup is not None:
        return min(
            limit_summary_output_tokens(primary, output_budget),
            limit_summary_output_tokens(backup, output_budget),
        )
    configured_limit = getattr(vlm, "max_tokens", None)
    if configured_limit is not None:
        return min(output_budget, int(configured_limit))
    return output_budget


def estimate_summary_template_tokens(
    render_prompt: Callable[..., str],
    latest_archive_overview: str,
    wm_sections: tuple[str, ...],
    checkpoint_instructions: str,
    build_reminders: Callable[[str], str],
) -> int:
    """Estimate template overhead tokens beyond ``latest_archive_overview``."""
    is_update = any(f"## {section}" in latest_archive_overview for section in wm_sections)
    variables: Dict[str, Any] = {
        "messages": "",
        "latest_archive_overview": latest_archive_overview,
        "checkpoint_instructions": checkpoint_instructions,
        "output_language": "en",
    }
    if is_update:
        variables["wm_section_reminders"] = build_reminders(latest_archive_overview)
    prompt = render_prompt(
        "compression.ov_wm_v2_update" if is_update else "compression.ov_wm_v2",
        variables,
    )
    return max(0, estimate_text_tokens(prompt) - estimate_text_tokens(latest_archive_overview))


async def complete_with_window_budget(
    vlm: Any,
    *,
    session_window_context: int,
    prompt: str = "",
    messages: Optional[List[Dict[str, Any]]] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    completion_kwargs: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Any:
    """Run vlm.get_completion_async bounded by remaining session_window_context."""
    used_tokens = estimate_text_tokens(prompt) + sum(
        estimate_text_tokens(str(message.get("content") or "")) + 4
        for message in (messages or [])
    )
    if prompt:
        used_tokens += 4
    if tools:
        used_tokens += estimate_text_tokens(json.dumps(tools, ensure_ascii=False))
    output_budget = session_window_context - used_tokens
    if output_budget <= 0:
        raise ValueError("Working Memory prompt exceeds session_window_context")
    output_budget = limit_summary_output_tokens(vlm, output_budget)
    extra = dict(completion_kwargs or {})
    extra.update(kwargs)
    explicit_max_tokens = extra.pop("max_tokens", None)
    final_max_tokens = (
        output_budget
        if explicit_max_tokens is None
        else min(output_budget, int(explicit_max_tokens))
    )
    try:
        return await vlm.get_completion_async(
            prompt=prompt,
            messages=messages,
            tools=tools,
            max_tokens=final_max_tokens,
            **extra,
        )
    except TypeError:
        return await vlm.get_completion_async(
            prompt=prompt,
            messages=messages,
            tools=tools,
            **extra,
        )


async def fit_summary_to_budget(
    vlm: Any,
    *,
    first_overview: str,
    input_material: str,
    summary_budget_tokens: int,
    session_window_context: int,
    retry_enabled: bool,
    reasoning_effort: Optional[str] = None,
    output_language: str = "en",
) -> str:
    """Compact an over-budget summary once via rewrite and once via final fallback."""
    overview = str(first_overview or "")
    if not retry_enabled:
        return overview
    actual_tokens = estimate_text_tokens(overview)
    if actual_tokens <= summary_budget_tokens:
        return overview

    logger.warning(
        "Working Memory summary exceeded budget; retrying compact summary "
        "actual_tokens=%s summary_budget_tokens=%s overage_tokens=%s",
        actual_tokens,
        summary_budget_tokens,
        actual_tokens - summary_budget_tokens,
    )
    completion_kwargs: Dict[str, Any] = (
        {"reasoning_effort": reasoning_effort} if reasoning_effort is not None else {}
    )
    second_system = (
        "The previous Working Memory exceeded the hard summary budget.\n\n"
        f"Hard budget: {summary_budget_tokens} tokens\n"
        f"Previous output: {actual_tokens} tokens\n"
        f"Overage: {max(0, actual_tokens - summary_budget_tokens)} tokens\n\n"
        "Rewrite the supplied complete Working Memory as a more compact complete "
        "Working Memory. Return only the full summary text, not tool calls or "
        "section update operations. "
        f"Write the summary in {output_language}. Merge duplicate wording, "
        "remove low-priority process details, resolved issues that no longer "
        "matter, and non-essential URLs or media lists. Preserve current state, "
        "open issues, concrete decisions, dates, numbers, file paths, and user "
        f"corrections. The final output must fit within {summary_budget_tokens} tokens."
    )
    second = str(
        await complete_with_window_budget(
            vlm,
            session_window_context=session_window_context,
            messages=[
                {"role": "system", "content": second_system},
                {"role": "user", "content": overview},
            ],
            completion_kwargs=completion_kwargs,
        )
        or ""
    )
    if estimate_text_tokens(second) <= summary_budget_tokens:
        return second

    third_system = (
        f"Final fallback: write at most {summary_budget_tokens} tokens. Drop details. "
        "Keep only current task, latest state, next step, key constraints or user "
        "corrections, and active paths, numbers, or dates. Do not preserve the "
        "7-section structure. Put the most important information first so that "
        "even a truncated output can support continued work."
    )
    third_user = (
        f"<summary_budget_tokens>{summary_budget_tokens}</summary_budget_tokens>\n"
        "<previous_output>\n"
        f"{second}\n"
        "</previous_output>\n\n"
        "<source_material>\n"
        f"{input_material}\n"
        "</source_material>"
    )
    third_limit = limit_summary_output_tokens(
        vlm, min(session_window_context, summary_budget_tokens)
    )
    material_budget = (
        session_window_context - third_limit - estimate_text_tokens(third_system) - 8
    )
    if material_budget <= 0:
        raise ValueError("Working Memory fallback leaves no room for source material")
    third_user = truncate_text_to_token_budget(
        third_user, material_budget, marker="", head_ratio=0.5
    )
    return str(
        await complete_with_window_budget(
            vlm,
            session_window_context=session_window_context,
            messages=[
                {"role": "system", "content": third_system},
                {"role": "user", "content": third_user},
            ],
            completion_kwargs=completion_kwargs,
            max_tokens=third_limit,
        )
        or ""
    )


def pop_rolling_summary_batch(
    remaining: deque[Message],
    *,
    chunk_limit: int,
    estimate_tokens: Callable[[List[Message]], int],
    format_single: Callable[[Message], str],
) -> List[Message]:
    """Pop one segment of messages fitting within ``chunk_limit`` tokens."""
    if chunk_limit <= 0:
        raise ValueError("Generated summary exceeds the rolling material budget")
    batch_messages: List[Message] = []
    batch_tokens = 0
    while remaining:
        message_tokens = estimate_tokens([remaining[0]])
        if batch_messages and batch_tokens + message_tokens > chunk_limit:
            break
        if not batch_messages and message_tokens > chunk_limit:
            message = remaining.popleft()
            text = (
                "".join(part.text for part in message.parts)
                if all(isinstance(part, TextPart) for part in message.parts)
                else format_single(message)
            )
            low, high = 0, len(text)
            while low < high:
                middle = (low + high + 1) // 2
                if estimate_text_tokens(text[:middle]) <= chunk_limit:
                    low = middle
                else:
                    high = middle - 1
            if low == 0:
                raise ValueError("Rolling summary leaves no room for the next message")
            batch_messages.append(replace(message, parts=[TextPart(text[:low])]))
            if low < len(text):
                remaining.appendleft(replace(message, parts=[TextPart(text[low:])]))
            break
        batch_messages.append(remaining.popleft())
        batch_tokens += message_tokens
        if batch_tokens >= chunk_limit:
            break
    return batch_messages
