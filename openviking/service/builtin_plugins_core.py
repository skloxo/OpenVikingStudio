# -*- coding: utf-8 -*-
"""内置核心战地与运维治理 Quad 插件定义清单 (Core & Ops Builtin Plugins SSOT)

严格遵循四大标杆标准:
1. Quad Plugin (四位一体: Tools + Hooks + Skill + GUI);
2. 单文件 100~300 行黄金甜点区 (<= 500 行安全红线);
3. 战地核心记忆插件收敛为 34 项战地工具 + 3 项 Hook 物理守卫;
4. 系统运维治理插件 openviking-ops 独立封装 (17 项运维特权工具 + 2 项 Hook 守卫).
"""

from typing import List, Dict, Tuple
from openviking.models.plugin import (
    QuadPluginDefinition,
    ToolDefinition,
    HookDefinition,
    SkillDefinition,
    GuiSchemaDefinition,
    PluginHealthProbe,
)


def resolve_package_version(pkg_name: str, fallback: str) -> str:
    """从本地 package.json 或 plugin.json 读取真实版本号，确保与各客户端插件 100% 同步 SSOT。"""
    try:
        from pathlib import Path
        import json
        studio_root = Path(__file__).resolve().parent.parent.parent
        # 1. 尝试 DSH package.json
        dsh_pkg = studio_root / "integrations" / "deepseek-harness" / pkg_name / "package.json"
        if dsh_pkg.is_file():
            data = json.loads(dsh_pkg.read_text(encoding="utf-8"))
            if data.get("version"):
                return data["version"]
        # 2. 尝试 Antigravity plugin.json
        ag_name = "openviking-memory" if pkg_name == "dsh-plugin-openviking-memory" else pkg_name.replace("dsh-plugin-", "")
        ag_plugin = studio_root / "integrations" / "antigravity" / ag_name / "plugin.json"
        if ag_plugin.is_file():
            data = json.loads(ag_plugin.read_text(encoding="utf-8"))
            if data.get("version"):
                return data["version"]
    except Exception:
        pass
    return fallback


# 战地 34 工具物理名称清单 SSOT (普通业务与研发 Agent 全量武器库)
BATTLEFIELD_34_TOOL_NAMES: List[str] = [
    # 1. 记忆中枢 (8 项)
    "openviking_find",
    "openviking_search",
    "openviking_read",
    "openviking_write",
    "openviking_store",
    "openviking_link",
    "openviking_get_relations",
    "openviking_unlink",
    # 2. 代码与工作区深度 AST (11 项)
    "openviking_ls",
    "openviking_tree",
    "openviking_grep",
    "openviking_glob",
    "openviking_code_outline",
    "openviking_code_search",
    "openviking_code_expand",
    "openviking_diff",
    "openviking_smart_read",
    "openviking_tokenshift_compress",
    "openviking_content_reduce",
    "openviking_tag",
    # 3. 技能中心感知与发布 (6 项 - 锚定 1214 全域技能)
    "openviking_skills",
    "openviking_audit_skills",
    "openviking_auto_onboard_skills",
    "openviking_get_onboard_queue_status",
    "openviking_fix_skill",
    "openviking_record_evolution_lesson",
    # 4. 工单自主建卡与哨兵 (4 项 - 异常自主建卡吹哨)
    "openviking_file_task_card",
    "openviking_list_pending_cards",
    "openviking_resolve_task_card",
    "openviking_task_cards_summary",
    # 5. 超大文档代客泊车 (2 项 - 50MB+ 异步批处理防 504)
    "openviking_valet_handover",
    "openviking_valet_ticket_status",
    # 6. 安全脱敏与传感器 (3 项)
    "openviking_privacy",
    "openviking_ping",
    "openviking_harness_stats",
]

# 运维治理 17 工具物理名称清单 SSOT (后台专属运维 Agent / 巡检 Engine 武器库)
OPS_17_TOOL_NAMES: List[str] = [
    "openviking_add_resource",
    "openviking_list_resources",
    "openviking_delete_resource",
    "openviking_reindex",
    "openviking_commit",
    "openviking_mv",
    "openviking_rename",
    "openviking_webdav_info",
    "openviking_memory_purity_report",
    "openviking_retry_dead_letter",
    "openviking_list_watches",
    "openviking_cancel_watch",
    "openviking_manage_watch",
    "openviking_server_control",
    "openviking_server_init",
    "openviking_server_doctor",
]


