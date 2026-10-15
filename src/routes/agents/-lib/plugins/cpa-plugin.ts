import type { PluginCapability } from '../capability-bundles'

export const cpaPlugin: PluginCapability = {
  pluginId: 'cpa-squad',
  name: 'CPA 跨模型算力协同插件',
  version: '1.0.0',
  description: 'CPA 多模型智囊协同与工兵批量调度中枢 (独立微服务 · 物理宿主 2080Ti WSL2 虚拟服务器)',
  totalTools: 2,
  skill: {
    name: 'cpa-squad',
    summary: '指导 Claude/GPT 专家决策咨询，Gemini/DeepSeek 工兵批量扇出，MIMO 限速避坑与故障无感转移规约。',
    chapters: [
      { title: '第 1 章：专家决策与工兵分工', summary: '高难架构推演咨询专家模型，机械重复任务扇出工兵模型。' },
      { title: '第 2 章：429 MIMO 限流避坑', summary: '检测并发阈值与冷却时间，自动触发降级熔断。' },
    ],
  },
  gui: {
    name: 'CPA 算力模型与分摊大盘',
    cloudConfigSummary: '集中观测 2080Ti 节点健康度、各模型 Token 消耗账单与路由负载。',
    clientDialogSummary: '智能体客户端无感调度跨模型集群，自动获得最高效能算力配比。',
  },
  hooks: [
    {
      id: 'cpa_fallback_failover_hook',
      name: '429 智能降级与熔断转移',
      triggerEvent: 'before_cpa_dispatch',
      description: '专家模型限流或超时瞬时降级到工兵集群，杜绝挂死',
      defaultEnabled: true,
    },
    {
      id: 'cpa_cost_telemetry_hook',
      name: 'Token 消耗与成本审计',
      triggerEvent: 'after_cpa_response',
      description: '自动提取真实 Token 消耗与延迟，沉淀结构化日记账',
      defaultEnabled: true,
    },
  ],
  bundles: [
    {
      id: 'cpa-squad-core',
      name: 'CPA 跨模型算力协同包',
      roleType: 'consumer',
      description: 'Claude/GPT 专家咨询与 Gemini/DeepSeek 工兵批量扇出调度',
      icon: 'sparkles',
      toolIds: ['openviking_cpa_consult', 'openviking_cpa_fanout'],
      tools: [
        { id: 'openviking_cpa_consult', name: 'cpa_consult', description: 'CPA 专家模型异步咨询与决策协同' },
        { id: 'openviking_cpa_fanout', name: 'cpa_fanout', description: 'CPA 任务批量扇出并行调度' },
      ],
    },
  ],
}
