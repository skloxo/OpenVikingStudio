/**
 * agent-tools.ts
 * 智能体工具池常量、角色工具包 (Tool Bundles) 与权限管理 (Tool ACL Matrix)
 * 100% 对齐 FastMCP 47 个全量物理工具 (SSOT)。
 *
 * 核心设计哲学 (第一性原理)：
 * 1. 角色分明：
 *    - 🛰️ 卫星工兵 (Satellite Consumer)：纯粹的使用者角色 (31项工具)，负责知识读写、代码阅读/AST/TDD、工单闭环、技能自上架与异步消化。
 *    - 🧠 中枢总控 (Master Maintainer)：即是使用者又是运维者 (47项全量工具)，涵盖使用者全量武器 + 代码写改、死信自愈、安全隔离与底座治理。
 * 2. 工具包直选：一键点选工具包卡片，免去 47 个复选框逐一勾选的繁琐认知负担。
 * 3. 网络自适应：彻底剥离硬编码的本地/公网标签，由运行时端点智能自适应。
 */

export type ToolItem = {
  id: string
  name: string
  description: string
  categoryBadge: string
  requiredRole?: 'admin' | 'root'
  defaultSelected?: boolean
}

export type ToolCategory = {
  id: 'satellite' | 'master_ops'
  name: string
  description: string
  tools: ToolItem[]
}

