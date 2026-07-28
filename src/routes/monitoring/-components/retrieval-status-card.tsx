import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { Badge } from '#/components/ui/badge'
import { Card, CardTitle } from '#/components/ui/card'
import { cn } from '#/lib/utils'
import { parseObserverStatus } from '../-lib/parse-status'

export interface RetrievalMetrics {
  totalQueries: number
  totalResults: number
  avgResultsPerQuery: number
  zeroResultQueries: number
  zeroResultRate: string
  avgScore: string
  rerankUsed: number
  avgLatencyMs: number
  maxLatencyMs: number
}

function parseRetrievalStatus(status: string): RetrievalMetrics | null {
  const blocks = parseObserverStatus(status)
  const tableBlock = blocks.find((b) => b.kind === 'table')
  if (!tableBlock) return null

  const map = new Map<string, string>()
  for (const row of tableBlock.rows) {
    if (row.length >= 2) {
      map.set(row[0].trim().toLowerCase(), row[1].trim())
    }
  }

  if (map.size === 0) return null

  return {
    totalQueries: parseInt(map.get('total queries') ?? '0', 10) || 0,
    totalResults: parseInt(map.get('total results') ?? '0', 10) || 0,
    avgResultsPerQuery: parseFloat(map.get('avg results/query') ?? '0') || 0,
    zeroResultQueries: parseInt(map.get('zero-result queries') ?? '0', 10) || 0,
    zeroResultRate: map.get('zero-result rate') ?? '0%',
    avgScore: map.get('avg score') ?? '0',
    rerankUsed: parseInt(map.get('rerank used') ?? '0', 10) || 0,
    avgLatencyMs: parseFloat(map.get('avg latency (ms)') ?? '0') || 0,
    maxLatencyMs: parseFloat(map.get('max latency (ms)') ?? '0') || 0,
  }
}

export interface RetrievalStatusCardProps {
  /** Observer system 返回的 retrieval 组件 status 文本 */
  status: string
  isHealthy: boolean
}

export function RetrievalStatusCard({ status, isHealthy }: RetrievalStatusCardProps) {
  const { t } = useTranslation('monitoringPage')
  const metrics = React.useMemo(() => parseRetrievalStatus(status), [status])

  return (
    <Card className="flex flex-col gap-4 p-4 shadow-none transition-colors hover:border-primary/30">
      <div className="flex items-center justify-between">
        <CardTitle className="text-base font-semibold">{t('retrievalCard.title')}</CardTitle>
        <Badge
          variant="outline"
          className={cn(
            'gap-1 font-normal',
            isHealthy
              ? 'border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
              : 'border-destructive/30 text-destructive',
          )}
        >
          <span
            className={cn(
              'size-1.5 rounded-full',
              isHealthy ? 'bg-emerald-500' : 'bg-destructive',
            )}
          />
          {isHealthy ? t('retrievalCard.healthy') : t('retrievalCard.unhealthy')}
        </Badge>
      </div>

      {!metrics ? (
        <div className="rounded-lg border bg-muted/20 p-3 text-center text-xs text-muted-foreground">
          {status ? (
            <span className="font-mono text-xs text-foreground/80">{status}</span>
          ) : (
            t('retrievalCard.noData')
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {/* 4 大核心关键数据瓷片 */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {/* 总检索数 */}
            <div className="flex flex-col justify-center rounded-lg border bg-muted/20 px-3 py-2">
              <span className="text-[11px] text-muted-foreground font-medium">{t('retrievalCard.totalQueries')}</span>
              <span className="font-mono text-base font-bold text-foreground tabular-nums mt-0.5">
                {metrics.totalQueries.toLocaleString()}
              </span>
            </div>

            {/* 总召回结果数 */}
            <div className="flex flex-col justify-center rounded-lg border bg-muted/20 px-3 py-2">
              <span className="text-[11px] text-muted-foreground font-medium">{t('retrievalCard.totalResults')}</span>
              <span className="font-mono text-base font-bold text-foreground tabular-nums mt-0.5">
                {metrics.totalResults.toLocaleString()}
              </span>
            </div>

            {/* 零结果率 */}
            <div
              className={cn(
                'flex flex-col justify-center rounded-lg border px-3 py-2',
                parseFloat(metrics.zeroResultRate) > 15
                  ? 'bg-amber-500/10 border-amber-500/20'
                  : 'bg-muted/20',
              )}
            >
              <span className="text-[11px] text-muted-foreground font-medium">{t('retrievalCard.zeroResultRate')}</span>
              <span
                className={cn(
                  'font-mono text-base font-bold tabular-nums mt-0.5',
                  parseFloat(metrics.zeroResultRate) > 15
                    ? 'text-amber-600 dark:text-amber-400'
                    : 'text-emerald-600 dark:text-emerald-400',
                )}
              >
                {metrics.zeroResultRate}
              </span>
            </div>

            {/* 平均延迟 */}
            <div
              className={cn(
                'flex flex-col justify-center rounded-lg border px-3 py-2',
                metrics.avgLatencyMs > 1000
                  ? 'bg-amber-500/10 border-amber-500/20'
                  : 'bg-emerald-500/10 border-emerald-500/20',
              )}
            >
              <span className="text-[11px] text-muted-foreground font-medium">{t('retrievalCard.avgLatency')}</span>
              <span
                className={cn(
                  'font-mono text-base font-bold tabular-nums mt-0.5',
                  metrics.avgLatencyMs > 1000
                    ? 'text-amber-600 dark:text-amber-400'
                    : 'text-emerald-600 dark:text-emerald-400',
                )}
              >
                {`${metrics.avgLatencyMs.toLocaleString()} ms`}
              </span>
            </div>
          </div>

          {/* 4 列明细数据次级网格 */}
          <div className="grid grid-cols-2 gap-2 rounded-lg border bg-muted/15 p-2.5 text-xs sm:grid-cols-4">
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] text-muted-foreground">{t('retrievalCard.avgResultsPerQuery')}</span>
              <span className="font-mono font-medium text-foreground tabular-nums">
                {metrics.avgResultsPerQuery}
              </span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] text-muted-foreground">{t('retrievalCard.rerankUsed')}</span>
              <span className="font-mono font-medium text-foreground tabular-nums">
                {metrics.rerankUsed.toLocaleString()}
              </span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] text-muted-foreground">{t('retrievalCard.avgScore')}</span>
              <span className="font-mono font-medium text-foreground tabular-nums">
                {metrics.avgScore}
              </span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] text-muted-foreground">{t('retrievalCard.maxLatency')}</span>
              <span className="font-mono font-medium text-foreground tabular-nums">
                {`${metrics.maxLatencyMs.toLocaleString()} ms`}
              </span>
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}
