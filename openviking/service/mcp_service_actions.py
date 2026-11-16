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
from openviking.service.mcp_service_models import (
    _AGENT_TOOLS_ROOT, _DEFAULT_TIMEOUT_SECONDS, _MOUNT_SCHEMA, _REGISTRY_VERSION,
    _SERVER_NAME_RE, _TOOL_NAME_RE, _TOOL_URI_RE, MCPToolMount, _decode_read_result, _now,
)

class _MCPActionsMixin:

    async def find(
        self,
        query: str,
        limit: int,
        ctx: RequestContext,
        *,
        include_definition: bool = False,
        target_uri: str | None = None,
    ) -> dict[str, Any]:
        query = query.strip()
        if not query:
            raise InvalidArgumentError("Tool search query must not be empty")

        roots = (
            (self._resolve_tools_root(ctx, target_uri),)
            if target_uri is not None
            else self._tools_roots(ctx)
        )
        search_results = await asyncio.gather(
            *(
                self._service.search.find(
                    query=query,
                    ctx=ctx,
                    target_uri=root,
                    limit=limit,
                    level=[2],
                )
                for root in roots
            )
        )
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for root, search_result in zip(roots, search_results, strict=True):
            result_dict = (
                search_result.to_dict()
                if hasattr(search_result, "to_dict")
                else dict(search_result or {})
            )
            for hit in result_dict.get("resources", []):
                uri = hit.get("uri")
                match = _TOOL_URI_RE.fullmatch(uri) if isinstance(uri, str) else None
                if match is None or not uri.startswith(f"{root}/") or uri in seen:
                    continue
                try:
                    document = await self._tool(uri, ctx)
                except NotFoundError:
                    continue
                seen.add(uri)
                tool = document["tool"]
                results.append(
                    {
                        "uri": uri,
                        "server": match.group("server"),
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "revision": document["revision"],
                        "input_revision": document["input_revision"],
                        "score": hit.get("score", 0.0),
                    }
                )
                if include_definition:
                    results[-1]["tool"] = tool
        results.sort(key=lambda item: item["score"], reverse=True)
        results = results[:limit]
        result = {"tools": results, "total": len(results)}
        if target_uri is not None:
            result["root_uri"] = roots[0]
        else:
            result["root_uris"] = list(roots)
        return result

    async def _registered(
        self,
        name: str,
        ctx: RequestContext,
        *,
        target_uri: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        tools_root = self._resolve_tools_root(ctx, target_uri)
        name = self._validate_server_name(name)
        registry = await self._load(ctx, tools_root)
        server = registry["servers"].get(name)
        if server is None:
            raise NotFoundError(name, "MCP server")
        headers = server.get("headers", {})
        return server, headers

    async def validate(
        self,
        name: str,
        url: str,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        name = self._validate_server_name(name)
        server = {"name": name, "url": self._validate_url(url)}
        headers = self._validate_headers(headers)
        initialized, tools = await self._discover(server, headers)
        return {
            "name": name,
            "valid": True,
            "protocol_version": initialized.protocolVersion,
            "server_info": initialized.serverInfo.model_dump(mode="json"),
            "tool_count": len(tools),
        }

    async def sync(
        self,
        name: str,
        ctx: RequestContext,
        *,
        target_uri: str | None = None,
        wait: bool = False,
    ) -> dict[str, Any]:
        tools_root = self._resolve_tools_root(ctx, target_uri)
        async with self._lock(ctx.account_id):
            server, headers = await self._registered(name, ctx, target_uri=tools_root)
            initialized, discovered = await self._discover(server, headers)
            tools = [self._tool_document(server, tool) for tool in discovered]
            invalid_names = [
                tool["tool"]["name"]
                for tool in tools
                if not self._valid_tool_name(tool["tool"]["name"])
            ]
            if invalid_names:
                raise InvalidArgumentError(
                    f"MCP tool names are not valid OpenViking filenames: {', '.join(invalid_names)}"
                )
            existing_tools = {
                document["tool"]["name"]: document
                for document in await self._catalog(name, ctx, tools_root)
            }
            current_tools = {document["tool"]["name"]: document for document in tools}
            existing_names = set(existing_tools)
            current_names = set(current_tools)
            added = sorted(current_names - existing_names)
            removed = sorted(existing_names - current_names)
            changed = sorted(
                tool_name
                for tool_name in existing_names & current_names
                if existing_tools[tool_name]["input_revision"]
                != current_tools[tool_name]["input_revision"]
            )
            unchanged = sorted((existing_names & current_names) - set(changed))
            definitions_to_publish = sorted(
                tool_name
                for tool_name in current_names
                if tool_name not in existing_tools
                or existing_tools[tool_name]["revision"] != current_tools[tool_name]["revision"]
            )
            await self._publish_catalog(
                name,
                [current_tools[tool_name] for tool_name in definitions_to_publish],
                set(removed),
                ctx,
                tools_root=tools_root,
                wait=wait,
            )
            affected_mounts = await self._affected_mounts(
                name,
                current_tools,
                ctx,
                tools_root,
            )
            registry = await self._load(ctx, tools_root)
            current = registry["servers"][name]
            current.pop("tools", None)
            current["updated_at"] = _now()
            await self._write_document(
                self._registry_path_for_root(ctx, tools_root),
                registry,
            )
        return {
            "name": name,
            "root_uri": tools_root,
            "synced": True,
            "protocol_version": initialized.protocolVersion,
            "tool_count": len(tools),
            "changes": {
                "added": added,
                "changed": changed,
                "unchanged": unchanged,
                "removed": removed,
            },
            "affected_mounts": affected_mounts,
        }

    async def status(
        self,
        name: str,
        ctx: RequestContext,
        *,
        target_uri: str | None = None,
    ) -> dict[str, Any]:
        tools_root = self._resolve_tools_root(ctx, target_uri)
        name = self._validate_server_name(name)
        registry = await self._load(ctx, tools_root)
        server = registry["servers"].get(name)
        if server is None:
            raise NotFoundError(name, "MCP server")
        headers = server.get("headers", {})
        try:
            initialized, tools = await self._discover(server, headers)
            return {
                "name": name,
                "root_uri": tools_root,
                "status": "running",
                "protocol_version": initialized.protocolVersion,
                "tool_count": len(tools),
            }
        except (InvalidArgumentError, UnavailableError) as exc:
            tool_names = await self._catalog_names(name, ctx, tools_root)
            return {
                "name": name,
                "root_uri": tools_root,
                "status": "error",
                "error": str(exc),
                "tool_count": len(tool_names),
            }
