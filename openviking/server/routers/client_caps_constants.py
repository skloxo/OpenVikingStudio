# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Client Capabilities Tool & Hook Catalog Constants (SSOT).
负责客户端通信桥梁 (DSH, Antigravity) 原生三大 Quad 插件工具与 Hook 真相源。
严格对齐 Card-141 (34 战地工具 + 3 Hook) 与 Card-142 (17 运维工具 + 2 Hook) 及 Card-140 (2 集群工具 + 1 Hook)。
"""

from typing import Any, Dict, List

# =========================================================================
# 1. 核心记忆与代码战地插件 (openviking-memory: 34 项战地武器矩阵)
# =========================================================================
BATTLEFIELD_34_TOOLS: List[Dict[str, str]] = [
    # 记忆中枢 (8 项)
    {"id": "openviking_find", "name": "find", "description": "基于向量与分词的混合记忆语义检索"},
    {"id": "openviking_search", "name": "search", "description": "高级混合关键词与过滤检索引擎"},
    {"id": "openviking_read", "name": "read", "description": "深读知识全文与 L2 正文切片"},
    {"id": "openviking_write", "name": "write", "description": "将重要记忆与结构化事实写入长程记忆"},
    {"id": "openviking_store", "name": "store", "description": "低阶元数据原子持久化存储"},
    {"id": "openviking_link", "name": "link", "description": "建立记忆节点间的语义双向关联边"},
    {"id": "openviking_get_relations", "name": "get_relations", "description": "查询指定记忆的图谱关联拓扑"},
    {"id": "openviking_unlink", "name": "unlink", "description": "解绑记忆节点间的语义拓扑边"},
    # 代码与工作区深度 AST (11 项)
    {"id": "openviking_ls", "name": "ls", "description": "查看工作区或知识目录物理文件清单"},
    {"id": "openviking_tree", "name": "tree", "description": "获取工作区层级目录拓扑树"},
    {"id": "openviking_grep", "name": "grep", "description": "工作区全盘正则文本模式极速检索"},
    {"id": "openviking_glob", "name": "glob", "description": "通配符快速定位工作区文件路径"},
    {"id": "openviking_code_outline", "name": "code_outline", "description": "提取源码 AST 核心大纲与接缝"},
    {"id": "openviking_code_search", "name": "code_search", "description": "基于 AST 结构的代码语义符号检索"},
    {"id": "openviking_code_expand", "name": "code_expand", "description": "针对深层函数实现按需展开精读"},
    {"id": "openviking_diff", "name": "diff", "description": "比对工作区文件变更或版本差异"},
    {"id": "openviking_smart_read", "name": "smart_read", "description": "自适应多级智能折叠精读代码"},
    {"id": "openviking_tokenshift_compress", "name": "tokenshift_compress", "description": "TokenShift 源码 AST 折叠压缩"},
    {"id": "openviking_tag", "name": "tag", "description": "为指定知识或代码节点打上语义标签"},
    # 技能中心感知与发布 (6 项 - 锚定 1214 全域技能)
    {"id": "openviking_skills", "name": "skills", "description": "感知并列出系统全域 1214 个在册技能"},
    {"id": "openviking_audit_skills", "name": "audit_skills", "description": "技能 4 维质量评分与冲突审计"},
    {"id": "openviking_auto_onboard_skills", "name": "auto_onboard_skills", "description": "自动感知新技能并提交入籍队列"},
    {"id": "openviking_get_onboard_queue_status", "name": "get_onboard_queue_status", "description": "查看技能自动化入籍队列状态"},
    {"id": "openviking_fix_skill", "name": "fix_skill", "description": "根据诊断结果自动自愈修复技能缺陷"},
    {"id": "openviking_record_evolution_lesson", "name": "record_evolution_lesson", "description": "沉淀战地踩坑经验与反思教训"},
    # 工单自主建卡与哨兵 (4 项)
    {"id": "openviking_file_task_card", "name": "file_task_card", "description": "智能体异常现场自主建卡吹哨"},
    {"id": "openviking_list_pending_cards", "name": "list_pending_cards", "description": "查看未解决的待办工单卡片清单"},
    {"id": "openviking_resolve_task_card", "name": "resolve_task_card", "description": "闭环解决工单并绑定 Git Commit"},
    {"id": "openviking_task_cards_summary", "name": "task_cards_summary", "description": "工单运转与自愈大盘统计总览"},
    # 超大文档代客泊车 (2 项)
    {"id": "openviking_valet_handover", "name": "valet_handover", "description": "大文档代客泊车异步深度消化"},
    {"id": "openviking_valet_ticket_status", "name": "valet_ticket_status", "description": "查询代客泊车任务处理状态"},
    # 安全脱敏与传感器 (3 项)
    {"id": "openviking_privacy", "name": "privacy", "description": "敏感凭据脱敏与私有端点保护"},
    {"id": "openviking_ping", "name": "ping", "description": "体外大脑端到端连通性心跳探针"},
    {"id": "openviking_harness_stats", "name": "harness_stats", "description": "智能体效能与硬件利用率探针"},
]

# 核心战地记忆 3 项 Hook 物理守卫
MEMORY_3_HOOKS: List[Dict[str, Any]] = [
    {"id": "ov_pre_invocation", "name": "跨会话前置记忆预取", "triggerEvent": "before_prompt", "description": "提问前静默召回匹配记忆并注入 Prompt 顶部，零 Token 机器级守护", "enabled": True},
    {"id": "ov_lesson_crystallizer", "name": "踩坑经验自动萃取", "triggerEvent": "after_response", "description": "会话解决复杂 Bug 后自动沉淀 Evolution Lesson 入库", "enabled": True},
    {"id": "ov_sandbox_guard", "name": "特权沙箱安全守卫", "triggerEvent": "before_tool", "description": "高危写操作与越权执行毫秒级安全阻断", "enabled": True},
]

# =========================================================================
# 2. 系统运维治理插件 (openviking-ops: 17 项运维特权武器矩阵)
# =========================================================================
OPS_17_TOOLS: List[Dict[str, Any]] = [
    {"id": "openviking_add_resource", "name": "add_resource", "description": "挂载外部新知识或源码资源"},
    {"id": "openviking_list_resources", "name": "list_resources", "description": "列出体外大脑全量挂载资源"},
    {"id": "openviking_delete_resource", "name": "delete_resource", "description": "安全删除指定知识资源", "isDangerous": True},
    {"id": "openviking_reindex", "name": "reindex", "description": "全量重建知识向量索引与 FTS5 倒排"},
    {"id": "openviking_commit", "name": "commit", "description": "持久化提交体外大脑变更"},
    {"id": "openviking_mv", "name": "mv", "description": "移动知识资源节点路径"},
    {"id": "openviking_rename", "name": "rename", "description": "重命名知识资源节点"},
    {"id": "openviking_webdav_info", "name": "webdav_info", "description": "WebDAV 挂载服务状态与连接凭据"},
    {"id": "openviking_dspy_compile", "name": "dspy_compile", "description": "提示词 DSPy 签名编译"},
    {"id": "openviking_memory_purity_report", "name": "memory_purity_report", "description": "概念漂移与记忆纯度审计报告"},
    {"id": "openviking_retry_dead_letter", "name": "retry_dead_letter", "description": "单条重试 QueueFS 失败死信消息"},
    {"id": "openviking_list_watches", "name": "list_watches", "description": "查看活跃的文件系统监听任务"},
    {"id": "openviking_cancel_watch", "name": "cancel_watch", "description": "取消指定的文件系统变更监听"},
    {"id": "openviking_manage_watch", "name": "manage_watch", "description": "调整监听策略与防抖窗口"},
    {"id": "openviking_server_control", "name": "server_control", "description": "服务端进程生命周期控制", "isDangerous": True},
    {"id": "openviking_server_init", "name": "server_init", "description": "服务端全新工作区初始化", "isDangerous": True},
    {"id": "openviking_server_doctor", "name": "server_doctor", "description": "服务端深度体检与诊断自愈"},
]

OPS_2_HOOKS: List[Dict[str, Any]] = [
    {"id": "ov_dead_letter_auto_healer", "name": "死信队列自动自愈", "triggerEvent": "on_error", "description": "捕获死信异常并自动排队重试自愈", "enabled": True},
    {"id": "ov_concept_drift_sentinel", "name": "概念漂移实时哨兵", "triggerEvent": "after_indexing", "description": "监控知识向量聚类漂移并在熵增超标时告警", "enabled": True},
]

# =========================================================================
# 3. 卫星集群同频运维插件 (fleet-mesh: 2 项集群工具)
# =========================================================================
FLEET_2_TOOLS: List[Dict[str, str]] = [
    {"id": "openviking_fleet_check", "name": "fleet_check", "description": "多物理节点全息同频健康体检与时钟延迟探针"},
    {"id": "openviking_fleet_sync", "name": "fleet_sync", "description": "一键跨物理节点触发配置与代码同频同步"},
]

FLEET_1_HOOKS: List[Dict[str, Any]] = [
    {"id": "fleet_heartbeat_sync", "name": "集群心跳同频守卫", "triggerEvent": "periodic", "description": "定期向各卫星节点同步心跳与拓扑时序", "enabled": True},
]

# =========================================================================
# 兼容别名导出 (保证历史引用平滑兼容)
# =========================================================================
MEMORY_CONSUMER_TOOLS = BATTLEFIELD_34_TOOLS
MEMORY_OPS_TOOLS = OPS_17_TOOLS
OFFICIAL_7_HOOKS = MEMORY_3_HOOKS + OPS_2_HOOKS + FLEET_1_HOOKS
