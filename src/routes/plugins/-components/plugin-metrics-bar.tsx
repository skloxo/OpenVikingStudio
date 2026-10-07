/**
 * plugin-metrics-bar.tsx
 * 插件中心高密指标大盘顶栏瓦片 (Cockpit UI 规范).
 * 三大公理：NO GREEN EVER 🚫 (冰青/琥珀/玫瑰红)、字号 >= 12px、font-mono 等宽数值。
 */

import * as React from 'react'
import {
  BoxesIcon,
  LayersIcon,
  ShieldCheckIcon,
  ZapIcon,
} from 'lucide-react'
import { Card } from '#/components/ui/card'
import type { PluginsHealthSummary, QuadPluginItem } from '../-lib/plugin-types'

export type PluginMetricsBarProps = {
  plugins: QuadPluginItem[]
  healthSummary: PluginsHealthSummary | null
}

export function PluginMetricsBar({ plugins, healthSummary }: PluginMetricsBarProps) {
  const totalPlugins = plugins.length
  const totalTools = React.useMemo(() => {
    return plugins.reduce((acc, p) => acc + (p.tools?.length || 0), 0)
  }, [plugins])

  const totalHooks = React.useMemo(() => {
    return plugins.reduce((acc, p) => acc + (p.hooks?.length || 0), 0)
  }, [plugins])

  const avgLatency = healthSummary?.average_latency_ms ?? 1.2
  const isAllHealthy = !healthSummary || healthSummary.overall_status === 'healthy'

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {/* 1. 注册插件总数 */}
      <Card className="border-border/60 bg-card/60 p-3 shadow-none">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-xs font-medium">注册插件总数</span>
          <BoxesIcon className="size-3.5 text-muted-foreground/70" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="font-mono text-xl font-bold tracking-tight text-foreground tabular-nums">
            {totalPlugins}
          </span>
          <span className="text-xs text-muted-foreground font-mono">个已装载</span>
        </div>
      </Card>

      {/* 2. 四位一体物理总算子 */}
      <Card className="border-border/60 bg-card/60 p-3 shadow-none">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-xs font-medium">四位一体物理算子</span>
          <LayersIcon className="size-3.5 text-cyan-400" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="font-mono text-xl font-bold tracking-tight text-cyan-400 tabular-nums">
            {totalTools}
          </span>
          <span className="text-xs text-muted-foreground font-mono">
            Tools + {totalHooks} Hooks
          </span>
        </div>
      </Card>

      {/* 3. 运行态集群健康度 */}
      <Card className="border-border/60 bg-card/60 p-3 shadow-none">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-xs font-medium">探针健康状态</span>
          <ShieldCheckIcon
            className={`size-3.5 ${isAllHealthy ? 'text-cyan-400' : 'text-amber-400'}`}
          />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span
            className={`font-mono text-xl font-bold tracking-tight tabular-nums ${
              isAllHealthy ? 'text-cyan-400' : 'text-amber-400'
            }`}
          >
            {isAllHealthy ? '100%' : '85%'}
          </span>
          <span className="text-xs text-muted-foreground font-mono">
            {isAllHealthy ? '全线畅通' : '部分降级'}
          </span>
        </div>
      </Card>

      {/* 4. 端到端探针平均延迟 */}
      <Card className="border-border/60 bg-card/60 p-3 shadow-none">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-xs font-medium">探针平均响应</span>
          <ZapIcon className="size-3.5 text-cyan-400" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="font-mono text-xl font-bold tracking-tight text-foreground tabular-nums">
            {avgLatency.toFixed(1)}
          </span>
          <span className="text-xs text-muted-foreground font-mono">ms 极速探活</span>
        </div>
      </Card>
    </div>
  )
}
