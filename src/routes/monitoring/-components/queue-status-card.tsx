import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { CpuIcon } from 'lucide-react'

import { Card, CardTitle } from '#/components/ui/card'
import { Tooltip, TooltipContent, TooltipTrigger } from '#/components/ui/tooltip'
import { cn } from '#/lib/utils'
import { parseObserverStatus } from '../-lib/parse-status'
import {
  ALL_PANORAMA_STEPS,
  TASK_FLOWS,
  type PanoramaStepDef,
} from '#/routes/tasks/-components/pipeline-steps-panorama'

export interface ParsedQueueRow {
  name: string
  typeKey?: string
  processing: number
  pending: number
  completed: number
  errors: number
  total: number
}

// 将 Observer status 字符串解析为结构化队列数据
export function parseQueueStatus(status: string): ParsedQueueRow[] {
  if (!status) return []
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
  title?: string
  /** Observer system 返回的 queue 组件的 status 原始文本 */
  status?: string
  isHealthy?: boolean
  isTaskCard?: boolean
  customRows?: ParsedQueueRow[]
}

export function QueueStatusCard({
  title,
  status = '',
  isHealthy = true,
  isTaskCard = false,
  customRows,
}: QueueStatusCardProps) {
  const { t, i18n } = useTranslation('monitoringPage')
  const isZh = i18n.language.startsWith('zh')
  const parsedFromStatus = React.useMemo(() => parseQueueStatus(status), [status])
  const rows = customRows ?? parsedFromStatus

  const nonTotalRows = React.useMemo(
    () => rows.filter((r) => r.name.toUpperCase() !== 'TOTAL'),
    [rows],
  )
  const totalRow = React.useMemo(
    () => rows.find((r) => r.name.toUpperCase() === 'TOTAL'),
    [rows],
  )

  const getQueueDisplayName = (name: string): string => {
    const lower = name.toLowerCase()
    if (lower === 'total') return t('queue.totalRow')
    if (lower.includes('embedding')) return t('queue.embedding')
    if (
      lower.includes('semantic-node') ||
      lower.includes('semantic_node') ||
      lower.includes('semantic-nodes')
    )
      return t('queue.semanticNodes')
    if (lower.includes('semantic')) return t('queue.semantic')
    if (lower.includes('externalparse') || lower.includes('external_parse'))
      return t('queue.externalParse')
    if (lower.includes('addresource') || lower.includes('add_resource') || lower.includes('resource'))
      return t('queue.addResource')
    if (lower.includes('userdeletion') || lower.includes('user_deletion') || lower.includes('user_delete'))
      return t('queue.userDeletion')
    if (lower.includes('sessioncommit') || lower.includes('session_commit'))
      return t('queue.sessionCommit')
    return name
  }

  const renderRow = (row: ParsedQueueRow, isTotalRow: boolean) => {
    const displayName = isTaskCard ? row.name : getQueueDisplayName(row.name)

    // Lookup matching task flow definition for Task Cards
    const taskFlow = isTaskCard && row.typeKey
      ? TASK_FLOWS.find((f) => f.typeKey === row.typeKey)
      : isTaskCard
        ? TASK_FLOWS.find((f) => f.nameZh === row.name || f.nameEn === row.name)
        : null

    const taskSteps: PanoramaStepDef[] = taskFlow
      ? taskFlow.stepIds
          .map((id) => ALL_PANORAMA_STEPS.find((s) => s.id === id))
          .filter((s): s is PanoramaStepDef => s !== undefined)
      : []

    return (
      <div
        key={row.name}
        className={cn(
          'grid grid-cols-12 gap-1 items-center px-2.5 py-1.5 text-[11px] rounded font-mono transition-colors',
          isTotalRow
            ? 'mt-auto bg-muted/60 font-bold border border-border/80 text-foreground'
            : 'bg-muted/20 hover:bg-muted/40 text-foreground/90',
        )}
      >
        {/* 任务名 / 引擎名 + 工序微胶囊链 */}
        <div className="col-span-7 flex flex-col justify-center min-w-0 pr-1">
          <div className="flex items-center gap-1.5">
            <span className="font-sans font-semibold text-xs text-foreground truncate">
              {displayName}
            </span>
          </div>

          {/* 如果是任务卡片，展示其专属的流水线工序链（带并发符 ∥ 与 Tooltip 物理职责） */}
          {isTaskCard && taskSteps.length > 0 && !isTotalRow && (
            <div className="flex items-center gap-1 mt-1 overflow-x-auto select-none py-0.5">
              {taskSteps.map((st, sIdx) => {
                // 特殊标记：add_resource 与 connector_import 中语义提取与向量建库为并行 (∥)
                const isParallel =
                  (row.typeKey === 'add_resource' || row.typeKey === 'connector_import') &&
                  st.id === 'step_embedding'

                return (
                  <React.Fragment key={st.id}>
                    {sIdx > 0 && (
                      <span
                        className={cn(
                          'font-mono text-[10px] shrink-0 select-none px-0.5',
                          isParallel
                            ? 'text-primary font-bold'
                            : 'text-muted-foreground/40',
                        )}
                        title={isParallel ? '并行工序 (Parallel Batch)' : '串行流转 (Serial)'}
                      >
                        {isParallel ? '∥' : '➔'}
                      </span>
                    )}

                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[11px] font-sans font-medium bg-muted/70 text-foreground/90 hover:text-foreground hover:bg-muted hover:border-primary/40 cursor-help border border-border/50 whitespace-nowrap shrink-0 transition-all shadow-2xs">
                          <span>{isZh ? st.nameZh : st.nameEn}</span>
                          <span className="font-mono text-[10px] text-muted-foreground">
                            {isZh ? st.unitZh : st.unitEn}
                          </span>
                        </span>
                      </TooltipTrigger>
                      <TooltipContent
                        side="top"
                        align="start"
                        className="text-xs max-w-xs p-2.5 space-y-1.5 bg-popover text-popover-foreground border shadow-md"
                      >
                        <div className="flex items-center justify-between gap-2 border-b pb-1">
                          <span className="font-sans font-bold text-foreground">
                            {isZh ? st.nameZh : st.nameEn}
                          </span>
                          <span className="font-mono text-[11px] text-primary font-medium bg-primary/10 px-1 rounded">
                            {isZh ? `单位: ${st.unitZh}` : `Unit: ${st.unitEn}`}
                          </span>
                        </div>
                        <p className="font-sans text-[11px] text-muted-foreground leading-relaxed">
                          {isZh ? st.descriptionZh : st.descriptionEn}
                        </p>
                        <div className="flex items-center gap-1 font-mono text-[11px] text-muted-foreground/90 pt-0.5 border-t border-border/40">
                          <CpuIcon className="size-3 text-primary shrink-0" />
                          <span>
                            {isZh ? '承接引擎' : 'Engine'}: {isZh ? st.engineNameZh : st.engineNameEn}
                          </span>
                        </div>
                      </TooltipContent>
                    </Tooltip>
                  </React.Fragment>
                )
              })}
            </div>
          )}
        </div>

        {/* 处理中 */}
        <span
          className={cn(
            'col-span-1 text-right tabular-nums font-bold text-xs',
            row.processing > 0
              ? 'font-bold text-primary animate-pulse'
              : 'text-muted-foreground/60',
          )}
        >
          {row.processing}
        </span>

        {/* 待处理 */}
        <span
          className={cn(
            'col-span-1 text-right tabular-nums font-bold text-xs',
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
            'col-span-2 text-right tabular-nums font-bold text-xs',
            row.completed > 0 ? 'text-foreground/90' : 'text-muted-foreground/60',
          )}
        >
          {row.completed.toLocaleString()}
        </span>

        {/* 错误数 */}
        <span
          className={cn(
            'col-span-1 text-right tabular-nums font-bold text-xs',
            row.errors > 0 ? 'text-destructive font-bold' : 'text-muted-foreground/60',
          )}
        >
          {row.errors}
        </span>
      </div>
    )
  }

  return (
    <Card className="flex h-full flex-col justify-between gap-2 p-3 shadow-xs transition-colors hover:border-primary/30">
      <div className="flex items-center justify-between gap-2">
        <CardTitle className="text-sm font-semibold">{title ?? t('queue.title')}</CardTitle>
      </div>

      {rows.length === 0 ? (
        <div className="rounded-lg border bg-muted/20 p-2.5 text-center text-xs text-muted-foreground">
          {t('queue.noData')}
        </div>
      ) : (
        <div className="flex flex-1 flex-col justify-between gap-1">
          {/* 统一顶置表头 (12 列格栅 100% 对齐) */}
          <div className="grid grid-cols-12 gap-1 items-center px-2.5 py-1 text-[11px] text-muted-foreground font-medium border-b border-border/60">
            <span className="col-span-7">
              {isTaskCard ? (isZh ? '业务任务与工序流转' : 'Task Type & Steps') : (isZh ? '执行引擎名称' : 'Engine Name')}
            </span>
            <span className="col-span-1 text-right">{t('queue.processing')}</span>
            <span className="col-span-1 text-right">{t('queue.pending')}</span>
            <span className="col-span-2 text-right">{t('queue.completed')}</span>
            <span className="col-span-1 text-right">{t('queue.errors')}</span>
          </div>

          {/* 数据列表 */}
          <div className="flex flex-col gap-1.5">
            {nonTotalRows.map((row) => renderRow(row, false))}
          </div>

          {/* 底端对齐合计行 */}
          {totalRow ? renderRow(totalRow, true) : null}
        </div>
      )}
    </Card>
  )
}
