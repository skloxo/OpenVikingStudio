import { useTranslation } from 'react-i18next'
import {
  CheckIcon,
  CircleDashedIcon,
  CircleXIcon,
  LoaderCircleIcon,
  RotateCcwIcon,
  Trash2Icon,
} from 'lucide-react'

import { Badge } from '#/components/ui/badge'
import type { ParsedQueueRow } from '#/routes/monitoring/-components/queue-status-card'
import { getEffectiveTaskStatus } from '#/routes/tasks/-lib/task-api'
import { getTaskExecutionDynamic } from '#/routes/tasks/-lib/task-pipeline'
import { normalizeTaskStatus } from '#/routes/tasks/-lib/task-record'
import type { TaskRecord } from '#/routes/tasks/-lib/task-record'
import { formatTaskDuration } from '#/routes/tasks/-lib/task-time'

interface TaskExecutionCellProps {
  task: TaskRecord
  allTasks: TaskRecord[]
  queueObserverRows: ParsedQueueRow[]
  isRetryingTask: (taskId?: string) => boolean
  onRetryTask: (task: TaskRecord) => void
  onDeleteTask: (taskId: string) => void
  isDeleting: boolean
}

export function TaskExecutionCell({
  task,
  allTasks,
  queueObserverRows,
  isRetryingTask,
  onRetryTask,
  onDeleteTask,
  isDeleting,
}: TaskExecutionCellProps) {
  const { i18n, t } = useTranslation('tasksPage')
  const taskId = task.task_id
  const dynamic = getTaskExecutionDynamic(task, queueObserverRows, i18n.language)
  const effStatus = getEffectiveTaskStatus(task, allTasks)
  const status = normalizeTaskStatus(effStatus)
  const durationText = formatTaskDuration(task, i18n.language.startsWith('zh'))
  const isRetrying = isRetryingTask(taskId)

  // 1. 已完成：仅状态徽章 + 耗时
  if (status === 'completed') {
    return (
      <div className="flex items-center gap-2 py-0.5 select-none text-foreground/85">
        <Badge
          variant="outline"
          className="text-[11px] px-1.5 py-0 h-5 border-border/60 text-muted-foreground bg-muted/30 font-sans font-medium shrink-0"
        >
          <CheckIcon className="size-2.5 stroke-[2.5] mr-1 text-primary" />
          {t('status.completed')}
        </Badge>
        {durationText && (
          <span className="font-mono text-[11px] text-muted-foreground/70 shrink-0 select-none tabular-nums">
            · {durationText}
          </span>
        )}
      </div>
    )
  }

  // 2. 进行中：并发工序胶囊
  if (status === 'running') {
    const stepPairs =
      dynamic.activeStepPairs && dynamic.activeStepPairs.length > 0
        ? dynamic.activeStepPairs
        : [{ name: dynamic.activeStepName, metric: dynamic.workloadText }]

    return (
      <div className="flex items-center gap-2 py-0.5 select-none whitespace-nowrap text-xs">
        <Badge
          variant="outline"
          className="text-[11px] px-1.5 py-0 h-5 border-primary/30 text-primary bg-primary/10 font-sans font-medium shrink-0"
        >
          <LoaderCircleIcon className="size-2.5 shrink-0 animate-spin mr-1 text-primary" />
          {t('status.running')}
        </Badge>
        {durationText && (
          <span className="font-mono text-[11px] text-muted-foreground/70 tabular-nums shrink-0">
            · {durationText}
          </span>
        )}
        <div className="flex items-center gap-1.5 shrink-0">
          {stepPairs.map((pair, idx) => (
            <div
              key={pair.name || idx}
              className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs bg-muted/40 text-foreground/85 border border-border/50 font-sans shrink-0"
            >
              <span className="font-medium text-foreground/90">{pair.name}</span>
              {pair.metric && (
                <>
                  <span className="text-muted-foreground/40 font-mono text-[10px] select-none">·</span>
                  <span className="font-mono text-[11px] text-muted-foreground tabular-nums">{pair.metric}</span>
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    )
  }

  // 3. 排队中：等待态
  if (status === 'pending') {
    return (
      <div className="flex items-center gap-2 py-0.5 text-muted-foreground select-none whitespace-nowrap text-xs">
        <Badge
          variant="outline"
          className="text-[11px] px-1.5 py-0 h-5 border-border/60 text-muted-foreground bg-muted/20 font-sans font-medium shrink-0"
        >
          <CircleDashedIcon className="size-2.5 mr-1 text-muted-foreground/60" />
          {t('status.pending', { defaultValue: '等待中' })}
        </Badge>
        {durationText && (
          <span className="font-mono text-[11px] text-muted-foreground/60 shrink-0 select-none tabular-nums">
            · {durationText}
          </span>
        )}
      </div>
    )
  }

  // 4. 失败：带重试与删除操作
  return (
    <div className="flex items-center gap-2 py-0.5 text-destructive select-none whitespace-nowrap text-xs">
      <Badge
        variant="destructive"
        className="text-[11px] px-1.5 py-0 h-5 font-sans font-medium shrink-0 gap-1"
      >
        <CircleXIcon className="size-2.5 mr-0.5" />
        {t('status.failed')}
        <button
          type="button"
          disabled={isRetrying}
          className="ml-1 inline-flex items-center justify-center rounded p-0.5 hover:bg-white/25 active:scale-95 transition-all cursor-pointer text-destructive-foreground disabled:opacity-50"
          title={t('pipeline.retrigger')}
          onClick={(e) => {
            e.stopPropagation()
            onRetryTask(task)
          }}
        >
          {isRetrying ? (
            <LoaderCircleIcon className="size-2.5 shrink-0 animate-spin" />
          ) : (
            <RotateCcwIcon className="size-2.5 shrink-0" />
          )}
        </button>
        <button
          type="button"
          disabled={isDeleting}
          className="ml-0.5 inline-flex items-center justify-center rounded p-0.5 hover:bg-white/25 active:scale-95 transition-all cursor-pointer text-destructive-foreground disabled:opacity-50"
          title={t('pipeline.deleteTask')}
          onClick={(e) => {
            e.stopPropagation()
            if (task.task_id) {
              onDeleteTask(task.task_id)
            }
          }}
        >
          <Trash2Icon className="size-2.5 shrink-0" />
        </button>
      </Badge>
      {durationText && (
        <span className="font-mono text-[11px] text-destructive/70 shrink-0 select-none tabular-nums">
          · {durationText}
        </span>
      )}
    </div>
  )
}
