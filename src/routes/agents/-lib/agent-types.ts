/**
 * agent-types.ts
 * 智能体中心强类型 DTO 与视图类型定义 (SSOT)。
 */
import type { UserAgentItem } from '#/lib/admin'

export type ClusterAgentItem = UserAgentItem & {
  // 扩展全集群视图字段
}

export type AgentsSummaryMetrics = {
  totalAgents: number
  activeCount: number
  localDirectCount: number
  remoteGatewayCount: number
}
