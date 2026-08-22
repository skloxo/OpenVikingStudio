import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronRightIcon, CpuIcon } from 'lucide-react'

import { Card, CardTitle } from '#/components/ui/card'
import { Tooltip, TooltipContent, TooltipTrigger } from '#/components/ui/tooltip'
import { cn } from '#/lib/utils'
import { parseObserverStatus } from '../-lib/parse-status'
import {
  ALL_PANORAMA_STEPS,
  ENGINE_DEFINITIONS,
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

export type TaskFlowItem =
  | { kind: 'single'; step: PanoramaStepDef }
  | { kind: 'parallel'; steps: PanoramaStepDef[] }

export function getTaskFlowItems(taskType: string): TaskFlowItem[] {
  if (taskType === 'add_resource') {
    const s1 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_ingestion')
    const s2 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_parse')
    const s3 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_semantic')
    const s4 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_embedding')
    const res: TaskFlowItem[] = []
    if (s1) res.push({ kind: 'single', step: s1 })
    if (s2) res.push({ kind: 'single', step: s2 })
    if (s3 && s4) res.push({ kind: 'parallel', steps: [s3, s4] })
    return res
  }

  if (taskType === 'connector_import') {
    const s1 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_auth')
    const s2 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_fetch')
    const s3 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_parse')
    const s4 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_semantic')
    const s5 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_embedding')
    const res: TaskFlowItem[] = []
    if (s1) res.push({ kind: 'single', step: s1 })
    if (s2) res.push({ kind: 'single', step: s2 })
    if (s3) res.push({ kind: 'single', step: s3 })
    if (s4 && s5) res.push({ kind: 'parallel', steps: [s4, s5] })
    return res
  }

  const flow = TASK_FLOWS.find((f) => f.typeKey === taskType)
  if (!flow) return []
  return flow.stepIds
    .map((id) => ALL_PANORAMA_STEPS.find((s) => s.id === id))
    .filter((s): s is PanoramaStepDef => s !== undefined)
    .map((step) => ({ kind: 'single' as const, step }))
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
  isLoading?: boolean
  customRows?: ParsedQueueRow[]
}

export function QueueStatusCard({
  title,
  status = '',
  isHealthy = true,
  isTaskCard = false,
  isLoading = false,
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

  const getQueueDisplayName = (name: string): string => {
    const clean = name.toLowerCase().replace(/[-_]/g, '')
    if (clean === 'total') return t('queue.totalRow')
    if (clean === 'embedding') return t('queue.embedding')
    if (clean === 'semanticnodes' || clean === 'semanticnode') return t('queue.semanticNodes')
    if (clean === 'semantic') return t('queue.semantic')
    if (clean === 'externalparse') return t('queue.externalParse')
    if (clean === 'addresource' || clean === 'resource') return t('queue.addResource')
    if (clean === 'userdeletion' || clean === 'userdelete') return t('queue.userDeletion')
    if (clean === 'sessioncommit') return t('queue.sessionCommit')
    return name
  }

  const renderRow = (row: ParsedQueueRow, isRowTotal: boolean) => {
    const isTotalRow =
      isRowTotal ||
      row.name.toUpperCase() === 'TOTAL' ||
      row.name === t('queue.total') ||
      row.name === '合计'

    const displayName = isTotalRow
      ? t('queue.total')
      : isTaskCard
        ? row.name
        : getQueueDisplayName(row.name)

    const taskTypeKey =
      row.typeKey ??
      TASK_FLOWS.find((f) => f.nameZh === row.name || f.nameEn === row.name)?.typeKey
    const flowItems = isTaskCard && taskTypeKey && !isTotalRow ? getTaskFlowItems(taskTypeKey) : []

    // Lookup matching Engine Definition for Engine Card (Exact match only, preventing partial substring shadowing)
    const engineDef =
      !isTaskCard && !isTotalRow
        ? ENGINE_DEFINITIONS.find((e) => {
            const rawClean = row.name.toLowerCase().replace(/[-_]/g, '')
            const keyClean = e.key.toLowerCase().replace(/[-_]/g, '')
            return (
              rawClean === keyClean ||
              e.nameZh === displayName ||
              e.nameEn === displayName
            )
          })
        : null

    const assignedSteps = engineDef
      ? ALL_PANORAMA_STEPS.filter((s) => s.engineKey === engineDef.key)
      : []

    return (
      <div
        key={row.name}
        className={cn(
          'grid grid-cols-12 gap-1 items-center px-2.5 py-1 text-[11px] rounded font-mono transition-colors leading-tight',
          isTotalRow
            ? 'mt-auto bg-muted/60 font-bold border border-border/80 text-foreground shadow-2xs py-1.5'
            : 'bg-muted/20 hover:bg-muted/40 text-foreground/90',
        )}
      >
        {/* 任务名 / 引擎名 + 工序微胶囊链 (单行高密对齐，防溢出截断保护) */}
        <div className="col-span-8 flex items-center min-w-0 pr-2 overflow-hidden select-none">
          {/* 如果是引擎卡片且非合计行：支持悬浮画像卡片 */}
          {engineDef ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="font-sans font-semibold text-xs text-foreground shrink-0 hover:text-primary hover:underline underline-offset-4 cursor-help transition-all">
                  {displayName}
                </span>
              </TooltipTrigger>
              <TooltipContent
                side="top"
                align="start"
                sideOffset={8}
                className="w-96 max-w-md p-3.5 space-y-2.5 bg-popover text-popover-foreground border border-border shadow-xl rounded-lg text-left"
              >
                {/* 顶部 Header: CPU 图标 + 引擎名称 + Raw Key 与 工序数量徽章 */}
                <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-2">
                  <div className="flex items-center gap-2">
                    <div className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary border border-primary/20">
                      <CpuIcon className="size-4 shrink-0" />
                    </div>
                    <div className="flex flex-col">
                      <span className="font-sans font-bold text-xs text-foreground">
                        {isZh ? engineDef.nameZh : engineDef.nameEn}
                      </span>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {engineDef.key}
                      </span>
                    </div>
                  </div>
                  <span className="font-mono text-[10px] font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded-full border border-primary/20">
                    {assignedSteps.length} {isZh ? '道工序' : 'Steps'}
                  </span>
                </div>

                {/* 中部: 物理职责说明 */}
                <p className="font-sans text-[11px] text-muted-foreground leading-relaxed">
                  {isZh ? engineDef.descZh : engineDef.descEn}
                </p>

                {/* 底部: 承接工序清单 */}
                {assignedSteps.length > 0 && (
                  <div className="space-y-1.5 pt-1.5 border-t border-border/40">
                    <span className="font-sans text-[11px] text-muted-foreground font-medium">
                      {isZh ? '承接工序清单：' : 'Assigned Steps:'}
                    </span>
                    <div className="flex flex-wrap gap-1.5 pt-0.5">
                      {assignedSteps.map((s) => (
                        <span
                          key={s.id}
                          className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-sans font-medium bg-muted/60 text-foreground/90 border border-border/50 shadow-2xs"
                        >
                          {isZh ? s.nameZh : s.nameEn}{' '}
                          <span className="font-mono text-[10px] text-muted-foreground ml-1">
                            ({isZh ? s.unitZh : s.unitEn})
                          </span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </TooltipContent>
            </Tooltip>
          ) : (
            <span
              className={cn(
                'font-sans font-semibold text-xs text-foreground shrink-0',
                isTaskCard && !isTotalRow && 'w-22 truncate text-left',
              )}
            >
              {displayName}
            </span>
          )}

          {/* 如果是任务卡片且非合计行：展示结构化对齐的发丝分界线与工序链 */}
          {isTaskCard && flowItems.length > 0 && !isTotalRow && (
            <div className="flex items-center gap-1 min-w-0 flex-1 overflow-x-auto no-scrollbar select-none pl-1">
              <div className="h-2.5 w-px bg-border/60 shrink-0 mx-0.5" />
              {flowItems.map((item, itemIdx) => {
                return (
                  <React.Fragment key={itemIdx}>
                    {itemIdx > 0 && (
                      <ChevronRightIcon className="size-2.5 text-muted-foreground/40 shrink-0 select-none -mx-0.5" />
                    )}

                    {item.kind === 'single' ? (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="inline-flex items-center px-1 py-px rounded text-[11px] font-sans font-medium bg-muted/60 text-foreground/90 hover:text-foreground hover:bg-muted hover:border-primary/40 cursor-help border border-border/50 whitespace-nowrap shrink-0 transition-all shadow-2xs leading-none">
                            {isZh ? item.step.nameZh : item.step.nameEn}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent
                          side="top"
                          align="center"
                          sideOffset={6}
                          className="w-80 max-w-sm p-3.5 space-y-2.5 bg-popover text-popover-foreground border border-border shadow-xl rounded-lg text-left"
                        >
                          <div className="flex items-center justify-between gap-2 border-b border-border/60 pb-2">
                            <span className="font-sans font-bold text-xs text-foreground">
                              {isZh ? item.step.nameZh : item.step.nameEn}
                            </span>
                            <span className="font-mono text-[10px] font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
                              {isZh ? `单位: ${item.step.unitZh}` : `Unit: ${item.step.unitEn}`}
                            </span>
                          </div>
                          <p className="font-sans text-[11px] text-muted-foreground leading-relaxed">
                            {isZh ? item.step.descriptionZh : item.step.descriptionEn}
                          </p>
                          <div className="flex items-center justify-between gap-1.5 pt-1.5 border-t border-border/40 font-mono text-[11px] text-foreground/80">
                            <span className="font-sans text-[11px] text-muted-foreground">
                              {isZh ? '承接算子：' : 'Assigned Operator:'}
                            </span>
                            <span className="inline-flex items-center gap-1 font-semibold text-foreground bg-muted/60 px-1.5 py-0.5 rounded border border-border/40">
                              <CpuIcon className="size-3 text-primary shrink-0" />
                              {isZh ? item.step.engineNameZh : item.step.engineNameEn}
                            </span>
                          </div>
                        </TooltipContent>
                      </Tooltip>
                    ) : (
                      /* 并发工序组合框 (Neutral Container Box with &) */
                      <div className="inline-flex items-center gap-1 px-1 py-px rounded text-[11px] font-sans font-medium bg-muted/60 text-foreground/90 border border-border/50 whitespace-nowrap shrink-0 transition-all shadow-2xs leading-none">
                        {item.steps.map((st, sIdx) => (
                          <React.Fragment key={st.id}>
                            {sIdx > 0 && (
                              <span className="text-muted-foreground/60 font-mono text-[10px] font-bold select-none px-0.5">
                                &
                              </span>
                            )}
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className="hover:text-foreground hover:underline underline-offset-2 cursor-help transition-all">
                                  {isZh ? st.nameZh : st.nameEn}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent
                                side="top"
                                align="center"
                                sideOffset={6}
                                className="w-80 max-w-sm p-3.5 space-y-2.5 bg-popover text-popover-foreground border border-border shadow-xl rounded-lg text-left"
                              >
                                <div className="flex items-center justify-between gap-2 border-b border-border/60 pb-2">
                                  <span className="font-sans font-bold text-xs text-foreground">
                                    {isZh ? st.nameZh : st.nameEn}
                                  </span>
                                  <span className="font-mono text-[10px] font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
                                    {isZh ? `单位: ${st.unitZh}` : `Unit: ${st.unitEn}`}
                                  </span>
                                </div>
                                <p className="font-sans text-[11px] text-muted-foreground leading-relaxed">
                                  {isZh ? st.descriptionZh : st.descriptionEn}
                                </p>
                                <div className="flex items-center justify-between gap-1.5 pt-1.5 border-t border-border/40 font-mono text-[11px] text-foreground/80">
                                  <span className="font-sans text-[11px] text-muted-foreground">
                                    {isZh ? '承接算子：' : 'Assigned Operator:'}
                                  </span>
                                  <span className="inline-flex items-center gap-1 font-semibold text-foreground bg-muted/60 px-1.5 py-0.5 rounded border border-border/40">
                                    <CpuIcon className="size-3 text-primary shrink-0" />
                                    {isZh ? st.engineNameZh : st.engineNameEn}
                                  </span>
                                </div>
                              </TooltipContent>
                            </Tooltip>
                          </React.Fragment>
                        ))}
                      </div>
                    )}
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
            'col-span-1 text-right tabular-nums font-bold text-xs',
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
            <span className="col-span-8">
              {isTaskCard ? (isZh ? '任务类型' : 'Task Type') : (isZh ? '引擎名称' : 'Engine Name')}
            </span>
            <span className="col-span-1 text-right">{t('queue.processing')}</span>
            <span className="col-span-1 text-right">{t('queue.pending')}</span>
            <span className="col-span-1 text-right">{t('queue.completed')}</span>
            <span className="col-span-1 text-right">{t('queue.errors')}</span>
          </div>

          {/* 数据列表 */}
          <div className="flex flex-col gap-0.5">
            {nonTotalRows.map((row) => renderRow(row, false))}
          </div>

          {/* 底端对齐合计行 */}
          {renderRow(computedTotalRow, true)}
        </div>
      )}
    </Card>
  )
}
