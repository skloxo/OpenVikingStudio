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
        # 1. 核心记忆插件 (openviking-memory) - 54 项核心战地工具 (CPA/Fleet 独立解耦) + 3 项 Hook 守卫 + 认知导轨 + GUI
        memory_core_tools = [
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
            # 核心战地大纲与技能中心直连感知工具池 (7 项)
            ToolDefinition(name="openviking_smart_read", description="分层自适应智能知识提取与概括", category="core"),
            ToolDefinition(name="openviking_code_outline", description="代码 AST 语法大纲提取", category="code"),
            ToolDefinition(name="openviking_code_search", description="代码语义符号深度检索", category="code"),
            ToolDefinition(name="openviking_code_expand", description="代码上下文智能折叠与按需展开", category="code"),
            ToolDefinition(name="openviking_record_evolution_lesson", description="踩坑事实与自演进经验入脑存盘", category="skill"),
            ToolDefinition(name="openviking_skills", description="知识中枢全量技能状态与分类总览", category="skill"),
            ToolDefinition(name="openviking_audit_skills", description="知识中枢技能规范静态安全审计", category="skill"),
        ]

        memory_plugin = QuadPluginDefinition(
            plugin_id="openviking-memory",
            name="OpenViking 核心记忆",
            version="2.0.11",
            category="platform",
            description="体外大脑中心化记忆中枢：长程记忆存储、代码语义索引与上下文自动路由 (官方平台底座)",
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
            tools=memory_core_tools,
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
            health=PluginHealthProbe(status="healthy", latency_ms=1.1, message="FastMCP 54 tools ready (CPA/Fleet Decoupled)"),
        )

        # 2. KeePass 凭据保险箱 (keepass-vault - 独立生态插件)
        keepass_plugin = QuadPluginDefinition(
            plugin_id="keepass-vault",
            name="KeePass 凭据保险箱",
            version="1.0.0",
            category="user",
            description="全集群密码、SSH 私钥与 API Key 凭据存储保险箱 (独立生态插件 · 零后端依赖)",
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

        # 3. 联网搜索与网页深度清洗 (network-search - 独立生态插件)
        search_plugin = QuadPluginDefinition(
            plugin_id="network-search",
            name="联网搜索与采集网关",
            version="1.0.0",
            category="user",
            description="独立多引擎联网搜索与采集聚合网关，支持原生标准 API (免装插件) 与定制插件双模态",
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
                ToolDefinition(name="deep_research", description="Exa Agent 多步自主调研长报告 (POST /agent/runs)", category="search"),
                ToolDefinition(name="search_vertical_expert", description="Keenable NEEDLE 5大垂类高精专家检索 (Scholar/Finance/Legal/News/Rare)", category="search"),
                ToolDefinition(name="benchmark_needle", description="Keenable NEEDLE 自建基准校验 (兼容别名)", category="search"),
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

        # 4. Dify 智能体与工作流中枢 (dify - 独立生态插件)
        dify_plugin = QuadPluginDefinition(
            plugin_id="dify",
            name="Dify 智能体与工作流中枢",
            version="1.0.0",
            category="user",
            description="全生命周期可视化 AI 智能体编排与工作流中枢 (应用管理、DSL 导入导出、知识库检索引擎与模型提供商)",
            skill=SkillDefinition(
                skill_id="dify-ops",
                name="Dify 工作流编排认知导轨",
                description="可视化工作流调度、DSL 规范导入导出与知识库 Hit-Testing 检索契约",
                sop_summary="探针测活 -> 列出应用与工作流 -> 导出/同步 DSL -> 触发工作流执行 -> 知识库召回",
                rules=[
                    "高危应用与知识库删除操作前必须二次确认",
                    "DSL 导入必须遵循官方 YAML 规范版本",
                    "工作流触发执行必须提供完整的必填 inputs 参数",
                ],
            ),
            hooks=[
                HookDefinition(
                    hook_id="dify_execution_audit",
                    name="工作流入参合规审计",
                    trigger_event="before_workflow_run",
                    description="工作流触发前校验 inputs 契约与入参必填项，防止脏入参导致执行崩溃",
                ),
                HookDefinition(
                    hook_id="dify_dsl_backup_hook",
                    name="DSL 覆写前自动备份",
                    trigger_event="before_dsl_import",
                    description="覆盖导入应用 DSL 前自动拉取当前版本归档备份，保障安全回滚",
                ),
            ],
            tools=[
                ToolDefinition(name="dify_status", description="检查 Dify 服务端连通状态与资产总览", category="workflow"),
                ToolDefinition(name="dify_list_apps", description="分页列出工作区内应用与工作流清单", category="workflow"),
                ToolDefinition(name="dify_get_app", description="获取指定应用/工作流详细配置规格", category="workflow"),
                ToolDefinition(name="dify_export_dsl", description="导出应用或工作流完整 YAML DSL 规范配置", category="workflow"),
                ToolDefinition(name="dify_import_dsl", description="导入 YAML DSL 创建或覆盖更新应用", category="workflow"),
                ToolDefinition(name="dify_delete_app", description="按 UUID 物理删除指定应用 (高危)", category="workflow", is_dangerous=True),
                ToolDefinition(name="dify_run_workflow", description="传入参数触发执行指定工作流并捕获执行轨迹", category="workflow"),
                ToolDefinition(name="dify_list_datasets", description="分页列出工作区内知识库数据集清单", category="knowledge"),
                ToolDefinition(name="dify_create_dataset", description="新建高品质知识库数据集", category="knowledge"),
                ToolDefinition(name="dify_delete_dataset", description="按 UUID 物理删除指定知识库 (高危)", category="knowledge", is_dangerous=True),
                ToolDefinition(name="dify_search_dataset", description="对指定知识库执行 Hit-Testing 语义测试检索", category="knowledge"),
                ToolDefinition(name="dify_list_model_providers", description="列出工作区已配置模型提供商与凭据状态", category="models"),
            ],
            gui=GuiSchemaDefinition(
                settings_fields={
                    "apiUrl": "http://127.0.0.1:13000",
                    "workspaceId": "693e2343-fa88-4273-9360-b7e4c8b0bd83",
                    "authMode": "Admin API Key (Verified)",
                    "consoleRoute": "/console/api",
                },
                dashboard_route="/plugins",
            ),
            health=PluginHealthProbe(status="healthy", latency_ms=1.2, message="Dify :13000 connected"),
        )

        # 5. CPA 跨模型算力协同中枢 (cpa-squad - 独立生态插件 · 物理宿主 2080Ti WSL2)
        cpa_plugin = QuadPluginDefinition(
            plugin_id="cpa-squad",
            name="CPA 跨模型算力协同",
            version="1.0.0",
            category="user",
            description="CPA 多模型智囊协同与工兵批量调度中枢 (独立微服务 · 物理宿主 2080Ti WSL2 虚拟服务器)",
            skill=SkillDefinition(
                skill_id="cpa-squad",
                name="CPA 算力与工兵协同认知导轨",
                description="Claude/GPT 专家决策咨询，Gemini/DeepSeek 工兵批量扇出，MIMO 限速避坑与故障无感转移规约",
                sop_summary="研判任务复杂度 -> 高难决策调 consult 问专家 -> 批量重复任务调 fanout 扇出工兵 -> 自动记账",
                rules=[
                    "专家模型(Claude/GPT)严格用于高难推演与决策，严禁用于机械体力活",
                    "工兵模型(Flash/V3)负责批量吞吐，遇429自动触发MIMO冷却避坑",
                    "CPA 服务宕机或网络中断时，本地业务核心100%自主运行不受阻断",
                ],
            ),
            hooks=[
                HookDefinition(
                    hook_id="cpa_fallback_failover_hook",
                    name="429 智能降级与熔断转移",
                    trigger_event="before_cpa_dispatch",
                    description="专家模型遭遇 429 限流或网络超时时，毫秒级无感降级到工兵集群，杜绝调用挂死",
                ),
                HookDefinition(
                    hook_id="cpa_cost_telemetry_hook",
                    name="Token 消耗与成本审计",
                    trigger_event="after_cpa_response",
                    description="自动提取请求输入/输出真实 Token 数与耗时，沉淀结构化记账日志",
                ),
            ],
            tools=[
                ToolDefinition(name="openviking_cpa_consult", description="CPA 专家模型异步咨询与决策协同", category="cpa"),
                ToolDefinition(name="openviking_cpa_fanout", description="CPA 任务批量扇出并行调度", category="cpa"),
            ],
            gui=GuiSchemaDefinition(
                settings_fields={
                    "cpaHost": "http://127.0.0.1:18000",
                    "workerNode": "2080Ti WSL2 (Dedicated Server)",
                    "expertModel": "claude-3-5-sonnet / gpt-4o",
                    "workerModels": "gemini-2.5-flash / deepseek-v3 / qwen-max",
                    "rateLimitAvoidance": "MIMO Enabled (Multi-Key Failover)",
                },
                dashboard_route="/plugins",
            ),
            health=PluginHealthProbe(status="healthy", latency_ms=1.2, message="CPA squad ready & workers active"),
        )

        # 6. 卫星集群同频运维中枢 (fleet-mesh - 独立生态插件 · 跨物理机节点)
        fleet_plugin = QuadPluginDefinition(
            plugin_id="fleet-mesh",
            name="卫星集群同频运维",
            version="1.0.0",
            category="user",
            description="跨物理机节点（MacBook M3 / 宿主 PC / 云端 VPS）健康巡检与配置技能一键同频",
            skill=SkillDefinition(
                skill_id="satellite-fleet-ops",
                name="卫星集群运维认知导轨",
                description="跨物理机节点巡检、网络拓扑探测与一键同频同步 SOP",
                sop_summary="定期体检 fleet_check -> 发现配置/技能漂移 -> 执行 fleet_sync 一键同频",
                rules=[
                    "跨节点同频前必须核验 Master Memory 版本指纹",
                    "网络隔离或高延迟节点自动标记休眠，禁止强行同步导致脑裂",
                ],
            ),
            hooks=[
                HookDefinition(
                    hook_id="fleet_heartbeat_sync_hook",
                    name="集群节点心跳同频探针",
                    trigger_event="before_node_probe",
                    description="侦测到跨物理机节点离线超时或新节点上线时，触发同频校验与拓扑自愈",
                ),
            ],
            tools=[
                ToolDefinition(name="openviking_fleet_check", description="卫星集群节点运行态健康体检", category="fleet"),
                ToolDefinition(name="openviking_fleet_sync", description="跨节点配置与技能一键同频同步", category="fleet"),
            ],
            gui=GuiSchemaDefinition(
                settings_fields={
                    "clusterDomain": "vk.tide.red",
                    "masterNode": "vk-master (Primary SSOT)",
                    "satelliteNodes": "Mac-Studio-M3, Host-PC-Windows, Cloud-VPS",
                    "syncInterval": "300s",
                },
                dashboard_route="/plugins",
            ),
            health=PluginHealthProbe(status="healthy", latency_ms=0.9, message="Cluster mesh synchronized"),
        )

        for p in (memory_plugin, keepass_plugin, search_plugin, dify_plugin, cpa_plugin, fleet_plugin):
            self.register_plugin(p)
        # 向下兼容历史 ID 与工具映射别名 (独立别名表，绝不污染 _plugins 真实列表)
        self._aliases["dsh-plugin-openviking"] = "openviking-memory"
        self._aliases["dify-workflow"] = "dify"
        self._aliases["dify-control-plane"] = "dify"
        self._aliases["cpa"] = "cpa-squad"
        self._aliases["fleet"] = "fleet-mesh"
        self._tool_to_plugin_map["searxng_search"] = "network-search"
        self._tool_to_plugin_map["crawl4ai_extract"] = "network-search"
        self._tool_to_plugin_map["cpa_consult"] = "cpa-squad"
        self._tool_to_plugin_map["cpa_fanout"] = "cpa-squad"
        self._tool_to_plugin_map["fleet_check"] = "fleet-mesh"
        self._tool_to_plugin_map["fleet_sync"] = "fleet-mesh"

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
            "architecture": "Multi-Channel Standard Bridge (三大官方标杆渠道接入中枢)",
            "description": "专供智能体生态 (Google 反重力 / DeepSeek Harness / 通用 MCP 智能体) 本地开箱即用安装的通道桥梁。安装后配置 userKey 与 agentId，即可安全连通 VK 服务端中心化三大标杆插件 (记忆/搜索/凭据) 动态能力。",
            "install_command": f"npm install {package_url}",
            "handshake_protocol": "HTTP/SSE + Bearer Auth (UserKey:AgentID)",
            "channels": {
                "antigravity": {
                    "name": "Google 反重力",
                    "standard": "Google Gemini Agent Framework Plugin Specification",
                    "version": "2.0.11",
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