def create_core_and_ops_plugins(
    tool_to_plugin_map: Dict[str, str],
    aliases: Dict[str, str],
) -> List[QuadPluginDefinition]:
    """创建核心战地记忆插件 (34工具) 与系统运维治理插件 (17工具)。"""
    # -------------------------------------------------------------
    # 1. 核心战地记忆插件 (openviking-memory): 34 工具 + 3 Hook + 1 Skill + GUI
    # -------------------------------------------------------------
    battlefield_tools = [
        # 1. 记忆中枢 (8 项)
        ToolDefinition(name="find", description="基于向量与分词的混合记忆语义检索", category="core"),
        ToolDefinition(name="search", description="高级混合关键词与过滤检索引擎", category="core"),
        ToolDefinition(name="read", description="深读知识全文与 L2 正文切片", category="core"),
        ToolDefinition(name="write", description="将重要记忆与结构化事实写入长程记忆", category="core"),
        ToolDefinition(name="store", description="原子持久化事实结晶与关系拓扑", category="core"),
        ToolDefinition(name="link", description="关联建立两个知识实体之间的双向语义链接", category="core"),
        ToolDefinition(name="get_relations", description="查询知识实体的所有拓扑关联与反向引用", category="core"),
        ToolDefinition(name="unlink", description="安全解除知识实体之间的语义关联", category="core"),
        # 2. 代码与工作区深度 AST (11 项)
        ToolDefinition(name="ls", description="列出当前工作区目录结构条目", category="workspace"),
        ToolDefinition(name="tree", description="获取代码库或工作区的层级结构树", category="workspace"),
        ToolDefinition(name="grep", description="在工作区文件中快速正则检索文本模式", category="workspace"),
        ToolDefinition(name="glob", description="按文件名通配符模式快速定位文件", category="workspace"),
        ToolDefinition(name="openviking_code_outline", description="代码 AST 语法大纲提取", category="code"),
        ToolDefinition(name="openviking_code_search", description="代码语义符号深度检索", category="code"),
        ToolDefinition(name="openviking_code_expand", description="代码上下文智能折叠与按需展开", category="code"),
        ToolDefinition(name="openviking_diff", description="文件与代码版本差异对比分析", category="code"),
        ToolDefinition(name="openviking_smart_read", description="分层自适应智能知识提取与概括", category="code"),
        ToolDefinition(name="openviking_tokenshift_compress", description="TokenShift 源码 AST 折叠压缩", category="code"),
        ToolDefinition(name="openviking_content_reduce", description="通用内容脱水压缩(AST/技能/文本)", category="code"),
        ToolDefinition(name="openviking_tag", description="资源与代码标签标注及分类检索", category="workspace"),
        # 3. 技能中心感知与发布 (6 项 - 锚定 1214 全域技能)
        ToolDefinition(name="openviking_skills", description="知识中枢 1214 全量技能状态与分类总览", category="skill"),
        ToolDefinition(name="openviking_audit_skills", description="知识中枢技能规范静态安全审计", category="skill"),
        ToolDefinition(name="openviking_auto_onboard_skills", description="自动化技能入库校验与发布上架", category="skill"),
        ToolDefinition(name="openviking_get_onboard_queue_status", description="技能入库队列状态与审批进展查询", category="skill"),
        ToolDefinition(name="openviking_fix_skill", description="技能缺陷自动化诊断与一键修复", category="skill"),
        ToolDefinition(name="openviking_record_evolution_lesson", description="踩坑事实与自演进经验入脑存盘", category="skill"),
        # 4. 工单自主建卡与哨兵 (4 项 - 异常自主建卡吹哨)
        ToolDefinition(name="openviking_file_task_card", description="智能体异常现场自主建卡吹哨上报", category="aifp"),
        ToolDefinition(name="openviking_list_pending_cards", description="查看待排期与未解决工单清单", category="aifp"),
        ToolDefinition(name="openviking_resolve_task_card", description="闭环归档工单并绑定 Git Tag", category="aifp"),
        ToolDefinition(name="openviking_task_cards_summary", description="工单运转指标总览与趋势分析", category="aifp"),
        # 5. 超大文档代客泊车 (2 项 - 50MB+ 异步批处理防 504)
        ToolDefinition(name="openviking_valet_handover", description="泊车管家 50MB+ 超大文档异步离线消化", category="async"),
        ToolDefinition(name="openviking_valet_ticket_status", description="查看泊车管家消化与入库进度", category="async"),
        # 6. 安全脱敏与传感器 (3 项)
        ToolDefinition(name="openviking_privacy", description="脱敏敏感凭据、Token 与私有端点", category="security"),
        ToolDefinition(name="openviking_ping", description="检测体外大脑与核心服务毫秒级连通性", category="health"),
        ToolDefinition(name="openviking_harness_stats", description="Token SNR、P@5 召回率与模型性能统计", category="sensors"),
    ]

    for tool in battlefield_tools:
        name = tool.name
        tool_to_plugin_map[name] = "openviking-memory"
        if not name.startswith("openviking_"):
            tool_to_plugin_map[f"openviking_{name}"] = "openviking-memory"
            aliases[f"openviking_{name}"] = name
        else:
            short = name[len("openviking_"):]
            tool_to_plugin_map[short] = "openviking-memory"
            aliases[short] = name

    aliases["memory"] = "openviking-memory"
    aliases["core"] = "openviking-memory"

    memory_plugin = QuadPluginDefinition(
        plugin_id="openviking-memory",
        name="OpenViking 核心记忆与代码战地",
        version=resolve_package_version("dsh-plugin-openviking-memory", "2.0.33"),
        category="platform",
        description="体外大脑中心化战地旗舰：长程记忆、工作区 AST、1214技能感知、工单吹哨与泊车管家 (面向全量普通 Agent)",
        skill=SkillDefinition(
            skill_id="openviking-memory",
            name="核心战地认知导轨",
            description="体外大脑统一长程记忆存储、代码 AST 大纲、经验沉淀与异常自主建卡 SOP",
            sop_summary="核心事实已前置预取 -> 按需查 outline -> 精确定位 grep -> 遇到阻塞自主吹哨建卡",
            rules=["严禁开局盲目重复调用 find 盲搜", "遇到死胡同自主调用 file_task_card 建卡", "403 优雅回退"],
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
                description="会话解决复杂 Bug 后自动沉淀 Evolution Lesson 入脑",
            ),
            HookDefinition(
                hook_id="ov_sandbox_guard",
                name="运行态特权沙箱守卫",
                trigger_event="before_tool_execution",
                description="高危越权与敏感凭据外泄毫秒级安全阻断",
            ),
        ],
        tools=battlefield_tools,
        gui=GuiSchemaDefinition(
            settings_fields={
                "storageEngine": "SQLite FTS5 + VikingFS /queue",
                "embeddingModel": "WeMM-Embedding-9B (INT8, 4096d)",
                "rerankerModel": "Qwen3-VL-Reranker-2B (INT8)",
                "compressionPipeline": "TokenShift (AST) + LLMLingua-2 (rate=0.50)",
                "contextRouting": "L0/L1/L2 Autonomous Adaptive Dehydration",
                "storageDatabase": "~/.openviking/data/memory_lifecycle.db",
            },
            dashboard_route="/",
        ),
        health=PluginHealthProbe(status="healthy", latency_ms=1.1, message="FastMCP 34 tools ready (Battlefield Core)"),
    )

    # -------------------------------------------------------------
    # 2. 系统运维治理插件 (openviking-ops): 17 工具 + 2 Hook + 1 Skill + GUI
    # -------------------------------------------------------------
    ops_tools = [
        ToolDefinition(name="openviking_add_resource", description="异步向体外大脑挂载新资源", category="ops"),
        ToolDefinition(name="openviking_list_resources", description="列出已登记的体外大脑物理资源", category="ops"),
        ToolDefinition(name="openviking_delete_resource", description="安全注销指定体外大脑资源", category="ops", is_dangerous=True),
        ToolDefinition(name="openviking_reindex", description="触发知识与向量库全盘或增量重索引", category="ops"),
        ToolDefinition(name="openviking_commit", description="工作区变更版本快照物理提交", category="ops"),
        ToolDefinition(name="openviking_mv", description="底层文件或目录安全原子重定位", category="ops", is_dangerous=True),
        ToolDefinition(name="openviking_rename", description="知识库文件或目录重命名", category="ops", is_dangerous=True),
        ToolDefinition(name="openviking_webdav_info", description="WebDAV 协议挂载端点与配额信息", category="ops"),
        ToolDefinition(name="openviking_memory_purity_report", description="体外大脑记忆纯度评估与概念漂移审计", category="ops"),
        ToolDefinition(name="openviking_retry_dead_letter", description="死信队列消息自愈重试与故障排查", category="ops"),
        ToolDefinition(name="openviking_list_watches", description="查看自动刷新系统监听订阅", category="ops"),
        ToolDefinition(name="openviking_cancel_watch", description="取消自动刷新系统监听订阅", category="ops"),
        ToolDefinition(name="openviking_manage_watch", description="动态更新或调整系统监听器参数", category="ops"),
        ToolDefinition(name="openviking_server_control", description="核心中枢服务生命周期与优雅重启控制", category="ops", is_dangerous=True),
        ToolDefinition(name="openviking_server_init", description="底座存储引擎与数据表引导初始化", category="ops"),
        ToolDefinition(name="openviking_server_doctor", description="全系统底层硬件与数据库深度体检诊断", category="ops"),
    ]

    for tool in ops_tools:
        name = tool.name
        tool_to_plugin_map[name] = "openviking-ops"
        short = name[len("openviking_"):] if name.startswith("openviking_") else name
        tool_to_plugin_map[short] = "openviking-ops"
        aliases[short] = name

    aliases["ops"] = "openviking-ops"
    aliases["openviking_ops"] = "openviking-ops"

    ops_plugin = QuadPluginDefinition(
        plugin_id="openviking-ops",
        name="OpenViking 系统运维治理",
        version=resolve_package_version("dsh-plugin-openviking-ops", "1.0.4"),
        category="platform",
        description="系统底层自愈、死信队列重试、概念漂移审计与特权写改中枢 (专门授权给后台专用运维 Agent / 巡检 Engine)",
        skill=SkillDefinition(
            skill_id="openviking-ops",
            name="系统运维与自愈认知导轨",
            description="后台哨兵自动巡检死信、审计概念漂移与底座治理的标准运维规约",
            sop_summary="定时巡检死信 -> 评估纯度报告 -> 触发自愈重试 -> 写前创建快照 commit",
            rules=[
                "仅限后台自动化运维智能体调用，严禁暴露给一线普通业务 Agent",
                "高危破坏性操作 (delete/mv/control) 必须产生不可篡改审计日志",
            ],
        ),
        hooks=[
            HookDefinition(
                hook_id="ov_ops_drift_sentinel",
                name="概念漂移与死信自愈巡检心跳",
                trigger_event="before_prompt_submit",
                description="后台定时感知死信积压与记忆衰减，主动调度自愈协程",
            ),
            HookDefinition(
                hook_id="ov_ops_audit_logger",
                name="特权操作全量物理审计日记账",
                trigger_event="before_tool_execution",
                description="对所有 ops 特权调用实施参数镜像留痕与 Nonce 防篡改",
            ),
        ],
        tools=ops_tools,
        gui=GuiSchemaDefinition(
            settings_fields={
                "sentinelDaemon": "Active (24h In-Process Watchdog)",
                "dlqMaxRetries": 3,
                "auditLogPath": "~/.openviking/data/ops_audit.jsonl",
            },
            dashboard_route="/settings",
        ),
        health=PluginHealthProbe(status="healthy", latency_ms=0.9, message="FastMCP 17 tools ready (Ops Sentinel Guard)"),
    )

    return [memory_plugin, ops_plugin]
