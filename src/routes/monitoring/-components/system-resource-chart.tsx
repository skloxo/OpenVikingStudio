import { useMemo } from 'react'
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

interface SystemResourceChartProps {
  isLoading?: boolean
  vectorCount?: number
}

export function SystemResourceChart({
  isLoading = false,
  vectorCount = 13949,
}: SystemResourceChartProps) {
  const { t } = useTranslation('monitoring')

  // 生成具备极客质感的系统资源与 VikingDB 向量增长高密走势模拟点（高平滑真实渲染）
  const chartData = useMemo(() => {
    const baseTime = new Date()
    return Array.from({ length: 12 }).map((_, i) => {
      const time = new Date(baseTime.getTime() - (11 - i) * 5 * 60 * 1000)
      const timeLabel = time.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      })

      // CPU / Memory / 向量存储增长平滑模拟
      const cpuUsage = Math.round(12 + Math.sin(i * 0.8) * 6 + (i % 3) * 2)
      const memoryUsage = Math.round(42 + (i * 0.5) + Math.cos(i) * 3)
      const vectors = Math.round(vectorCount - (11 - i) * 12 + Math.random() * 4)

      return {
        time: timeLabel,
        cpu: cpuUsage,
        memory: memoryUsage,
        vectors: vectors,
      }
    })
  }, [vectorCount])

  if (isLoading) {
    return (
      <div className="h-64 animate-pulse rounded border border-border/40 bg-muted/20 p-4" />
    )
  }

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
            CPU: {chartData[chartData.length - 1]?.cpu}%
          </span>
          <span className="inline-flex items-center gap-1 rounded-xs border border-indigo-500/30 bg-indigo-500/10 px-2 py-0.5 text-indigo-600 dark:text-indigo-400">
            <HardDrive className="size-3" />
            RAM: {chartData[chartData.length - 1]?.memory}%
          </span>
          <span className="inline-flex items-center gap-1 rounded-xs border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-emerald-600 dark:text-emerald-400">
            <Layers className="size-3" />
            Vectors: {chartData[chartData.length - 1]?.vectors?.toLocaleString()}
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
              tick={{ fontSize: 10, fontFamily: 'monospace' }}
              tickLine={false}
            />

            <YAxis
              stroke="currentColor"
              opacity={0.5}
              tick={{ fontSize: 10, fontFamily: 'monospace' }}
              tickLine={false}
              domain={[0, 100]}
              unit="%"
            />

            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
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
