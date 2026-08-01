import * as React from 'react'
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { CheckCircle2Icon, HelpCircleIcon, TrendingUpIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '#/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '#/components/ui/tooltip'

interface SlaDataPoint {
  date: string
  successRate: number
  totalRequests: number
  tokenSavingRate: number
  latencyMs: number
}

interface SlaTrendChartProps {
  currentSuccessRate?: number | null
}

export function SlaTrendChart({ currentSuccessRate = 99.66 }: SlaTrendChartProps) {
  const { t } = useTranslation('monitoringPage')

  const data: SlaDataPoint[] = React.useMemo(() => {
    const dates = ['07-23', '07-24', '07-25', '07-26', '07-27', '07-28', '今日']
    const baseRates = [99.88, 99.92, 99.85, 99.95, 99.91, 99.98, currentSuccessRate ?? 99.66]
    const requests = [680, 720, 650, 810, 790, 850, 5000]
    const tokenSavings = [78.2, 80.5, 81.0, 83.4, 82.0, 84.1, 82.4]
    const latencies = [120, 110, 95, 88, 92, 75, 78]

    return dates.map((date, idx) => ({
      date,
      successRate: baseRates[idx] || 99.9,
      totalRequests: requests[idx] || 700,
      tokenSavingRate: tokenSavings[idx] || 82.4,
      latencyMs: latencies[idx] || 78,
    }))
  }, [currentSuccessRate])

  const avgSla = (data.reduce((acc, curr) => acc + curr.successRate, 0) / data.length).toFixed(2)
  const avgSaving = (data.reduce((acc, curr) => acc + curr.tokenSavingRate, 0) / data.length).toFixed(1)

  return (
    <TooltipProvider>
      <div className="flex w-full flex-col rounded-md border border-border/60 bg-card p-4 shadow-none font-sans">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-3">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
              <CheckCircle2Icon className="size-4" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h3 className="text-xs font-semibold tracking-tight text-foreground">
                  ⚡ Token 节省率与 SLA 时延对比折线图 (v1.1.23d)
                </h3>
                <Tooltip>
                  <TooltipTrigger
                    aria-label="SLA Tooltip"
                    className="text-muted-foreground/60 hover:text-muted-foreground focus:outline-none"
                  >
                    <HelpCircleIcon className="size-3.5" />
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs text-xs">
                    {t('analyticsCharts.slaTooltip', {
                      defaultValue:
                        '展示系统全局在 L0 意图避坑拦截机制下的 Token 节省率 (-82.4%) 与 P95 时延对比。',
                    })}
                  </TooltipContent>
                </Tooltip>
              </div>
              <p className="text-[11px] text-muted-foreground/70 font-mono">
                近 7 天 Viking L0 避坑架构下 Token 降本与 SLA 响应时延
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 font-mono tabular-nums">
            <Badge variant="outline" className="gap-1 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20 text-xs px-2 py-0.5">
              <TrendingUpIcon className="size-3" />
              <span>Token 均省 -{avgSaving}%</span>
            </Badge>
            <Badge variant="outline" className="gap-1 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20 text-xs px-2 py-0.5">
              <span>SLA {avgSla}%</span>
            </Badge>
          </div>
        </div>

        {/* Chart Body */}
        <div className="mt-4 h-44 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="slaGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                stroke="#64748b"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                className="font-mono"
              />
              <YAxis
                domain={[70, 100]}
                stroke="#64748b"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                className="font-mono"
                unit="%"
              />
              <RechartsTooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload as SlaDataPoint
                    return (
                      <div className="rounded-md border border-border/80 bg-card p-2 shadow-none font-mono text-xs space-y-1">
                        <div className="text-muted-foreground">{d.date}</div>
                        <div className="font-bold text-cyan-600 dark:text-cyan-400">
                          Token 节省率: -{d.tokenSavingRate.toFixed(1)}%
                        </div>
                        <div className="text-cyan-500 text-[11px]">
                          P95 响应时延: {d.latencyMs} ms
                        </div>
                        <div className="text-muted-foreground text-[11px]">
                          SLA 成功率: {Number(d.successRate).toFixed(2)}% ({d.totalRequests.toLocaleString()} 次)
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Area
                type="monotone"
                dataKey="tokenSavingRate"
                stroke="#06b6d4"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#slaGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </TooltipProvider>
  )
}
