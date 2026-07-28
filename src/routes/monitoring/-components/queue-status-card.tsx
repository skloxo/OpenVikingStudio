import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { Badge } from '#/components/ui/badge'
import { Card, CardTitle } from '#/components/ui/card'
import { cn } from '#/lib/utils'
import { parseObserverStatus } from '../-lib/parse-status'

// 从 Observer 返回的 status 文本中解析出的队列行数据
interface ParsedQueueRow {
  name: string
  processing: number
  pending: number
  completed: number
  errors: number
  total: number
}

// 将 Observer status 字符串解析为结构化队列数据
function parseQueueStatus(status: string): ParsedQueueRow[] {
  const blocks = parseObserverStatus(status)
  const tableBlock = blocks.find((b) => b.kind === 'table')
  if (!tableBlock) return []

  const headers = tableBlock.headers
  const col = {
    name: headers.findIndex((h) => h === 'Queue'),
    inProgress: headers.findIndex((h) => h === 'In Progress'),
    pending: headers.findIndex((h) => h === 'Pending'),
    processed: headers.findIndex((h) => h === 'Processed'),
    errors: headers.findIndex((h) => h === 'Errors'),
    total: headers.findIndex((h) => h === 'Total'),
  }

  return tableBlock.rows.map((row) => ({
    name: col.name >= 0 ? (row[col.name] ?? '') : '',
    processing: col.inProgress >= 0 ? (parseInt(row[col.inProgress] ?? '0', 10) || 0) : 0,
    pending: col.pending >= 0 ? (parseInt(row[col.pending] ?? '0', 10) || 0) : 0,
    completed: col.processed >= 0 ? (parseInt(row[col.processed] ?? '0', 10) || 0) : 0,
    errors: col.errors >= 0 ? (parseInt(row[col.errors] ?? '0', 10) || 0) : 0,
    total: col.total >= 0 ? (parseInt(row[col.total] ?? '0', 10) || 0) : 0,
  }))
}

export interface QueueStatusCardProps {
  /** Observer system 返回的 queue 组件的 status 原始文本 */
  status: string
  isHealthy: boolean
}

export function QueueStatusCard({ status, isHealthy }: QueueStatusCardProps) {
  const { t } = useTranslation('monitoringPage')
  const rows = React.useMemo(() => parseQueueStatus(status), [status])

  const getQueueDisplayName = (name: string): string => {
    const lower = name.toLowerCase()
    if (lower === 'total') return 'TOTAL'
    if (lower.includes('embedding')) return t('queue.embedding')
    if (lower.includes('semantic-node') || lower.includes('semantic_node')) return t('queue.semanticNodes')
    if (lower.includes('semantic')) return t('queue.semantic')
    return name
  }

  return (
    <Card className="flex flex-col gap-4 p-4 shadow-none transition-colors hover:border-primary/30">
      <div className="flex items-center justify-between">
        <CardTitle className="text-base font-semibold">{t('queue.title')}</CardTitle>
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
          {isHealthy ? t('queue.healthy') : t('queue.unhealthy')}
        </Badge>
      </div>

      {rows.length === 0 ? (
        <div className="rounded-lg border bg-muted/20 p-3 text-center text-xs text-muted-foreground">
          {t('queue.noData')}
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          {/* 统一顶置表头 (只出现一次，彻底消除重复感) */}
          <div className="grid grid-cols-6 items-center px-3 py-1 text-xs text-muted-foreground font-medium border-b border-border/50">
            <span className="col-span-2">{t('queue.queueName')}</span>
            <span className="text-right">{t('queue.processing')}</span>
            <span className="text-right">{t('queue.pending')}</span>
            <span className="text-right">{t('queue.completed')}</span>
            <span className="text-right">{t('queue.errors')}</span>
          </div>

          {/* 数据列表 */}
          {rows.map((row, i) => {
            const isTotalRow = row.name.toUpperCase() === 'TOTAL'
            const displayName = getQueueDisplayName(row.name)

            return (
              <div
                key={row.name + i}
                className={cn(
                  'grid grid-cols-6 items-center px-3 py-2 text-xs rounded-md font-mono transition-colors',
                  isTotalRow
                    ? 'bg-muted/60 font-bold border border-border/80 text-foreground mt-1'
                    : 'bg-muted/20 hover:bg-muted/40 text-foreground/90',
                )}
              >
                {/* 队列名 */}
                <span className="col-span-2 font-sans font-medium truncate">{displayName}</span>

                {/* 处理中 */}
                <span
                  className={cn(
                    'text-right tabular-nums font-bold',
                    row.processing > 0
                      ? 'text-blue-600 dark:text-blue-400'
                      : 'text-muted-foreground/60',
                  )}
                >
                  {row.processing}
                </span>

                {/* 待处理 */}
                <span
                  className={cn(
                    'text-right tabular-nums font-bold',
                    row.pending > 0
                      ? 'text-amber-600 dark:text-amber-400'
                      : 'text-muted-foreground/60',
                  )}
                >
                  {row.pending}
                </span>

                {/* 已完成 */}
                <span
                  className={cn(
                    'text-right tabular-nums font-bold',
                    row.completed > 0
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-muted-foreground/60',
                  )}
                >
                  {row.completed.toLocaleString()}
                </span>

                {/* 错误数 */}
                <span
                  className={cn(
                    'text-right tabular-nums font-bold',
                    row.errors > 0 ? 'text-destructive' : 'text-muted-foreground/60',
                  )}
                >
                  {row.errors}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}
