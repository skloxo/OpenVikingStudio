# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
_core: OpenViking MCP 基础架构与基础设施包
包含跨平台配置解析、HTTP 客户端、CLI 封装与双模态装饰器
"""

from .config import (
    DEFAULT_API,
    DEFAULT_CLI,
    DEFAULT_ROOT_API_KEY,
    CLI_ONLY_MODE,
    SATELLITE_ALLOWED_TOOLS,
    resolve_mcp_mode,
    _get_config,
    _run_cli,
    OpenVikingHTTPClient,
    http_client,
    _format_result,
    _api_then_cli,
    _has_error,
    _make_error,
    _handle_http_error,
    _handle_cli_error,
    _handle_timeout,
    _validate_uri,
    _normalize_level,
    _validate_level,
    _validate_limit,
    _validate_score_threshold,
    _get_skill_base_sources,
    _infer_skill_source,
    _parse_skill_description,
)
from .decorators import create_mcp_tool_decorator

__all__ = [
    "DEFAULT_API",
    "DEFAULT_CLI",
    "DEFAULT_ROOT_API_KEY",
    "CLI_ONLY_MODE",
    "SATELLITE_ALLOWED_TOOLS",
    "resolve_mcp_mode",
    "_get_config",
    "_run_cli",
    "OpenVikingHTTPClient",
    "http_client",
    "_format_result",
    "_api_then_cli",
    "_has_error",
    "_make_error",
    "_handle_http_error",
    "_handle_cli_error",
    "_handle_timeout",
    "_validate_uri",
    "_normalize_level",
    "_validate_level",
    "_validate_limit",
    "_validate_score_threshold",
    "_get_skill_base_sources",
    "_infer_skill_source",
    "_parse_skill_description",
    "create_mcp_tool_decorator",
]
