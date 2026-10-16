/**
 * agent-tools.ts
 * 智能体工具池常量、角色工具包 (Tool Bundles) 与权限管理 (Tool ACL Matrix)
 * 100% 对齐 FastMCP 58 个全量物理工具 (SSOT)。
 *
 * 核心设计哲学 (第一性原理)：
 * 1. 角色分明：
 *    - 🛰️ 卫星工兵 (Satellite Consumer)：纯粹的使用者角色 (31项工具)，负责知识读写、代码阅读/AST/TDD、工单闭环、技能自上架与异步消化。
 *    - 🧠 中枢总控 (Master Maintainer)：即是使用者又是运维者 (58项全量工具)，涵盖使用者全量武器 + 代码写改、死信自愈、安全隔离与底座治理。
 * 2. 工具包直选：一键点选工具包卡片，免去 58 个复选框逐一勾选的繁琐认知负担。
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
    name: '🛰️ 核心战地工具池 (34 项)',
    description: '涵盖长程记忆、工作区 AST、1214技能感知、工单吹哨与大文档代客泊车 (面向全量研发工兵)',
    tools: [
      // 1. 记忆中枢 (8 项)
      { id: 'find', name: 'find (语义召回)', description: '基于向量与分词的混合记忆语义检索', categoryBadge: '记忆中枢', defaultSelected: true },
      { id: 'search', name: 'search (精确检索)', description: '高级混合关键词与过滤检索引擎', categoryBadge: '记忆中枢', defaultSelected: true },
      { id: 'read', name: 'read (读取记忆)', description: '深读知识全文与 L2 正文切片', categoryBadge: '记忆中枢', defaultSelected: true },
      { id: 'write', name: 'write (长程沉淀)', description: '将重要记忆与结构化事实写入长程记忆', categoryBadge: '记忆中枢', defaultSelected: true },
      { id: 'store', name: 'store (原子持久化)', description: '原子持久化事实结晶与关系拓扑', categoryBadge: '记忆中枢', defaultSelected: true },
      { id: 'link', name: 'link (实体双向关联)', description: '关联建立两个知识实体之间的双向语义链接', categoryBadge: '记忆中枢' },
      { id: 'get_relations', name: 'get_relations (拓扑反查)', description: '查询知识实体的所有拓扑关联与反向引用', categoryBadge: '记忆中枢' },
      { id: 'unlink', name: 'unlink (解除实体关联)', description: '安全解除知识实体之间的语义关联', categoryBadge: '记忆中枢' },

      // 2. 代码与工作区深度 AST (11 项)
      { id: 'ls', name: 'ls (目录列举)', description: '列出当前工作区目录结构条目', categoryBadge: '工作区AST' },
      { id: 'tree', name: 'tree (递归目录树)', description: '获取代码库或工作区的层级结构树', categoryBadge: '工作区AST' },
      { id: 'grep', name: 'grep (正则匹配)', description: '在工作区文件中快速正则检索文本模式', categoryBadge: '工作区AST' },
      { id: 'glob', name: 'glob (文件通配)', description: '按文件名通配符模式快速定位文件', categoryBadge: '工作区AST' },
      { id: 'openviking_code_outline', name: 'code_outline (AST大纲)', description: '代码 AST 语法大纲提取', categoryBadge: '工作区AST' },
      { id: 'openviking_code_search', name: 'code_search (语义搜索)', description: '代码语义符号深度检索', categoryBadge: '工作区AST' },
      { id: 'openviking_code_expand', name: 'code_expand (按需展开)', description: '代码上下文智能折叠与按需展开', categoryBadge: '工作区AST' },
      { id: 'openviking_diff', name: 'diff (差异对比)', description: '文件与代码版本差异对比分析', categoryBadge: '工作区AST' },
      { id: 'openviking_smart_read', name: 'smart_read (分层深读)', description: '分层自适应智能知识提取与概括', categoryBadge: '工作区AST' },
      { id: 'openviking_tokenshift_compress', name: 'tokenshift_compress (AST折叠)', description: 'TokenShift 源码 AST 折叠压缩，节约远程传输', categoryBadge: '工作区AST' },
      { id: 'openviking_tag', name: 'tag (标签标注)', description: '资源与代码标签标注及分类检索', categoryBadge: '工作区AST' },

      // 3. 技能中心感知与发布 (6 项 - 锚定 1214 全域技能)
      { id: 'openviking_skills', name: 'skills (技能总览)', description: '知识中枢 1214 全量技能状态与分类总览', categoryBadge: '技能中心', defaultSelected: true },
      { id: 'openviking_audit_skills', name: 'audit_skills (技能审计)', description: '知识中枢技能规范静态安全审计', categoryBadge: '技能中心' },
      { id: 'openviking_auto_onboard_skills', name: 'auto_onboard_skills (技能入库)', description: '自动化技能入库校验与发布上架', categoryBadge: '技能中心' },
      { id: 'openviking_get_onboard_queue_status', name: 'get_onboard_queue_status (入库队列)', description: '技能入库队列状态与审批进展查询', categoryBadge: '技能中心' },
      { id: 'openviking_fix_skill', name: 'fix_skill (技能修复)', description: '技能缺陷自动化诊断与一键修复', categoryBadge: '技能中心' },
      { id: 'openviking_record_evolution_lesson', name: 'record_lesson (经验入脑)', description: '踩坑事实与自演进经验入脑存盘', categoryBadge: '技能中心', defaultSelected: true },

      // 4. 工单自主建卡与哨兵 (4 项 - 异常自主建卡吹哨)
      { id: 'openviking_file_task_card', name: 'file_task_card (自主建卡)', description: '智能体异常现场自主建卡吹哨上报', categoryBadge: 'AIFP工单', defaultSelected: true },
      { id: 'openviking_list_pending_cards', name: 'list_pending_cards (待办工单)', description: '查看待排期与未解决工单清单', categoryBadge: 'AIFP工单' },
      { id: 'openviking_resolve_task_card', name: 'resolve_task_card (工单归档)', description: '闭环归档工单并绑定 Git Tag', categoryBadge: 'AIFP工单' },
      { id: 'openviking_task_cards_summary', name: 'task_cards_summary (工单总览)', description: '工单运转指标总览与趋势分析', categoryBadge: 'AIFP工单' },

      // 5. 超大文档代客泊车 (2 项 - 50MB+ 异步批处理防 504)
      { id: 'openviking_valet_handover', name: 'valet_handover (泊车消化)', description: '泊车管家 50MB+ 超大文档异步离线消化', categoryBadge: '泊车管家' },
      { id: 'openviking_valet_ticket_status', name: 'valet_ticket_status (泊车进度)', description: '查看泊车管家消化与入库进度', categoryBadge: '泊车管家' },

      // 6. 安全脱敏与传感器 (3 项)
      { id: 'openviking_privacy', name: 'privacy (隐私脱敏)', description: '脱敏敏感凭据、Token 与私有端点', categoryBadge: '安全脱敏' },
      { id: 'openviking_ping', name: 'ping (毫秒测活)', description: '检测体外大脑与核心服务毫秒级连通性', categoryBadge: '探针雷达' },
      { id: 'openviking_harness_stats', name: 'harness_stats (雷达指标)', description: 'Token SNR、P@5 召回率与模型性能统计', categoryBadge: '探针雷达' },
    ],
  },
  {
    id: 'master_ops',
    name: '🛡️ 系统运维治理特权工具池 (17 项)',
    description: '涵盖存储资源管理、文件重定位、死信自愈、系统监听与底座体检 (授权给后台专用运维 Agent / 巡检 Engine)',
    tools: [
      // 1. 存储与资源管理 (5 项)
      { id: 'openviking_add_resource', name: 'add_resource (挂载资源)', description: '异步向体外大脑挂载新资源', categoryBadge: '存储资源' },
      { id: 'openviking_list_resources', name: 'list_resources (资源列表)', description: '列出已登记的体外大脑物理资源', categoryBadge: '存储资源' },
      { id: 'openviking_delete_resource', name: 'delete_resource (注销资源)', description: '安全注销指定体外大脑资源', categoryBadge: '存储资源', requiredRole: 'admin' },
      { id: 'openviking_reindex', name: 'reindex (全盘重索引)', description: '触发知识与向量库全盘或增量重索引', categoryBadge: '存储资源' },
      { id: 'openviking_commit', name: 'commit (版本快照)', description: '工作区变更版本快照物理提交', categoryBadge: '存储资源' },

      // 2. 文件与目录写改 (3 项)
      { id: 'openviking_mv', name: 'mv (安全移动)', description: '底层文件或目录安全原子重定位', categoryBadge: '底层写改', requiredRole: 'admin' },
      { id: 'openviking_rename', name: 'rename (安全重命名)', description: '知识库文件或目录重命名', categoryBadge: '底层写改', requiredRole: 'admin' },
      { id: 'openviking_webdav_info', name: 'webdav_info (WebDAV配额)', description: 'WebDAV 协议挂载端点与配额信息', categoryBadge: '底层写改' },

      // 3. 系统自愈与纯度度量 (3 项)
      { id: 'openviking_dspy_compile', name: 'dspy_compile (DSPy编译)', description: '提示词强类型 DSPy 签名编译与调优', categoryBadge: '系统自愈' },
      { id: 'openviking_memory_purity_report', name: 'memory_purity_report (纯度报告)', description: '体外大脑记忆纯度评估与概念漂移审计', categoryBadge: '系统自愈' },
      { id: 'openviking_retry_dead_letter', name: 'retry_dead_letter (死信重试)', description: '死信队列消息自愈重试与故障排查', categoryBadge: '系统自愈' },

      // 4. 系统监听 (3 项)
      { id: 'openviking_list_watches', name: 'list_watches (订阅列表)', description: '查看自动刷新系统监听订阅', categoryBadge: '系统监听', requiredRole: 'admin' },
      { id: 'openviking_cancel_watch', name: 'cancel_watch (取消订阅)', description: '取消自动刷新系统监听订阅', categoryBadge: '系统监听', requiredRole: 'admin' },
      { id: 'openviking_manage_watch', name: 'manage_watch (管理监听)', description: '动态更新或调整系统监听器参数', categoryBadge: '系统监听', requiredRole: 'admin' },

      // 5. 服务控制与体检 (3 项)
      { id: 'openviking_server_control', name: 'server_control (服务控制)', description: '核心中枢服务生命周期与优雅重启控制', categoryBadge: '服务控制', requiredRole: 'admin' },
      { id: 'openviking_server_init', name: 'server_init (引导初始化)', description: '底座存储引擎与数据表引导初始化', categoryBadge: '服务控制', requiredRole: 'admin' },
      { id: 'openviking_server_doctor', name: 'server_doctor (深度体检)', description: '全系统底层硬件与数据库深度体检诊断', categoryBadge: '服务控制' },
    ],
  },
]

export const ALL_TOOL_IDS = TOOL_CATEGORIES.flatMap((c) => c.tools.map((t) => t.id))

export const DEFAULT_TOOL_IDS = TOOL_CATEGORIES.flatMap((c) =>
  c.tools.filter((t) => t.defaultSelected).map((t) => t.id),
)

// 核心战地工具包 (34项)
export const SATELLITE_CONSUMER_TOOL_IDS =
  TOOL_CATEGORIES.find((c) => c.id === 'satellite')?.tools.map((t) => t.id) ?? []

// 系统运维治理特权工具包 (17项专属特权)
export const MASTER_OPS_TOOL_IDS =
  TOOL_CATEGORIES.find((c) => c.id === 'master_ops')?.tools.map((t) => t.id) ?? []

// 中枢总控工具包 (战地 34项 + 运维 17项 = 51项全量核心)
export const MASTER_MAINTAINER_TOOL_IDS = ALL_TOOL_IDS

// 保持历史导出别名对齐
export const SATELLITE_TOOL_IDS = SATELLITE_CONSUMER_TOOL_IDS
export const CORE_MASTER_TOOL_IDS = MASTER_MAINTAINER_TOOL_IDS

/**
 * Hook 核心生命周期与被动注入控制定义 (3 项)
 */
