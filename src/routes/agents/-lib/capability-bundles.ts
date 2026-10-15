/**
 * capability-bundles.ts
 * 智能体中心角色工具包 (Capability Bundles) 与三大官方 Quad 插件规约单一真实源 (SSOT)。
 *
 * 核心架构哲学：
 * 1. 客户端通信桥梁 (dsh-plugin-openviking) 独立打包托管，供外部智能体安装通道；
 * 2. 服务端真实三大官方标杆 Quad 插件 (The Big Three)：
 *    - openviking-memory (47工具, 3 Hook, 记忆检索与代码感知)；
 *    - network-search (12工具, 3 Hook, 26-Key 轮询与全网采集)；
 *    - keepass-vault (8工具, 1 Hook, 密码凭据单一真实源)；
 * 3. “四位一体 (Quad)”架构：每个插件均具备【① 技能导轨 + ② Hook 拦截 + ③ MCP 角色包 + ④ GUI 视窗】；
 * 4. 工具包化：将 67 项微观 MCP 工具按角色整合为若干直观工具包，降低逐一勾选的心智负担；
 * 5. Hook 守卫：每个插件提供独立的先验拦截 Hook 守卫开关。
 */

export type ToolItem = {
  id: string
  name: string
  description: string
  isDangerous?: boolean
}

export type ToolBundle = {
  id: string
  name: string
  roleType: 'consumer' | 'ops'
  description: string
  icon: string
  requiredRole?: 'admin' | 'root'
  toolIds: string[]
  tools: ToolItem[]
}

export type HookItem = {
  id: string
  name: string
  description: string
  triggerEvent: string
  defaultEnabled?: boolean
}

export type PluginSkill = {
  name: string
  chapters: { title: string; summary: string }[]
  summary: string
}

export type PluginGui = {
  name: string
  cloudConfigSummary: string
  clientDialogSummary: string
}

export type PluginCapability = {
  pluginId: string
  name: string
  version: string
  description: string
  totalTools: number
  // 四位一体固定四大支柱
  bundles: ToolBundle[] // 1. MCP 工具包
  hooks: HookItem[] // 2. 钩子 (Hook)
  skill?: PluginSkill // 3. 技能 (Skill)
  gui?: PluginGui // 4. 插件的 GUI
}

export type ClientBridgePackageInfo = {
  packageName: string
  version: string
  packageUrl: string
  installCommand: string
}

/**
 * 实时从服务端动态获取最新客户端通道桥包信息 (单一真实源 SSOT)。
 * 坚决杜绝依赖静态编译常量或页面加载初期的过时缓存。
 */
export async function fetchLatestClientBridge(
  networkMode: 'local' | 'public' = 'public'
): Promise<ClientBridgePackageInfo> {
  const baseUrl = networkMode === 'local' ? 'http://127.0.0.1:1933' : 'https://vk.tide.red'
  try {
    const timestamp = Date.now()
    const res = await fetch(`/api/v1/plugins/bridge/client-package?_t=${timestamp}`, {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        Pragma: 'no-cache',
      },
    })
    if (res.ok) {
      const data = await res.json()
      const ver = data?.result?.version || '1.5.2'
      const pkgName = data?.result?.package_name || 'dsh-plugin-openviking'
      const pkgFile = data?.result?.package_file || `${pkgName}-${ver}.tgz`
      const pkgUrl = data?.result?.package_url || `${baseUrl}/studio/${pkgFile}`
      const installCmd = data?.result?.install_command || `npm install ${pkgUrl}`
      return {
        packageName: pkgName,
        version: ver,
        packageUrl: pkgUrl,
        installCommand: installCmd,
      }
    }
  } catch (err) {
    console.error('Failed to fetch latest client bridge package info:', err)
  }
  const fallbackUrl = `${baseUrl}/studio/dsh-plugin-openviking-1.5.4.tgz`
  return {
    packageName: 'dsh-plugin-openviking',
    version: '1.5.4',
    packageUrl: fallbackUrl,
    installCommand: `npm install ${fallbackUrl}`,
  }
}

export const CLIENT_BRIDGE_META = {
  packageName: 'dsh-plugin-openviking',
  version: '1.5.4',
  downloadUrl: 'https://vk.tide.red/studio/dsh-plugin-openviking-1.5.4.tgz',
  description: '轻量客户端通信通道桥梁。安装到智能体本地环境后，通过 UserKey + AgentID 握手与服务端中心化三大标杆插件 (记忆/搜索/凭据) 动态交互。',
  installCommand: 'npm install https://vk.tide.red/studio/dsh-plugin-openviking-1.5.4.tgz',
}

