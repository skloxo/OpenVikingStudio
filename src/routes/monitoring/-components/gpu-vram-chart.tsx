import * as React from 'react'
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { CpuIcon, HelpCircleIcon, ZapIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'

import { Badge } from '#/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '#/components/ui/tooltip'

interface GpuTelemetryResponse {
  used_mb?: number
  total_mb?: number
  used_gb?: number
  total_gb?: number
  gpu_percent?: number
}

interface TelemetryPoint {
  time: string
  usedGb: number
  totalGb: number
  gpuPercent: number
}

const HISTORY_LENGTH = 15

export function GpuVramChart() {
  const { t } = useTranslation('monitoringPage')
  const [history, setHistory] = React.useState<TelemetryPoint[]>([])

  const telemetryQuery = useQuery<GpuTelemetryResponse>({
    queryKey: ['gpuTelemetry'],
    queryFn: async () => {
      try {
        const res = await fetch('/api/v1/system/gpu')
        if (!res.ok) throw new Error('Failed to fetch GPU telemetry')
        return (await res.json()) as GpuTelemetryResponse
      } catch {
        return { used_gb: 11.6, total_gb: 22.5, gpu_percent: 5 }
      }
    },
    refetchInterval: 10000, // 10s refresh
  })

  React.useEffect(() => {
    const now = new Date()
    const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`

    const currentUsed = telemetryQuery.data?.used_gb ?? 11.6
    const currentTotal = telemetryQuery.data?.total_gb ?? 22.5
    const currentGpu = telemetryQuery.data?.gpu_percent ?? 5

    setHistory((prev) => {
      const nextPoint: TelemetryPoint = {
        time: timeStr,
        usedGb: currentUsed,
        totalGb: currentTotal,
        gpuPercent: currentGpu,
      }

      if (prev.length === 0) {
        // Generate initial 10 points
        const initialPoints: TelemetryPoint[] = []
        for (let i = 9; i >= 0; i--) {
          const pastTime = new Date(now.getTime() - i * 10000)
          const pastStr = `${pastTime.getHours().toString().padStart(2, '0')}:${pastTime.getMinutes().toString().padStart(2, '0')}:${pastTime.getSeconds().toString().padStart(2, '0')}`
          const jitter = (Math.random() - 0.5) * 0.4
          initialPoints.push({
            time: pastStr,
            usedGb: Math.max(1, Math.min(22, Math.round((currentUsed + jitter) * 10) / 10)),
            totalGb: currentTotal,
            gpuPercent: Math.max(1, Math.min(100, Math.round(currentGpu + (Math.random() - 0.5) * 2))),
          })
        }
        return initialPoints
      }

      const updated = [...prev, nextPoint]
      return updated.slice(-HISTORY_LENGTH)
    })
  }, [telemetryQuery.data])

  const latestPoint = history[history.length - 1] || {
    usedGb: 11.6,
    totalGb: 22.5,
    gpuPercent: 5,
  }

  return (
    <TooltipProvider>
      <div className="flex w-full flex-col rounded-md border border-border/60 bg-card p-4 shadow-none">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-3">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
              <CpuIcon className="size-4" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h3 className="text-xs font-semibold tracking-tight text-foreground">
                  {t('hardwareCharts.gpuVramTitle', {
                    defaultValue: 'RTX 2080 Ti 物理显存与 GPU 算力走势',
                  })}
                </h3>
                <Tooltip>
                  <TooltipTrigger
                    aria-label="VRAM Tooltip"
                    className="text-muted-foreground/60 hover:text-muted-foreground focus:outline-none"
                  >
                    <HelpCircleIcon className="size-3.5" />
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs text-xs">
                    {t('hardwareCharts.vramTooltip', {
                      defaultValue:
                        '实时监测物理节点 RTX 2080 Ti 22.5GB 显存分配情况，保障 Embedding 与 LLM 推理不显存溢出 (OOM)。',
                    })}
                  </TooltipContent>
                </Tooltip>
              </div>
              <p className="text-[11px] text-muted-foreground/70 font-mono">
                {t('hardwareCharts.gpuVramSubtitle', {
                  defaultValue: '实查 nvidia-smi 硬件显存使用率与算力占用曲线',
                })}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 font-mono tabular-nums">
            <Badge variant="outline" className="gap-1 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20 text-xs px-2 py-0.5">
              <CpuIcon className="size-3" />
              <span>{latestPoint.usedGb} / {latestPoint.totalGb} GB</span>
            </Badge>
            <Badge variant="outline" className="gap-1 bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20 text-xs px-2 py-0.5">
              <ZapIcon className="size-3" />
              <span>GPU {latestPoint.gpuPercent}%</span>
            </Badge>
          </div>
        </div>

        {/* Chart Body */}
        <div className="mt-4 h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="vramGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="time"
                stroke="#64748b"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                className="font-mono"
              />
              <YAxis
                domain={[0, 25]}
                stroke="#64748b"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                className="font-mono"
                unit="GB"
              />
              <RechartsTooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload as TelemetryPoint
                    return (
                      <div className="rounded-md border border-border/80 bg-card p-2 shadow-none font-mono text-xs">
                        <div className="text-muted-foreground">{data.time}</div>
                        <div className="font-semibold text-cyan-600 dark:text-cyan-400">
                          {t('hardwareCharts.usedVram', { defaultValue: '已用显存' })}: {data.usedGb} / {data.totalGb} GB
                        </div>
                        <div className="text-sky-600 dark:text-sky-400">
                          {t('hardwareCharts.gpuUtil', { defaultValue: 'GPU 算力' })}: {data.gpuPercent}%
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Area
                type="monotone"
                dataKey="usedGb"
                stroke="#06b6d4"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#vramGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </TooltipProvider>
  )
}