export type HookCapabilityItem = {
  id: string
  name: string
  timing: string
  description: string
}

export const HOOK_CAPABILITIES: HookCapabilityItem[] = [
  {
    id: 'pre_prompt_recall',
    name: '🧠 先验记忆自动预取',
    timing: 'Prompt 前置',
    description: '模型组装提示词前，自动从体外大脑检索相关经验并注入 System Prompt',
  },
  {
    id: 'post_turn_capture',
    name: '📥 轮次经验自动沉淀',
    timing: '对话后置',
    description: '单轮会话结束后，自动捕获助手输出的新结论与踩坑事实并入库',
  },
  {
    id: 'pre_tool_guard',
    name: '🛡️ 工具前置安全守卫',
    timing: '工具拦截',
    description: '工具执行前拦截敏感 Key 泄露、检测目标路径越权，确保安全沙箱',
  },
]

/**
 * 插件包关联技能 (Plugin Bundled Skills) 数据模型
 */
export type PluginSkillItem = {
  id: string
  name: string
  category: string
  description: string
}

export type PluginBundleMeta = {
  pluginName: string
  version: string
  skills: PluginSkillItem[]
  description: string
}

export const DSH_PLUGIN_VERSION = '2.0.11'

export const OFFICIAL_PLUGIN_META: PluginBundleMeta = {
  pluginName: 'dsh-plugin-openviking',
  version: DSH_PLUGIN_VERSION,
  skills: [],
  description: '专注于 FastMCP 工具箱桥接与 Hook 前置预取/后置沉淀守卫，未随包附带独立技能',
}