export const TOOL_CATEGORIES: ToolCategory[] = [
  {
    id: 'satellite',
    name: '🛰️ 业务使用者工具池 (31 项)',
    description: '涵盖知识检索、代码分析、契约单测、工单流转与全网采集等通用研发工具',
    tools: [
      // 1. 记忆与知识沉淀
      { id: 'find', name: 'find (语义召回)', description: '基于分层语义索引智能查找最相关记忆', categoryBadge: '记忆检索', defaultSelected: true },
      { id: 'search', name: 'search (精确检索)', description: '对记忆中枢进行关键词与过滤检索', categoryBadge: '记忆检索', defaultSelected: true },
      { id: 'read', name: 'read (读取记忆)', description: '读取特定记忆资源或文档的完整内容', categoryBadge: '记忆读取', defaultSelected: true },
      { id: 'remember', name: 'remember (长程沉淀)', description: '将结构化对话与重要知识写入长程记忆', categoryBadge: '记忆沉淀', defaultSelected: true },
      { id: 'openviking_history_search', name: 'history_search (历史检索)', description: 'FTS5 对话全文字词与知识召回检索', categoryBadge: '对话记录' },
      { id: 'web_search', name: 'web_search (全网搜索)', description: '像素级对齐 DSH，45+ 引擎聚合与百度广告清洗，带 1.3ms 极速缓存', categoryBadge: '全球情报', defaultSelected: true },
      { id: 'web_fetch', name: 'web_fetch (网页精读)', description: '像素级对齐 DSH，Crawl4AI Playwright 无头穿透渲染提取纯净正文', categoryBadge: '全球情报', defaultSelected: true },
      { id: 'openviking_web_search', name: 'openviking_web_search (中枢搜索)', description: 'OpenViking 原生全网高精搜索兼容易名', categoryBadge: '全球情报' },

      // 2. 上下文与工作约束
      { id: 'openviking_active_notes_get', name: 'active_notes_get (获取约束)', description: '检索活跃里程碑与工作约束', categoryBadge: '上下文' },
      { id: 'openviking_active_notes_update', name: 'active_notes_update (更新约束)', description: '更新当前目标与工作约束', categoryBadge: '上下文' },
      { id: 'openviking_context_route', name: 'context_route (上下文路由)', description: '多模态上下文自适应分流与压缩决策', categoryBadge: '上下文' },

      // 3. 工作区文件与代码分析 (只读安全)
      { id: 'list', name: 'list (目录列举)', description: '列出 viking:// 目录结构条目', categoryBadge: '工作区' },
      { id: 'tree', name: 'tree (递归目录树)', description: '获取代码库或工作区的层级结构', categoryBadge: '工作区' },
      { id: 'grep', name: 'grep (正则匹配)', description: '在工作区文件中快速检索正则文本模式', categoryBadge: '工作区' },
      { id: 'glob', name: 'glob (文件通配)', description: '按文件名通配符扫描定位文件', categoryBadge: '工作区' },
      { id: 'zg_search', name: 'zg_search (AST检索)', description: '阿里 zg-grep 代码语义 AST 静态搜索', categoryBadge: '代码分析' },
      { id: 'openviking_code_impact', name: 'code_impact (爆炸半径)', description: '查询表/接口反向依赖与爆炸半径，改动前查清影响面', categoryBadge: '代码分析' },
      { id: 'openviking_tokenshift_compress', name: 'tokenshift_compress (代码压缩)', description: 'TokenShift 源码 AST 折叠压缩，节约远程传输与上下文', categoryBadge: '上下文' },

      // 4. 测试与研发辅助 (TDD 契约单测)
      { id: 'openviking_generate_contract_test', name: 'generate_contract_test (契约测试)', description: '由 AST 事实直接派生 pytest 契约测试脚手架', categoryBadge: 'AST测试' },

      // 5. 技能生态全周期 (编写/评估/修复/上架)
      { id: 'openviking_skill_validate', name: 'skill_validate (契约校验)', description: '校验 SKILL.md YAML 头与规约契约合法性', categoryBadge: '技能生态' },
      { id: 'openviking_skill_judge', name: 'skill_judge (质量评分)', description: '技能 4 维质量评分与达标门禁', categoryBadge: '技能生态' },
      { id: 'openviking_skill_remediate', name: 'skill_remediate (自愈修复)', description: '技能缺陷诊断与自愈修复建议', categoryBadge: '技能生态' },
      { id: 'openviking_skill_zip', name: 'skill_zip (规约压缩)', description: '技能 0-rollout 契约级压缩', categoryBadge: '规约压缩' },
      { id: 'openviking_skill_intent_match', name: 'skill_intent_match (意图匹配)', description: '自然语言意图匹配与冲突检测', categoryBadge: '技能生态' },
      { id: 'openviking_skill_publish', name: 'skill_publish (技能发布)', description: '一线工兵技能成果发布上架至体外大脑', categoryBadge: '技能生态' },

      // 6. AIFP 工单流转闭环 (建卡/看卡/结单/看板)
      { id: 'openviking_file_task_card', name: 'file_task_card (自主建卡)', description: '智能体异常现场自主建卡上报', categoryBadge: 'AIFP工单', defaultSelected: true },
      { id: 'openviking_list_pending_cards', name: 'list_pending_cards (待办工单)', description: '查看待排期与未解决工单清单', categoryBadge: 'AIFP工单' },
      { id: 'openviking_resolve_task_card', name: 'resolve_task_card (工单归档)', description: '闭环归档工单并绑定 Git Tag', categoryBadge: 'AIFP工单' },
      { id: 'openviking_task_cards_summary', name: 'task_cards_summary (工单总览)', description: '工单运转指标总览与趋势分析', categoryBadge: 'AIFP工单' },

      // 7. 异步大文档消化外包 (泊车管家)
      { id: 'openviking_valet_handover', name: 'valet_handover (泊车消化)', description: '泊车管家异步大文档深度消化', categoryBadge: '异步批处理' },
      { id: 'openviking_valet_ticket_status', name: 'valet_ticket_status (泊车进度)', description: '查看泊车管家消化与入库进度', categoryBadge: '异步批处理' },

      // 8. 安全感知与雷达
      { id: 'health', name: 'health (服务探针)', description: '检测记忆引擎与向量数据库健康状态', categoryBadge: '探针检测' },
      { id: 'openviking_privacy_mask', name: 'privacy_mask (脱敏过滤)', description: '脱敏敏感凭据、Token 与私有端点，公网出海防泄密', categoryBadge: '隐私脱敏' },
      { id: 'openviking_agent_sensors', name: 'agent_sensors (3D传感器)', description: 'Token SNR, P@5 召回率传感器', categoryBadge: '观测雷达' },
    ],
  },
  {
    id: 'master_ops',
    name: '🧠 中枢运维特权工具池 (16 项)',
    description: '涵盖工作区代码写改、底层自愈、隔离舱与运维探针特权',
    tools: [
      // 1. 本地代码精准写改
      { id: 'write', name: 'write (写入文件)', description: '新建或全量覆写工作区文件内容', categoryBadge: '代码写入' },
      { id: 'edit', name: 'edit (精准编辑)', description: '对指定文件执行唯一指纹锚点编辑', categoryBadge: '代码修改' },

      // 2. 编译与底座度量
      { id: 'openviking_dspy_compile', name: 'dspy_compile (DSPy编译)', description: '提示词强类型 DSPy 签名编译', categoryBadge: '提示词编译' },
      { id: 'openviking_vector_sync_metrics', name: 'vector_sync_metrics (同步度量)', description: '向量索引同步完成度与未索引积压检测', categoryBadge: '索引度量' },
      { id: 'openviking_skill_weight_tune', name: 'skill_weight_tune (权重调优)', description: '动态调优技能唤醒权重', categoryBadge: '技能生态' },

      // 3. 底座数据治理与消息自愈
      { id: 'forget', name: 'forget (永久遗忘)', description: '永久删除指定 URI 记忆资源 (高危)', categoryBadge: '记忆抹除' },
      { id: 'openviking_memory_purity_report', name: 'memory_purity_report (纯度报告)', description: '体外大脑记忆纯度评估与概念漂移审计', categoryBadge: '记忆审计' },
      { id: 'openviking_dlq_status', name: 'dlq_status (死信队列)', description: '查看死信队列积压与健康状态', categoryBadge: '系统队列' },
      { id: 'openviking_retry_dead_letter', name: 'retry_dead_letter (死信重试)', description: '重试失败的死信消息', categoryBadge: '故障自愈' },

      // 4. 全域自演进流水线
      { id: 'openviking_skill_evolution_pipeline', name: 'skill_evolution_pipeline (自演进流水线)', description: '技能自演进流水线执行与回滚', categoryBadge: '核心流水线' },

      // 5. 隔离舱与安全合规
      { id: 'openviking_privacy_quarantine', name: 'privacy_quarantine (隔离舱)', description: '敏感数据隔离舱封存与还原', categoryBadge: '凭证隔离' },
      { id: 'openviking_privacy_audit', name: 'privacy_audit (合规审计)', description: '合规安全审计流水追溯', categoryBadge: '安全审计' },

      // 6. 底层监听与硬件探针
      { id: 'list_watches', name: 'list_watches (订阅列表)', description: '查看自动刷新系统监听订阅', categoryBadge: '系统监听', requiredRole: 'admin' },
      { id: 'cancel_watch', name: 'cancel_watch (取消订阅)', description: '取消自动刷新系统监听订阅', categoryBadge: '系统监听', requiredRole: 'admin' },
      { id: 'add_resource', name: 'add_resource (挂载资源)', description: '异步向体外大脑挂载新资源', categoryBadge: '存储挂载' },
      { id: 'openviking_harness_probe', name: 'harness_probe (探针验证)', description: '探针物理验证', categoryBadge: '硬件探针' },
    ],
  },
]

