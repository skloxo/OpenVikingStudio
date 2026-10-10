/**
 * agent-metrics-bar.tsx
 * 智能体中心高密指标大盘顶栏瓦片 (Cockpit UI 规范).
 * 三大公理：NO GREEN EVER 🚫、字号 >= 12px、font-mono 等宽数值、沉静中性配色。
 */
import {
  BotIcon,
  CpuIcon,
  GlobeIcon,
  ShieldCheckIcon,
} from 'lucide-react'
import { Card } from '#/components/ui/card'
import type { AgentsSummaryMetrics } from '../-lib/agent-types'

export type AgentMetricsBarProps = {
  metrics: AgentsSummaryMetrics
}

export function AgentMetricsBar({ metrics }: AgentMetricsBarProps) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {/* 1. 在册智能体总数 */}
      <Card className="border-border/60 bg-card/60 p-3 shadow-none">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-xs font-medium">在册智能体总数</span>
          <BotIcon className="size-3.5 text-muted-foreground/70" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="font-mono text-xl font-bold tracking-tight text-foreground tabular-nums">
            {metrics.totalAgents}
          </span>
          <span className="text-xs text-muted-foreground font-mono">个已注册</span>
        </div>
      </Card>

      {/* 2. 活跃就绪智能体 */}
      <Card className="border-border/60 bg-card/60 p-3 shadow-none">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-xs font-medium">活跃就绪状态</span>
          <ShieldCheckIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="font-mono text-xl font-bold tracking-tight text-cyan-600 dark:text-cyan-400 tabular-nums">
            {metrics.activeCount}
          </span>
          <span className="text-xs text-muted-foreground font-mono">
            / {metrics.totalAgents} 正常生效
          </span>
        </div>
      </Card>

      {/* 3. 本地宿主直连模式 */}
      <Card className="border-border/60 bg-card/60 p-3 shadow-none">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-xs font-medium">本地宿主直连 (2080Ti)</span>
          <CpuIcon className="size-3.5 text-muted-foreground" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="font-mono text-xl font-bold tracking-tight text-foreground tabular-nums">
            {metrics.localDirectCount}
          </span>
          <span className="text-xs text-muted-foreground font-mono">127.0.0.1:1933</span>
        </div>
      </Card>

      {/* 4. 网络远程卫星模式 */}
      <Card className="border-border/60 bg-card/60 p-3 shadow-none">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-xs font-medium">公网穿透远程 (3070/FRP)</span>
          <GlobeIcon className="size-3.5 text-muted-foreground" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="font-mono text-xl font-bold tracking-tight text-foreground tabular-nums">
            {metrics.remoteGatewayCount}
          </span>
          <span className="text-xs text-muted-foreground font-mono">vk.tide.red 穿透</span>
        </div>
      </Card>
    </div>
  )
}
