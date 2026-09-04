import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Cpu, HardDrive, Layers, Microchip } from 'lucide-react'

export interface HostResources {
  cpu_percent?: number
  memory_percent?: number
  memory_used_gb?: number
  memory_total_gb?: number
}

interface SystemResourceChartProps {
  isLoading?: boolean
  vectorCount?: number | null
  hostResources?: HostResources | null
}

interface ResourcePoint {
  time: string
  cpu: number
  memory: number
  vectors: number
}

export function SystemResourceChart({
  isLoading = false,
  vectorCount = null,
  hostResources = null,
}: SystemResourceChartProps) {
  const { t } = useTranslation('monitoring')

  const [history, setHistory] = useState<ResourcePoint[]>([])

  useEffect(() => {
    if (!hostResources || typeof hostResources.cpu_percent !== 'number') return

    const now = new Date()
    const timeLabel = now.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })

    const point: ResourcePoint = {
      time: timeLabel,
      cpu: hostResources.cpu_percent,
      memory: hostResources.memory_percent ?? 0,
      vectors: vectorCount ?? 0,
    }

    setHistory((prev) => {
      if (prev.length === 0) {
        return Array.from({ length: 8 }).map((_, i) => {
          const tPoint = new Date(now.getTime() - (7 - i) * 15 * 1000)
          return {
            time: tPoint.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            }),
            cpu: hostResources.cpu_percent ?? 0,
            memory: hostResources.memory_percent ?? 0,
            vectors: vectorCount ?? 0,
          }
        })
      }
      const next = [...prev, point]
      return next.slice(-12)
    })
  }, [hostResources, vectorCount])

  const chartData = useMemo(() => {
    if (history.length > 0) return history
    const baseTime = new Date()
    return Array.from({ length: 8 }).map((_, i) => {
      const time = new Date(baseTime.getTime() - (7 - i) * 15 * 1000)
      return {
        time: time.toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }),
        cpu: hostResources?.cpu_percent ?? 0,
        memory: hostResources?.memory_percent ?? 0,
        vectors: vectorCount ?? 0,
      }
    })
  }, [history, hostResources, vectorCount])

  if (isLoading) {
    return (
      <div className="h-64 animate-pulse rounded border border-border/40 bg-muted/20 p-4" />
    )
  }

  const latestCpu = hostResources && typeof hostResources.cpu_percent === 'number'
    ? `${hostResources.cpu_percent.toFixed(1)}%`
    : '--'
  const latestMem = hostResources && typeof hostResources.memory_percent === 'number'
    ? `${hostResources.memory_percent.toFixed(1)}%`
    : '--'
  const vectorStr = typeof vectorCount === 'number'
    ? vectorCount.toLocaleString()
    : '--'

  return (
    <div className="rounded border border-border/60 bg-card p-3.5 transition-colors">
      {/* 头部区域 */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-sm bg-cyan-500/10 text-cyan-500 dark:bg-cyan-500/20">
            <Microchip className="size-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground tracking-tight">
              ⚡ {t('systemResource.title', { defaultValue: '系统物理资源与 VikingDB 索引走势' })}
            </h3>
            <p className="text-[11px] text-muted-foreground font-mono">
              {t('systemResource.subtitle', { defaultValue: 'CPU / 内存占用率 & 向量节点增长曲线 (Real-time Metric Stream)' })}
            </p>
          </div>
        </div>

        {/* 资源快照 Badge */}
        <div className="flex items-center gap-2 font-mono text-[11px]">
          <span className="inline-flex items-center gap-1 rounded-xs border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-cyan-600 dark:text-cyan-400">
            <Cpu className="size-3" />
            {t('systemResource.cpuLabel', { defaultValue: 'CPU' })}: {latestCpu}
          </span>
          <span className="inline-flex items-center gap-1 rounded-xs border border-indigo-500/30 bg-indigo-500/10 px-2 py-0.5 text-indigo-600 dark:text-indigo-400">
            <HardDrive className="size-3" />
            {t('systemResource.ramLabel', { defaultValue: 'RAM' })}: {latestMem}
          </span>
          <span className="inline-flex items-center gap-1 rounded-xs border border-border/60 bg-muted/20 px-2 py-0.5 text-foreground/90">
            <Layers className="size-3" />
            {t('systemResource.vectors', { defaultValue: '向量数' })}: {vectorStr}
          </span>
        </div>
      </div>

      {/* Recharts 高密面积走势图 */}
      <div className="h-56 w-full pt-1">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00f0ff" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#00f0ff" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="memoryGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="currentColor" opacity={0.1} />

            <XAxis
              dataKey="time"
              stroke="currentColor"
              opacity={0.5}
              tick={{ fontSize: 11, fontFamily: 'monospace' }}
              tickLine={false}
            />

            <YAxis
              stroke="currentColor"
              opacity={0.5}
              tick={{ fontSize: 11, fontFamily: 'monospace' }}
              tickLine={false}
              domain={[0, 100]}
              unit="%"
            />

            <Tooltip
              content={({ active, payload, label }) => {
                if (active) {
                  return (
                    <div className="rounded border border-border/80 bg-background/95 p-2 text-xs shadow-lg backdrop-blur-md font-mono">
                      <p className="font-semibold text-foreground mb-1 border-b border-border/40 pb-1">
                        ⏰ {label}
                      </p>
                      <div className="space-y-1">
                        <p className="flex items-center gap-2 text-cyan-400">
                          <span className="size-2 rounded-full bg-cyan-400" />
                          CPU 占用率: <span className="font-bold tabular-nums">{payload[0]?.value}%</span>
                        </p>
                        <p className="flex items-center gap-2 text-indigo-400">
                          <span className="size-2 rounded-full bg-indigo-400" />
                          内存 占用率: <span className="font-bold tabular-nums">{payload[1]?.value}%</span>
                        </p>
                      </div>
                    </div>
                  )
                }
                return null
              }}
            />

            <Area
              type="monotone"
              dataKey="cpu"
              stroke="#00f0ff"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#cpuGradient)"
              name="CPU Usage"
            />

            <Area
              type="monotone"
              dataKey="memory"
              stroke="#6366f1"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#memoryGradient)"
              name="Memory Usage"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
