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

class _MCPInvokeMixin:

    async def unmount(
        self,
        node_uri: str,
        ctx: RequestContext,
        *,
        wait: bool = False,
    ) -> dict[str, Any]:
        node_uri = self._validate_node_uri(node_uri, ctx)
        async with self._lock(ctx.account_id):
            connection = await self._open_mount_database(ctx)
            try:
                row = connection.execute(
                    "SELECT * FROM live_context_nodes WHERE node_uri = ?",
                    (node_uri,),
                ).fetchone()
                if row is None:
                    raise NotFoundError(node_uri, "live context mount")
                try:
                    content = await self._service.fs.read(node_uri, ctx=ctx)
                except (AGFSNotFoundError, NotFoundError, FileNotFoundError):
                    content = None
                await self._service.fs.rm(node_uri, ctx=ctx, recursive=False, wait=wait)
                connection.execute(
                    "DELETE FROM live_context_nodes WHERE node_uri = ?",
                    (node_uri,),
                )
                try:
                    await self._write_mount_database(connection, ctx)
                except Exception:
                    if content is not None:
                        await self._service.fs.write(
                            node_uri,
                            content,
                            ctx=ctx,
                            mode="create",
                            wait=True,
                        )
                    raise
            finally:
                self._close_mount_database(connection)
        return {
            "node_uri": node_uri,
            "mcp": row["mcp_name"],
            "tool": row["tool_name"],
            "tool_uri": row["tool_uri"],
            "unmounted": True,
        }

    async def batch_unmount(
        self,
        node_uris: list[str],
        ctx: RequestContext,
        *,
        wait: bool = False,
    ) -> dict[str, Any]:
        if not node_uris:
            raise InvalidArgumentError("Batch unmount must contain at least one node URI")

        normalized_node_uris = self._batch_node_uris(node_uris, ctx)

        async with self._lock(ctx.account_id):
            connection = await self._open_mount_database(ctx)
            try:
                rows = []
                failed = []
                for node_uri in normalized_node_uris:
                    try:
                        self._validate_node_uri(node_uri, ctx)
                        await self._service.fs.ensure_remove_access(node_uri, ctx)
                    except Exception as exc:
                        failed.append(self._batch_item_failure(node_uri, exc))
                        continue
                    row = connection.execute(
                        "SELECT * FROM live_context_nodes WHERE node_uri = ?", (node_uri,)
                    ).fetchone()
                    if row is None:
                        failed.append(
                            self._batch_item_failure(
                                node_uri, NotFoundError(node_uri, "live context mount")
                            )
                        )
                        continue
                    rows.append(row)

                completed = []
                for index, row in enumerate(rows):
                    node_uri = row["node_uri"]
                    remove_error = None
                    try:
                        await self._service.fs.rm(
                            node_uri,
                            ctx=ctx,
                            recursive=False,
                            wait=wait,
                        )
                    except Exception as exc:
                        remove_error = exc
                        try:
                            removed = not await self._service.viking_fs.exists(node_uri, ctx=ctx)
                        except Exception:
                            removed = False
                        if not removed:
                            failed.append(self._batch_item_failure(node_uri, exc))
                            continue
                    connection.execute(
                        "DELETE FROM live_context_nodes WHERE node_uri = ?", (node_uri,)
                    )
                    try:
                        await self._persist_batch_mount_database(connection, ctx, node_uri)
                    except OpenVikingError as exc:
                        self._annotate_batch_failure(
                            exc,
                            completed,
                            failed,
                            normalized_node_uris,
                            [remaining["node_uri"] for remaining in rows[index + 1 :]],
                        )
                        raise
                    completed.append(row)
                    if remove_error is not None:
                        failed.append(
                            self._batch_item_failure(node_uri, remove_error, applied=True)
                        )
            finally:
                self._close_mount_database(connection)

        results = [
            {
                "node_uri": row["node_uri"],
                "mcp": row["mcp_name"],
                "tool": row["tool_name"],
                "tool_uri": row["tool_uri"],
                "unmounted": True,
            }
            for row in completed
        ]
        return {
            "unmounts": results,
            "total": len(results),
            "succeeded": self._batch_succeeded(completed, failed),
            "failed": self._batch_failures_in_order(failed, normalized_node_uris),
            "not_attempted": [],
        }

    async def mounts(
        self,
        mcp_name: str,
        tool_name: str | None,
        ctx: RequestContext,
        *,
        target_uri: str | None = None,
    ) -> dict[str, Any]:
        tools_root = self._resolve_tools_root(ctx, target_uri)
        mcp_name = self._validate_server_name(mcp_name)
        await self._registered(mcp_name, ctx, target_uri=tools_root)
        if tool_name is not None and not self._valid_tool_name(tool_name):
            raise InvalidArgumentError("Invalid MCP tool name")

        connection = await self._open_mount_database(ctx)
        try:
            query = "SELECT * FROM live_context_nodes WHERE mcp_name = ? AND tool_uri LIKE ?"
            parameters: tuple[str, ...] = (
                mcp_name,
                f"{tools_root}/{mcp_name}/%",
            )
            if tool_name is not None:
                query += " AND tool_name = ?"
                parameters = (
                    mcp_name,
                    f"{tools_root}/{mcp_name}/%",
                    tool_name,
                )
            query += " ORDER BY tool_name, node_uri"
            rows = connection.execute(query, parameters).fetchall()
        finally:
            self._close_mount_database(connection)

        rows = await self._readable_mount_rows(rows, ctx)
        tags_by_uri = await self._service.fs.get_tags_many(
            [row["node_uri"] for row in rows],
            ctx,
            check_access=False,
        )
        items = []
        for row in rows:
            data = json.loads(row["data"])
            items.append(
                {
                    "node_uri": row["node_uri"],
                    "mcp": row["mcp_name"],
                    "tool": row["tool_name"],
                    "tool_uri": row["tool_uri"],
                    "input_revision": row["input_revision"],
                    "arguments": json.loads(row["args_json"]),
                    "title": data["title"],
                    "description": data.get("description"),
                    "timeout_seconds": data["timeout_seconds"],
                    "tags": tags_by_uri.get(row["node_uri"], []),
                    "created_at": row["created_at"],
                }
            )
        return {
            "root_uri": tools_root,
            "mounts": items,
            "total": len(items),
        }

    async def invoke_live_context(
        self,
        content: str,
        ctx: RequestContext,
    ) -> dict[str, Any] | None:
        invocation = self._parse_live_context_node(content)
        if invocation is None:
            return None
        tool_uri, arguments, timeout_seconds = invocation
        return await self.invoke(
            tool_uri,
            arguments,
            ctx,
            timeout_seconds=timeout_seconds,
        )

    async def read_live_context(
        self,
        content: str,
        ctx: RequestContext,
    ) -> str | None:
        invocation = self._parse_live_context_node(content)
        if invocation is None:
            return None
        tool_uri, arguments, timeout_seconds = invocation
        result = await self.invoke(
            tool_uri,
            arguments,
            ctx,
            timeout_seconds=timeout_seconds,
            require_read_only=True,
        )
        return self._live_context_read_value(result, tool_uri)

    async def invoke(
        self,
        uri: str,
        arguments: dict[str, Any],
        ctx: RequestContext,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        *,
        require_read_only: bool = False,
    ) -> dict[str, Any]:
        uri, tools_root, server_name, tool_name = self._parse_tool_uri(uri, ctx)
        server, headers = await self._registered(
            server_name,
            ctx,
            target_uri=tools_root,
        )
        tool_document = await self._read_tool_document(uri, server_name, tool_name, ctx)
        if require_read_only and not self._tool_is_read_only(tool_document):
            invocation = json.dumps(
                {"tool_uri": uri, "arguments": arguments},
                ensure_ascii=False,
                sort_keys=True,
            )
            raise ProcessingError(
                "Live context read cannot execute a tool explicitly marked as "
                "non-read-only or destructive. Invoke the MCP tool explicitly with "
                f"{invocation}",
                source=uri,
            )
        self._validate_tool_arguments(tool_document, arguments)

        async with self._session(server, headers, timeout_seconds) as session:
            await session.initialize()
            try:
                result: CallToolResult = await session.call_tool(
                    tool_name,
                    arguments=arguments,
                    read_timeout_seconds=timedelta(seconds=timeout_seconds),
                )
            except Exception as exc:
                raise UnavailableError(
                    "MCP tool",
                    f"call failed ({type(exc).__name__}); outcome may be unknown and was not retried",
                ) from exc
        return result.model_dump(mode="json", by_alias=True, exclude_none=True)