export const PLUGIN_CAPABILITIES: PluginCapability[] = [
  // 1. VK 核心记忆插件 (四位一体标杆插件)
  {
    pluginId: 'openviking-memory',
    name: 'OpenViking 核心记忆插件',
    version: '1.5.0',
    description: '体外大脑记忆语义检索、代码感知、上下文路由与经验沉淀核心',
    totalTools: 47,
    skill: {
      name: 'openviking-memory',
      summary: '指导 Agent 开局主动向体外记忆检索、解决复杂难题后自动沉淀教训的标准技能。',
      chapters: [
        { title: '第 1 章：体外长程记忆主动检索', summary: '开局静默调用 find / search 召回匹配知识，绝不裸跑盲目猜测。' },
        { title: '第 2 章：踩坑教训提纯沉淀', summary: '解决 Bug 后自动调用 record_lesson 写入体外大脑，形成跨会话智力复利。' },
        { title: '第 3 章：代码感知与影响面分析', summary: '重构前调用 code_outline 与 code_impact 精确圈定变更爆炸半径。' },
      ],
    },
    gui: {
      name: '全景记忆大盘与规则中枢',
      cloudConfigSummary: '云端控制台直接提供知识库层级树浏览、记忆节点检索、FastMCP 工具授权、探针状态监测与沙箱隔离规则。',
      clientDialogSummary: '在 Agent 客户端环境以纯文本/引用标注形式透明呈现召回的记忆片段与关联知识卡片。',
    },
    hooks: [
      { id: 'ov_pre_invocation', name: '跨会话前置记忆预取', triggerEvent: 'before_prompt', description: '提问前静默召回匹配记忆并注入 Prompt 顶部，零 Token 机器级守护', defaultEnabled: true },
      { id: 'ov_lesson_crystallizer', name: '踩坑经验自动萃取', triggerEvent: 'after_response', description: '会话解决复杂 Bug 后自动沉淀 Evolution Lesson 入库', defaultEnabled: true },
      { id: 'ov_sandbox_guard', name: '特权沙箱安全守卫', triggerEvent: 'before_tool', description: '高危写操作与越权执行毫秒级安全阻断', defaultEnabled: true },
    ],
    bundles: [
      // 角色工具包 1：业务使用者工具包 (31 项工具，卫星/通用业务 Agent 专属)
      {
        id: 'memory-consumer',
        name: '业务使用者工具包',
        roleType: 'consumer',
        description: '通用业务/卫星智能体专属日常工具集 (检索、深读、写入、代码感知、工单协同与自愈)',
        icon: 'bot',
        toolIds: [
          'find', 'search', 'read', 'openviking_history_search', 'openviking_agent_sensors',
          'remember', 'openviking_active_notes_get', 'openviking_active_notes_update', 'openviking_context_route', 'openviking_valet_handover', 'openviking_valet_ticket_status',
          'grep', 'glob', 'tree', 'list', 'zg_search', 'openviking_code_impact', 'openviking_tokenshift_compress', 'openviking_generate_contract_test',
          'openviking_skill_validate', 'openviking_skill_judge', 'openviking_skill_remediate', 'openviking_skill_zip', 'openviking_skill_intent_match', 'openviking_skill_publish',
          'openviking_file_task_card', 'openviking_list_pending_cards', 'openviking_resolve_task_card', 'openviking_task_cards_summary', 'health', 'openviking_privacy_mask',
        ],
        tools: [
          { id: 'find', name: 'find', description: '分层语义混合记忆向量检索' },
          { id: 'search', name: 'search', description: '高级混合关键词过滤检索' },
          { id: 'read', name: 'read', description: '深读知识全文与 L2 正文切片' },
          { id: 'openviking_history_search', name: 'history_search', description: 'FTS5 全文对话字词召回' },
          { id: 'openviking_agent_sensors', name: 'agent_sensors', description: 'Token SNR 与 P@5 传感器' },
          { id: 'remember', name: 'remember', description: '将结构化对话与知识写入长程记忆' },
          { id: 'openviking_active_notes_get', name: 'active_notes_get', description: '检索活跃里程碑与工作约束' },
          { id: 'openviking_active_notes_update', name: 'active_notes_update', description: '更新当前工作目标与约束' },
          { id: 'openviking_context_route', name: 'context_route', description: '多模态上下文自适应分流' },
          { id: 'openviking_valet_handover', name: 'valet_handover', description: '泊车管家异步大文档深度消化' },
          { id: 'openviking_valet_ticket_status', name: 'valet_ticket_status', description: '查看泊车管家消化入库进度' },
          { id: 'list', name: 'list', description: '列出 viking:// 目录条目' },
          { id: 'tree', name: 'tree', description: '获取代码库层级目录结构' },
          { id: 'grep', name: 'grep', description: '工作区正则文本模式检索' },
          { id: 'glob', name: 'glob', description: '通配符快速定位文件' },
          { id: 'zg_search', name: 'zg_search', description: '阿里 zg-grep 代码语义 AST 搜索' },
          { id: 'openviking_code_impact', name: 'code_impact', description: 'AST 影响面与爆炸半径分析' },
          { id: 'openviking_tokenshift_compress', name: 'tokenshift_compress', description: 'TokenShift 源码 AST 折叠压缩' },
          { id: 'openviking_generate_contract_test', name: 'generate_contract_test', description: 'AST 事实派生契约测试用例' },
          { id: 'openviking_skill_validate', name: 'skill_validate', description: '校验 YAML 头与规约契约合法性' },
          { id: 'openviking_skill_judge', name: 'skill_judge', description: '技能 4 维质量评分与门禁' },
          { id: 'openviking_skill_remediate', name: 'skill_remediate', description: '技能缺陷诊断与自愈建议' },
          { id: 'openviking_skill_zip', name: 'skill_zip', description: '技能 0-rollout 契约级压缩' },
          { id: 'openviking_skill_intent_match', name: 'skill_intent_match', description: '自然语言意图匹配与冲突检测' },
          { id: 'openviking_skill_publish', name: 'skill_publish', description: '工兵技能成果发布至体外大脑' },
          { id: 'openviking_file_task_card', name: 'file_task_card', description: '智能体异常现场自主建卡上报' },
          { id: 'openviking_list_pending_cards', name: 'list_pending_cards', description: '查看待办与未解决工单清单' },
          { id: 'openviking_resolve_task_card', name: 'resolve_task_card', description: '闭环归档工单并绑定 Git Tag' },
          { id: 'openviking_task_cards_summary', name: 'task_cards_summary', description: '工单运转指标总览与趋势' },
          { id: 'health', name: 'health', description: '记忆引擎健康探针检测' },
          { id: 'openviking_privacy_mask', name: 'privacy_mask', description: '脱敏凭据Token与私有端点' },
        ],
      },
      // 角色工具包 2：中枢运维特权工具包 (16 项工具，主控/系统管理员 Agent 专属)
      {
        id: 'memory-ops',
        name: '中枢运维特权工具包',
        roleType: 'ops',
        description: '主控指挥官与超级管理员专属高危特权工具集 (文件写改、高危删除、DSPy、死信与隔离舱)',
        icon: 'shield-alert',
        requiredRole: 'admin',
        toolIds: [
          'write', 'edit', 'forget', 'openviking_dspy_compile', 'openviking_vector_sync_metrics',
          'openviking_skill_weight_tune', 'openviking_memory_purity_report', 'openviking_dlq_status',
          'openviking_retry_dead_letter', 'openviking_skill_evolution_pipeline', 'openviking_privacy_quarantine',
          'openviking_privacy_audit', 'list_watches', 'cancel_watch', 'add_resource', 'openviking_harness_probe',
        ],
        tools: [
          { id: 'write', name: 'write', description: '新建或全量覆写工作区文件', isDangerous: true },
          { id: 'edit', name: 'edit', description: '执行唯一指纹锚点编辑', isDangerous: true },
          { id: 'forget', name: 'forget', description: '永久删除记忆资源 (高危)', isDangerous: true },
          { id: 'openviking_dspy_compile', name: 'dspy_compile', description: '提示词 DSPy 签名编译' },
          { id: 'openviking_vector_sync_metrics', name: 'vector_sync_metrics', description: '向量索引同步度量' },
          { id: 'openviking_skill_weight_tune', name: 'skill_weight_tune', description: '动态调优技能唤醒权重' },
          { id: 'openviking_memory_purity_report', name: 'memory_purity_report', description: '概念漂移与记忆纯度审计' },
          { id: 'openviking_dlq_status', name: 'dlq_status', description: '查看死信队列积压状态' },
          { id: 'openviking_retry_dead_letter', name: 'retry_dead_letter', description: '重试失败死信消息' },
          { id: 'openviking_skill_evolution_pipeline', name: 'skill_evolution_pipeline', description: '自演进流水线执行' },
          { id: 'openviking_privacy_quarantine', name: 'privacy_quarantine', description: '敏感数据隔离舱封存' },
          { id: 'openviking_privacy_audit', name: 'privacy_audit', description: '合规安全审计流水追溯' },
          { id: 'list_watches', name: 'list_watches', description: '查看自动刷新系统监听' },
          { id: 'cancel_watch', name: 'cancel_watch', description: '取消自动刷新监听订阅' },
          { id: 'add_resource', name: 'add_resource', description: '挂载外部新知识资源' },
          { id: 'openviking_harness_probe', name: 'harness_probe', description: '硬件与驱动探针验证' },
        ],
      },
    ],
  },

  // 2. 联网搜索与网页采集插件 (12 项 MCP 工具 + 3 项 Hook)
  {
    pluginId: 'network-search',
    name: '联网搜索与采集插件',
    version: '1.1.0',
    description: '3家在线矩阵 (26-Key 轮询) + 2项本地服务调度与 45天流水账滚动归档',
    totalTools: 12,
    skill: {
      name: 'network-search-ops',
      summary: '指导 Agent 在遭遇时效性或未知事实时，进行多路自适应轮询、网页深度抓取与脱水。',
      chapters: [
        { title: '第 1 章：多源搜索智能分流', summary: '根据提问类型自动选择宽幅搜索、深度学术调研或代码逆向。' },
        { title: '第 2 章：多 Key 轮询与 429 熔断避障', summary: '动态调度 26 个 Key 资源池，遇到超频自动静默轮换退避。' },
        { title: '第 3 章：网页免爬虫脱水与污点隔离', summary: '防范外部网页提示词注入，只抽取核心纯文本正文入库。' },
      ],
    },
    gui: {
      name: '多引擎聚合搜索配置与配额中心',
      cloudConfigSummary: '云端管理控制台集中配置各厂商 (Tavily/Exa/SearXNG) 接口端点、多 API Key 轮询池、冷却降级策略与 45 天账期流水。',
      clientDialogSummary: 'Agent 客户端环境免密免配置，通过通信桥梁透明调用聚合搜索算子并直观回显多源引用来源。',
    },
    hooks: [
      { id: 'key_rotator_hook', name: '26-Key 轮询与 429 防抖', triggerEvent: 'before_dispatch', description: '多账号配额均衡分摊，遇 429 标记 60s 冷却换 Key', defaultEnabled: true },
      { id: 'search_guard_hook', name: '时效感知与污点标记', triggerEvent: 'before_search', description: '对外部抓取网页实施单向熔断隔离，防止诱骗泄露凭据', defaultEnabled: true },
      { id: 'credit_audit_hook', name: 'Credits 捕获与45天归档', triggerEvent: 'after_response', description: '从官方响应捕获消耗明细，落地并在超 45 天后自动物理归档', defaultEnabled: true },
    ],
    bundles: [
      {
        id: 'web-search-core',
        name: '全网实时宽幅搜索包',
        roleType: 'consumer',
        description: 'Keenable 80万次池 -> Tavily -> SearXNG 本地自适应搜索与基准校验',
        icon: 'globe',
        toolIds: ['web_search', 'search_neural', 'search_qna', 'benchmark_needle'],
        tools: [
          { id: 'web_search', name: 'web_search', description: '多路宽幅自适应网络检索' },
          { id: 'search_neural', name: 'search_neural', description: 'Exa 神经网络语义意图检索' },
          { id: 'search_qna', name: 'search_qna', description: 'Tavily/Exa 权威解答与引用' },
          { id: 'benchmark_needle', name: 'benchmark_needle', description: 'Keenable NEEDLE 基准校验' },
        ],
      },
      {
        id: 'deep-research-code',
        name: '深度调研与代码反查包',
        roleType: 'consumer',
        description: 'Tavily Advanced 交叉检索、GitHub 源码定位与自主调研长报告',
        icon: 'search',
        toolIds: ['search_deep', 'search_code_context', 'search_similar_repos', 'deep_research'],
        tools: [
          { id: 'search_deep', name: 'search_deep', description: 'Tavily 深度多源交叉检索' },
          { id: 'search_code_context', name: 'search_code_context', description: 'Exa GitHub 开源上下文定位' },
          { id: 'search_similar_repos', name: 'search_similar_repos', description: 'Exa findSimilar 竞品反查' },
          { id: 'deep_research', name: 'deep_research', description: 'Exa Agent 多步自主调研长报告' },
        ],
      },
      {
        id: 'crawl-extract',
        name: '整站测绘与无头抓取包',
        roleType: 'ops',
        description: '站点拓扑测绘、免爬虫正文抽取与本地 Crawl4AI 无头渲染',
        icon: 'scan',
        toolIds: ['map_site', 'extract_urls', 'tavily_crawl', 'crawl_local'],
        tools: [
          { id: 'map_site', name: 'map_site', description: 'Tavily Map 站点拓扑树测绘' },
          { id: 'extract_urls', name: 'extract_urls', description: '免爬虫快速正文脱水提取' },
          { id: 'tavily_crawl', name: 'tavily_crawl', description: '整站自动化爬行流水线' },
          { id: 'crawl_local', name: 'crawl_local', description: 'Crawl4AI Playwright 动态渲染' },
        ],
      },
    ],
  },

  // 3. KeePass 凭据保险箱插件 (8 项 MCP 工具 + 1 项 Hook)
  {
    pluginId: 'keepass-vault',
    name: 'KeePass 凭据保险箱插件',
    version: '1.0.1',
    description: '本地私有凭据管理插件 (云端零密码存储，客户端本地直接挂载 KDBX 数据文件)',
    totalTools: 8,
    skill: {
      name: 'keepass-vault',
      summary: '全集群凭据唯一真实源规范，要求 Agent 遇到外部鉴权强制先查库、严禁索要或明文输出密码。',
      chapters: [
        { title: '第 1 章：查库第一性公理', summary: '遇到服务器登录或 API 鉴权，强制调用 keepass_get，严禁询问用户。' },
        { title: '第 2 章：高熵密码生成与写盘', summary: '批量注册或改密时自动生成 ≥20 位高熵密码，并实时安全回写归档。' },
        { title: '第 3 章：写前自动快照容灾', summary: '任何写操作前底层自动生成 .bak 快照，保障物理库绝对零丢失。' },
      ],
    },
    gui: {
      name: '本地私有凭据托管展厅',
      cloudConfigSummary: '云端控制台仅提供官方展厅展示、不可变插件包托管下载与配置引导，绝不集中存储或远程传输用户私有密码库。',
      clientDialogSummary: '智能体客户端直接在本地通过 keepassxc-cli 解密用户本机的 .kdbx 数据库文件，密码数据 100% 留存本地。',
    },
    hooks: [
      { id: 'vault_guard_hook', name: '写前防抖物理快照', triggerEvent: 'before_vault_write', description: '任何凭据增删改前自动生成 *.bak 快照防抖备份', defaultEnabled: true },
    ],
    bundles: [
      {
        id: 'vault-read',
        name: '凭据安全只读包',
        roleType: 'consumer',
        description: '条目模糊搜索、明文安全解密、凭据拓扑树与保险箱探针',
        icon: 'key',
        toolIds: ['keepass_get', 'keepass_search', 'keepass_list_tree', 'keepass_status'],
        tools: [
          { id: 'keepass_get', name: 'keepass_get', description: '安全读取指定凭据条目' },
          { id: 'keepass_search', name: 'keepass_search', description: '模糊搜索凭据条目与账号' },
          { id: 'keepass_list_tree', name: 'keepass_list_tree', description: '获取凭据分组拓扑树' },
          { id: 'keepass_status', name: 'keepass_status', description: '凭据库解锁与健康状态' },
        ],
      },
      {
        id: 'vault-manage',
        name: '凭据治理运维包',
        roleType: 'ops',
        description: '高熵新建凭据、属性修改、条目废弃与弱密健康审计 (敏感)',
        icon: 'shield-check',
        requiredRole: 'admin',
        toolIds: ['keepass_add', 'keepass_edit', 'keepass_rm', 'keepass_analyze'],
        tools: [
          { id: 'keepass_add', name: 'keepass_add', description: '高熵新建凭据条目' },
          { id: 'keepass_edit', name: 'keepass_edit', description: '更新已有凭据属性' },
          { id: 'keepass_rm', name: 'keepass_rm', description: '安全废弃或删除凭据', isDangerous: true },
          { id: 'keepass_analyze', name: 'keepass_analyze', description: '弱密与重复密码健康审计' },
        ],
      },
    ],
  },

  // 4. Dify 智能体与工作流中枢插件 (12 项 MCP 工具 + 2 项 Hook)
  {
    pluginId: 'dify',
    name: 'Dify 智能体与工作流中枢',
    version: '1.0.0',
    description: '全生命周期可视化 AI 智能体编排与工作流中枢 (应用管理、DSL 导入导出、知识库检索引擎与模型提供商)',
    totalTools: 12,
    skill: {
      name: 'dify-ops',
      summary: '指导 Agent 调度 Dify 工作流执行、DSL 配置导入导出与知识库语义检索测试。',
      chapters: [
        { title: '第 1 章：应用检索与工作流调度', summary: '通过 dify_list_apps 与 dify_run_workflow 自动化触发编排任务。' },
        { title: '第 2 章：DSL 版本化规范归档', summary: '通过 export_dsl 与 import_dsl 实现工作流代码化版本受控。' },
        { title: '第 3 章：知识库检索与切片评测', summary: '通过 dify_search_dataset 执行 Hit-Testing 语义切片测试。' },
      ],
    },
    gui: {
      name: 'Dify 工作流与知识库配置中心',
      cloudConfigSummary: '集中配置 Dify 实例控制面 API 端点、Workspace 租户空间、管理员密钥与应用路由映射。',
      clientDialogSummary: '智能体客户端无缝感知已装配的工作流与知识库，直接通过 MCP 执行自动化任务。',
    },
    hooks: [
      { id: 'dify_execution_audit', name: '工作流入参合规审计', triggerEvent: 'before_workflow_run', description: '工作流触发前校验 inputs 契约与入参必填项', defaultEnabled: true },
      { id: 'dify_dsl_backup_hook', name: 'DSL 覆写前自动备份', triggerEvent: 'before_dsl_import', description: '覆盖导入应用 DSL 前自动拉取当前版本归档备份', defaultEnabled: true },
    ],
    bundles: [
      {
        id: 'dify-app-ops',
        name: '应用编排与工作流包',
        roleType: 'consumer',
        description: '应用检索、规范详情、DSL 导入导出、工作流触发与应用删除',
        icon: 'workflow',
        toolIds: ['dify_status', 'dify_list_apps', 'dify_get_app', 'dify_export_dsl', 'dify_import_dsl', 'dify_delete_app', 'dify_run_workflow'],
        tools: [
          { id: 'dify_status', name: 'dify_status', description: '检查 Dify 服务端连通状态与资产总览' },
          { id: 'dify_list_apps', name: 'dify_list_apps', description: '分页列出工作区内应用与工作流清单' },
          { id: 'dify_get_app', name: 'dify_get_app', description: '获取指定应用/工作流详细配置规格' },
          { id: 'dify_export_dsl', name: 'dify_export_dsl', description: '导出应用或工作流完整 YAML DSL 规范配置' },
          { id: 'dify_import_dsl', name: 'dify_import_dsl', description: '导入 YAML DSL 创建或覆盖更新应用' },
          { id: 'dify_delete_app', name: 'dify_delete_app', description: '按 UUID 物理删除指定应用 (高危)', isDangerous: true },
          { id: 'dify_run_workflow', name: 'dify_run_workflow', description: '传入参数触发执行指定工作流并捕获执行轨迹' },
        ],
      },
      {
        id: 'dify-kb-ops',
        name: '知识库与模型管理包',
        roleType: 'consumer',
        description: '知识库列表、高品质数据集创建、语义检索 Hit-Testing 与模型厂商',
        icon: 'database',
        toolIds: ['dify_list_datasets', 'dify_create_dataset', 'dify_delete_dataset', 'dify_search_dataset', 'dify_list_model_providers'],
        tools: [
          { id: 'dify_list_datasets', name: 'dify_list_datasets', description: '分页列出工作区内知识库数据集清单' },
          { id: 'dify_create_dataset', name: 'dify_create_dataset', description: '新建高品质知识库数据集' },
          { id: 'dify_delete_dataset', name: 'dify_delete_dataset', description: '按 UUID 物理删除指定知识库 (高危)', isDangerous: true },
          { id: 'dify_search_dataset', name: 'dify_search_dataset', description: '对指定知识库执行 Hit-Testing 语义测试检索' },
          { id: 'dify_list_model_providers', name: 'dify_list_model_providers', description: '列出工作区已配置模型提供商与凭据状态' },
        ],
      },
    ],
  },
]
