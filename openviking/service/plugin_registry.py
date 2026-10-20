# -*- coding: utf-8 -*-
"""
OpenViking 四位一体插件中心中枢注册表 (PluginRegistry SSOT)
基于第一性原理，统一管理服务端四大核心标杆资产：
Tools (MCP 原子工具) + Hooks (生命周期钩子) + Skill (专家操作认知导轨) + GUI (微观配置与可视化)
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional, Any

from openviking.models.plugin import (
    QuadPluginDefinition,
    ToolDefinition,
)
from openviking.service.builtin_plugins import (
    BATTLEFIELD_34_TOOL_NAMES,
    OPS_17_TOOL_NAMES,
    create_builtin_plugins,
)

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    单例模式插件中枢注册表。
    维护系统中已就绪的所有四位一体插件、工具反查映射与动态权限鉴权契约。
    """

    _instance: Optional[PluginRegistry] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._registry_lock = threading.RLock()
        self._plugins: Dict[str, QuadPluginDefinition] = {}
        self._aliases: Dict[str, str] = {}
        self._tool_to_plugin_map: Dict[str, str] = {}
        self._init_builtin_plugins()

    @classmethod
    def get_instance(cls) -> PluginRegistry:
        """获取单例实例 (双检锁安全守卫)。"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例 (用于单元测试隔离)。"""
        with cls._lock:
            cls._instance = None

    def _init_builtin_plugins(self) -> None:
        """从单一真相源初始化官方内置 Quad 插件列表。"""
        plugins, aliases, tool_map = create_builtin_plugins()
        for p in plugins:
            self.register_plugin(p)
        self._aliases.update(aliases)
        self._tool_to_plugin_map.update(tool_map)

    @classmethod
    def get_client_bridge_info(cls, plugin_id: str = "openviking-memory") -> Dict[str, Any]:
        """
        现场物理扫描磁盘最新客户端通信通道桥安装包 (单一真实源 SSOT)。
        支持原生三大插件 (openviking-memory, openviking-ops, fleet-mesh) 的独立桥接器。
        """
        from pathlib import Path
        import re

        pid = (plugin_id or "openviking-memory").strip().lower()
        if pid in ("openviking-ops", "ops"):
            target_pkg = "dsh-plugin-openviking-ops"
            def_ver = "1.0.3"
        elif pid in ("fleet-mesh", "fleet", "openviking-fleet"):
            target_pkg = "dsh-plugin-openviking-fleet"
            def_ver = "1.0.3"
        elif pid in ("keepass-vault", "keepass", "vault"):
            target_pkg = "dsh-plugin-keepass-vault"
            def_ver = "1.0.2"
        elif pid in ("dify", "dify-workflow"):
            target_pkg = "dsh-plugin-dify"
            def_ver = "1.0.1"
        elif pid in ("cpa-squad", "cpa"):
            target_pkg = "dsh-plugin-cpa"
            def_ver = "1.0.1"
        else:
            target_pkg = "dsh-plugin-openviking-memory"
            def_ver = "2.0.16"

        latest_version = def_ver
        latest_filename = f"{target_pkg}-{latest_version}.tgz"

        try:
            current_dir = Path(__file__).resolve().parent
            studio_root = current_dir.parent.parent  # OpenVikingStudio
            search_dirs = [
                studio_root / "dist",
                studio_root / "public",
                studio_root / "integrations" / "deepseek-harness" / target_pkg,
                studio_root / "integrations" / "deepseek-harness" / "dsh-plugin-openviking",
            ]

            target_candidates = []
            fallback_candidates = []
            for sdir in search_dirs:
                if not sdir.is_dir():
                    continue
                # 1. 严格精准匹配当前插件专属包
                for fpath in sdir.glob(f"{target_pkg}-*.tgz"):
                    m = re.match(r"^" + re.escape(target_pkg) + r"-(\d+(?:\.\d+)+.*?)\.tgz$", fpath.name)
                    if m:
                        ver_str = m.group(1)
                        parts = re.split(r"[-+.]", ver_str)
                        nums = [int(p) for p in parts if p.isdigit()]
                        target_candidates.append((tuple(nums), fpath.stat().st_mtime, ver_str, fpath.name))
                # 2. 仅当专属包不存在时，兼容历史别名包
                if target_pkg == "dsh-plugin-openviking-memory":
                    for fpath in sdir.glob("dsh-plugin-openviking-*.tgz"):
                        m = re.match(r"^dsh-plugin-openviking-(\d+(?:\.\d+)+.*?)\.tgz$", fpath.name)
                        if m:
                            ver_str = m.group(1)
                            parts = re.split(r"[-+.]", ver_str)
                            nums = [int(p) for p in parts if p.isdigit()]
                            fallback_candidates.append((tuple(nums), fpath.stat().st_mtime, ver_str, fpath.name))

            candidates = target_candidates if target_candidates else fallback_candidates
            if candidates:
                candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _, _, latest_version, latest_filename = candidates[0]
        except Exception as e:
            logger.warning("动态扫描最新客户端通道桥包异常，启用安全保底: %s", e)

        package_url = f"https://vk.tide.red/studio/{latest_filename}"
        return {
            "package_name": target_pkg,
            "version": latest_version,
            "package_file": latest_filename,
            "package_url": package_url,
            "architecture": f"Independent Quad Bridge ({target_pkg})",
            "description": f"专供智能体生态接入 {plugin_id} 的独立轻量级通信桥梁，开箱即用。",
            "install_command": f"npm install {package_url}",
            "handshake_protocol": "HTTP/SSE + Bearer Auth (UserKey)",
            "channels": {
                "antigravity": {
                    "name": "Google 反重力",
                    "standard": "Google Gemini Agent Framework Plugin Specification",
                    "version": latest_version,
                    "plugin_dir": "integrations/antigravity/openviking-memory",
                    "setup_script": "setup.py",
                },
                "dsh": {
                    "name": "DeepSeek Harness",
                    "standard": "Cordis Plugin Ecosystem",
                    "version": latest_version,
                    "package_url": package_url,
                    "install_command": f"npm install {package_url}",
                },
                "universal_mcp": {
                    "name": "标准通用智能体",
                    "standard": "Universal Model Context Protocol (Streamable-HTTP / Stdio)",
                    "endpoint_url": "https://vk.tide.red/mcp",
                },
            },
        }

    def register_plugin(self, plugin: QuadPluginDefinition) -> None:
        """登记四位一体插件定义。"""
        with self._registry_lock:
            self._plugins[plugin.plugin_id] = plugin
            for tool in plugin.tools:
                self._tool_to_plugin_map[tool.name] = plugin.plugin_id
            logger.info("已注册插件: %s (%s, %d tools)", plugin.plugin_id, plugin.name, len(plugin.tools))

    def resolve_alias(self, alias: str) -> str:
        """解析别名至标准 Canonical Plugin ID 或 Tool Name。"""
        with self._registry_lock:
            return self._aliases.get(alias, alias)

    def get_plugin(self, plugin_id: str) -> Optional[QuadPluginDefinition]:
        """按 ID 查询插件，支持别名自动映射。"""
        with self._registry_lock:
            canonical_id = self._aliases.get(plugin_id, plugin_id)
            return self._plugins.get(canonical_id)

    def list_plugins(self, category: Optional[str] = None) -> List[QuadPluginDefinition]:
        """列出所有插件，支持分类过滤。"""
        with self._registry_lock:
            plugins = list(self._plugins.values())
            if category:
                plugins = [p for p in plugins if p.category == category]
            return plugins

    def get_plugin_tools(self, plugin_id: str) -> List[ToolDefinition]:
        """获取指定插件的工具列表。"""
        plugin = self.get_plugin(plugin_id)
        return plugin.tools if plugin else []

    def get_plugin_id_by_tool(self, tool_name: str) -> Optional[str]:
        """根据工具名称反查所属插件 ID。"""
        with self._registry_lock:
            return self._tool_to_plugin_map.get(tool_name)

    def is_tool_authorized(self, plugin_grants: Dict[str, List[str]], tool_name: str) -> bool:
        """
        判断某工具是否在 Agent 的 plugin_grants 授权白名单中。
        grants 结构例如: {"openviking-memory": ["openviking_find"], "network-search": ["*"]}
        """
        plugin_id = self.get_plugin_id_by_tool(tool_name)
        if not plugin_id:
            # 兼容未归属插件的历史工具：若未归属，允许放行或交由底层 ACL 兜底
            return True

        if plugin_id not in plugin_grants:
            return False

        allowed = plugin_grants[plugin_id]
        if "*" in allowed:
            return True
        return tool_name in allowed
