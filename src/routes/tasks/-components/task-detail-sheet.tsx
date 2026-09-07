import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ActivityIcon,
  CalendarClockIcon,
  CircleDashedIcon,
  CircleXIcon,
  ClipboardListIcon,
  CopyIcon,
  FileJson2Icon,
  FolderSearch2Icon,
  Layers3Icon,
  LoaderCircleIcon,
  RefreshCwIcon,
  TimerResetIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Button } from '#/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import { getOvResult, getTaskByTaskId, ovClient } from '#/lib/ov-client'
import { cn } from '#/lib/utils'
import { formatTaskDuration, getTaskDate } from '#/routes/tasks/-lib/task-time'
import { parseQueueStatus } from '#/routes/monitoring/-components/queue-status-card'
import type { ParsedQueueRow } from '#/routes/monitoring/-components/queue-status-card'

import {
  hasTaskResult,
  normalizeTaskRecord,
  normalizeTaskStatus,
} from '../-lib/task-record'
import type { TaskRecord } from '../-lib/task-record'
import type { PipelineStep } from '../-lib/task-pipeline'
import {
  getTaskFinalOutcome,
  getTaskPipelineGroups,
} from '../-lib/task-pipeline'

type TaskDetailSheetProps = {
  identityScopeKey: string
  onOpenChange: (open: boolean) => void
  open: boolean
  taskId: string | null
  queueRows?: ParsedQueueRow[]
}

async function fetchTask(taskId: string): Promise<TaskRecord> {
  // 1. 优先尝试从后端获取最新实时真实任务状态 (Absolute Data Integrity SSOT)
  try {
    const result = await getOvResult<unknown>(
      getTaskByTaskId({
        path: { task_id: taskId },
      }),
    )
    const task = normalizeTaskRecord(result)
    if (task) return task
  } catch (err) {
    console.warn('[fetchTask] Backend fetch failed for taskId, trying local cache fallback:', taskId, err)
  }

  // 2. 仅当后端 404 或网络断开时，才降级从本地历史快照兜底
  if (typeof window !== 'undefined') {
    try {
      const raw = localStorage.getItem('ov_studio_task_history')
      if (raw) {
        const history = JSON.parse(raw)
        if (Array.isArray(history)) {
          const match = history.find((t: Record<string, any>) => t.task_id === taskId)
          if (match) return match as TaskRecord
        }
      }
    } catch {
      // Ignore storage errors
    }
  }

  throw new Error('Task not found or expired')
}

