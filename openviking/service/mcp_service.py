# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Account-scoped MCP server registry and tool catalog management."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sqlite3
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.parse import urlsplit

import httpx
import yaml
from jsonschema import SchemaError, ValidationError, validate
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, InitializeResult, Tool

from openviking.core.namespace import canonical_user_root
from openviking.core.path_variables import resolve_path_variables
from openviking.core.uri_validation import validate_request_viking_uri
from openviking.pyagfs import AGFSNotFoundError, AsyncAGFSClient
from openviking.server.identity import RequestContext
from openviking_cli.exceptions import (
    AlreadyExistsError,
    InvalidArgumentError,
    NotFoundError,
    OpenVikingError,
    ProcessingError,
    UnavailableError,
)
from openviking.service.mcp_service_actions import _MCPActionsMixin
from openviking.service.mcp_service_catalog import _MCPCatalogMixin
from openviking.service.mcp_service_invoke import _MCPInvokeMixin
from openviking.service.mcp_service_models import (
    MCPToolMount, _MCPValidationMixin, _decode_read_result, _now,
)
from openviking.service.mcp_service_mounts import _MCPMountOpsMixin
from openviking.service.mcp_service_store import _MCPStoreMixin


class MCPService(
    _MCPValidationMixin,
    _MCPStoreMixin,
    _MCPCatalogMixin,
    _MCPActionsMixin,
    _MCPMountOpsMixin,
    _MCPInvokeMixin,
):
    """Manage remote Streamable HTTP MCP servers for one OpenViking account."""

    def __init__(self, service: Any) -> None:
        self._service = service
        self._async_agfs: AsyncAGFSClient | None = None
        self._locks: dict[str, asyncio.Lock] = {}

__all__ = ["MCPService", "MCPToolMount"]
