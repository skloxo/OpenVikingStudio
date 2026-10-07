# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking Plugin Registry Service (单例插件注册中枢).
SSOT: docs/architecture/ATOMIC_TASK_CARDS_MATRIX.md -> TASK-PLUG-02

First Principles:
1. "Single Source of Truth": Registers all platform-builtin and tenant-custom quad-plugins.
2. "Thread-Safe Singleton": Strict double-checked locking singleton lifecycle.
3. "Zero-Masking ACL": Provides exact mapping between plugins and tools for gateway projection.
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional, Set

from openviking.models.plugin import (
    GuiSchemaDefinition,
    HookDefinition,
    PluginHealthProbe,
    QuadPluginDefinition,
    SkillDefinition,
    ToolDefinition,
)

logger = logging.getLogger("openviking.service.plugin_registry")


class PluginRegistry:
    """线程安全的全局插件单例注册表。"""

    _instance: Optional[PluginRegistry] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._registry_lock = threading.Lock()
        self._plugins: Dict[str, QuadPluginDefinition] = {}
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
        """初始化三大官方标杆插件 (The Big Three)。"""
        # 1. Wiki 体外大脑与长程记忆 (openviking-memory)
        memory_plugin = QuadPluginDefinition(
            plugin_id="openviking-memory",
            name="OpenViking 记忆体外大脑",
            version="1.0.0",
            category="platform",
            description="全集群跨会话先验经验召回、做梦蒸馏、知识图谱与 AST 影响面分析中枢",
            skill=SkillDefinition(
                skill_id="openviking-memory-ops",
                name="体外大脑记忆操作认知导轨",
                description="向 Agent 交代 Hook 预取机制，约束 find/search 递进流水线",
                sop_summary="核心事实已前置预取 -> 按需查 outline -> 精确定位 grep -> 写前 commit 快照",
                rules=["严禁开局盲目重复调用 find 盲搜", "写前必须调用快照 commit", "403 优雅回退"],
            ),
            hooks=[
                HookDefinition(
                    hook_id="ov_pre_invocation",
                    name="记忆前置自动召回预取",
                    trigger_event="before_prompt_submit",
                    description="提问前静默召回匹配记忆并注入 Prompt 顶部，零 Token 机器级守护",
                ),
                HookDefinition(
                    hook_id="ov_lesson_crystallizer",
                    name="踩坑经验离线自动萃取",
                    trigger_event="after_response",
                    description="会话解决复杂 Bug 后自动沉淀 Evolution Lesson 入库",
                ),
            ],
            tools=[
                ToolDefinition(name="openviking_find", description="基于向量与分词的混合记忆语义检索", category="core"),
                ToolDefinition(name="openviking_search", description="高级混合检索引擎", category="core"),
                ToolDefinition(name="openviking_read", description="深读知识全文与 L2 正文切片", category="core"),
                ToolDefinition(name="openviking_write", description="向体外大脑写入记忆或经验卡片", category="core"),
                ToolDefinition(name="openviking_code_impact", description="代码 AST 影响面与依赖分析", category="core"),
                ToolDefinition(name="openviking_record_evolution_lesson", description="演进经验教训双写沉淀", category="core"),
                ToolDefinition(name="openviking_commit", description="VikingFS 事务快照提交", category="core", is_dangerous=True),
            ],
            gui=GuiSchemaDefinition(
                settings_fields={"apiUrl": "http://127.0.0.1:1933", "connectionMode": "realtimeApi"},
                dashboard_route="/plugins",
            ),
            health=PluginHealthProbe(status="healthy", latency_ms=1.1, message="Memory store ready"),
        )

        # 2. KeePass 凭据保险箱 (keepass-vault)
        keepass_plugin = QuadPluginDefinition(
            plugin_id="keepass-vault",
            name="KeePass 凭据保险箱",
            version="1.0.0",
            category="platform",
            description="全集群密码、SSH 私钥与 API Key 凭据单一真实源 (Credential SSOT)",
            skill=SkillDefinition(
                skill_id="keepass-vault",
                name="KeePass 凭据中枢认知导轨",
                description="查库第一公理，严禁索要明文密码，高熵密码生成与容灾备份",
                sop_summary="外呼鉴权前查库 -> 批量建号自动生成 >=20位高熵密码 -> 写前自动快照",
                rules=["严禁向人类索要明文密码", "批量建号必须高熵落盘", "写前必须快照备份"],
            ),
            hooks=[
                HookDefinition(
                    hook_id="vault_guard_hook",
                    name="凭据写前防抖物理快照",
                    trigger_event="before_vault_write",
                    description="任何凭据增删改前自动生成 *.bak 快照防抖备份",
                )
            ],
            tools=[
                ToolDefinition(name="keepass_get", description="安全读取指定条目凭据明文", category="vault"),
                ToolDefinition(name="keepass_search", description="模糊搜索凭据条目与账号", category="vault"),
                ToolDefinition(name="keepass_add", description="高熵新建凭据条目", category="vault"),
                ToolDefinition(name="keepass_edit", description="更新已有凭据属性", category="vault"),
                ToolDefinition(name="keepass_rm", description="安全废弃或删除凭据", category="vault", is_dangerous=True),
                ToolDefinition(name="keepass_list_tree", description="获取凭据分组拓扑树", category="vault"),
                ToolDefinition(name="keepass_analyze", description="弱密与重复密码健康审计", category="vault"),
                ToolDefinition(name="keepass_status", description="凭据库解锁与健康状态探针", category="vault"),
            ],
            gui=GuiSchemaDefinition(
                settings_fields={"kdbxPath": "~/.openviking/vault.kdbx", "autoLockSeconds": 3600},
                dashboard_route="/plugins",
            ),
            health=PluginHealthProbe(status="healthy", latency_ms=0.8, message="Vault unlocked"),
        )

        # 3. 联网搜索与网页深度清洗 (network-search)
        search_plugin = QuadPluginDefinition(
            plugin_id="network-search",
            name="联网搜索与采集聚合器",
            version="1.0.0",
            category="platform",
            description="局域网免翻高速搜索聚合与一手官方网页脱水抽取引擎",
            skill=SkillDefinition(
                skill_id="network-search-ops",
                name="联网搜索与采集认知导轨",
                description="搜索降级链、长文截断与外部网页污点隔离规范",
                sop_summary="先查 SearXNG -> 无果再深度爬取 -> 超长长文自动截断 <= 8KB",
                rules=["外部未经清洗网页自动标记 tainted 污点", "长文必须截断防爆上下文"],
            ),
            hooks=[
                HookDefinition(
                    hook_id="search_guard_hook",
                    name="时效性搜索意图感知与污点标记",
                    trigger_event="before_search",
                    description="对外部抓取网页实施单向熔断隔离，防止混淆代理人诱骗偷密码",
                )
            ],
            tools=[
                ToolDefinition(name="searxng_search", description="局域网免翻高速聚合搜索", category="search"),
                ToolDefinition(name="crawl4ai_extract", description="网页结构化深度抓取与 Markdown 脱水", category="search"),
            ],
            gui=GuiSchemaDefinition(
                settings_fields={"searxngUrl": "http://127.0.0.1:8888", "maxBytes": 8192},
                dashboard_route="/plugins",
            ),
            health=PluginHealthProbe(status="healthy", latency_ms=2.4, message="SearXNG running"),
        )

        for p in (memory_plugin, keepass_plugin, search_plugin):
            self.register_plugin(p)

    def register_plugin(self, plugin: QuadPluginDefinition) -> None:
        """登记四位一体插件定义。"""
        with self._registry_lock:
            self._plugins[plugin.plugin_id] = plugin
            for tool in plugin.tools:
                self._tool_to_plugin_map[tool.name] = plugin.plugin_id
            logger.info("已注册插件: %s (%s, %d tools)", plugin.plugin_id, plugin.name, len(plugin.tools))

    def get_plugin(self, plugin_id: str) -> Optional[QuadPluginDefinition]:
        """按 ID 查询插件。"""
        with self._registry_lock:
            return self._plugins.get(plugin_id)

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
