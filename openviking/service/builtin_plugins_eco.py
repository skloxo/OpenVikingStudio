# -*- coding: utf-8 -*-
"""内置生态扩展 Quad 插件定义清单 (Ecosystem Builtin Plugins SSOT)

包含 KeePass 凭据、联网搜索、Dify 工作流、CPA 跨模型算力协同与卫星集群同频。
严格遵循四大标杆标准与单文件 100~300 行黄金甜点区 (<= 500 行安全红线)。
"""

from typing import List, Dict
from openviking.models.plugin import (
    QuadPluginDefinition,
    ToolDefinition,
    HookDefinition,
    SkillDefinition,
    GuiSchemaDefinition,
    PluginHealthProbe,
)


def create_ecosystem_plugins(
    tool_to_plugin_map: Dict[str, str],
    aliases: Dict[str, str],
) -> List[QuadPluginDefinition]:
    """创建并注册所有内置生态插件 (KeePass, Search, Dify, CPA, Fleet)。"""
    # -------------------------------------------------------------
    # 1. KeePass 凭据保险箱 (keepass-vault)
    # -------------------------------------------------------------
    keepass_tools = [
        ToolDefinition(name="keepass_search", description="按标题、URL 或标签搜索凭据条目", category="vault"),
        ToolDefinition(name="keepass_get", description="安全读取指定条目的用户名、高熵密码或 TOTP", category="vault"),
        ToolDefinition(name="keepass_add", description="新建凭据条目并自动生成高熵随机密码", category="vault"),
        ToolDefinition(name="keepass_edit", description="更新已有条目的密码或元数据属性", category="vault"),
        ToolDefinition(name="keepass_rm", description="安全归档或删除指定凭据条目", category="vault", is_dangerous=True),
        ToolDefinition(name="keepass_list_tree", description="以树状层级列出保险箱分组目录", category="vault"),
        ToolDefinition(name="keepass_analyze", description="扫描全库弱密码、重复密码与过期凭据", category="vault"),
        ToolDefinition(name="keepass_export_attachment", description="安全导出条目绑定的 SSH 私钥或证书附件", category="vault"),
        ToolDefinition(name="keepass_status", description="凭据库解锁与健康状态探针", category="vault"),
    ]
    for t in keepass_tools:
        tool_to_plugin_map[t.name] = "keepass-vault"

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
            sop_summary="查库第一公理 -> 找不到再新增 -> 高熵写盘 -> 严禁明文外传",
            rules=["严禁向人类索要明文密码", "新增凭据必须生成>=16位高熵密码", "敏感操作前快照备份"],
        ),
        hooks=[
            HookDefinition(
                hook_id="auto_lock_hook",
                name="空闲自动锁定保护",
                trigger_event="after_tool_execution",
                description="连续无操作超过阈值自动锁定内存敏感密钥，防范冷启动内存倾倒",
            ),
        ],
        tools=keepass_tools,
        gui=GuiSchemaDefinition(
            settings_fields={"kdbxPath": "~/.openviking/vault.kdbx", "autoLockSeconds": 3600},
            dashboard_route="/plugins",
        ),
        health=PluginHealthProbe(status="healthy", latency_ms=0.8, message="Vault unlocked"),
    )

    # -------------------------------------------------------------
    # 2. 联网搜索与网页深度清洗 (network-search)
    # -------------------------------------------------------------
    search_tools = [
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
        ToolDefinition(name="search_vertical_expert", description="Keenable NEEDLE 5大垂类高精专家检索", category="search"),
        ToolDefinition(name="benchmark_needle", description="Keenable NEEDLE 自建基准校验 (兼容别名)", category="search"),
    ]
    for t in search_tools:
        tool_to_plugin_map[t.name] = "network-search"

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
        tools=search_tools,
        gui=GuiSchemaDefinition(
            settings_fields={
                "totalKeys": 26,
                "keenablePool": "8 Keys / 800,000 req/mo",
                "exaPool": "9 Keys / $90.0/mo",
                "tavilyPool": "9 Keys / 9,000 pts/mo",
                "searxngLocalUrl": "http://127.0.0.1:8888",
                "crawl4aiLocalUrl": "http://127.0.0.1:18789",
                "retentionDays": 45,
            },
            dashboard_route="/plugins",
        ),
        health=PluginHealthProbe(status="healthy", latency_ms=1.8, message="26 Keys active & SearXNG connected"),
    )

    # -------------------------------------------------------------
    # 3. Dify 智能体与工作流中枢 (dify)
    # -------------------------------------------------------------
    dify_tools = [
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
    ]
    for t in dify_tools:
        tool_to_plugin_map[t.name] = "dify"

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
            rules=["高危应用与知识库删除操作前必须二次确认", "DSL 导入必须遵循官方 YAML 规范版本"],
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
        tools=dify_tools,
        gui=GuiSchemaDefinition(
            settings_fields={
                "apiUrl": "http://127.0.0.1:13000",
                "workspaceId": "693e2343-fa88-4273-9360-b7e4c8b0bd83",
                "authMode": "Admin API Key (Verified)",
            },
            dashboard_route="/plugins",
        ),
        health=PluginHealthProbe(status="healthy", latency_ms=1.2, message="Dify :13000 connected"),
    )

    # -------------------------------------------------------------
    # 4. CPA 跨模型算力协同中枢 (cpa-squad)
    # -------------------------------------------------------------
    cpa_tools = [
        ToolDefinition(name="openviking_cpa_consult", description="CPA 专家模型异步咨询与决策协同", category="cpa"),
        ToolDefinition(name="openviking_cpa_fanout", description="CPA 任务批量扇出并行调度", category="cpa"),
    ]
    for t in cpa_tools:
        tool_to_plugin_map[t.name] = "cpa-squad"

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
        tools=cpa_tools,
        gui=GuiSchemaDefinition(
            settings_fields={
                "cpaHost": "http://127.0.0.1:18000",
                "workerNode": "2080Ti WSL2 (Dedicated Server)",
                "expertModel": "claude-3-5-sonnet / gpt-4o",
                "workerModels": "gemini-2.5-flash / deepseek-v3 / qwen-max",
            },
            dashboard_route="/plugins",
        ),
        health=PluginHealthProbe(status="healthy", latency_ms=1.2, message="CPA squad ready & workers active"),
    )

    # -------------------------------------------------------------
    # 5. 卫星集群同频运维中枢 (fleet-mesh)
    # -------------------------------------------------------------
    fleet_tools = [
        ToolDefinition(name="openviking_fleet_check", description="卫星集群节点运行态健康体检", category="fleet"),
        ToolDefinition(name="openviking_fleet_sync", description="跨节点配置与技能一键同频同步", category="fleet"),
    ]
    for t in fleet_tools:
        tool_to_plugin_map[t.name] = "fleet-mesh"

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
        tools=fleet_tools,
        gui=GuiSchemaDefinition(
            settings_fields={
                "clusterDomain": "vk.tide.red",
                "masterNode": "vk-master (Primary SSOT)",
                "syncInterval": "300s",
            },
            dashboard_route="/plugins",
        ),
        health=PluginHealthProbe(status="healthy", latency_ms=0.9, message="Cluster mesh synchronized"),
    )

    # 注册别名映射
    aliases["dsh-plugin-openviking"] = "openviking-memory"
    aliases["dify-workflow"] = "dify"
    aliases["dify-control-plane"] = "dify"
    aliases["cpa"] = "cpa-squad"
    aliases["fleet"] = "fleet-mesh"
    aliases["ops"] = "openviking-ops"
    aliases["cpa_consult"] = "openviking_cpa_consult"
    aliases["cpa_fanout"] = "openviking_cpa_fanout"
    aliases["fleet_check"] = "openviking_fleet_check"
    aliases["fleet_sync"] = "openviking_fleet_sync"
    tool_to_plugin_map["searxng_search"] = "network-search"
    tool_to_plugin_map["crawl4ai_extract"] = "network-search"
    tool_to_plugin_map["cpa_consult"] = "cpa-squad"
    tool_to_plugin_map["cpa_fanout"] = "cpa-squad"
    tool_to_plugin_map["fleet_check"] = "fleet-mesh"
    tool_to_plugin_map["fleet_sync"] = "fleet-mesh"

    return [keepass_plugin, search_plugin, dify_plugin, cpa_plugin, fleet_plugin]
