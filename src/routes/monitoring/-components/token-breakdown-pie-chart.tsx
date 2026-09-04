import * as React from 'react'
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from 'recharts'
import { CoinsIcon, HelpCircleIcon, PieChartIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '#/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '#/components/ui/tooltip'

interface TokenSlice {
  name: string
  key: string
  tokens: number
  percent: number
  color: string
}

export interface TokenDistribution {
  vlm_input?: number
  vlm_output?: number
  embedding_input?: number
  rerank_input?: number
  total?: number
}

interface TokenBreakdownPieChartProps {
  tokenDistribution?: TokenDistribution | null
  totalTokens?: number | null
}

export function TokenBreakdownPieChart({
  tokenDistribution = null,
  totalTokens = null,
}: TokenBreakdownPieChartProps) {
  const { t } = useTranslation('monitoringPage')

  const total = tokenDistribution?.total ?? totalTokens ?? null

  const { slices, allCategories } = React.useMemo(() => {
    if (!tokenDistribution || typeof total !== 'number' || total <= 0) {
      return { slices: [], allCategories: [] }
    }

    const vlmIn = tokenDistribution.vlm_input ?? 0
    const vlmOut = tokenDistribution.vlm_output ?? 0
    const embIn = tokenDistribution.embedding_input ?? 0
    const rerankIn = tokenDistribution.rerank_input ?? 0

    const pctVlmIn = Math.round((vlmIn / total) * 100)
    const pctVlmOut = Math.round((vlmOut / total) * 100)
    const pctRerankIn = Math.round((rerankIn / total) * 100)
    const pctEmbIn = Math.max(0, 100 - pctVlmIn - pctVlmOut - pctRerankIn)

    const categories: TokenSlice[] = [
      {
        name: t('analyticsCharts.embeddingInput', { defaultValue: 'Embedding 向量 Token' }),
        key: 'embeddingInput',
        tokens: embIn,
        percent: pctEmbIn,
        color: '#0284c7', // Sky 600
      },
      {
        name: t('analyticsCharts.vlmInput', { defaultValue: 'VLM 输入 Token' }),
        key: 'vlmInput',
        tokens: vlmIn,
        percent: pctVlmIn,
        color: '#06b6d4', // Cyan 500
      },
      {
        name: t('analyticsCharts.vlmOutput', { defaultValue: 'VLM 输出 Token' }),
        key: 'vlmOutput',
        tokens: vlmOut,
        percent: pctVlmOut,
        color: '#38bdf8', // Sky 400
      },
      {
        name: t('analyticsCharts.rerankInput', { defaultValue: 'Rerank 算子 Token' }),
        key: 'rerankInput',
        tokens: rerankIn,
        percent: pctRerankIn,
        color: '#818cf8', // Indigo 400
      },
    ]

    return {
      slices: categories.filter((c) => c.tokens > 0),
      allCategories: categories,
    }
  }, [tokenDistribution, total, t])

  const totalBadgeText = typeof total === 'number' && total > 0
    ? total >= 1000
      ? `${(total / 1000).toFixed(1)}k 累计 Token`
      : `${total} 累计 Token`
    : '--'

  return (
    <TooltipProvider>
      <div className="flex w-full flex-col rounded-md border border-border/60 bg-card p-4 shadow-none">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-3">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
              <PieChartIcon className="size-4" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h3 className="text-xs font-semibold tracking-tight text-foreground">
                  {t('analyticsCharts.tokenPieTitle', {
                    defaultValue: 'Token 消耗物理分布构成',
                  })}
                </h3>
                <Tooltip>
                  <TooltipTrigger
                    aria-label={t('analyticsCharts.tokenPieTooltip', { defaultValue: 'Token Tooltip' })}
                    className="text-muted-foreground/60 hover:text-muted-foreground focus:outline-none"
                  >
                    <HelpCircleIcon className="size-3.5" />
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs text-xs">
                    {t('analyticsCharts.tokenPieTooltip', {
                      defaultValue:
                        '展示不同模型与环节产生的 Token 物理消耗分布占比，帮您直观发现成本大头。',
                    })}
                  </TooltipContent>
                </Tooltip>
              </div>
              <p className="text-[11px] text-muted-foreground/70 font-mono">
                {t('analyticsCharts.tokenPieSubtitle', {
                  defaultValue: '全量 VLM 输入/输出与 Embedding 向量 Token 比例划分',
                })}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 font-mono tabular-nums">
            <Badge variant="outline" className="gap-1 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20 text-xs px-2 py-0.5">
              <CoinsIcon className="size-3" />
              <span>{totalBadgeText}</span>
            </Badge>
          </div>
        </div>

        {/* Chart Body */}
        {slices.length > 0 ? (
          <div className="mt-4 flex h-44 w-full items-center justify-between gap-4">
            <div className="h-full w-1/2">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <RechartsTooltip
                    content={({ active, payload }) => {
                      if (active) {
                        const d = payload[0]?.payload as TokenSlice | undefined
                        if (!d) return null
                        return (
                          <div className="rounded-md border border-border/80 bg-card p-2 shadow-none font-mono text-xs space-y-1">
                            <div className="font-semibold text-foreground">{d.name}</div>
                            <div className="font-bold text-cyan-600 dark:text-cyan-400">
                              消耗: {d.tokens.toLocaleString()} Tokens ({d.percent}%)
                            </div>
                          </div>
                        )
                      }
                      return null
                    }}
                  />
                  <Pie
                    data={slices}
                    cx="50%"
                    cy="50%"
                    innerRadius={42}
                    outerRadius={68}
                    paddingAngle={slices.length > 1 ? 3 : 0}
                    dataKey="tokens"
                  >
                    {slices.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Legend Details: Explicitly render all 4 physical categories */}
            <div className="flex w-1/2 flex-col justify-center gap-2 text-[11px] font-mono tabular-nums">
              {allCategories.map((item) => (
                <div
                  key={item.key}
                  className="flex items-center justify-between border-b border-border/30 pb-1"
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span
                      className="size-2.5 shrink-0 rounded-full"
                      style={{
                        backgroundColor: item.tokens > 0 ? item.color : '#64748b',
                        opacity: item.tokens > 0 ? 1 : 0.4,
                      }}
                    />
                    <span
                      className={`truncate ${
                        item.tokens > 0
                          ? 'text-foreground font-medium'
                          : 'text-muted-foreground/60'
                      }`}
                    >
                      {item.name}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span
                      className={
                        item.tokens > 0
                          ? 'font-bold text-foreground'
                          : 'text-muted-foreground/50'
                      }
                    >
                      {item.percent}%
                    </span>
                    <span className="text-[10px] text-muted-foreground/60">
                      ({item.tokens > 0 ? item.tokens.toLocaleString() : '0'})
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="mt-4 flex h-44 w-full items-center justify-center rounded border border-dashed border-border/60 font-mono text-xs text-muted-foreground">
            {t('analyticsCharts.noTokenData', { defaultValue: '暂无 Token 消耗数据 (--)' })}
          </div>
        )}
      </div>
    </TooltipProvider>
  )
}

