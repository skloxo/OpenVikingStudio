# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Cursor pagination and keyword filtering helpers for /api/v1/tasks."""

import base64
import json
from typing import Any, Iterable, Optional

from openviking_cli.exceptions import InvalidArgumentError


def matches_task_query(task: Any, query: Optional[str]) -> bool:
    """Case-insensitive substring filter across task ID, resource, status, and compile request."""
    needle = (query or "").strip().lower()
    if not needle:
        return True

    candidates: list[str] = [
        str(getattr(task, "task_id", "") or ""),
        str(getattr(task, "resource_id", "") or ""),
        str(getattr(task, "task_type", "") or ""),
        str(getattr(getattr(task, "status", None), "value", getattr(task, "status", "")) or ""),
        str(getattr(task, "error", "") or ""),
    ]
    meta = getattr(task, "meta", None)
    if isinstance(meta, dict):
        if meta.get("human_title"):
            candidates.append(str(meta["human_title"]))
        req = meta.get("request")
        if isinstance(req, dict):
            for key in ("skill", "to"):
                if req.get(key):
                    candidates.append(str(req[key]))
            sources = req.get("from")
            if isinstance(sources, list):
                candidates.extend(str(s) for s in sources if s)

    return any(needle in text.lower() for text in candidates if text)


def _encode_cursor(created_at: float, task_id: str) -> str:
    payload = json.dumps({"created_at": created_at, "task_id": task_id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[float, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict) or "created_at" not in data or "task_id" not in data:
            raise ValueError("missing fields")
        return float(data["created_at"]), str(data["task_id"])
    except Exception as exc:
        raise InvalidArgumentError(f"Invalid pagination cursor: {cursor}") from exc


def paginate_tasks_cursor(
    tasks: Iterable[Any],
    *,
    limit: int,
    cursor: Optional[str] = None,
    q: Optional[str] = None,
) -> dict[str, Any]:
    """Filter, sort descending by (created_at, task_id), and return cursor page payload."""
    filtered = [t for t in tasks if matches_task_query(t, q)]
    filtered.sort(key=lambda t: (float(getattr(t, "created_at", 0.0)), str(t.task_id)), reverse=True)

    if cursor:
        cursor_key = _decode_cursor(cursor)
        filtered = [
            t
            for t in filtered
            if (float(getattr(t, "created_at", 0.0)), str(t.task_id)) < cursor_key
        ]

    page_items = filtered[:limit]
    has_more = len(filtered) > limit
    next_cursor = (
        _encode_cursor(float(getattr(page_items[-1], "created_at", 0.0)), str(page_items[-1].task_id))
        if has_more and page_items
        else None
    )
    return {
        "items": [t.to_dict() for t in page_items],
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
