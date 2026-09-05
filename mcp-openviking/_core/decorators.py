# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: _core.decorators ──────────────────────────────────────────────
"""
用途: 双模态 MCP 工具注册装饰器工程
依赖: FastMCP, pydantic, _core.config
被调用: mcp_openviking_server.py
"""

# SECTION: Imports
import inspect
import logging
from functools import wraps
from typing import Any, Callable
from mcp.server.fastmcp import FastMCP
from .config import SATELLITE_ALLOWED_TOOLS

logger = logging.getLogger("openviking-mcp")

# SECTION: Decorator Factory
def create_mcp_tool_decorator(mcp: FastMCP, mcp_mode: str) -> Callable:
    """创建双模态感知的 MCP 工具注册装饰器。
    在 Satellite 模式下只注册 16 个安全实用数据工具，物理阻断 40+ 运维特权；
    自动解包 FastMCP/Pydantic FieldInfo 默认对象，防止序列化崩塌；
    针对 openviking_find 自动注入【Mandatory First Step】强注意力触发头。
    """
    def mcp_tool(*args, **kwargs):
        def decorator(fn):
            tool_name = kwargs.get("name") or fn.__name__
            if mcp_mode == "satellite" and tool_name not in SATELLITE_ALLOWED_TOOLS:
                logger.debug(f"[Dual-Mode MCP] Satellite mode: skipping registration of sensitive tool '{tool_name}'")
                return fn

            tool_kwargs = dict(kwargs)
            if tool_name == "openviking_find":
                orig_desc = tool_kwargs.get("description") or fn.__doc__ or ""
                prefix = "【Mandatory First Step / 开局必调】在开始回答任何工程、架构或排障问题前，必须首先调用此工具查询体外大脑（VK）中的历史经验与避坑规则。\n"
                if prefix not in orig_desc:
                    tool_kwargs["description"] = prefix + orig_desc

            sig = inspect.signature(fn)

            @wraps(fn)
            def cleaned_fn(*f_args, **f_kwargs):
                try:
                    bound = sig.bind_partial(*f_args, **f_kwargs)
                    for name, param in sig.parameters.items():
                        if name not in bound.arguments:
                            val = param.default
                            if hasattr(val, "default"):
                                d = getattr(val, "default")
                                bound.arguments[name] = "" if d is None or "PydanticUndefined" in str(type(d)) else d
                        else:
                            val = bound.arguments[name]
                            if hasattr(val, "default"):
                                d = getattr(val, "default")
                                bound.arguments[name] = "" if d is None or "PydanticUndefined" in str(type(d)) else d
                    return fn(*bound.args, **bound.kwargs)
                except Exception:
                    return fn(*f_args, **f_kwargs)

            return mcp.tool(*args, **tool_kwargs)(cleaned_fn)
        return decorator
    return mcp_tool
