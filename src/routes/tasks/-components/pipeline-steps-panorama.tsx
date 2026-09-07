import * as React from 'react'
import {
  ArrowRightIcon,
  ChevronDownIcon,
  CpuIcon,
  WorkflowIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '#/components/ui/badge'
import { Card } from '#/components/ui/card'
import { cn } from '#/lib/utils'

// ─── 强类型与静态数据导入与向后兼容 Re-exports ──────────────────────────────────
import type {
  PanoramaStepDef,
  EngineDef,
  TaskTypeFlowDef,
} from '../-lib/pipeline-definitions'
import {
  ENGINE_DEFINITIONS,
  ALL_PANORAMA_STEPS,
  TASK_FLOWS,
} from '../-lib/pipeline-definitions'

export type { PanoramaStepDef, EngineDef, TaskTypeFlowDef }
export { ENGINE_DEFINITIONS, ALL_PANORAMA_STEPS, TASK_FLOWS }

export function PipelineStepsPanoramaCard() {
  const { i18n } = useTranslation('tasksPage')
  const isZh = i18n.language.startsWith('zh')
  const [isOpen, setIsOpen] = React.useState(false)
  const [activeTab, setActiveTab] = React.useState<'flows' | 'matrix' | 'engines'>('flows')
  const [selectedTaskType, setSelectedTaskType] = React.useState<string>('all')

  const filteredFlows = React.useMemo(() => {
    if (selectedTaskType === 'all') return TASK_FLOWS
    return TASK_FLOWS.filter((f) => f.typeKey === selectedTaskType)
  }, [selectedTaskType])

  return (
    <Card className="rounded-xl border bg-card/75 p-0 shadow-xs transition-all">
      {/* Header Banner */}
      <div
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex cursor-pointer select-none items-center justify-between px-4 py-3 hover:bg-muted/20 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
            <WorkflowIcon className="size-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-sans text-sm font-semibold text-foreground">
                {isZh ? '流水线全工序全景大盘' : 'Pipeline Steps Panorama'}
              </span>
              <Badge variant="outline" className="text-[11px] font-mono px-1.5 py-0 h-4.5 bg-muted/30">
                {isZh ? `${TASK_FLOWS.length} 业务任务` : `${TASK_FLOWS.length} Tasks`}
              </Badge>
              <Badge variant="outline" className="text-[11px] font-mono px-1.5 py-0 h-4.5 bg-primary/10 text-primary border-primary/20">
                {isZh ? `${ALL_PANORAMA_STEPS.length} 原子工序` : `${ALL_PANORAMA_STEPS.length} Steps`}
              </Badge>
              <Badge variant="outline" className="text-[11px] font-mono px-1.5 py-0 h-4.5 bg-muted/30">
                {isZh ? `${ENGINE_DEFINITIONS.length} 执行引擎` : `${ENGINE_DEFINITIONS.length} Engines`}
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {isZh
                ? `任务（业务目标）➔ 编排拆解出 ${ALL_PANORAMA_STEPS.length} 道流水线工序 ➔ 调度驱动底层 ${ENGINE_DEFINITIONS.length} 大执行引擎物理计算`
                : `Business Tasks ➔ Decomposed into ${ALL_PANORAMA_STEPS.length} Pipeline Steps ➔ Dispatched to ${ENGINE_DEFINITIONS.length} Execution Engines`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-medium text-muted-foreground">
            {isOpen ? (isZh ? '收起全景' : 'Collapse') : (isZh ? '展开全景' : 'Expand')}
          </span>
          <ChevronDownIcon
            className={cn('size-4 text-muted-foreground transition-transform duration-200', isOpen && 'rotate-180')}
          />
        </div>
      </div>

      {/* Expanded Content */}
      {isOpen && (
        <div className="border-t px-4 py-3.5 space-y-3.5">
          {/* Sub-Header Tabs & Quick Filter */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-2.5">
            <div className="flex items-center gap-1.5 bg-muted/40 p-0.5 rounded-lg border border-border/60">
              <button
                type="button"
                onClick={() => setActiveTab('flows')}
                className={cn(
                  'px-2.5 py-1 text-xs font-medium rounded-md transition-all cursor-pointer select-none',
                  activeTab === 'flows'
                    ? 'bg-background text-foreground shadow-2xs font-semibold'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {isZh ? `① 任务流转全景 (${TASK_FLOWS.length} 任务)` : `① Task Flows (${TASK_FLOWS.length} Tasks)`}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('matrix')}
                className={cn(
                  'px-2.5 py-1 text-xs font-medium rounded-md transition-all cursor-pointer select-none',
                  activeTab === 'matrix'
                    ? 'bg-background text-foreground shadow-2xs font-semibold'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {isZh ? `② ${ALL_PANORAMA_STEPS.length} 道工序总字典` : `② ${ALL_PANORAMA_STEPS.length} Steps Dictionary`}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('engines')}
                className={cn(
                  'px-2.5 py-1 text-xs font-medium rounded-md transition-all cursor-pointer select-none',
                  activeTab === 'engines'
                    ? 'bg-background text-foreground shadow-2xs font-semibold'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {isZh ? `③ ${ENGINE_DEFINITIONS.length} 大引擎承接图` : `③ ${ENGINE_DEFINITIONS.length} Engine Mappings`}
              </button>
            </div>

            {activeTab === 'flows' && (
              <div className="flex items-center gap-1.5 overflow-x-auto text-[11px]">
                <button
                  type="button"
                  onClick={() => setSelectedTaskType('all')}
                  className={cn(
                    'px-2 py-0.5 rounded border transition-colors cursor-pointer',
                    selectedTaskType === 'all'
                      ? 'bg-primary/10 text-primary border-primary/30 font-medium'
                      : 'bg-muted/20 text-muted-foreground hover:bg-muted/40',
                  )}
                >
                  {isZh ? `全部任务 (${TASK_FLOWS.length})` : `All (${TASK_FLOWS.length})`}
                </button>
                {TASK_FLOWS.map((f) => (
                  <button
                    key={f.typeKey}
                    type="button"
                    onClick={() => setSelectedTaskType(f.typeKey)}
                    className={cn(
                      'px-2 py-0.5 rounded border transition-colors cursor-pointer whitespace-nowrap',
                      selectedTaskType === f.typeKey
                        ? 'bg-primary/10 text-primary border-primary/30 font-medium'
                        : 'bg-muted/20 text-muted-foreground hover:bg-muted/40',
                    )}
                  >
                    {isZh ? f.nameZh : f.nameEn}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* View 1: 8 任务流转全景 (Task Flows) */}
          {activeTab === 'flows' && (
            <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
              {filteredFlows.map((flow, flowIdx) => {
                const steps = flow.stepIds
                  .map((id) => ALL_PANORAMA_STEPS.find((s) => s.id === id))
                  .filter((s): s is PanoramaStepDef => s !== undefined)

                return (
                  <div
                    key={flow.typeKey}
                    className="flex flex-col rounded-lg border bg-background/80 p-3 shadow-2xs space-y-2"
                  >
                    {/* Task Title Row */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-muted-foreground text-xs font-semibold">
                          #{flowIdx + 1}
                        </span>
                        <span className="font-sans font-bold text-xs text-foreground">
                          {isZh ? flow.nameZh : flow.nameEn}
                        </span>
                        <span className="font-mono text-[11px] text-muted-foreground bg-muted/40 px-1 rounded border border-border/50">
                          {flow.typeKey}
                        </span>
                      </div>
                      <Badge variant="outline" className="text-[11px] font-mono px-1.5 py-0">
                        {steps.length} {isZh ? '道工序' : 'steps'}
                      </Badge>
                    </div>

                    {/* Step Chain */}
                    <div className="grid gap-1.5">
                      {steps.map((st, sIdx) => (
                        <div
                          key={st.id}
                          className="flex items-center justify-between rounded-md border bg-muted/15 px-2.5 py-1.5 text-xs"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="font-mono text-muted-foreground text-[11px] font-medium shrink-0">
                              {sIdx + 1}.
                            </span>
                            <span className="font-medium text-foreground text-xs truncate">
                              {isZh ? st.nameZh : st.nameEn}
                            </span>
                            <span className="font-mono text-[11px] text-muted-foreground bg-muted/50 px-1.5 py-0.2 rounded border border-border/40 shrink-0">
                              {isZh ? st.unitZh : st.unitEn}
                            </span>
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0 ml-2">
                            <ArrowRightIcon className="size-2.5 text-muted-foreground/40" />
                            <Badge
                              variant="outline"
                              className="text-[11px] font-sans font-normal px-1.5 py-0 bg-background text-foreground/85 border-border/70"
                            >
                              <CpuIcon className="size-2.5 mr-1 text-primary/70" />
                              {isZh ? st.engineNameZh : st.engineNameEn}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* View 2: 23 道工序总字典矩阵 (Step Matrix) */}
          {activeTab === 'matrix' && (
            <div className="overflow-x-auto rounded-lg border bg-background/80">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b bg-muted/40 text-muted-foreground text-[11px]">
                    <th className="px-3 py-2 font-medium w-12 text-center">#</th>
                    <th className="px-3 py-2 font-medium w-36">{isZh ? '工序名称' : 'Step Name'}</th>
                    <th className="px-3 py-2 font-medium w-36">{isZh ? '承接执行引擎' : 'Assigned Engine'}</th>
                    <th className="px-3 py-2 font-medium w-24">{isZh ? '量化单位' : 'Unit'}</th>
                    <th className="px-3 py-2 font-medium w-48">{isZh ? '所属业务任务' : 'Task Types'}</th>
                    <th className="px-3 py-2 font-medium">{isZh ? '物理职责说明' : 'Physical Responsibility'}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60 font-mono text-[11px]">
                  {ALL_PANORAMA_STEPS.map((st, i) => (
                    <tr key={st.id} className="hover:bg-muted/20 transition-colors">
                      <td className="px-3 py-2 text-center text-muted-foreground font-semibold">{i + 1}</td>
                      <td className="px-3 py-2 font-sans font-semibold text-foreground text-xs">
                        {isZh ? st.nameZh : st.nameEn}
                      </td>
                      <td className="px-3 py-2">
                        <span className="inline-flex items-center gap-1 font-sans text-foreground bg-muted/50 px-1.5 py-0.5 rounded border border-border/50">
                          <CpuIcon className="size-2.5 text-primary" />
                          {isZh ? st.engineNameZh : st.engineNameEn}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-mono text-muted-foreground font-medium">
                        {isZh ? st.unitZh : st.unitEn}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          {st.taskTypes.map((tKey) => {
                            const matchFlow = TASK_FLOWS.find((f) => f.typeKey === tKey)
                            return (
                              <span
                                key={tKey}
                                className="font-sans text-[11px] bg-secondary/80 text-foreground px-1.5 py-0.2 rounded border border-border/40"
                              >
                                {isZh ? matchFlow?.nameZh ?? tKey : matchFlow?.nameEn ?? tKey}
                              </span>
                            )
                          })}
                        </div>
                      </td>
                      <td className="px-3 py-2 font-sans text-muted-foreground text-[11px]">
                        <div>{isZh ? st.descriptionZh : st.descriptionEn}</div>
                        {st.operators && st.operators.length > 0 && (
                          <div className="mt-1 flex items-center gap-1 font-mono text-[11px] text-foreground/80">
                            <span className="text-muted-foreground">{isZh ? '执行算子：' : 'Operators:'}</span>
                            {st.operators.map((op, opIdx) => (
                              <React.Fragment key={op}>
                                <span className="bg-muted/70 px-1 py-0.2 rounded border border-border/50 text-[11px]">{op}</span>
                                {opIdx < st.operators!.length - 1 && <span className="text-muted-foreground/60">➔</span>}
                              </React.Fragment>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* View 3: 7 大执行引擎承接图 (Engine Mappings) */}
          {activeTab === 'engines' && (
            <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2 lg:grid-cols-3">
              {ENGINE_DEFINITIONS.map((eng) => {
                const assignedSteps = ALL_PANORAMA_STEPS.filter((s) => s.engineKey === eng.key)

                return (
                  <div
                    key={eng.key}
                    className="flex flex-col rounded-lg border bg-background/80 p-3 shadow-2xs space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                          <CpuIcon className="size-3.5" />
                        </div>
                        <div>
                          <span className="font-sans font-bold text-xs text-foreground block">
                            {isZh ? eng.nameZh : eng.nameEn}
                          </span>
                          <span className="font-mono text-[11px] text-muted-foreground">
                            {eng.key}
                          </span>
                        </div>
                      </div>
                      <Badge variant="outline" className="text-[11px] font-mono px-1.5 py-0">
                        {assignedSteps.length} {isZh ? '道工序' : 'steps'}
                      </Badge>
                    </div>

                    <p className="text-[11px] text-muted-foreground font-sans">
                      {isZh ? eng.descZh : eng.descEn}
                    </p>

                    <div className="space-y-1 pt-1 border-t border-border/60 mt-auto">
                      <span className="text-[11px] font-medium text-muted-foreground font-sans block">
                        {isZh ? '承接工序清单：' : 'Assigned Steps:'}
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {assignedSteps.map((st) => (
                          <span
                            key={st.id}
                            className="font-sans text-[11px] bg-muted/50 text-foreground px-1.5 py-0.5 rounded border border-border/50"
                          >
                            {isZh ? st.nameZh : st.nameEn}
                            <span className="font-mono text-muted-foreground ml-1">({isZh ? st.unitZh : st.unitEn})</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
