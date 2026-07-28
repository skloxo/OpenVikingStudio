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

interface QueueRowProps {
  title: string
  processing: number
  pending: number
  completed: number
  errors: number
  total: number
}

function QueueRow({ title, processing, pending, completed, errors, total }: QueueRowProps) {
  const { t } = useTranslation('monitoring')

  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs font-medium text-muted-foreground">{title}</span>
      <div className="grid grid-cols-5 gap-1.5 rounded-lg border bg-muted/20 p-1.5 text-center text-xs">
        <div className="flex flex-col items-center justify-center rounded-md bg-blue-500/10 py-1.5 px-1">
          <span className="text-[10px] text-muted-foreground">{t('queue.processing')}</span>
          <span className="font-mono text-sm font-bold text-blue-600 dark:text-blue-400 tabular-nums">
            {processing}
          </span>
        </div>
        <div className="flex flex-col items-center justify-center rounded-md bg-amber-500/10 py-1.5 px-1">
          <span className="text-[10px] text-muted-foreground">{t('queue.pending')}</span>
          <span className="font-mono text-sm font-bold text-amber-600 dark:text-amber-400 tabular-nums">
            {pending}
          </span>
        </div>
        <div className="flex flex-col items-center justify-center rounded-md bg-emerald-500/10 py-1.5 px-1">
          <span className="text-[10px] text-muted-foreground">{t('queue.completed')}</span>
          <span className="font-mono text-sm font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
            {completed}
          </span>
        </div>
        <div className="flex flex-col items-center justify-center rounded-md bg-destructive/10 py-1.5 px-1">
          <span className="text-[10px] text-muted-foreground">{t('queue.errors')}</span>
          <span className="font-mono text-sm font-bold text-destructive tabular-nums">
            {errors}
          </span>
        </div>
        <div className="flex flex-col items-center justify-center rounded-md bg-muted/50 py-1.5 px-1">
          <span className="text-[10px] text-muted-foreground">{t('queue.total')}</span>
          <span className="font-mono text-sm font-bold text-foreground tabular-nums">
            {total}
          </span>
        </div>
      </div>
    </div>
  )
}

export function QueueStatusCard({ status, isHealthy }: QueueStatusCardProps) {
  const { t } = useTranslation('monitoring')
  const rows = React.useMemo(() => parseQueueStatus(status), [status])

  const getQueueDisplayName = (name: string): string => {
    const lower = name.toLowerCase()
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
        <p className="text-sm text-muted-foreground">{t('queue.noData')}</p>
      ) : (
        <div className="flex flex-col gap-4">
          {rows.map((row) => (
            <QueueRow
              key={row.name}
              title={getQueueDisplayName(row.name)}
              processing={row.processing}
              pending={row.pending}
              completed={row.completed}
              errors={row.errors}
              total={row.total}
            />
          ))}
        </div>
      )}
    </Card>
  )
}
