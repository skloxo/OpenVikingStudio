import type { PluginCapability } from '../capability-bundles'

export const searchPlugin: PluginCapability = {
  pluginId: 'network-search',
  name: '联网搜索与采集插件',
  version: '1.1.0',
  description: '3家在线矩阵 (26-Key 轮询) + 2项本地服务调度与 45天流水账滚动归档',
  totalTools: 13,
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
    {
      id: 'key_rotator_hook',
      name: '26-Key 轮询与 429 防抖',
      triggerEvent: 'before_dispatch',
      description: '多账号配额均衡分摊，遇 429 标记 60s 冷却换 Key',
      defaultEnabled: true,
    },
    {
      id: 'search_guard_hook',
      name: '时效感知与污点标记',
      triggerEvent: 'before_search',
      description: '对外部抓取网页实施单向熔断隔离，防止诱骗泄露凭据',
      defaultEnabled: true,
    },
    {
      id: 'credit_audit_hook',
      name: 'Credits 捕获与45天归档',
      triggerEvent: 'after_response',
      description: '从官方响应捕获消耗明细，落地并在超 45 天后自动物理归档',
      defaultEnabled: true,
    },
  ],
  bundles: [
    {
      id: 'web-search-core',
      name: '全网实时宽幅搜索包',
      roleType: 'consumer',
      description: 'Keenable 80万次池 -> Tavily -> SearXNG 本地自适应搜索与基准校验',
      icon: 'globe',
      toolIds: ['web_search', 'search_neural', 'search_qna', 'benchmark_needle', 'search_vertical_expert'],
      tools: [
        { id: 'web_search', name: 'web_search', description: '多路宽幅自适应网络检索' },
        { id: 'search_neural', name: 'search_neural', description: 'Exa 神经网络语义意图检索' },
        { id: 'search_qna', name: 'search_qna', description: 'Tavily/Exa 权威解答与引用' },
        { id: 'benchmark_needle', name: 'benchmark_needle', description: 'Keenable NEEDLE 基准校验' },
        { id: 'search_vertical_expert', name: 'search_vertical_expert', description: 'Keenable 5大垂类高精检索' },
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
}