export const ALL_TOOL_IDS = TOOL_CATEGORIES.flatMap((c) => c.tools.map((t) => t.id))

export const DEFAULT_TOOL_IDS = TOOL_CATEGORIES.flatMap((c) =>
  c.tools.filter((t) => t.defaultSelected).map((t) => t.id),
)

// 卫星工兵工具包 (使用者全量 - 31项)
export const SATELLITE_CONSUMER_TOOL_IDS =
  TOOL_CATEGORIES.find((c) => c.id === 'satellite')?.tools.map((t) => t.id) ?? []

// 中枢总控工具包 (使用者 + 运维特权 = 全量 47项)
export const MASTER_MAINTAINER_TOOL_IDS = ALL_TOOL_IDS

// 保持历史导出别名对齐
export const SATELLITE_TOOL_IDS = SATELLITE_CONSUMER_TOOL_IDS
export const CORE_MASTER_TOOL_IDS = MASTER_MAINTAINER_TOOL_IDS

/**
 * 官方标准工具包 (Tool Bundles) 定义
 */
export type ToolBundleId = 'satellite_consumer' | 'master_maintainer'

export type ToolBundle = {
  id: ToolBundleId
  name: string
  shortName: string
  roleTitle: string
  description: string
  toolIds: string[]
  recommendedFor: string
  highlightBadge: string
}

export const OFFICIAL_TOOL_BUNDLES: ToolBundle[] = [
  {
    id: 'satellite_consumer',
    name: '🛰️ 业务使用者工具包',
    shortName: '业务使用者包',
    roleTitle: '一线业务工兵 / 研发助手',
    description: '涵盖知识读写、代码分析、契约单测、工单流转与全球搜索等一线全套工具',
    toolIds: SATELLITE_CONSUMER_TOOL_IDS,
    recommendedFor: '适用于常规编程助手、业务自动化与各类一线任务工兵智能体',
    highlightBadge: '31 项业务工具',
  },
  {
    id: 'master_maintainer',
    name: '🧠 中枢运维者工具包',
    shortName: '中枢运维者包',
    roleTitle: '自治中枢 / 运维与总控大脑',
    description: '在业务工具基础上，追加工作区代码写改、底座探针自愈与集群底座运维特权',
    toolIds: MASTER_MAINTAINER_TOOL_IDS,
    recommendedFor: '适用于系统核心大脑、巡检自治与集群总控智能体',
    highlightBadge: '47 项全量特权',
  },
]

/**
 * 校验工具是否因当前所属用户角色权限不足而被置灰 (Disabled)
 */
export function isToolDisabledByRole(tool: ToolItem, userRole?: string): boolean {
  if (!tool.requiredRole) return false
  if (!userRole) return false
  const role = userRole.toLowerCase()
  if (role === 'root' || role === 'admin') return false
  return true
}

/**
 * DSH 官方 OpenViking 插件当前最新发布版本号 (SSOT)
 */
export const DSH_PLUGIN_VERSION = '1.5.0'
