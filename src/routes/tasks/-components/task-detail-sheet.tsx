import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  CircleXIcon,
  ClipboardListIcon,
  LoaderCircleIcon,
  RefreshCwIcon,
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
import { parseQueueStatus } from '#/routes/monitoring/-components/queue-status-card'
import type { ParsedQueueRow } from '#/routes/monitoring/-components/queue-status-card'

import {
  normalizeTaskRecord,
  normalizeTaskStatus,
  type TaskRecord,
} from '../-lib/task-record'
import {
  TaskOverviewGrid,
  TaskResultOutcomeSummary,
} from './task-detail/task-overview-grid'
import { TaskPipelineDiagram } from './task-detail/task-pipeline-diagram'
import { TaskExecutionLogs } from './task-detail/task-execution-logs'

export type TaskDetailSheetProps = {
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
    console.warn(
      '[fetchTask] Backend fetch failed for taskId, trying local cache fallback:',
      taskId,
      err,
    )
  }

  // 2. 仅当后端 404 或网络断开时，才降级从本地历史快照兜底
  if (typeof window !== 'undefined') {
    try {
      const raw = localStorage.getItem('ov_studio_task_history')
      if (raw) {
        const history = JSON.parse(raw)
        if (Array.isArray(history)) {
          const match = history.find(
            (t: Record<string, any>) => t.task_id === taskId,
          )
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
  const { t } = useTranslation('tasksPage')
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
  const effectiveQueueRows =
    queueRows && queueRows.length > 0
      ? queueRows
      : queueObserverQuery.data || []

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
          ) : task ? (
            <div className="grid gap-6">
              <TaskOverviewGrid task={task} />
              <TaskPipelineDiagram
                task={task}
                effectiveQueueRows={effectiveQueueRows}
              />
              <TaskExecutionLogs task={task} />
              <TaskResultOutcomeSummary task={task} />
            </div>
          ) : null}
        </div>
      </SheetContent>
    </Sheet>
  )
}
