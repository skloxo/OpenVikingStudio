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

  // 100% 真实后端数据计算，绝不使用硬编码伪造数据 (NO MOCK RULE)
  const healthyCount = React.useMemo(() => {
    if (healthSummary?.healthy_count != null) return healthSummary.healthy_count
    return plugins.filter((p) => p.health?.status === 'healthy').length
  }, [healthSummary, plugins])

  const healthyRate = React.useMemo(() => {
    if (healthSummary?.healthy_rate != null) return Math.round(healthSummary.healthy_rate)
    return totalPlugins > 0 ? Math.round((healthyCount / totalPlugins) * 100) : null
  }, [healthSummary, healthyCount, totalPlugins])

  const avgLatency = React.useMemo(() => {
    if (healthSummary?.average_latency_ms != null && healthSummary.average_latency_ms > 0) {
      return healthSummary.average_latency_ms
    }
    const latencies = plugins
      .map((p) => p.health?.latency_ms)
      .filter((v): v is number => typeof v === 'number' && v > 0)
    return latencies.length > 0 ? latencies.reduce((a, b) => a + b, 0) / latencies.length : null
  }, [healthSummary, plugins])

  const isAllHealthy = totalPlugins > 0 && healthyCount === totalPlugins

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {/* 1. 注册插件总数 */}
      <div className="rounded-md border border-border/60 bg-card/60 p-3 shadow-none">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-xs font-medium">注册插件总数</span>
          <BoxesIcon className="size-3.5 text-muted-foreground/70" />
        </div>
        <div className="mt-1.5 flex items-baseline gap-2">
          <span className="font-mono text-xl font-bold tracking-tight text-foreground tabular-nums">
            {totalPlugins}
          </span>
          <span className="text-xs text-muted-foreground font-mono">个已装载</span>
        </div>
      </div>

      {/* 2. 已装载工具与拦截反射 (同等评级展示) */}
      <div className="rounded-md border border-border/60 bg-card/60 p-3 shadow-none">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-xs font-medium">已装载工具与拦截反射</span>
          <LayersIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
        </div>
        <div className="mt-1.5 flex items-baseline gap-1.5 font-mono">
          <span className="font-mono text-xl font-bold tracking-tight text-foreground tabular-nums">
            {totalTools}
          </span>
          <span className="text-xs text-muted-foreground">项工具</span>
          <span className="mx-1 text-muted-foreground/40 font-sans">·</span>
          <span className="font-mono text-xl font-bold tracking-tight text-foreground tabular-nums">
            {totalHooks}
          </span>
          <span className="text-xs text-muted-foreground">项 Hook</span>
        </div>
      </div>

      {/* 3. 运行态集群健康度 (真实百分比) */}
      <div className="rounded-md border border-border/60 bg-card/60 p-3 shadow-none">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-xs font-medium">探针健康状态</span>
          <ShieldCheckIcon
            className={`size-3.5 ${isAllHealthy ? 'text-cyan-600 dark:text-cyan-400' : 'text-amber-600 dark:text-amber-400'}`}
          />
        </div>
        <div className="mt-1.5 flex items-baseline gap-2">
          <span
            className={`font-mono text-xl font-bold tracking-tight tabular-nums ${
              isAllHealthy ? 'text-cyan-600 dark:text-cyan-400' : 'text-amber-600 dark:text-amber-400'
            }`}
          >
            {healthyRate !== null ? `${healthyRate}%` : '--'}
          </span>
          <span className="text-xs text-muted-foreground font-mono">
            {totalPlugins === 0 ? '检测中' : isAllHealthy ? '全线畅通' : `异常 ${totalPlugins - healthyCount} 项`}
          </span>
        </div>
      </div>

      {/* 4. 端到端探针平均延迟 (真实物理测量) */}
      <div className="rounded-md border border-border/60 bg-card/60 p-3 shadow-none">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-xs font-medium">探针平均响应</span>
          <ZapIcon className="size-3.5 text-muted-foreground" />
        </div>
        <div className="mt-1.5 flex items-baseline gap-2">
          <span className="font-mono text-xl font-bold tracking-tight text-foreground tabular-nums">
            {avgLatency !== null ? avgLatency.toFixed(1) : '--'}
          </span>
          <span className="text-xs text-muted-foreground font-mono">
            {avgLatency !== null ? 'ms 真实探活' : '探针采样中'}
          </span>
        </div>
      </div>
    </div>
  )
}
