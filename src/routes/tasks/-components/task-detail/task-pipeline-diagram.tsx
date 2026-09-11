import { useMemo, useState } from 'react'
import { BrainCircuitIcon, ChevronUpIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '#/components/ui/button'
import {
  UniversalMemoryImpact,
  deriveMemoryType,
} from '#/components/memory-impact'
import type { SessionMeta } from '@ov-server/api/v1/sessions'
import type { UniversalMemoryDiffOperation } from '#/components/memory-impact/types'
import { cn } from '#/lib/utils'
import type { ParsedQueueRow } from '#/routes/monitoring/-components/queue-status-card'
import { normalizeTaskStatus } from '../../-lib/task-record'
import type { TaskRecord } from '../../-lib/task-record'
import {
  getTaskFinalOutcome,
  getTaskPipelineGroups,
} from '../../-lib/task-pipeline'
import type { PipelineStep } from '../../-lib/task-pipeline'
import { DetailSection } from './task-detail-common'

interface TaskPipelineDiagramProps {
  task: TaskRecord
  effectiveQueueRows: ParsedQueueRow[]
}

export function TaskPipelineDiagram({
  task,
  effectiveQueueRows,
}: TaskPipelineDiagramProps) {
  const { i18n, t } = useTranslation('tasksPage')
  const [impactExpanded, setImpactExpanded] = useState(false)
  const groups = getTaskPipelineGroups(task, effectiveQueueRows, i18n.language)
  const outcome = getTaskFinalOutcome(task, i18n.language)
  const isDoneAll = normalizeTaskStatus(task.status) === 'completed'

  const isSessionTask = task.task_type === 'session_commit'
  const resObj = (task.result && typeof task.result === 'object' ? task.result : {}) as Record<string, any>
  const metaObj = task.meta || {}

  const sessionId = isSessionTask
    ? (resObj.session_id || task.resource_id || metaObj.session_id)
    : undefined
  const sessionProp = sessionId
    ? ({
        session_id: String(sessionId),
        commit_count: Math.max(1, Number(resObj.commit_count || metaObj.commit_count || 1)),
      } as SessionMeta)
    : undefined

  const operationsProp = useMemo<UniversalMemoryDiffOperation[] | undefined>(() => {
    if (isSessionTask) return undefined

    const ops: UniversalMemoryDiffOperation[] = []
    const mainUri = resObj.root_uri || resObj.uri || task.resource_id || metaObj.source_path
    const rawAction = String(resObj.action || metaObj.action || 'add').toLowerCase()
    const kind =
      rawAction === 'delete' || rawAction === 'purge'
        ? ('delete' as const)
        : rawAction === 'update'
          ? ('update' as const)
          : ('add' as const)

    const defaultNotice = t('detail.resourcePersistedNotice', {
      defaultValue: '已成功存储落盘至向量索引中，状态正常。',
    })

    // 1. 若任务携带多 items/results/affected_uris 列表
    const rawItems = Array.isArray(resObj.items)
      ? resObj.items
      : Array.isArray(resObj.results)
        ? resObj.results
        : Array.isArray(resObj.affected_uris)
          ? resObj.affected_uris.map((u: string) => ({ uri: u }))
          : []

    if (rawItems.length > 0) {
      for (const it of rawItems) {
        const itUri = typeof it === 'string' ? it : it.uri || it.path
        if (!itUri) continue
        const itAction = (typeof it === 'object' && it.action ? String(it.action) : kind) as any
        ops.push({
          kind: itAction === 'delete' ? 'delete' : itAction === 'update' ? 'update' : 'add',
          uri: String(itUri),
          memoryType: deriveMemoryType(String(itUri)),
          description: (typeof it === 'object' && it.description) ? String(it.description) : undefined,
          after: (typeof it === 'object' && it.content) ? String(it.content) : defaultNotice,
        })
      }
    }

    // 2. 主 URI 登记
    if (mainUri && !ops.some((o) => o.uri === String(mainUri))) {
      const afterContent =
        resObj.summary_snippet ||
        resObj.text_snippet ||
        resObj.content ||
        resObj.message ||
        (resObj.deliverable?.label ? `${resObj.deliverable.label}: ${mainUri}` : undefined) ||
        defaultNotice

      const desc =
        resObj.message || metaObj.human_title || metaObj.message || resObj.reason || undefined

      ops.push({
        kind,
        memoryType: deriveMemoryType(String(mainUri)),
        uri: String(mainUri),
        description: desc ? String(desc) : undefined,
        after: afterContent ? String(afterContent) : undefined,
      })
    }

    return ops.length > 0 ? ops : undefined
  }, [task, isSessionTask, resObj, metaObj, t])

  const hasMemoryImpact = isDoneAll && (Boolean(sessionId) || Boolean(operationsProp && operationsProp.length > 0))
  let runningStepIndex = 0

  const renderMetrics = (st: PipelineStep) => {
    // 1. 若工序尚未开始（等待前置工序交付），统一展示标准中性胶囊与连贯文案 (SSOT)
    if (st.state === 'pending') {
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-medium select-none shrink-0 bg-muted/50 text-muted-foreground border border-border/40">
          {t('detail.pendingPreceding', { defaultValue: '待前置交付' })}
        </span>
      )
    }

    // 2. 若工序正在执行中 (Running)
    if (st.state === 'running') {
      const hasValidFraction =
        st.processed !== undefined &&
        st.total !== undefined &&
        st.total > 0 &&
        !(st.total === 1 && st.processed === 0)

      if (hasValidFraction) {
        return (
          <span className="font-mono font-medium text-foreground bg-muted/60 px-2 py-0.5 rounded border border-border/60 tabular-nums">
            {(st.processed ?? 0).toLocaleString()} / {st.total!.toLocaleString()} {st.unit ?? ''}
          </span>
        )
      }

      if (st.processed !== undefined && st.processed > 0) {
        return (
          <span className="font-mono font-medium text-foreground bg-muted/60 px-2 py-0.5 rounded border border-border/60 tabular-nums">
            {st.processed.toLocaleString()} {st.unit ?? ''}
          </span>
        )
      }

      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-medium select-none shrink-0 bg-primary/10 text-primary border border-primary/20 flex items-center gap-1.5">
          <span className="size-1.5 rounded-full bg-primary animate-ping" />
          {t('detail.stepRunningText', { defaultValue: '正在执行' })}
        </span>
      )
    }

    // 3. 若工序已完成 (Completed)
    if (st.state === 'completed') {
      const hasFraction = st.processed !== undefined && st.total !== undefined && st.total > 0
      if (hasFraction && st.total !== undefined && st.total >= 1) {
        return (
          <span className="font-mono font-medium text-foreground bg-muted/60 px-2 py-0.5 rounded border border-border/60 tabular-nums">
            {(st.processed ?? 0).toLocaleString()} / {st.total.toLocaleString()} {st.unit ?? ''}
          </span>
        )
      }
      const countVal = st.count ?? st.processed ?? st.total
      if (countVal !== undefined && countVal > 0) {
        return (
          <span className="font-mono font-medium text-foreground bg-muted/60 px-2 py-0.5 rounded border border-border/60 tabular-nums">
            {countVal.toLocaleString()} {st.unit ?? ''}
          </span>
        )
      }
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-medium select-none shrink-0 bg-muted/40 text-muted-foreground border border-border/30">
          {t('detail.stepCompletedText', { defaultValue: '已完成' })}
        </span>
      )
    }

    return (
      <span className="px-2 py-0.5 rounded text-[11px] font-medium select-none shrink-0 bg-muted/30 text-muted-foreground/60 border border-border/30">
        --
      </span>
    )
  }

  return (
    <DetailSection title={t('detail.pipelineSteps')}>
      <div className="rounded-xl border bg-muted/20 p-3 text-xs space-y-2.5 min-w-0 overflow-hidden">
        <div className="grid gap-2 min-w-0">
          {groups.map((group, i) => {
            if (group.type === 'serial') {
              runningStepIndex += 1
              const currentNum = runningStepIndex

              return (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-lg border bg-background/80 px-3.5 py-2.5 shadow-2xs"
                >
                  <div className="flex items-center gap-2 min-w-0 pr-2">
                    <span className="font-mono text-muted-foreground text-[11px] font-semibold">
                      {currentNum}.
                    </span>
                    <span className="font-medium text-foreground text-xs">
                      {group.step.name}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] shrink-0">
                    {group.step.detail && (
                      <span className="font-mono text-muted-foreground bg-muted/40 px-1.5 py-0.5 rounded border border-border/40 text-[11px]">
                        {group.step.detail}
                      </span>
                    )}
                    {renderMetrics(group.step)}
                  </div>
                </div>
              )
            }

            // Parallel Steps: 50/50 side-by-side sibling cards
            return (
              <div key={i} className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {group.steps.map((st, sIdx) => {
                  runningStepIndex += 1
                  const currentNum = runningStepIndex

                  return (
                    <div
                      key={sIdx}
                      className="flex items-center justify-between rounded-lg border bg-background/80 px-3.5 py-2.5 shadow-2xs"
                    >
                      <div className="flex items-center gap-2 min-w-0 pr-1.5">
                        <span className="font-mono text-muted-foreground text-[11px] font-semibold">
                          {currentNum}.
                        </span>
                        <span className="font-medium text-foreground text-xs truncate">
                          {st.name}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-[11px] shrink-0">
                        {st.detail && (
                          <span className="font-mono text-muted-foreground bg-muted/40 px-1.5 py-0.5 rounded border border-border/40 text-[11px]">
                            {st.detail}
                          </span>
                        )}
                        {renderMetrics(st)}
                      </div>
                    </div>
                  )
                })}
              </div>
            )
          })}

          {/* 终点工序：最终输出的结果 */}
          {(() => {
            runningStepIndex += 1
            const finalNum = runningStepIndex

            return (
              <div
                className={cn(
                  'flex items-center justify-between rounded-lg border px-3.5 py-2.5 shadow-2xs transition-colors',
                  isDoneAll
                    ? 'border-primary/30 bg-primary/5'
                    : 'border-dashed border-border/80 bg-muted/20',
                )}
              >
                <div className="flex items-center gap-2.5 min-w-0 pr-2">
                  <span className="font-mono text-primary text-[11px] font-semibold">
                    {finalNum}.
                  </span>
                  <div className="flex flex-col min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-foreground text-xs">
                        {outcome.title}
                      </span>
                      <span className="text-[11px] font-mono text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded border border-border/60">
                        {t('detail.finalDeliverable', {
                          defaultValue: '最终输出结果',
                        })}
                      </span>
                    </div>
                    <span className="text-[11px] text-muted-foreground truncate mt-0.5">
                      {isDoneAll
                        ? outcome.deliverableText
                        : `${t('detail.expectedOutputPrefix', { defaultValue: '预期产出：' })}${outcome.expectedText}`}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-[11px] shrink-0">
                  {hasMemoryImpact && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-6 px-2 text-[11px] gap-1 text-cyan-600 dark:text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/10 font-medium cursor-pointer"
                      onClick={() => setImpactExpanded((prev) => !prev)}
                    >
                      <BrainCircuitIcon className="size-3" />
                      <span>
                        {impactExpanded
                          ? t('detail.hideMemoryImpact', { defaultValue: '收起记忆影响' })
                          : t('detail.viewMemoryImpact', { defaultValue: '查看记忆影响' })}
                      </span>
                      <ChevronUpIcon
                        className={cn(
                          'size-3 transition-transform duration-200',
                          !impactExpanded && 'rotate-180',
                        )}
                      />
                    </Button>
                  )}
                  <span
                    className={cn(
                      'px-2 py-0.5 rounded text-[11px] font-medium select-none shrink-0 border',
                      isDoneAll
                        ? 'bg-secondary text-foreground font-semibold border-border/60'
                        : task.status === 'failed'
                          ? 'bg-destructive/10 text-destructive border-destructive/20'
                          : 'bg-muted/50 text-muted-foreground border-border/40',
                    )}
                  >
                    {isDoneAll
                      ? t('detail.delivered', { defaultValue: '已就绪' })
                      : task.status === 'failed'
                        ? t('detail.aborted', { defaultValue: '交付中断' })
                        : t('detail.pendingPreceding', {
                            defaultValue: '待前置交付',
                          })}
                  </span>
                </div>
              </div>
            )
          })()}

          {/* 任务记忆增量审计快照 (原子化通用组件) */}
          {hasMemoryImpact && impactExpanded && (
            <UniversalMemoryImpact
              session={sessionProp}
              operations={operationsProp}
              title={t('detail.memoryImpactTitle', { defaultValue: '任务记忆增量审计快照' })}
            />
          )}
        </div>
      </div>
    </DetailSection>
  )
}
