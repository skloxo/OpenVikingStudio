/**
 * agent-tools.ts
 * 智能体工具池常量与场景化分类定义 (Tool ACL Matrix)
 * 100% 对齐 FastMCP 47 个全量物理工具 (SSOT)。
 *
 * 核心设计哲学：
 * 1. 分类基于「用户真实使用场景与智能体角色定位」：
 *    - 🛰️ 远程协同与日常感知 (Satellite Agent - 15项)
 *    - 🧠 中枢全栈与工程研发 (Core Master Agent - 17项)
 *    - 🛡️ 集群运维与高危自愈 (Cluster Ops & Governance - 15项)
 * 2. 标签表达「工具具体技术属性」 (categoryBadge: 记忆/工作区/AST/工单/压缩/隐私/运维)
 * 3. 权限继承「用户基础凭证角色」 (requiredRole: 普通 user 自动置灰，需 admin/root 解锁)
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
  id: 'satellite' | 'core_master' | 'cluster_ops'
  name: string
  description: string
  tools: ToolItem[]
}

export const TOOL_CATEGORIES: ToolCategory[] = [
  {
    id: 'satellite',
    name: '🛰️ 远程协同与日常感知 (卫星节点 / 随身协作)',
    description: '适用于 3070/Mac 远程节点、轻量 IDE 助手与结对助手，专注召回、沉淀与工单建卡',
    tools: [
      { id: 'find', name: 'find (语义召回)', description: '基于分层语义索引智能查找最相关记忆', categoryBadge: '记忆检索', defaultSelected: true },
      { id: 'search', name: 'search (精确检索)', description: '对记忆中枢进行关键词与过滤检索', categoryBadge: '记忆检索', defaultSelected: true },
      { id: 'read', name: 'read (读取记忆)', description: '读取特定记忆资源或文档的完整内容', categoryBadge: '记忆读取', defaultSelected: true },
      { id: 'remember', name: 'remember (长程沉淀)', description: '将结构化对话与重要知识写入长程记忆', categoryBadge: '记忆沉淀', defaultSelected: true },
      { id: 'health', name: 'health (服务探针)', description: '检测记忆引擎与向量数据库健康状态', categoryBadge: '探针检测' },
      { id: 'list', name: 'list (目录列举)', description: '列出 viking:// 目录结构条目', categoryBadge: '工作区' },
      { id: 'tree', name: 'tree (递归目录树)', description: '获取代码库或工作区的层级结构', categoryBadge: '工作区' },
      { id: 'grep', name: 'grep (正则匹配)', description: '在工作区文件中快速检索正则文本模式', categoryBadge: '工作区' },
      { id: 'glob', name: 'glob (文件通配)', description: '按文件名通配符扫描定位文件', categoryBadge: '工作区' },
      { id: 'zg_search', name: 'zg_search (AST检索)', description: '阿里 zg-grep 代码语义 AST 静态搜索', categoryBadge: '代码分析' },
      { id: 'openviking_file_task_card', name: 'file_task_card (自主建卡)', description: '智能体异常现场自主建卡上报', categoryBadge: 'AIFP工单', defaultSelected: true },
      { id: 'openviking_list_pending_cards', name: 'list_pending_cards (待办工单)', description: '查看待排期与未解决工单清单', categoryBadge: 'AIFP工单' },
      { id: 'openviking_active_notes_get', name: 'active_notes_get (获取约束)', description: '检索活跃里程碑与工作约束', categoryBadge: '上下文' },
      { id: 'openviking_history_search', name: 'history_search (历史对话检索)', description: 'FTS5 对话全文字词检索', categoryBadge: '对话记录' },
      { id: 'openviking_agent_sensors', name: 'agent_sensors (3D传感器)', description: 'Token SNR, P@5 召回率传感器', categoryBadge: '观测雷达' },
    ],
  },
  {
    id: 'core_master',
    name: '🧠 中枢全栈与工程研发 (总控大脑 / 全栈开发)',
    description: '适用于主力研发智能体，具备代码精准读写修改、AST 爆炸半径分析与上下文深度压缩能力',
    tools: [
      { id: 'write', name: 'write (写入文件)', description: '新建或全量覆写工作区文件内容', categoryBadge: '代码写入' },
      { id: 'edit', name: 'edit (精准编辑)', description: '对指定文件执行唯一指纹锚点编辑', categoryBadge: '代码修改' },
      { id: 'openviking_code_impact', name: 'code_impact (爆炸半径)', description: '查询表/接口反向依赖与爆炸半径', categoryBadge: 'AST分析' },
      { id: 'openviking_generate_contract_test', name: 'generate_contract_test (契约测试)', description: '由 AST 事实派生 pytest 测试脚手架', categoryBadge: 'AST测试' },
      { id: 'openviking_vector_sync_metrics', name: 'vector_sync_metrics (同步度量)', description: '向量索引同步完成度与未索引积压检测', categoryBadge: '索引度量' },
      { id: 'openviking_tokenshift_compress', name: 'tokenshift_compress (代码压缩)', description: 'TokenShift 源码 AST 折叠压缩', categoryBadge: '代码压缩' },
      { id: 'openviking_skill_zip', name: 'skill_zip (技能压缩)', description: '技能 0-rollout 契约级压缩', categoryBadge: '规约压缩' },
      { id: 'openviking_dspy_compile', name: 'dspy_compile (DSPy编译)', description: '提示词强类型 DSPy 签名编译', categoryBadge: '提示词编译' },
      { id: 'openviking_context_route', name: 'context_route (上下文路由)', description: '多模态上下文自适应分流与压缩', categoryBadge: '上下文' },
      { id: 'openviking_resolve_task_card', name: 'resolve_task_card (工单归档)', description: '闭环归档工单并绑定 Git Tag', categoryBadge: 'AIFP工单' },
      { id: 'openviking_task_cards_summary', name: 'task_cards_summary (工单总览)', description: '工单运转指标总览与趋势分析', categoryBadge: 'AIFP工单' },
      { id: 'openviking_skill_validate', name: 'skill_validate (契约校验)', description: '校验 SKILL.md YAML 头与规约契约', categoryBadge: '技能生态' },
      { id: 'openviking_skill_intent_match', name: 'skill_intent_match (意图匹配)', description: '自然语言意图匹配与冲突检测', categoryBadge: '技能生态' },
      { id: 'openviking_skill_judge', name: 'skill_judge (质量评分)', description: '技能 4 维质量评分与达标门禁', categoryBadge: '技能生态' },
      { id: 'openviking_skill_remediate', name: 'skill_remediate (自愈修复)', description: '技能缺陷诊断与自愈修复建议', categoryBadge: '技能生态' },
      { id: 'openviking_skill_weight_tune', name: 'skill_weight_tune (权重调优)', description: '动态调优技能唤醒权重', categoryBadge: '技能生态' },
      { id: 'openviking_active_notes_update', name: 'active_notes_update (更新约束)', description: '更新当前目标与工作约束', categoryBadge: '上下文' },
    ],
  },
  {
    id: 'cluster_ops',
    name: '🛡️ 集群运维与高危自愈 (系统治理 / 管理特权)',
    description: '适用于系统管理员智能体，涉及死信队列自愈、合规审计与全域流水线，受用户凭证强管控',
    tools: [
      { id: 'forget', name: 'forget (永久遗忘)', description: '永久删除指定 URI 记忆资源', categoryBadge: '记忆抹除', requiredRole: 'admin' },
      { id: 'openviking_memory_purity_report', name: 'memory_purity_report (纯度报告)', description: '体外大脑记忆纯度评估与概念漂移审计', categoryBadge: '记忆审计' },
      { id: 'openviking_dlq_status', name: 'dlq_status (死信队列)', description: '查看死信队列积压与健康', categoryBadge: '系统队列', requiredRole: 'admin' },
      { id: 'openviking_retry_dead_letter', name: 'retry_dead_letter (死信重试)', description: '重试失败的死信消息', categoryBadge: '故障自愈', requiredRole: 'admin' },
      { id: 'openviking_skill_publish', name: 'skill_publish (技能发布)', description: '原子化发布并上线新技能', categoryBadge: '技能上线', requiredRole: 'admin' },
      { id: 'openviking_skill_evolution_pipeline', name: 'skill_evolution_pipeline (自演进流水线)', description: '技能自演进流水线执行与回滚', categoryBadge: '核心流水线', requiredRole: 'admin' },
      { id: 'openviking_privacy_mask', name: 'privacy_mask (脱敏过滤)', description: '脱敏敏感凭据、Token 与私有端点', categoryBadge: '隐私脱敏' },
      { id: 'openviking_privacy_quarantine', name: 'privacy_quarantine (隔离舱)', description: '敏感数据隔离舱封存与还原', categoryBadge: '凭证隔离', requiredRole: 'admin' },
      { id: 'openviking_privacy_audit', name: 'privacy_audit (合规审计)', description: '合规安全审计流水追溯', categoryBadge: '安全审计', requiredRole: 'admin' },
      { id: 'openviking_valet_handover', name: 'valet_handover (泊车消化)', description: '泊车管家异步大文档深度消化', categoryBadge: '异步批处理' },
      { id: 'openviking_valet_ticket_status', name: 'valet_ticket_status (泊车进度)', description: '查看泊车管家消化与入库进度', categoryBadge: '异步批处理' },
      { id: 'list_watches', name: 'list_watches (订阅列表)', description: '查看自动刷新订阅', categoryBadge: '系统监听', requiredRole: 'admin' },
      { id: 'cancel_watch', name: 'cancel_watch (取消订阅)', description: '取消自动刷新订阅', categoryBadge: '系统监听', requiredRole: 'admin' },
      { id: 'add_resource', name: 'add_resource (挂载资源)', description: '异步向体外大脑挂载新资源', categoryBadge: '存储挂载', requiredRole: 'admin' },
      { id: 'openviking_harness_probe', name: 'harness_probe (探针验证)', description: '探针物理验证', categoryBadge: '硬件探针' },
    ],
  },
]

export const ALL_TOOL_IDS = TOOL_CATEGORIES.flatMap((c) => c.tools.map((t) => t.id))

export const DEFAULT_TOOL_IDS = TOOL_CATEGORIES.flatMap((c) =>
  c.tools.filter((t) => t.defaultSelected).map((t) => t.id),
)

export const SATELLITE_TOOL_IDS = TOOL_CATEGORIES.find((c) => c.id === 'satellite')?.tools.map((t) => t.id) ?? []

export const CORE_MASTER_TOOL_IDS = [
  ...SATELLITE_TOOL_IDS,
  ...(TOOL_CATEGORIES.find((c) => c.id === 'core_master')?.tools.map((t) => t.id) ?? []),
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
