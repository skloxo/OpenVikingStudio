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

_SERVER_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
_TOOL_URI_RE = re.compile(
    r"^viking://(?P<scope>agent|user/[^/]+)/tools/"
    r"(?P<server>[A-Za-z0-9_-]{1,64})/"
    r"(?P<tool>[A-Za-z0-9_.-]{1,128})\.json$"
)
_AGENT_TOOLS_ROOT = "viking://agent/tools"
_REGISTRY_VERSION = 1
_DEFAULT_TIMEOUT_SECONDS = 30.0
_MOUNT_SCHEMA = """
CREATE TABLE IF NOT EXISTS live_context_nodes (
    node_uri TEXT PRIMARY KEY,
    mcp_name TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_uri TEXT NOT NULL,
    input_revision TEXT NOT NULL,
    args_json TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_live_context_nodes_tool
ON live_context_nodes (mcp_name, tool_name);
"""


@dataclass(frozen=True, slots=True)
class MCPToolMount:
    tool_uri: str
    node_uri: str
    title: str
    description: str | None
    timeout_seconds: int
    arguments: dict[str, Any]
    tags: list[str] | None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decode_read_result(result: Any) -> bytes:
    if isinstance(result, bytes):
        return result
    content = getattr(result, "content", None)
    if isinstance(content, bytes):
        return content
    if isinstance(content, str):
        return content.encode("utf-8")
    if isinstance(result, str):
        return result.encode("utf-8")
    raise ValueError("MCP registry content must be bytes or JSON text")