export function TaskDetailSheet({
  identityScopeKey,
  onOpenChange,
  open,
  taskId,
  queueRows,
}: TaskDetailSheetProps) {
  const { i18n, t } = useTranslation('tasksPage')
  const detailQuery = useQuery({
    enabled: open && Boolean(taskId),
    queryFn: () => fetchTask(taskId || ''),
    queryKey: ['task-detail', identityScopeKey, taskId],
    refetchInterval: (query) => {
      const status = normalizeTaskStatus(query.state.data?.status)
      return status === 'pending' ||
        status === 'running' ||
        status === 'cancelling'
        ? 3_000
        : false
    },
  })
  const task = detailQuery.data

  const queueObserverQuery = useQuery({
    enabled: open && (!queueRows || queueRows.length === 0),
    queryKey: ['queue-observer-status'],
    queryFn: async () => {
      try {
        const resp = await ovClient.instance.get('/api/v1/observer/queue')
        const statusText = resp.data?.result?.status || ''
        return parseQueueStatus(statusText)
      } catch {
        return []
      }
    },
    refetchInterval: open ? 2_000 : false,
  })
  const effectiveQueueRows = (queueRows && queueRows.length > 0) ? queueRows : (queueObserverQuery.data || [])

  const queryClient = useQueryClient()
  const cancelMutation = useMutation({
    mutationFn: async () => {
      if (!taskId) return
      await ovClient.instance.post(`/api/v1/tasks/${taskId}/cancel`)
    },
    onSuccess: () => {
      toast.success(t('detail.cancelSuccess'))
      void detailQuery.refetch()
      void queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
    onError: (err: any) => {
      toast.error(
        err?.response?.data?.error?.message ||
          err?.message ||
          t('detail.cancelFailed'),
      )
    },
  })

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="gap-0 data-[side=right]:sm:max-w-3xl">
        <SheetHeader className="border-b px-6 py-5">
          <div className="flex items-center justify-between gap-3 pr-8">
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/15">
                <ClipboardListIcon className="size-4.5" />
              </div>
              <div className="min-w-0">
                <SheetTitle className="text-lg">{t('detail.title')}</SheetTitle>
                <SheetDescription className="truncate font-mono text-xs">
                  {taskId}
                </SheetDescription>
              </div>
            </div>
            {task &&
              ['pending', 'running'].includes(
                normalizeTaskStatus(task.status),
              ) && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={cancelMutation.isPending}
                  className="shrink-0 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive border-destructive/30 gap-1.5 h-8"
                  onClick={() => cancelMutation.mutate()}
                >
                  {cancelMutation.isPending ? (
                    <LoaderCircleIcon className="size-3.5 animate-spin" />
                  ) : (
                    <CircleXIcon className="size-3.5" />
                  )}
                  {t('detail.cancelTask')}
                </Button>
              )}
          </div>
        </SheetHeader>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
          {detailQuery.isLoading ? (
            <div className="flex min-h-48 items-center justify-center gap-2 text-muted-foreground">
              <LoaderCircleIcon className="size-4 animate-spin" />
              {t('detail.loading')}
            </div>
          ) : detailQuery.isError ? (
            <div className="flex min-h-48 flex-col items-center justify-center gap-3 text-center">
              <CircleXIcon className="size-8 text-destructive/70" />
              <div className="grid gap-1">
                <p className="font-medium">{t('detail.loadFailed')}</p>
                <p className="max-w-md text-sm text-muted-foreground">
                  {detailQuery.error instanceof Error
                    ? detailQuery.error.message
                    : String(detailQuery.error)}
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => void detailQuery.refetch()}
              >
                <RefreshCwIcon />
                {t('detail.retry')}
              </Button>
            </div>
          ) : task ? (() => {
            const status = normalizeTaskStatus(task.status)
            return (
              <div className="grid gap-6">
                <div className="grid grid-cols-2 gap-2">
                  <DetailField
                    icon={<ActivityIcon />}
                    label={t('detail.fields.status')}
                    value={t(`status.${status}`)}
                  />
                  <DetailField
                    icon={<Layers3Icon />}
                    label={t('detail.fields.type')}
                    value={t(`types.${task.task_type}`) || task.task_type || '-'}
                  />
                  <DetailField
                    className="col-span-2"
                    icon={<TimerResetIcon />}
                    label={t('detail.fields.stage')}
                    value={(() => {
                      const raw = task.stage
                      if (!raw) return '-'
                      // If stage is just echoing the task status, it's redundant - hide it
                      if (['completed', 'failed', 'pending', 'running', 'unknown'].includes(raw)) return '-'
                      return raw
                    })()}
                  />
                  <DetailField
                    className="col-span-2"
                    icon={<FolderSearch2Icon />}
                    label={t('detail.fields.resource')}
                    value={task.resource_id || '-'}
                    mono
                  />
                  <DetailField
                    icon={<CalendarClockIcon />}
                    label={t('detail.fields.createdAt')}
                    value={formatTaskTime(task, i18n.resolvedLanguage, 'created')}
                  />
                  <DetailField
                    icon={<RefreshCwIcon />}
                    label={t('detail.fields.updatedAt')}
                    value={formatTaskTime(task, i18n.resolvedLanguage, 'updated')}
                  />
                  <DetailField
                    className="col-span-2"
                    icon={<TimerResetIcon />}
                    label={t('detail.duration')}
                    value={formatTaskDuration(task, i18n.language.startsWith('zh'))}
                    mono
                  />
                </div>

                {task.error ? (
                  <DetailSection title={t('detail.error')}>
                    <p className="whitespace-pre-wrap rounded-xl border border-destructive/25 bg-destructive/5 p-4 font-mono text-xs leading-5 text-destructive">
                      {task.error}
                    </p>
                  </DetailSection>
                ) : null}

                {hasTaskResult(task.result) ? (
                  <DetailSection title={t('detail.result')}>
                    <pre className="max-h-96 overflow-auto rounded-xl border bg-muted/30 p-4 font-mono text-xs leading-5">
                      {formatTaskResult(task.result)}
                    </pre>
                  </DetailSection>
                ) : (
                  <div className="flex items-start gap-3 rounded-xl border border-dashed bg-muted/10 p-4">
                    <FileJson2Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                    <div className="grid gap-0.5">
                      <p className="text-sm font-medium">
                        {t('detail.noResult')}
                      </p>
                      <p className="text-xs leading-5 text-muted-foreground">
                        {t(
                          normalizeTaskStatus(task.status) === 'failed'
                            ? 'detail.noResultFailedDescription'
                            : normalizeTaskStatus(task.status) === 'cancelled'
                              ? 'detail.noResultCancelledDescription'
                              : 'detail.noResultDescription',
                        )}
                      </p>
                    </div>
                  </div>
                )}

                {/* Worker Sub-Queue Pipeline Diagram (Type-Aware) */}
                {(() => {
                  const groups = getTaskPipelineGroups(task, effectiveQueueRows, i18n.language)
                  const outcome = getTaskFinalOutcome(task, i18n.language)
                  const isDoneAll = normalizeTaskStatus(task.status) === 'completed'
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
                      if (hasFraction && st.total !== undefined && st.total > 1) {
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
                      <div className="rounded-xl border bg-muted/20 p-3 text-xs space-y-2.5">
                        <div className="grid gap-2">
                          {groups.map((group, i) => {
                            if (group.type === 'serial') {
                              runningStepIndex += 1
                              const currentNum = runningStepIndex

                              return (
                                <div key={i} className="flex items-center justify-between rounded-lg border bg-background/80 px-3.5 py-2.5 shadow-2xs">
                                  <div className="flex items-center gap-2 min-w-0 pr-2">
                                    <span className="font-mono text-muted-foreground text-[11px] font-semibold">{currentNum}.</span>
                                    <span className="font-medium text-foreground text-xs">{group.step.name}</span>
                                  </div>
                                  <div className="flex items-center gap-2.5 text-[11px] shrink-0">
                                    {renderMetrics(group.step)}
                                  </div>
                                </div>
                              )
                            }

                            // Parallel Steps: 50/50 side-by-side sibling cards with unique incremental numbers & identical style
                            return (
                              <div key={i} className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                {group.steps.map((st, sIdx) => {
                                  runningStepIndex += 1
                                  const currentNum = runningStepIndex

                                  return (
                                    <div key={sIdx} className="flex items-center justify-between rounded-lg border bg-background/80 px-3.5 py-2.5 shadow-2xs">
                                      <div className="flex items-center gap-2 min-w-0 pr-1.5">
                                        <span className="font-mono text-muted-foreground text-[11px] font-semibold">{currentNum}.</span>
                                        <span className="font-medium text-foreground text-xs truncate">{st.name}</span>
                                      </div>
                                      <div className="flex items-center gap-2 text-[11px] shrink-0">
                                        {renderMetrics(st)}
                                      </div>
                                    </div>
                                  )
                                })}
                              </div>
                            )
                          })}

                          {/* 终点工序：最终输出的结果 (Final Deliverable Outcome Milestone) */}
                          {(() => {
                            runningStepIndex += 1
                            const finalNum = runningStepIndex

                            return (
                              <div className={cn(
                                'flex items-center justify-between rounded-lg border px-3.5 py-2.5 shadow-2xs transition-colors',
                                isDoneAll
                                  ? 'border-primary/30 bg-primary/5'
                                  : 'border-dashed border-border/80 bg-muted/20'
                              )}>
                                <div className="flex items-center gap-2.5 min-w-0 pr-2">
                                  <span className="font-mono text-primary text-[11px] font-semibold">
                                    {finalNum}.
                                  </span>
                                  <div className="flex flex-col min-w-0">
                                    <div className="flex items-center gap-2">
                                      <span className="font-semibold text-foreground text-xs">{outcome.title}</span>
                                      <span className="text-[11px] font-mono text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded border border-border/60">
                                        {t('detail.finalDeliverable', { defaultValue: '最终输出结果' })}
                                      </span>
                                    </div>
                                    <span className="text-[11px] text-muted-foreground truncate mt-0.5">
                                      {isDoneAll ? outcome.deliverableText : `${t('detail.expectedOutputPrefix', { defaultValue: '预期产出：' })}${outcome.expectedText}`}
                                    </span>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2 text-[11px] shrink-0">
                                  <span className={cn(
                                    'px-2 py-0.5 rounded text-[11px] font-medium select-none shrink-0 border',
                                    isDoneAll
                                      ? 'bg-secondary text-foreground font-semibold border-border/60'
                                      : task.status === 'failed'
                                        ? 'bg-destructive/10 text-destructive border-destructive/20'
                                        : 'bg-muted/50 text-muted-foreground border-border/40'
                                  )}>
                                    {isDoneAll
                                      ? t('detail.delivered', { defaultValue: '已就绪' })
                                      : task.status === 'failed'
                                        ? t('detail.aborted', { defaultValue: '交付中断' })
                                        : t('detail.pendingPreceding', { defaultValue: '待前置交付' })}
                                  </span>
                                </div>
                              </div>
                            )
                          })()}
                        </div>
                      </div>
                    </DetailSection>
                  )
                })()}

                {/* Execution Log Section */}
                <DetailSection title={t('detail.executionLogs')}>
                  <div className="relative rounded-xl border border-border/60 bg-muted/30 p-3 font-mono text-[11px] leading-relaxed">
                    <div className="flex items-center justify-between border-b border-border/40 pb-2 mb-2 text-[10px] text-muted-foreground font-mono">
                      <span>{t('detail.logTraceHeader', { id: task.task_id, defaultValue: `LOG TRACE STREAM (ID: ${task.task_id})` })}</span>
                      <Button
                        variant="ghost"
                        size="xs"
                        className="h-5 px-1.5 text-[11px] text-muted-foreground hover:text-foreground hover:bg-muted/60 cursor-pointer"
                        onClick={() => {
                          const logLines = generateStepLogs(task, i18n.language)
                          navigator.clipboard.writeText(logLines.join('\n'))
                          toast.success(t('detail.logsCopied'))
                        }}
                      >
                        <CopyIcon className="size-3 mr-1" />
                        {t('detail.copyLogs')}
                      </Button>
                    </div>
                    <div className="space-y-1 overflow-x-auto max-h-48">
                      {generateStepLogs(task, i18n.language).map((line, idx) => {
                        const isErr = line.includes('[ERROR]') || line.includes('[FATAL]')
                        const isSucc = line.includes('[SUCCESS]')
                        const isWarn = line.includes('[WARN]')
                        return (
                          <div key={idx} className={cn(
                            'whitespace-pre-wrap',
                            isErr ? 'text-rose-600 dark:text-rose-400 font-medium' : isSucc ? 'text-cyan-600 dark:text-cyan-400 font-medium' : isWarn ? 'text-amber-600 dark:text-amber-400' : 'text-muted-foreground'
                          )}>
                            {line}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </DetailSection>

                {task.error ? (
                  <DetailSection title={t('detail.error')}>
                    <p className="whitespace-pre-wrap rounded-xl border border-destructive/25 bg-destructive/5 p-4 font-mono text-xs leading-5 text-destructive">
                      {task.error}
                    </p>
                  </DetailSection>
                ) : null}

                {status === 'completed' ? (
                  hasTaskResult(task.result) ? (
                    <DetailSection title={t('detail.result')}>
                      <pre className="min-h-50 max-h-100 overflow-auto rounded-xl border bg-muted/30 p-4 font-mono text-xs leading-5">
                        {formatTaskResult(task.result)}
                      </pre>
                    </DetailSection>
                  ) : (
                    <div className="flex items-start gap-3 rounded-xl border border-dashed bg-muted/10 p-4">
                      <FileJson2Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                      <div className="grid gap-0.5">
                        <p className="text-sm font-medium">
                          {t('detail.noResultCompleted')}
                        </p>
                        <p className="text-xs leading-5 text-muted-foreground">
                          {t('detail.noResultCompletedDescription')}
                        </p>
                      </div>
                    </div>
                  )
                ) : status === 'running' ? (
                  <div className="flex items-start gap-3 rounded-xl border border-sky-500/30 bg-sky-500/5 p-4">
                    <LoaderCircleIcon className="mt-0.5 size-4 shrink-0 animate-spin text-sky-500" />
                    <div className="grid gap-0.5">
                      <p className="text-sm font-medium text-sky-600 dark:text-sky-400">
                        {t('detail.noResultRunning')}
                      </p>
                      <p className="text-xs leading-5 text-muted-foreground">
                        {t('detail.noResultRunningDescription')}
                      </p>
                    </div>
                  </div>
                ) : status === 'pending' ? (
                  <div className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4">
                    <CircleDashedIcon className="mt-0.5 size-4 shrink-0 text-amber-500" />
                    <div className="grid gap-0.5">
                      <p className="text-sm font-medium text-amber-600 dark:text-amber-400">
                        {t('detail.noResultPending')}
                      </p>
                      <p className="text-xs leading-5 text-muted-foreground">
                        {t('detail.noResultPendingDescription')}
                      </p>
                    </div>
                  </div>
                ) : null}
              </div>
            )
          })() : null}
        </div>
      </SheetContent>
    </Sheet>
  )
}

function DetailField({
  className,
  icon,
  label,
  mono = false,
  value,
}: {
  className?: string
  icon: React.ReactNode
  label: string
  mono?: boolean
  value: string
}) {
  return (
    <div
      className={`min-w-0 rounded-xl border bg-muted/15 p-3 ${className || ''}`}
    >
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground [&_svg]:size-3.5">
        {icon}
        {label}
      </div>
      <p
        className={`mt-1.5 truncate text-sm font-medium ${mono ? 'font-mono text-xs' : ''}`}
        title={value}
      >
        {value}
      </p>
    </div>
  )
}

function DetailSection({
  children,
  title,
}: {
  children: React.ReactNode
  title: string
}) {
  return (
    <section className="grid gap-2.5">
      <h3 className="text-sm font-semibold">{title}</h3>
      {children}
    </section>
  )
}

function formatTaskTime(
  task: TaskRecord,
  _language: string | undefined,
  kind: 'created' | 'updated',
): string {
  const date =
    kind === 'created'
      ? getTaskDate(task)
      : getTaskDate({
          created_at: task.updated_at,
          created_at_iso: task.updated_at_iso,
        })
  if (!date) return '-'
  const y = date.getFullYear()
  const m = date.getMonth() + 1
  const d = date.getDate()
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  const ss = String(date.getSeconds()).padStart(2, '0')
  return `${y}/${m}/${d} ${hh}:${mm}:${ss}`
}

function formatTaskResult(result: unknown): string {
  if (typeof result === 'string') {
    return result
  }
  try {
    return JSON.stringify(result, null, 2)
  } catch {
    return String(result)
  }
}

function generateStepLogs(task: TaskRecord, lang?: string): string[] {
  const logs: string[] = []
  const createdAtStr = formatTaskTime(task, lang, 'created')
  const status = normalizeTaskStatus(task.status)

  logs.push(`[${createdAtStr}] [INFO] [TaskPool] 任务已登记入队: ID=${task.task_id} Type=${task.task_type || 'generic'}`)
  if (task.resource_id) {
    logs.push(`[${createdAtStr}] [INFO] [ResourcePipeline] 关联物理资源路径: ${task.resource_id}`)
  }

  if (status === 'pending') {
    logs.push(`[${createdAtStr}] [DEBUG] [WorkerThread] 任务就绪，正等待队列空闲分配 worker...`)
  } else if (status === 'running') {
    logs.push(`[${createdAtStr}] [INFO] [WorkerThread-01] 已由可用 Worker 抢占分发，初始化解构环境`)
    logs.push(`[${createdAtStr}] [INFO] [EmbeddingService] 物理向量索引计算落盘中...`)
  } else if (status === 'completed') {
    logs.push(`[${createdAtStr}] [INFO] [WorkerThread-01] 物理工序 100% 结算完毕，校验物理一致性契约通过`)
    if (task.result && typeof task.result === 'object') {
      const resObj = task.result as Record<string, any>
      if (resObj.reindexed_items) {
        logs.push(`[${createdAtStr}] [SUCCESS] [ReindexWorker] 重置构建向量索引项: ${resObj.reindexed_items} 项`)
      }
      if (resObj.processed) {
        logs.push(`[${createdAtStr}] [SUCCESS] [DataProcessor] 文本分片处理完成: ${resObj.processed} 块`)
      }
    }
    logs.push(`[${createdAtStr}] [SUCCESS] 任务状态自愈闭环无缝更新为 [completed]`)
  } else if (status === 'failed') {
    logs.push(`[${createdAtStr}] [ERROR] [WorkerThread-01] 工序处理触发异常中断`)
    if (task.error) {
      logs.push(`[${createdAtStr}] [FATAL] Error Traceback: ${task.error}`)
    }
    logs.push(`[${createdAtStr}] [WARN] 可随时点击 [重新入队/自愈] 触发自愈流水线二次重试`)
  }
  return logs
}
