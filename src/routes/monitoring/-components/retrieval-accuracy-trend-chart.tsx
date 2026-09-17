import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Area,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { HelpCircleIcon, TargetIcon, ZapIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '#/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '#/components/ui/tooltip'
import { fetchTelemetryTrends } from '#/lib/telemetry'
import type {
  RetrievalAccuracyDataPoint,
  TelemetryTimeWindow,
} from '#/lib/telemetry'

interface RetrievalAccuracyTrendChartProps {
  currentAccuracy?: number | null
  currentCosine?: number | null
  window?: TelemetryTimeWindow
}

export function RetrievalAccuracyTrendChart({
  currentAccuracy,
  currentCosine,
  window = '7d',
}: RetrievalAccuracyTrendChartProps) {
  const { t } = useTranslation('monitoringPage')

  const trendsQuery = useQuery({
    queryKey: ['telemetry-trends-retrieval', window],
    queryFn: () =>
      fetchTelemetryTrends<RetrievalAccuracyDataPoint>('retrieval', window),
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    staleTime: 30_000,
  })

  const rawData = trendsQuery.data ?? []

  const data: RetrievalAccuracyDataPoint[] = React.useMemo(() => {
    return rawData
  }, [rawData])

  const latestAcc = data.length > 0
    ? (data[data.length - 1]?.hitRate ?? 0).toFixed(1)
    : (typeof currentAccuracy === 'number' ? currentAccuracy.toFixed(1) : '--')
  const latestCosine = data.length > 0
    ? (data[data.length - 1]?.avgScore ?? 0).toFixed(4)
    : (typeof currentCosine === 'number' ? currentCosine.toFixed(4) : '--')

  return (
    <TooltipProvider>
      <div className="flex w-full flex-col rounded-md border border-border/60 bg-card p-4 shadow-none">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-3">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
              <TargetIcon className="size-4" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h3 className="text-xs font-semibold tracking-tight text-foreground">
                  {t('analyticsCharts.retrievalAccuracyTitle', {
                    defaultValue: '向量召回命中率与余弦得分时序曲线',
                  })}
                </h3>
                <Tooltip>
                  <TooltipTrigger
                    aria-label="Accuracy Tooltip"
                    className="text-muted-foreground/60 hover:text-muted-foreground focus:outline-none"
                  >
                    <HelpCircleIcon className="size-3.5" />
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs text-xs">
                    {t('analyticsCharts.retrievalTooltip', {
                      defaultValue:
                        '展示 OpenViking 引擎召回命中率与余弦相似度历史时序变化。真实后端 SQLite 驱动。',
                    })}
                  </TooltipContent>
                </Tooltip>
              </div>
              <p className="text-xs text-muted-foreground/70 font-mono">
                {window.toUpperCase()} 周期语义检索命中率与平均余弦相似度时序记录
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 font-mono tabular-nums">
            <Badge variant="outline" className="gap-1 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20 text-xs px-2 py-0.5">
              <TargetIcon className="size-3" />
              <span>命中率 {latestAcc !== '--' ? `${latestAcc}%` : '--'}</span>
            </Badge>
            <Badge variant="outline" className="gap-1 bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20 text-xs px-2 py-0.5">
              <ZapIcon className="size-3" />
              <span>Cosine {latestCosine}</span>
            </Badge>
          </div>
        </div>

        {/* Chart Body */}
        {data.length === 0 ? (
          <div className="mt-4 flex h-44 w-full flex-col items-center justify-center rounded border border-dashed border-border/50 text-xs text-muted-foreground font-mono">
            <span>暂无历史时序数据</span>
            <span className="text-xs text-muted-foreground/60 mt-1">系统产生检索后将自动沉淀时序趋势</span>
          </div>
        ) : (
          <div className="mt-4 h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="cosineGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0284c7" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#0284c7" stopOpacity={0.0} />
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
                  yAxisId="left"
                  domain={[0, 100]}
                  stroke="#06b6d4"
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
                  className="font-mono"
                  unit="%"
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  domain={[0, 1.0]}
                  stroke="#0284c7"
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
                  className="font-mono"
                />
                <RechartsTooltip
                  content={({ active, payload }) => {
                    if (active && payload.length > 0) {
                      const d = payload[0].payload as RetrievalAccuracyDataPoint
                      return (
                        <div className="rounded-md border border-border/80 bg-card p-2 shadow-none font-mono text-xs space-y-1">
                          <div className="text-muted-foreground">{d.date}</div>
                          <div className="font-bold text-cyan-600 dark:text-cyan-400">
                            召回命中率: {Number(d.hitRate || 100).toFixed(1)}% ({d.queries} 次请求)
                          </div>
                          <div className="font-bold text-sky-600 dark:text-sky-400">
                            余弦相似度: {Number(d.avgScore || 0).toFixed(4)}
                          </div>
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Area
                  yAxisId="right"
                  type="monotone"
                  dataKey="avgScore"
                  fill="url(#cosineGradient)"
                  stroke="#0284c7"
                  strokeWidth={1.5}
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="hitRate"
                  stroke="#06b6d4"
                  strokeWidth={2}
                  dot={{ r: 3, fill: '#06b6d4' }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </TooltipProvider>
  )
}
