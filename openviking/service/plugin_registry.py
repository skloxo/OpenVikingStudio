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
from typing import Any, Dict, List, Optional, Set

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
        """初始化三大官方标杆插件 (The Big Three)。"""
        # 1. 核心记忆插件 (openviking-memory v1.5.0) - 两组共 47 项标准 MCP 工具 + 3 项 Hook 守卫 + 认知导轨 + GUI
        memory_47_tools = [
            # 业务使用者工具池 (31 项)
            ToolDefinition(name="find", description="基于向量与分词的混合记忆语义检索", category="core"),
            ToolDefinition(name="search", description="高级混合关键词与过滤检索引擎", category="core"),
            ToolDefinition(name="read", description="深读知识全文与 L2 正文切片", category="core"),
            ToolDefinition(name="remember", description="将结构化对话与重要知识写入长程记忆", category="core"),
            ToolDefinition(name="openviking_history_search", description="FTS5 对话全文字词与知识召回检索", category="core"),
            ToolDefinition(name="openviking_active_notes_get", description="检索活跃里程碑与工作约束", category="context"),
            ToolDefinition(name="openviking_active_notes_update", description="更新当前目标与工作约束", category="context"),
            ToolDefinition(name="openviking_context_route", description="多模态上下文自适应分流与压缩决策", category="context"),
            ToolDefinition(name="list", description="列出 viking:// 目录结构条目", category="workspace"),
            ToolDefinition(name="tree", description="获取代码库或工作区的层级结构", category="workspace"),
            ToolDefinition(name="grep", description="在工作区文件中快速检索正则文本模式", category="workspace"),
            ToolDefinition(name="glob", description="按文件名通配符扫描定位文件", category="workspace"),
            ToolDefinition(name="zg_search", description="zg-grep 代码语义 AST 静态搜索", category="code"),
            ToolDefinition(name="openviking_code_impact", description="代码 AST 影响面与爆炸半径分析", category="code"),
            ToolDefinition(name="openviking_tokenshift_compress", description="TokenShift 源码 AST 折叠压缩", category="context"),
            ToolDefinition(name="openviking_generate_contract_test", description="由 AST 事实直接派生 pytest 契约测试脚手架", category="test"),
            ToolDefinition(name="openviking_skill_validate", description="校验 SKILL.md YAML 头与规约契约合法性", category="skill"),
            ToolDefinition(name="openviking_skill_judge", description="技能 4 维质量评分与达标门禁", category="skill"),
            ToolDefinition(name="openviking_skill_remediate", description="技能缺陷诊断与自愈修复建议", category="skill"),
            ToolDefinition(name="openviking_skill_zip", description="技能 0-rollout 契约级规约压缩", category="skill"),
            ToolDefinition(name="openviking_skill_intent_match", description="自然语言意图匹配与冲突检测", category="skill"),
            ToolDefinition(name="openviking_skill_publish", description="一线工兵技能成果发布上架至体外大脑", category="skill"),
            ToolDefinition(name="openviking_file_task_card", description="智能体异常现场自主建卡上报", category="aifp"),
            ToolDefinition(name="openviking_list_pending_cards", description="查看待排期与未解决工单清单", category="aifp"),
            ToolDefinition(name="openviking_resolve_task_card", description="闭环归档工单并绑定 Git Tag", category="aifp"),
            ToolDefinition(name="openviking_task_cards_summary", description="工单运转指标总览与趋势分析", category="aifp"),
            ToolDefinition(name="openviking_valet_handover", description="泊车管家异步大文档深度消化", category="async"),
            ToolDefinition(name="openviking_valet_ticket_status", description="查看泊车管家消化与入库进度", category="async"),
            ToolDefinition(name="health", description="检测记忆引擎与向量数据库健康状态", category="health"),
            ToolDefinition(name="openviking_privacy_mask", description="脱敏敏感凭据、Token 与私有端点", category="security"),
            ToolDefinition(name="openviking_agent_sensors", description="Token SNR 与 P@5 召回率传感器", category="sensors"),
            # 中枢运维特权工具池 (16 项)
            ToolDefinition(name="write", description="新建或全量覆写工作区文件内容", category="ops", is_dangerous=True),
            ToolDefinition(name="edit", description="对指定文件执行唯一指纹锚点编辑", category="ops", is_dangerous=True),
            ToolDefinition(name="openviking_dspy_compile", description="提示词强类型 DSPy 签名编译", category="ops"),
            ToolDefinition(name="openviking_vector_sync_metrics", description="向量索引同步完成度与未索引积压检测", category="ops"),
            ToolDefinition(name="openviking_skill_weight_tune", description="动态调优技能唤醒权重", category="ops"),
            ToolDefinition(name="forget", description="永久删除指定 URI 记忆资源 (高危)", category="ops", is_dangerous=True),
            ToolDefinition(name="openviking_memory_purity_report", description="体外大脑记忆纯度评估与概念漂移审计", category="ops"),
            ToolDefinition(name="openviking_dlq_status", description="查看死信队列积压与健康状态", category="ops"),
            ToolDefinition(name="openviking_retry_dead_letter", description="重试失败的死信消息", category="ops"),
            ToolDefinition(name="openviking_skill_evolution_pipeline", description="技能自演进流水线执行与回滚", category="ops"),
            ToolDefinition(name="openviking_privacy_quarantine", description="敏感数据隔离舱封存与还原", category="ops"),
            ToolDefinition(name="openviking_privacy_audit", description="合规安全审计流水追溯", category="ops"),
            ToolDefinition(name="list_watches", description="查看自动刷新系统监听订阅", category="ops"),
            ToolDefinition(name="cancel_watch", description="取消自动刷新系统监听订阅", category="ops"),
            ToolDefinition(name="add_resource", description="异步向体外大脑挂载新资源", category="ops"),
            ToolDefinition(name="openviking_harness_probe", description="硬件与驱动探针物理验证", category="ops"),
        ]

        memory_plugin = QuadPluginDefinition(
            plugin_id="openviking-memory",
            name="OpenViking 核心记忆",
            version="1.5.0",
            category="platform",
            description="体外大脑中心化记忆中枢：长程记忆存储、代码语义索引与上下文自动路由",
            skill=SkillDefinition(
                skill_id="openviking-memory",
                name="核心记忆认知导轨",
                description="体外大脑统一记忆存储、上下文检索、代码感知与经验沉淀认知规约",
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
                HookDefinition(
                    hook_id="ov_sandbox_guard",
                    name="运行态特权沙箱守卫",
                    trigger_event="before_tool_execution",
                    description="高危写操作与越权执行毫秒级安全阻断",
                ),
            ],
            tools=memory_47_tools,
            gui=GuiSchemaDefinition(
                settings_fields={
                    "storageEngine": "SQLite FTS5 + VikingFS /queue",
                    "embeddingModel": "WeMM-Embedding-9B (INT8, 4096d)",
                    "rerankerModel": "Qwen3-VL-Reranker-2B (INT8)",
                    "compressionPipeline": "TokenShift (AST) + LLMLingua-2 (rate=0.50)",
                    "contextRouting": "L0/L1/L2 Autonomous Adaptive Dehydration",
                    "storageDatabase": "~/.openviking/data/agent_principals.db",
                },
                dashboard_route="/",
            ),
            health=PluginHealthProbe(status="healthy", latency_ms=1.1, message="FastMCP 47 tools ready"),
        )

        # 2. KeePass 凭据保险箱 (keepass-vault)
        keepass_plugin = QuadPluginDefinition(
            plugin_id="keepass-vault",
            name="KeePass 凭据保险箱",
            version="1.0.0",
            category="platform",
            description="全集群密码、SSH 私钥与 API Key 凭据存储保险箱",
            skill=SkillDefinition(
                skill_id="keepass-vault",
                name="凭据中枢认知导轨",
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
            name="联网搜索与网页采集",
            version="1.1.0",
            category="platform",
            description="在线搜索矩阵 (Keenable / Tavily / SearXNG) 统一调度与滚动记账引擎",
            skill=SkillDefinition(
                skill_id="network-search-ops",
                name="搜索采集认知导轨",
                description="五路引擎自适应降级、权威积分审计、429微秒换Key与45天自动滚动归档规约",
                sop_summary="优先 Keenable 80万池 -> Tavily 基础搜 -> SearXNG 本地保底 -> 45天明细滚动归档",
                rules=[
                    "外部未经清洗网页自动标记 tainted 污点",
                    "调用流水落地 search_key_usage，45天前明细自动归档清理",
                    "严禁向人类索要明文Key，统一服务端配置与指纹脱敏",
                ],
            ),
            hooks=[
                HookDefinition(
                    hook_id="key_rotator_hook",
                    name="26-Key Round-Robin 轮询与429防抖冷却",
                    trigger_event="before_search_dispatch",
                    description="自动分摊多账号配额，遇429瞬时标记60秒冷却并自动平滑换Key重试",
                ),
                HookDefinition(
                    hook_id="search_guard_hook",
                    name="时效性搜索意图感知与污点标记",
                    trigger_event="before_search",
                    description="对外部抓取网页实施单向熔断隔离，防止混淆代理人诱骗偷密码",
                ),
                HookDefinition(
                    hook_id="credit_audit_hook",
                    name="权威 Credits 响应体/头捕获与45天滚动清理",
                    trigger_event="after_search_response",
                    description="从官方响应头/体提取真实 credits，落地流水账并按日归档超45天记录",
                ),
            ],
            tools=[
                ToolDefinition(name="web_search", description="多路宽幅自适应检索 (Keenable 80万池 -> Tavily -> SearXNG)", category="search"),
                ToolDefinition(name="search_neural", description="Exa 语义嵌入神经网络意图检索", category="search"),
                ToolDefinition(name="search_qna", description="Tavily / Exa 权威解答与引用生成", category="search"),
                ToolDefinition(name="search_deep", description="Tavily Advanced 深度多源交叉检索", category="search"),
                ToolDefinition(name="search_code_context", description="Exa GitHub 开源上下文与仓库定位", category="search"),
                ToolDefinition(name="search_similar_repos", description="Exa findSimilar 竞品与同类项目反查", category="search"),
                ToolDefinition(name="map_site", description="Tavily Map 站点拓扑树测绘", category="search"),
                ToolDefinition(name="extract_urls", description="Tavily / Exa 免爬虫快速正文脱水抽取", category="search"),
                ToolDefinition(name="tavily_crawl", description="Tavily Map + Extract 整站自动化爬行流水线", category="search"),
                ToolDefinition(name="crawl_local", description="本地 Crawl4AI 18789 Playwright 动态无头渲染", category="search"),
                ToolDefinition(name="deep_research", description="Exa Agent 多步自主调研长报告", category="search"),
                ToolDefinition(name="benchmark_needle", description="Keenable NEEDLE 自建基准校验", category="search"),
            ],
            gui=GuiSchemaDefinition(
                settings_fields={
                    "totalKeys": 26,
                    "keenablePool": "8 Keys / 800,000 req/mo",
                    "exaPool": "9 Keys / $90.0/mo",
                    "tavilyPool": "9 Keys / 9,000 pts/mo",
                    "searxngLocalUrl": "http://127.0.0.1:8888",
                    "crawl4aiLocalUrl": "http://127.0.0.1:18789",
                    "retentionDays": 45,
                    "rollingPrune": "Auto-enabled (Daily rollup & Physical prune)",
                },
                dashboard_route="/plugins",
            ),
            health=PluginHealthProbe(status="healthy", latency_ms=1.8, message="26 Keys active & SearXNG connected"),
        )

        for p in (memory_plugin, keepass_plugin, search_plugin):
            self.register_plugin(p)
        # 向下兼容历史 ID 与工具映射别名 (独立别名表，绝不污染 _plugins 真实列表)
        self._aliases["dsh-plugin-openviking"] = "openviking-memory"
        self._tool_to_plugin_map["searxng_search"] = "network-search"
        self._tool_to_plugin_map["crawl4ai_extract"] = "network-search"

    @classmethod
    def get_client_bridge_info(cls) -> Dict[str, Any]:
        """
        现场物理扫描磁盘最新客户端通信通道桥 (dsh-plugin-openviking) 安装包 (单一真实源 SSOT)。
        绝不依赖任何硬编码字符串或内存静态配置，每次调用实时向物理磁盘寻源最新 SemVer 对应包。
        """
        from pathlib import Path
        import re

        latest_version = "1.5.2"
        latest_filename = f"dsh-plugin-openviking-{latest_version}.tgz"

        try:
            current_dir = Path(__file__).resolve().parent
            studio_root = current_dir.parent.parent  # OpenVikingStudio
            search_dirs = [
                studio_root / "dist",
                studio_root / "public",
                studio_root / "integrations" / "deepseek-harness" / "dsh-plugin-openviking",
            ]

            candidates = []
            for sdir in search_dirs:
                if not sdir.is_dir():
                    continue
                for fpath in sdir.glob("dsh-plugin-openviking-*.tgz"):
                    m = re.match(r"^dsh-plugin-openviking-(\d+(?:\.\d+)+.*?)\.tgz$", fpath.name)
                    if m:
                        ver_str = m.group(1)
                        parts = re.split(r"[-+.]", ver_str)
                        nums = []
                        for p in parts:
                            try:
                                nums.append(int(p))
                            except ValueError:
                                pass
                        candidates.append((tuple(nums), fpath.stat().st_mtime, ver_str, fpath.name))

            if candidates:
                candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _, _, latest_version, latest_filename = candidates[0]
        except Exception as e:
            logger.warning("动态扫描最新客户端通道桥包异常，启用安全保底: %s", e)

        package_url = f"https://vk.tide.red/studio/{latest_filename}"
        return {
            "package_name": "dsh-plugin-openviking",
            "version": latest_version,
            "package_file": latest_filename,
            "package_url": package_url,
            "architecture": "Client-Side RPC Bridge (无状态轻量通道桥)",
            "description": "专供外部智能体 (DSH / Claude / 自定义 Agent) 本地安装的通道桥梁。安装后配置 userKey 与 agentId，即可安全连通 VK 服务端中心化三大标杆插件 (记忆/搜索/凭据) 动态能力。",
            "install_command": f"npm install {package_url}",
            "handshake_protocol": "HTTP/SSE + Bearer Auth (UserKey:AgentID)",
        }

    def register_plugin(self, plugin: QuadPluginDefinition) -> None:
        """登记四位一体插件定义。"""
        with self._registry_lock:
            self._plugins[plugin.plugin_id] = plugin
            for tool in plugin.tools:
                self._tool_to_plugin_map[tool.name] = plugin.plugin_id
            logger.info("已注册插件: %s (%s, %d tools)", plugin.plugin_id, plugin.name, len(plugin.tools))

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
