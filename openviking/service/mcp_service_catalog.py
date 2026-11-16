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

class _MCPCatalogMixin:

    async def _publish_catalog(
        self,
        server_name: str,
        tools: list[dict[str, Any]],
        removed_names: set[str],
        ctx: RequestContext,
        *,
        tools_root: str = _AGENT_TOOLS_ROOT,
        wait: bool = True,
    ) -> dict[str, Any] | None:
        server_root = f"{tools_root}/{server_name}"
        await self._ensure_directory(tools_root, ctx)
        await self._ensure_directory(server_root, ctx)

        operations = [
            {
                "uri": f"{server_root}/{item['tool']['name']}.json",
                "content": json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True),
                "mode": "upsert",
            }
            for item in tools
        ]
        result = None
        if operations:
            result = await self._service.fs.batch_write(
                root_uri=server_root,
                operations=operations,
                ctx=ctx,
                wait=wait,
            )

        for name in sorted(removed_names):
            await self._service.fs.rm(
                f"{server_root}/{name}.json",
                ctx=ctx,
                recursive=False,
                wait=wait,
            )
        return result

    async def _catalog_uris(
        self,
        server_name: str,
        ctx: RequestContext,
        tools_root: str = _AGENT_TOOLS_ROOT,
    ) -> list[str]:
        root = f"{tools_root}/{server_name}"
        uris: list[str] = []
        offset = 0
        while True:
            try:
                page = await self._service.fs.ls(
                    root,
                    ctx=ctx,
                    output="original",
                    node_limit=1000,
                    offset=offset,
                )
            except (AGFSNotFoundError, NotFoundError):
                return []
            entries = page.entries
            uris.extend(
                entry["uri"]
                for entry in entries
                if not entry.get("isDir", False)
                and isinstance(entry.get("uri"), str)
                and entry["uri"].endswith(".json")
            )
            if not page.has_more:
                return uris
            if not entries:
                raise RuntimeError(f"Unable to paginate MCP tool catalog: {root}")
            offset += len(entries)

    async def _catalog_names(
        self,
        server_name: str,
        ctx: RequestContext,
        tools_root: str = _AGENT_TOOLS_ROOT,
    ) -> set[str]:
        prefix = f"{tools_root}/{server_name}/"
        return {
            uri[len(prefix) : -len(".json")]
            for uri in await self._catalog_uris(server_name, ctx, tools_root)
            if uri.startswith(prefix)
        }

    async def _catalog(
        self,
        server_name: str,
        ctx: RequestContext,
        tools_root: str = _AGENT_TOOLS_ROOT,
    ) -> list[dict[str, Any]]:
        uris = await self._catalog_uris(server_name, ctx, tools_root)
        contents = await asyncio.gather(*(self._service.fs.read(uri, ctx=ctx) for uri in uris))
        documents: list[dict[str, Any]] = []
        for uri, content in zip(uris, contents, strict=True):
            try:
                document = json.loads(content)
                tool = document["tool"]
                tool_name = tool["name"]
            except (KeyError, TypeError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"Invalid MCP tool document: {uri}") from exc
            expected_uri = f"{tools_root}/{server_name}/{tool_name}.json"
            if (
                not isinstance(document, dict)
                or not isinstance(tool, dict)
                or not isinstance(tool_name, str)
                or document.get("server") != server_name
                or uri != expected_uri
            ):
                raise RuntimeError(f"Invalid MCP tool document: {uri}")
            documents.append({"uri": uri, **document})
        return documents

    async def _tool(self, uri: str, ctx: RequestContext) -> dict[str, Any]:
        uri, tools_root, server_name, tool_name = self._parse_tool_uri(uri, ctx)
        await self._registered(server_name, ctx, target_uri=tools_root)
        return await self._read_tool_document(uri, server_name, tool_name, ctx)

    async def _read_tool_document(
        self,
        uri: str,
        server_name: str,
        tool_name: str,
        ctx: RequestContext,
    ) -> dict[str, Any]:
        """Read and validate a tool definition after checking its server registration."""
        try:
            content = await self._service.fs.read(uri, ctx=ctx)
            document = json.loads(content)
            tool = document["tool"]
        except (AGFSNotFoundError, NotFoundError, FileNotFoundError) as exc:
            raise NotFoundError(uri, "MCP tool") from exc
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Invalid MCP tool document: {uri}") from exc
        if (
            not isinstance(document, dict)
            or document.get("server") != server_name
            or not isinstance(document.get("revision"), str)
            or not isinstance(document.get("input_revision"), str)
            or not isinstance(tool, dict)
            or tool.get("name") != tool_name
        ):
            raise RuntimeError(f"Invalid MCP tool document: {uri}")
        return document

    async def add(
        self,
        name: str,
        url: str,
        headers: dict[str, str],
        ctx: RequestContext,
        *,
        target_uri: str | None = None,
        wait: bool = False,
    ) -> dict[str, Any]:
        tools_root = self._resolve_tools_root(ctx, target_uri)
        name = self._validate_server_name(name)
        url = self._validate_url(url)
        headers = self._validate_headers(headers)
        candidate = {"name": name, "url": url}
        initialized, discovered = await self._discover(candidate, headers)
        tools = [self._tool_document(candidate, tool) for tool in discovered]
        invalid_names = [
            tool["tool"]["name"]
            for tool in tools
            if not self._valid_tool_name(tool["tool"]["name"])
        ]
        if invalid_names:
            raise InvalidArgumentError(
                f"MCP tool names are not valid OpenViking filenames: {', '.join(invalid_names)}"
            )

        async with self._lock(ctx.account_id):
            registry = await self._load(ctx, tools_root)
            if name in registry["servers"]:
                raise AlreadyExistsError(name, "MCP server")
            timestamp = _now()
            server = {
                "name": name,
                "url": url,
                "headers": headers,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            processing = await self._publish_catalog(
                name,
                tools,
                set(),
                ctx,
                tools_root=tools_root,
                wait=wait,
            )
            registry["servers"][name] = server
            await self._write_document(
                self._registry_path_for_root(ctx, tools_root),
                registry,
            )

        result = {
            **self._public_server(server, len(tools), tools_root),
            "protocol_version": initialized.protocolVersion,
        }
        if processing is not None:
            result["processing"] = processing
        return result

    async def remove(
        self,
        name: str,
        ctx: RequestContext,
        *,
        target_uri: str | None = None,
    ) -> dict[str, Any]:
        tools_root = self._resolve_tools_root(ctx, target_uri)
        name = self._validate_server_name(name)
        async with self._lock(ctx.account_id):
            registry = await self._load(ctx, tools_root)
            if name not in registry["servers"]:
                raise NotFoundError(name, "MCP server")
            await self._service.fs.rm(
                f"{tools_root}/{name}",
                ctx=ctx,
                recursive=True,
                wait=True,
            )
            registry["servers"].pop(name)
            await self._write_document(
                self._registry_path_for_root(ctx, tools_root),
                registry,
            )
        return {"name": name, "root_uri": tools_root, "removed": True}

    async def list(
        self,
        ctx: RequestContext,
        *,
        target_uri: str | None = None,
    ) -> dict[str, Any]:
        roots = (
            (self._resolve_tools_root(ctx, target_uri),)
            if target_uri is not None
            else self._tools_roots(ctx)
        )
        registries = await asyncio.gather(*(self._load(ctx, root) for root in roots))
        entries = [
            (root, name, server)
            for root, registry in zip(roots, registries, strict=True)
            for name, server in sorted(registry["servers"].items())
        ]
        counts = await asyncio.gather(
            *(self._catalog_names(name, ctx, root) for root, name, _ in entries)
        )
        servers = [
            self._public_server(server, len(tool_names), root)
            for (root, _, server), tool_names in zip(entries, counts, strict=True)
        ]
        result: dict[str, Any] = {"servers": servers, "total": len(servers)}
        if target_uri is not None:
            result["root_uri"] = roots[0]
        else:
            result["root_uris"] = list(roots)
        return result

    async def show(
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
        tools = await self._catalog(name, ctx, tools_root)
        return {
            **self._public_server(server, len(tools), tools_root),
            "tools": tools,
        }
