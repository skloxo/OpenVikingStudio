# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Redis directory indexes and expiry-driven maintenance for the OV writer."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from bisect import bisect_right
from collections import OrderedDict
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from itertools import islice
from random import uniform
from typing import TYPE_CHECKING, Any, Sequence
from urllib.parse import quote
from uuid import uuid4
from zoneinfo import ZoneInfo

from openviking.config.ttl import (
    TTL_ROOT_DEPTH,
    TTLIndexType,
    classify_ttl_uri,
    resolve_effective_ttl,
    validate_ttl_root,
)
from openviking.core.namespace import uri_parts
from openviking.scheduling.expiry.api import (
    TTL_ITEM_TYPE,
    CallbackRequest,
    CallbackResult,
    CallbackStatus,
    ExpiryRegistration,
    ExpiryScheduler,
    HandlerOptions,
    ItemIdentity,
)
from openviking.scheduling.expiry.config import ExpiryRedisConfig
from openviking.scheduling.expiry.redis_store import create_redis_client
from openviking.server.error_mapping import is_not_found_error
from openviking.server.identity import RequestContext, Role
from openviking.service.task_tracker_concurrency import OwnerLoopDispatcher
from openviking.storage.abstract_overview import ABSTRACT_OVERVIEW_FILENAMES
from openviking.ttl.adapter import TTLBackfillRequest, TTLRecycleRequest, TTLRecycleResult
from openviking_cli.exceptions import (
    ConflictError,
    FailedPreconditionError,
    InvalidArgumentError,
    NotFoundError,
    UnavailableError,
)
from openviking_cli.session.user_id import UserIdentifier
from openviking_cli.utils.config.ttl_config import TTLConfig

if TYPE_CHECKING:
    from openviking.server.api_keys import APIKeyManager
    from openviking.service.core import OpenVikingService

TTLDirectory = tuple[TTLIndexType, str, str, list[str]]

logger = logging.getLogger(__name__)
DAY_MS = 86_400_000
# The schema uses Go url.PathEscape, not QueryEscape or Python's default quote.
PATH_SAFE = "-._~$&+:=@"
RESET = """
local intents = cjson.decode(ARGV[3])
local matched = {}
for scope, token in pairs(intents) do
  if redis.call('HGET', KEYS[4], scope) == token then
    table.insert(matched, scope)
  end
end
-- An acknowledged or superseded automatic reset must not erase new progress.
if next(intents) and #matched == 0 then return 2 end
redis.call('DEL', KEYS[2])
redis.call('HSET', KEYS[1], 'roots', ARGV[1], 'checkpoint', ARGV[2], 'discover', ARGV[4])
redis.call('SADD', KEYS[3], 'initial')
if ARGV[4] == '0' then
  for _, scope in ipairs(matched) do redis.call('HDEL', KEYS[4], scope) end
end
return 1
"""
INITIAL = """
local roots = redis.call('HGET', KEYS[1], 'roots')
local discover = redis.call('HGET', KEYS[1], 'discover') == '1'
if roots and roots ~= ARGV[1] and not discover then return 0 end
if not roots or discover then redis.call('HSET', KEYS[1], 'roots', ARGV[1]) end
redis.call('HSETNX', KEYS[1], 'checkpoint', ARGV[2])
redis.call('HSET', KEYS[1], 'discover', ARGV[4])
if not redis.call('GET', KEYS[2]) then redis.call('SADD', KEYS[3], 'initial') end
return 1
"""
REMOVE = """
local score = redis.call('ZSCORE', KEYS[1], ARGV[1])
if score and tonumber(score) == tonumber(ARGV[2]) then
  return redis.call('ZREM', KEYS[1], ARGV[1])
end
return 0
"""
READ_INITIAL = """
local intents = {}
local fields = redis.call('HGETALL', KEYS[4])
for i = 1, #fields, 2 do intents[fields[i]] = fields[i + 1] end
local encoded = '{}'
if #fields > 0 then encoded = cjson.encode(intents) end
return {redis.call('HGET', KEYS[1], 'roots') or '',
        redis.call('HGET', KEYS[1], 'checkpoint') or '',
        redis.call('GET', KEYS[2]) or '',
        tostring(redis.call('SISMEMBER', KEYS[3], 'initial')), encoded,
        redis.call('HGET', KEYS[1], 'discover') or '0'}
"""


def directory(uri: str) -> TTLDirectory | None:
    """Return (index type, policy root, recycle unit, date components)."""
    try:
        parts = uri_parts(uri)
    except (TypeError, ValueError):
        return None
    kind = classify_ttl_uri(uri)
    if kind is None:
        return None
    root_depth = TTL_ROOT_DEPTH[kind]
    root = "viking://" + "/".join(parts[:root_depth])
    unit_depth = 1 if kind == "sessions" else 3
    if len(parts) < root_depth + unit_depth:
        return None
    date_parts = parts[root_depth : root_depth + unit_depth]
    if kind == "sessions" and date_parts[0] in ABSTRACT_OVERVIEW_FILENAMES:
        return None
    if kind != "sessions":
        if not re.fullmatch(r"\d{4}/\d{2}/\d{2}", "/".join(date_parts)):
            return None
        try:
            datetime(*map(int, date_parts))
        except ValueError:
            return None
    return kind, root, root + "/" + "/".join(date_parts), date_parts


def next_check_ms(resource_id: str, now_ms: int) -> int:
    """Preserve the Server's FNV-1a32 hourly offset; skip missed windows."""
    value = 2166136261
    for byte in resource_id.encode():
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    hour = 3_600_000
    due = now_ms // hour * hour + value % 3600 * 1000
    return due if due > now_ms else due + hour


