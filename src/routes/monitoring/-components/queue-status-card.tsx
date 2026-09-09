import * as React from 'react'
import { useTranslation } from 'react-i18next'

import { Card, CardTitle } from '#/components/ui/card'
import { cn } from '#/lib/utils'
import { parseQueueStatus, type ParsedQueueRow } from '../-lib/queue-parser'
import { QueueRowItem } from './queue-row-item'
import { getTaskFlowItems, type TaskFlowItem } from '../-lib/task-flow-helpers'

export type { TaskFlowItem, ParsedQueueRow }
export { getTaskFlowItems, parseQueueStatus }

export interface QueueStatusCardProps {
  title?: string
  /** Observer system 返回的 queue 组件的 status 原始文本 */
  status?: string
  isHealthy?: boolean
  isTaskCard?: boolean
  isLoading?: boolean
  customRows?: ParsedQueueRow[]
}

export function QueueStatusCard({
  title,
  status = '',
  isTaskCard = false,
  customRows,
}: QueueStatusCardProps) {
  const { t } = useTranslation('monitoringPage')
  const parsedFromStatus = React.useMemo(() => parseQueueStatus(status), [status])
  const rows = customRows ?? parsedFromStatus

  const nonTotalRows = React.useMemo(
    () => rows.filter((r) => r.name.toUpperCase() !== 'TOTAL'),
    [rows],
  )
  const computedTotalRow = React.useMemo<ParsedQueueRow>(() => {
    let processing = 0
    let pending = 0
    let completed = 0
    let errors = 0
    for (const r of nonTotalRows) {
      processing += r.processing || 0
      pending += r.pending || 0
      completed += r.completed || 0
      errors += r.errors || 0
    }
    return {
      name: 'TOTAL',
      processing,
      pending,
      completed,
      errors,
      total: processing + pending + completed,
    }
  }, [nonTotalRows])

  return (
    <Card className="flex h-full flex-col justify-between gap-1.5 p-3 shadow-xs transition-colors hover:border-primary/30">
      <div className="flex items-center justify-between gap-2">
        <CardTitle className="text-sm font-semibold">{title ?? t('queue.title')}</CardTitle>
      </div>

      {rows.length === 0 ? (
        <div className="rounded-lg border bg-muted/20 p-2.5 text-center text-xs text-muted-foreground">
          {t('queue.noData')}
        </div>
      ) : (
        <div className="flex flex-1 flex-col justify-between gap-0.5">
          {/* 统一顶置表头 (12 列格栅 100% 对齐) */}
          <div className="grid grid-cols-12 gap-1 items-center px-2.5 py-1 text-[11px] text-muted-foreground font-medium border-b border-border/60">
            <div className="col-span-8 flex items-center min-w-0 pr-2 overflow-hidden select-none">
              <span className={cn('shrink-0', isTaskCard && 'w-22 text-left')}>
                {isTaskCard ? t('queue.taskType') : t('queue.queueName')}
              </span>
              {isTaskCard && (
                <div className="flex items-center gap-1 min-w-0 flex-1 pl-1">
                  <div className="h-2.5 w-px bg-border/60 shrink-0 mx-0.5" />
                  <span className="text-muted-foreground/80 pl-1 font-sans">
                    {t('queue.taskFlow')}
                  </span>
                </div>
              )}
            </div>
            <span className="col-span-1 text-right">{t('queue.processing')}</span>
            <span className="col-span-1 text-right">{t('queue.pending')}</span>
            <span className="col-span-1 text-right">{t('queue.completed')}</span>
            <span className="col-span-1 text-right">{t('queue.errors')}</span>
          </div>

          {/* 数据列表 */}
          <div className="flex flex-col gap-0.5">
            {nonTotalRows.map((row) => (
              <QueueRowItem
                key={row.name}
                row={row}
                isRowTotal={false}
                isTaskCard={isTaskCard}
              />
            ))}
          </div>

          {/* 底端对齐合计行 */}
          <QueueRowItem
            row={computedTotalRow}
            isRowTotal={true}
            isTaskCard={isTaskCard}
          />
        </div>
      )}
    </Card>
  )
}