class _MCPValidationMixin:

    @staticmethod
    def _user_tools_root(ctx: RequestContext) -> str:
        return f"{canonical_user_root(ctx)}/tools"

    @classmethod
    def _tools_roots(cls, ctx: RequestContext) -> tuple[str, str]:
        return cls._user_tools_root(ctx), _AGENT_TOOLS_ROOT

    @classmethod
    def _resolve_tools_root(
        cls,
        ctx: RequestContext,
        target_uri: str | None,
    ) -> str:
        if target_uri is None:
            return cls._user_tools_root(ctx)
        normalized = validate_request_viking_uri(
            resolve_path_variables(target_uri),
            ctx,
            field_name="target_uri",
        ).rstrip("/")
        allowed = cls._tools_roots(ctx)
        if normalized not in allowed:
            raise InvalidArgumentError(
                f"Unsupported MCP tools root URI: {target_uri}",
                details={
                    "field": "target_uri",
                    "allowed": list(allowed),
                },
            )
        return normalized

    @classmethod
    def _registry_path_for_root(cls, ctx: RequestContext, tools_root: str) -> str:
        if tools_root == _AGENT_TOOLS_ROOT:
            return cls._registry_path(ctx.account_id)
        return cls._registry_path(ctx.account_id, ctx.user.user_id)

    @classmethod
    def _parse_tool_uri(
        cls,
        uri: str,
        ctx: RequestContext,
    ) -> tuple[str, str, str, str]:
        normalized = validate_request_viking_uri(
            resolve_path_variables(uri),
            ctx,
            field_name="tool URI",
        ).rstrip("/")
        match = _TOOL_URI_RE.fullmatch(normalized)
        if match is None:
            raise InvalidArgumentError(
                "Tool URI must match viking://agent/tools/<server>/<tool>.json "
                "or viking://~/tools/<server>/<tool>.json"
            )
        suffix = f"/{match.group('server')}/{match.group('tool')}.json"
        tools_root = normalized[: -len(suffix)]
        if tools_root not in cls._tools_roots(ctx):
            raise InvalidArgumentError(
                "Tool URI must belong to the current user's tools space or the shared agent space"
            )
        return normalized, tools_root, match.group("server"), match.group("tool")

    @staticmethod
    def _validate_server_name(name: str) -> str:
        if not _SERVER_NAME_RE.fullmatch(name):
            raise InvalidArgumentError(
                "MCP server name must contain only letters, numbers, '_' or '-' (max 64)"
            )
        return name

    @staticmethod
    def _validate_url(url: str) -> str:
        parsed = urlsplit(url)
        if parsed.username or parsed.password or parsed.fragment:
            raise InvalidArgumentError("MCP URL must not contain credentials or a fragment")
        if parsed.scheme in {"http", "https"} and parsed.hostname:
            return url
        raise InvalidArgumentError("MCP URL must use HTTP or HTTPS and include a host")

    @staticmethod
    def _validate_headers(headers: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for raw_name, raw_value in headers.items():
            name = raw_name.strip()
            value = raw_value.strip()
            if (
                not name
                or not value
                or any(char in name for char in "\r\n:")
                or any(char in value for char in "\r\n")
            ):
                raise InvalidArgumentError("Invalid MCP HTTP header")
            normalized[name] = value
        return normalized

    @staticmethod
    def _public_server(
        server: dict[str, Any],
        tool_count: int,
        tools_root: str,
    ) -> dict[str, Any]:
        return {
            key: value
            for key, value in server.items()
            if key not in {"header_names", "headers", "tools"}
        } | {
            "root_uri": tools_root,
            "header_names": sorted(server.get("headers", {})),
            "tool_count": tool_count,
        }

    @staticmethod
    def _input_revision(tool: dict[str, Any]) -> str:
        revision_input = {
            "name": tool.get("name"),
            "inputSchema": tool.get("inputSchema", {}),
        }
        payload = json.dumps(
            revision_input,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _tool_revision(tool: dict[str, Any]) -> str:
        payload = json.dumps(
            tool,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def _tool_document(cls, server: dict[str, Any], tool: Tool) -> dict[str, Any]:
        raw_tool = tool.model_dump(mode="json", by_alias=True, exclude_none=True)
        return {
            "kind": "mcp_tool",
            "server": server["name"],
            "address": server["url"],
            "revision": cls._tool_revision(raw_tool),
            "input_revision": cls._input_revision(raw_tool),
            "tool": raw_tool,
        }

    @staticmethod
    def _validate_tool_arguments(tool_document: dict[str, Any], arguments: dict[str, Any]) -> None:
        schema = tool_document["tool"].get("inputSchema", {"type": "object"})
        try:
            validate(instance=arguments, schema=schema)
        except SchemaError as exc:
            raise RuntimeError("Invalid inputSchema in MCP tool document") from exc
        except ValidationError as exc:
            location = ".".join(str(part) for part in exc.absolute_path)
            prefix = (
                f"Invalid MCP tool arguments at '{location}'"
                if location
                else ("Invalid MCP tool arguments")
            )
            raise InvalidArgumentError(f"{prefix}: {exc.message}") from exc

    @staticmethod
    def _tool_is_read_only(tool_document: dict[str, Any]) -> bool:
        annotations = tool_document["tool"].get("annotations")
        if annotations is None:
            return True
        return (
            isinstance(annotations, dict)
            and annotations.get("readOnlyHint") is not False
            and annotations.get("destructiveHint") is not True
        )

    @staticmethod
    def _valid_tool_name(name: str) -> bool:
        return name not in {".", ".."} and _TOOL_NAME_RE.fullmatch(name) is not None

    @staticmethod
    def _validate_node_uri(uri: str, ctx: RequestContext) -> str:
        normalized = validate_request_viking_uri(
            uri,
            ctx,
            field_name="live context node URI",
        )
        if not normalized.endswith(".md"):
            raise InvalidArgumentError("Live context node URI must end with .md")
        return normalized

    @staticmethod
    def _render_live_context_node(
        tool_uri: str,
        tool_document: dict[str, Any],
        title: str,
        description: str | None,
        timeout_seconds: int,
        arguments: dict[str, Any],
    ) -> str:
        metadata: dict[str, Any] = {
            "type": "OpenViking Live Context",
            "title": title,
        }
        if description is not None:
            metadata["description"] = description
        metadata.update(
            {
                "x-openviking": {
                    "schema_version": "v1",
                    "type": "mcp",
                    "definition": tool_uri,
                    "input_revision": tool_document["input_revision"],
                    "args": arguments,
                    "timeout_seconds": timeout_seconds,
                    "retry": {
                        "max_attempts": 3,
                        "backoff_seconds": 1,
                        "backoff_multiplier": 2,
                        "max_backoff_seconds": 5,
                    },
                },
            }
        )
        frontmatter = yaml.safe_dump(
            metadata,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        ).rstrip()
        return f"---\n{frontmatter}\n---\n"

    @staticmethod
    def _parse_live_context_node(content: str) -> tuple[str, dict[str, Any], int] | None:
        lines = content.splitlines()
        if not lines or lines[0] != "---":
            return None
        try:
            closing_index = lines[1:].index("---") + 1
            metadata = yaml.safe_load("\n".join(lines[1:closing_index]))
        except (ValueError, yaml.YAMLError):
            return None
        if not isinstance(metadata, dict) or metadata.get("type") != "OpenViking Live Context":
            return None
        extension = metadata.get("x-openviking")
        if not isinstance(extension, dict) or extension.get("type") != "mcp":
            return None
        tool_uri = extension.get("definition")
        arguments = extension.get("args", {})
        timeout_seconds = extension.get("timeout_seconds", 60)
        if (
            not isinstance(tool_uri, str)
            or not isinstance(arguments, dict)
            or not isinstance(timeout_seconds, int)
            or isinstance(timeout_seconds, bool)
            or timeout_seconds <= 0
        ):
            raise InvalidArgumentError(
                "Live context node requires string x-openviking.definition "
                "object x-openviking.args, and positive integer "
                "x-openviking.timeout_seconds"
            )
        return tool_uri, arguments, timeout_seconds

    @staticmethod
    def _live_context_read_value(
        result: dict[str, Any],
        tool_uri: str,
    ) -> str:
        content = result.get("content")
        text_blocks = (
            [
                block["text"]
                for block in content
                if isinstance(block, dict)
                and block.get("type") == "text"
                and isinstance(block.get("text"), str)
            ]
            if isinstance(content, list)
            else []
        )

        if result.get("isError") is True:
            detail = "\n".join(text_blocks).strip() or "upstream MCP tool returned an error"
            raise ProcessingError(
                f"Live context read failed: {detail}",
                source=tool_uri,
            )

        if isinstance(content, list):
            if text_blocks:
                return "\n".join(text_blocks)

        structured = result.get("structuredContent")
        if structured is not None:
            return json.dumps(structured, ensure_ascii=False, indent=2)

        if isinstance(content, list) and not content:
            return ""

        raise ProcessingError(
            "Live context read only supports text or structured MCP results",
            source=tool_uri,
        )