export const COMPANION_SKILLS: PluginSkillItem[] = OFFICIAL_PLUGIN_META.skills

/**
 * 官方标准能力包 (Bundles) 定义
 */
export type ToolBundleId = 'satellite_consumer' | 'master_ops'

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
    name: '🛰️ 核心战地工具包',
    shortName: '战地工兵包',
    roleTitle: '战地旗舰 / 研发工兵',
    description: '涵盖知识读写、长程记忆、工作区 AST、技能中心感知、工单吹哨与泊车管家 (面向全量普通 Agent)',
    toolIds: SATELLITE_CONSUMER_TOOL_IDS,
    recommendedFor: '适用于常规业务编程助手、脚本自动化与各类一线任务工兵智能体',
    highlightBadge: '34 项战地武器',
  },
  {
    id: 'master_ops',
    name: '🛡️ 系统运维特权工具包',
    shortName: '运维特权包',
    roleTitle: '哨兵治理 / 运维特权',
    description: '涵盖底层存储挂载、文件重定位、死信自愈重试、系统监听订阅与底座体检',
    toolIds: MASTER_OPS_TOOL_IDS,
    recommendedFor: '适用于后台自动化运维智能体 (如 24 小时哨兵 Sentinel) 与巡检 Engine',
    highlightBadge: '17 项运维特权',
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

export const BIG_THREE_PLUGIN_MAPPINGS: Record<string, { name: string; tools: string[] }> = {
  'openviking-memory': {
    name: 'OpenViking 核心记忆与代码战地',
    tools: [
      'find', 'search', 'read', 'write', 'store', 'link', 'get_relations', 'unlink',
      'ls', 'tree', 'grep', 'glob', 'openviking_code_outline', 'openviking_code_search',
      'openviking_code_expand', 'openviking_diff', 'openviking_smart_read', 'openviking_tokenshift_compress',
      'openviking_tag', 'openviking_skills', 'openviking_audit_skills', 'openviking_auto_onboard_skills',
      'openviking_get_onboard_queue_status', 'openviking_fix_skill', 'openviking_record_evolution_lesson',
      'openviking_file_task_card', 'openviking_list_pending_cards', 'openviking_resolve_task_card',
      'openviking_task_cards_summary', 'openviking_valet_handover', 'openviking_valet_ticket_status',
      'openviking_privacy', 'openviking_ping', 'openviking_harness_stats',
    ],
  },
  'openviking-ops': {
    name: 'OpenViking 系统运维治理',
    tools: [
      'openviking_add_resource', 'openviking_list_resources', 'openviking_delete_resource',
      'openviking_reindex', 'openviking_commit', 'openviking_mv', 'openviking_rename',
      'openviking_webdav_info', 'openviking_dspy_compile', 'openviking_memory_purity_report',
      'openviking_retry_dead_letter', 'openviking_list_watches', 'openviking_cancel_watch',
      'openviking_manage_watch', 'openviking_server_control', 'openviking_server_init',
      'openviking_server_doctor',
    ],
  },
  'keepass-vault': {
    name: 'KeePass 凭据保险箱',
    tools: [
      'keepass_search', 'keepass_get', 'keepass_status', 'keepass_add', 'keepass_edit',
      'keepass_rm', 'keepass_list_tree', 'keepass_analyze', 'keepass_export_attachment',
    ],
  },
  'network-search': {
    name: '联网搜索与采集聚合网关',
    tools: [
      'web_search', 'search_neural', 'search_qna', 'search_deep', 'search_code_context',
      'search_similar_repos', 'map_site', 'extract_urls', 'tavily_crawl', 'crawl_local',
      'deep_research', 'search_vertical_expert', 'benchmark_needle',
    ],
  },
  dify: {
    name: 'Dify 智能体与工作流中枢',
    tools: [
      'dify_status', 'dify_list_apps', 'dify_get_app', 'dify_export_dsl', 'dify_import_dsl',
      'dify_delete_app', 'dify_run_workflow', 'dify_list_datasets', 'dify_create_dataset',
      'dify_delete_dataset', 'dify_search_dataset', 'dify_list_model_providers',
    ],
  },
  'cpa-squad': {
    name: 'CPA 跨模型算力协同',
    tools: ['openviking_cpa_consult', 'openviking_cpa_fanout'],
  },
  'fleet-mesh': {
    name: '卫星集群同频运维',
    tools: ['openviking_fleet_check', 'openviking_fleet_sync'],
  },
}

export function derivePluginGrantsFromTools(selectedTools: string[]): Record<string, string[]> {
  const selectedSet = new Set(selectedTools)
  const grants: Record<string, string[]> = {}

  for (const [pluginId, meta] of Object.entries(BIG_THREE_PLUGIN_MAPPINGS)) {
    const granted = meta.tools.filter((t) => selectedSet.has(t))
    if (granted.length > 0) {
      grants[pluginId] = granted
    }
  }

  const allMappedTools = new Set(
    Object.values(BIG_THREE_PLUGIN_MAPPINGS).flatMap((m) => m.tools)
  )
  const unmapped = selectedTools.filter((t) => !allMappedTools.has(t))
  if (unmapped.length > 0) {
    grants['custom'] = unmapped
  }

  return grants
}

export function deriveToolsFromPluginGrants(grants: Record<string, string[]>): string[] {
  const tools = Object.values(grants).flatMap((tList) => tList)
  return Array.from(new Set(tools))
}
