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

class _MCPStoreMixin:

    def _agfs(self) -> AsyncAGFSClient:
        if self._async_agfs is None:
            agfs = self._service._agfs
            if agfs is None:
                raise RuntimeError("AGFS is not initialized")
            self._async_agfs = agfs if isinstance(agfs, AsyncAGFSClient) else AsyncAGFSClient(agfs)
        return self._async_agfs

    def _lock(self, account_id: str) -> asyncio.Lock:
        return self._locks.setdefault(account_id, asyncio.Lock())

    @staticmethod
    def _registry_path(account_id: str, user_id: str | None = None) -> str:
        if user_id is not None:
            return f"/local/{account_id}/_system/mcps/{user_id}.json"
        return f"/local/{account_id}/_system/mcps.json"

    @staticmethod
    def _mounts_path(account_id: str) -> str:
        return f"/local/{account_id}/_system/live_context_nodes.dat"

    @staticmethod
    def _empty_document() -> dict[str, Any]:
        return {"version": _REGISTRY_VERSION, "servers": {}}

    async def _read_document(self, path: str) -> dict[str, Any]:
        try:
            raw = _decode_read_result(await self._agfs().read(path))
        except (AGFSNotFoundError, FileNotFoundError):
            return self._empty_document()
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Invalid MCP registry document: {path}") from exc
        if not isinstance(document, dict) or not isinstance(document.get("servers"), dict):
            raise RuntimeError(f"Invalid MCP registry document: {path}")
        return document

    async def _write_document(self, path: str, document: dict[str, Any]) -> None:
        await self._agfs().ensure_parent_dirs(path)
        payload = json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ).encode("utf-8")
        await self._agfs().write(path, payload)

    async def _open_mount_database(self, ctx: RequestContext) -> sqlite3.Connection:
        path = self._mounts_path(ctx.account_id)
        try:
            raw = _decode_read_result(await self._agfs().read(path))
        except (AGFSNotFoundError, FileNotFoundError):
            raw = b""
        temporary = tempfile.NamedTemporaryFile(
            prefix="openviking-mounts-",
            suffix=".sqlite3",
            delete=False,
        )
        temporary_path = temporary.name
        if raw:
            temporary.write(raw)
            temporary.flush()
        temporary.close()
        connection = sqlite3.connect(temporary_path)
        connection.row_factory = sqlite3.Row
        try:
            connection.executescript(_MOUNT_SCHEMA)
            return connection
        except sqlite3.DatabaseError as exc:
            connection.close()
            Path(temporary_path).unlink(missing_ok=True)
            raise RuntimeError(f"Invalid live context mount database: {path}") from exc

    @staticmethod
    def _close_mount_database(connection: sqlite3.Connection) -> None:
        row = connection.execute("PRAGMA database_list").fetchone()
        temporary_path = row[2] if row and len(row) > 2 else ""
        connection.close()
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)

    async def _write_mount_database(
        self,
        connection: sqlite3.Connection,
        ctx: RequestContext,
    ) -> None:
        connection.commit()
        row = connection.execute("PRAGMA database_list").fetchone()
        database_path = row[2] if row and len(row) > 2 else ""
        if not database_path:
            raise RuntimeError("Live context mount database has no backing file")
        payload = Path(database_path).read_bytes()
        path = self._mounts_path(ctx.account_id)
        await self._agfs().ensure_parent_dirs(path)
        await self._agfs().write(path, payload)

    async def _load(
        self,
        ctx: RequestContext,
        tools_root: str = _AGENT_TOOLS_ROOT,
    ) -> dict[str, Any]:
        registry = await self._read_document(self._registry_path_for_root(ctx, tools_root))
        for server in registry["servers"].values():
            if isinstance(server, dict):
                server.pop("tools", None)
        return registry

    async def _session(
        self,
        server: dict[str, Any],
        headers: dict[str, str],
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> AsyncIterator[ClientSession]:
        timeout = httpx.Timeout(timeout_seconds, read=timeout_seconds)
        try:
            async with httpx.AsyncClient(headers=headers, timeout=timeout) as http_client:
                async with streamable_http_client(
                    server["url"],
                    http_client=http_client,
                ) as (read, write, _):
                    async with ClientSession(
                        read,
                        write,
                        read_timeout_seconds=timedelta(seconds=timeout_seconds),
                    ) as session:
                        yield session
        except (InvalidArgumentError, NotFoundError, UnavailableError):
            raise
        except Exception as exc:
            raise UnavailableError(
                "MCP server",
                f"connection failed ({type(exc).__name__}); check endpoint and credentials",
            ) from exc

    async def _discover(
        self,
        server: dict[str, Any],
        headers: dict[str, str],
    ) -> tuple[InitializeResult, list[Tool]]:
        async with self._session(server, headers) as session:
            initialized = await session.initialize()
            tools: list[Tool] = []
            cursor: str | None = None
            seen: set[str] = set()
            for _ in range(100):
                result = await session.list_tools(cursor=cursor)
                tools.extend(result.tools)
                cursor = result.nextCursor
                if not cursor:
                    return initialized, tools
                if cursor in seen:
                    raise InvalidArgumentError(
                        "MCP server returned a repeated tool pagination cursor"
                    )
                seen.add(cursor)
            raise InvalidArgumentError("MCP tool catalog exceeded 100 pages")

    async def _ensure_directory(self, uri: str, ctx: RequestContext) -> None:
        if await self._service.viking_fs.exists(uri, ctx=ctx):
            return
        try:
            await self._service.fs.mkdir(uri, ctx=ctx)
        except AlreadyExistsError:
            return
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                raise

    async def _readable_mount_rows(
        self,
        rows: list[sqlite3.Row],
        ctx: RequestContext,
    ) -> list[sqlite3.Row]:
        if not rows:
            return []
        access = await self._service.fs.can_read_many(
            [row["node_uri"] for row in rows],
            ctx,
        )
        return [row for row in rows if access.get(row["node_uri"], False)]

    async def _affected_mounts(
        self,
        server_name: str,
        current_tools: dict[str, dict[str, Any]],
        ctx: RequestContext,
        tools_root: str = _AGENT_TOOLS_ROOT,
    ) -> list[dict[str, Any]]:
        connection = await self._open_mount_database(ctx)
        try:
            rows = connection.execute(
                """
                SELECT * FROM live_context_nodes
                WHERE mcp_name = ? AND tool_uri LIKE ?
                ORDER BY tool_name, node_uri
                """,
                (server_name, f"{tools_root}/{server_name}/%"),
            ).fetchall()
        finally:
            self._close_mount_database(connection)

        rows = await self._readable_mount_rows(rows, ctx)
        affected: list[dict[str, Any]] = []
        for row in rows:
            current = current_tools.get(row["tool_name"])
            item = {
                "node_uri": row["node_uri"],
                "tool_uri": row["tool_uri"],
                "tool": row["tool_name"],
                "mounted_input_revision": row["input_revision"],
                "current_input_revision": (
                    current["input_revision"] if current is not None else None
                ),
            }
            if current is None:
                affected.append(
                    {
                        **item,
                        "status": "REMOVED",
                        "reason": "Tool is no longer provided by the MCP server",
                    }
                )
                continue
            if row["input_revision"] == current["input_revision"]:
                continue

            try:
                arguments = json.loads(row["args_json"])
                if not isinstance(arguments, dict):
                    raise ValueError("mounted arguments are not a JSON object")
                self._validate_tool_arguments(current, arguments)
            except (InvalidArgumentError, RuntimeError, ValueError) as exc:
                affected.append(
                    {
                        **item,
                        "status": "INVALID",
                        "reason": f"Tool input revision changed; {exc}",
                    }
                )
            else:
                affected.append(
                    {
                        **item,
                        "status": "REVIEW",
                        "reason": (
                            "Tool input revision changed; mounted arguments remain valid "
                            "under the current input schema"
                        ),
                    }
                )
        return affected
