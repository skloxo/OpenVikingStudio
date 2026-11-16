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

class _MCPMountOpsMixin:

    async def mount(
        self,
        tool_uri: str,
        node_uri: str,
        title: str,
        description: str | None,
        timeout_seconds: int,
        arguments: dict[str, Any],
        ctx: RequestContext,
        *,
        tags: list[str] | None = None,
        wait: bool = False,
    ) -> dict[str, Any]:
        if not title.strip():
            raise InvalidArgumentError("Live context node title must not be empty")
        if timeout_seconds <= 0:
            raise InvalidArgumentError("Live context node timeout_seconds must be positive")
        node_uri = self._validate_node_uri(node_uri, ctx)
        async with self._lock(ctx.account_id):
            tool_document = await self._tool(tool_uri, ctx)
            self._validate_tool_arguments(tool_document, arguments)
            tool_uri, _, server_name, tool_name = self._parse_tool_uri(tool_uri, ctx)

            connection = await self._open_mount_database(ctx)
            try:
                existing = connection.execute(
                    "SELECT * FROM live_context_nodes WHERE node_uri = ?",
                    (node_uri,),
                ).fetchone()
                content = self._render_live_context_node(
                    tool_uri,
                    tool_document,
                    title,
                    description,
                    timeout_seconds,
                    arguments,
                )
                arguments_json = json.dumps(arguments, ensure_ascii=False, sort_keys=True)
                created_at = existing["created_at"] if existing is not None else _now()
                mount_data = {
                    "title": title,
                    "description": description,
                    "timeout_seconds": timeout_seconds,
                }
                await self._service.fs.write(
                    node_uri,
                    content,
                    ctx=ctx,
                    mode="replace",
                    wait=wait,
                    tags=tags,
                )
                connection.execute(
                    """
                    INSERT INTO live_context_nodes (
                        node_uri, mcp_name, tool_name, tool_uri, input_revision, args_json,
                        data, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(node_uri) DO UPDATE SET
                        mcp_name = excluded.mcp_name,
                        tool_name = excluded.tool_name,
                        tool_uri = excluded.tool_uri,
                        input_revision = excluded.input_revision,
                        args_json = excluded.args_json,
                        data = excluded.data
                    """,
                    (
                        node_uri,
                        server_name,
                        tool_name,
                        tool_uri,
                        tool_document["input_revision"],
                        arguments_json,
                        json.dumps(mount_data, ensure_ascii=False, sort_keys=True),
                        created_at,
                    ),
                )
                await self._write_mount_database(connection, ctx)
            finally:
                self._close_mount_database(connection)

        return {
            "node_uri": node_uri,
            "mcp": server_name,
            "tool": tool_name,
            "tool_uri": tool_uri,
            "input_revision": tool_document["input_revision"],
            "title": title,
            "description": description,
            "timeout_seconds": timeout_seconds,
            "arguments": arguments,
            "created_at": created_at,
            "mounted": True,
        }

    async def batch_mount(
        self,
        mounts: list[MCPToolMount],
        ctx: RequestContext,
        *,
        wait: bool = False,
    ) -> dict[str, Any]:
        if not mounts:
            raise InvalidArgumentError("Batch mount must contain at least one mount")
        node_uris = self._batch_node_uris([mount.node_uri for mount in mounts], ctx)

        async with self._lock(ctx.account_id):
            prepared: list[dict[str, Any]] = []
            failed: list[dict[str, Any]] = []
            tool_documents: dict[str, dict[str, Any]] = {}
            for mount, node_uri in zip(mounts, node_uris, strict=True):
                try:
                    item = await self._prepare_batch_mount(mount, ctx, tool_documents)
                    await self._service.fs.ensure_write_access(node_uri, ctx)
                except Exception as exc:
                    failed.append(self._batch_item_failure(node_uri, exc))
                    continue
                prepared.append(item)

            connection = await self._open_mount_database(ctx)
            try:
                for item in prepared:
                    existing = connection.execute(
                        "SELECT created_at FROM live_context_nodes WHERE node_uri = ?",
                        (item["node_uri"],),
                    ).fetchone()
                    item["created_at"] = existing["created_at"] if existing is not None else _now()
                    item["data"] = {
                        "title": item["title"],
                        "description": item["description"],
                        "timeout_seconds": item["timeout_seconds"],
                    }

                completed: list[dict[str, Any]] = []
                for index, item in enumerate(prepared):
                    write_error = None
                    try:
                        await self._service.fs.write(
                            item["node_uri"],
                            item["content"],
                            ctx=ctx,
                            mode="replace",
                            wait=wait,
                            tags=item.get("tags"),
                        )
                    except Exception as exc:
                        write_error = exc
                        # Refresh/wait can fail after the content was persisted.
                        # Register that node without rewriting its content or ACL.
                        try:
                            persisted = (
                                await self._service.fs.read(
                                    item["node_uri"], ctx=replace(ctx, bypass_acl=True)
                                )
                                == item["content"]
                            )
                        except Exception:
                            persisted = False
                        if not persisted:
                            failed.append(self._batch_item_failure(item["node_uri"], exc))
                            continue
                    connection.execute(
                        """
                        INSERT INTO live_context_nodes (
                            node_uri, mcp_name, tool_name, tool_uri, input_revision, args_json,
                            data, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(node_uri) DO UPDATE SET
                            mcp_name = excluded.mcp_name,
                            tool_name = excluded.tool_name,
                            tool_uri = excluded.tool_uri,
                            input_revision = excluded.input_revision,
                            args_json = excluded.args_json,
                            data = excluded.data
                        """,
                        (
                            item["node_uri"],
                            item["server_name"],
                            item["tool_name"],
                            item["tool_uri"],
                            item["tool_document"]["input_revision"],
                            item["arguments_json"],
                            json.dumps(item["data"], ensure_ascii=False, sort_keys=True),
                            item["created_at"],
                        ),
                    )
                    try:
                        await self._persist_batch_mount_database(connection, ctx, item["node_uri"])
                    except OpenVikingError as exc:
                        self._annotate_batch_failure(
                            exc,
                            completed,
                            failed,
                            node_uris,
                            [remaining["node_uri"] for remaining in prepared[index + 1 :]],
                        )
                        raise
                    completed.append(item)
                    if write_error is not None:
                        failed.append(
                            self._batch_item_failure(item["node_uri"], write_error, applied=True)
                        )
            finally:
                self._close_mount_database(connection)

        results = [
            {
                "node_uri": item["node_uri"],
                "mcp": item["server_name"],
                "tool": item["tool_name"],
                "tool_uri": item["tool_uri"],
                "input_revision": item["tool_document"]["input_revision"],
                "title": item["title"],
                "description": item.get("description"),
                "timeout_seconds": item["timeout_seconds"],
                "arguments": item["arguments"],
                "created_at": item["created_at"],
                "mounted": True,
            }
            for item in completed
        ]
        return {
            "mounts": results,
            "total": len(results),
            "succeeded": self._batch_succeeded(completed, failed),
            "failed": self._batch_failures_in_order(failed, node_uris),
            "not_attempted": [],
        }

    def _batch_node_uris(self, node_uris: list[str], ctx: RequestContext) -> list[str]:
        """Reject duplicates before mutations, leaving invalid targets to item validation."""
        normalized = []
        seen = set()
        for raw_uri in node_uris:
            try:
                uri = validate_request_viking_uri(raw_uri, ctx, field_name="live context node URI")
            except OpenVikingError:
                uri = raw_uri
            if uri in seen:
                raise InvalidArgumentError(f"Duplicate batch node URI: {uri}")
            seen.add(uri)
            normalized.append(uri)
        return normalized

    async def _prepare_batch_mount(
        self,
        mount: MCPToolMount,
        ctx: RequestContext,
        tool_documents: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        node_uri = self._validate_node_uri(mount.node_uri, ctx)
        if not mount.title.strip():
            raise InvalidArgumentError("Live context node title must not be empty")
        if mount.timeout_seconds <= 0:
            raise InvalidArgumentError("Live context node timeout_seconds must be positive")
        tool_document = tool_documents.get(mount.tool_uri)
        if tool_document is None:
            tool_document = await self._tool(mount.tool_uri, ctx)
            tool_documents[mount.tool_uri] = tool_document
        self._validate_tool_arguments(tool_document, mount.arguments)
        tool_uri, _, server_name, tool_name = self._parse_tool_uri(mount.tool_uri, ctx)
        return {
            "tool_uri": tool_uri,
            "node_uri": node_uri,
            "title": mount.title,
            "description": mount.description,
            "timeout_seconds": mount.timeout_seconds,
            "arguments": mount.arguments,
            "arguments_json": json.dumps(mount.arguments, ensure_ascii=False, sort_keys=True),
            "tags": mount.tags,
            "tool_document": tool_document,
            "server_name": server_name,
            "tool_name": tool_name,
            "content": self._render_live_context_node(
                tool_uri,
                tool_document,
                mount.title,
                mount.description,
                mount.timeout_seconds,
                mount.arguments,
            ),
        }

    @staticmethod
    def _batch_succeeded(
        completed: list[dict[str, Any]] | list[sqlite3.Row], failed: list[dict[str, Any]]
    ) -> list[str]:
        failed_uris = {item["node_uri"] for item in failed}
        return [item["node_uri"] for item in completed if item["node_uri"] not in failed_uris]

    @staticmethod
    def _batch_failures_in_order(
        failed: list[dict[str, Any]], node_uris: list[str]
    ) -> list[dict[str, Any]]:
        by_uri = {item["node_uri"]: item for item in failed}
        return [by_uri[uri] for uri in node_uris if uri in by_uri]

    def _annotate_batch_failure(
        self,
        error: OpenVikingError,
        completed: list[dict[str, Any]] | list[sqlite3.Row],
        failed: list[dict[str, Any]],
        node_uris: list[str],
        not_attempted: list[str],
    ) -> None:
        failures = [*failed, self._batch_item_failure(error.details["node_uri"], error)]
        error.details.update(
            {
                "succeeded": self._batch_succeeded(completed, failures),
                "failed": self._batch_failures_in_order(failures, node_uris),
                "not_attempted": not_attempted,
            }
        )

    @staticmethod
    def _batch_item_failure(
        node_uri: str, error: Exception, *, applied: bool = False
    ) -> dict[str, Any]:
        return {
            "node_uri": node_uri,
            "code": getattr(error, "code", "UNKNOWN"),
            "message": str(error),
            "applied": applied,
        }

    async def _persist_batch_mount_database(
        self, connection: sqlite3.Connection, ctx: RequestContext, node_uri: str
    ) -> None:
        """Retry only the current record snapshot, never the filesystem mutation."""
        try:
            await self._write_mount_database(connection, ctx)
        except Exception:
            try:
                await self._write_mount_database(connection, ctx)
            except Exception as exc:
                raise OpenVikingError(
                    "Could not persist live context mount records; filesystem changes were retained",
                    code="PROCESSING_ERROR",
                    details={"node_uri": node_uri, "reconciliation_required": True},
                ) from exc
