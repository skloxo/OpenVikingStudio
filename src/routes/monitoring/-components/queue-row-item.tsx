import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronRightIcon, CpuIcon } from 'lucide-react'

import { Tooltip, TooltipContent, TooltipTrigger } from '#/components/ui/tooltip'
import { cn } from '#/lib/utils'
import {
  ALL_PANORAMA_STEPS,
  ENGINE_DEFINITIONS,
  TASK_FLOWS,
} from '#/routes/tasks/-lib/pipeline-definitions'
import { getTaskFlowItems } from '../-lib/task-flow-helpers'
import type { ParsedQueueRow } from '../-lib/queue-parser'

export interface QueueRowItemProps {
  row: ParsedQueueRow
  isRowTotal: boolean
  isTaskCard?: boolean
}

export function QueueRowItem({ row, isRowTotal, isTaskCard = false }: QueueRowItemProps) {
  const { t, i18n } = useTranslation('monitoringPage')
  const isZh = i18n.language.startsWith('zh')

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

  const engineDef =
    !isTaskCard && !isTotalRow
      ? ENGINE_DEFINITIONS.find((e) => {
          const rawClean = row.name.toLowerCase().replace(/[-_]/g, '')
          const keyClean = e.key.toLowerCase().replace(/[-_]/g, '')
          return rawClean === keyClean || e.nameZh === displayName || e.nameEn === displayName
        })
      : null

  const assignedSteps = engineDef
    ? ALL_PANORAMA_STEPS.filter((s) => s.engineKey === engineDef.key)
    : []

  return (
    <div
      className={cn(
        'grid grid-cols-12 gap-1 items-center px-2.5 py-1 text-[11px] rounded font-mono transition-colors leading-tight',
        isTotalRow
          ? 'mt-auto bg-muted/60 font-bold border border-border/80 text-foreground shadow-2xs py-1.5'
          : 'bg-muted/20 hover:bg-muted/40 text-foreground/90',
      )}
    >
      {/* 任务名 / 引擎名 + 工序微胶囊链 */}
      <div className="col-span-8 flex items-center min-w-0 pr-2 overflow-hidden select-none">
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
              <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-2">
                <div className="flex items-center gap-2">
                  <div className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary border border-primary/20">
                    <CpuIcon className="size-4 shrink-0" />
                  </div>
                  <div className="flex flex-col">
                    <span className="font-sans font-bold text-xs text-foreground">
                      {isZh ? engineDef.nameZh : engineDef.nameEn}
                    </span>
                    <span className="font-mono text-[10px] text-muted-foreground">{engineDef.key}</span>
                  </div>
                </div>
                <span className="font-mono text-[10px] font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded-full border border-primary/20">
                  {assignedSteps.length} {isZh ? '道工序' : 'Steps'}
                </span>
              </div>
              <p className="font-sans text-[11px] text-muted-foreground leading-relaxed">
                {isZh ? engineDef.descZh : engineDef.descEn}
              </p>
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

        {/* 任务卡片展示工序链 */}
        {isTaskCard && flowItems.length > 0 && !isTotalRow && (
          <div className="flex items-center gap-1 min-w-0 flex-1 overflow-x-auto no-scrollbar select-none pl-1">
            <div className="h-2.5 w-px bg-border/60 shrink-0 mx-0.5" />
            {flowItems.map((item, itemIdx) => (
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
            ))}
          </div>
        )}
      </div>

      {/* 处理中 */}
      <span
        className={cn(
          'col-span-1 text-right tabular-nums font-bold text-xs',
          row.processing > 0 ? 'font-bold text-primary animate-pulse' : 'text-muted-foreground/60',
        )}
      >
        {row.processing}
      </span>

      {/* 待处理 */}
      <span
        className={cn(
          'col-span-1 text-right tabular-nums font-bold text-xs',
          row.pending > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-muted-foreground/60',
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
