import * as React from 'react'
import { useTranslation } from 'react-i18next'
import {
  CheckIcon,
  ChevronRightIcon,
  CircleDashedIcon,
  CircleXIcon,
  ClipboardListIcon,
  FileTextIcon,
  LoaderCircleIcon,
  RotateCcwIcon,
  Trash2Icon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Card } from '#/components/ui/card'
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from '#/components/ui/pagination'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'
import { cn } from '#/lib/utils'
import { formatFileSize } from '#/routes/resources/-lib/upload'
import type { ParsedQueueRow } from '#/routes/monitoring/-components/queue-status-card'
import type { TaskRecord } from '#/routes/tasks/-lib/task-record'
import { normalizeTaskStatus } from '#/routes/tasks/-lib/task-record'
import { formatTaskDuration } from '#/routes/tasks/-lib/task-time'
import {
  PAGE_SIZE_OPTIONS,
  formatTime,
  getEffectiveTaskStatus,
} from '#/routes/tasks/-lib/task-api'
import { getTaskExecutionDynamic } from '#/routes/tasks/-lib/task-pipeline'

interface TasksTableProps {
  tasks: TaskRecord[]
  allTasks: TaskRecord[]
  isLoading: boolean
  isError: boolean
  error: unknown
  hasActiveFilters: boolean
  selectedTaskId: string | null
  urlTaskId?: string
  page: number
  setPage: React.Dispatch<React.SetStateAction<number>>
  pageSize: number
  setPageSize: (size: number) => void
  totalPages: number
  onSelectTask: (taskId: string) => void
  onRetryTask: (task: TaskRecord) => void
  isRetryingTask: (taskId?: string) => boolean
  onDeleteTask: (taskId: string) => void
  isDeleting: boolean
  queueObserverRows: ParsedQueueRow[]
  maxTasks: number
}

export function TasksTable({
  tasks,
  allTasks,
  isLoading,
  isError,
  error,
  hasActiveFilters,
  selectedTaskId,
  urlTaskId,
  page,
  setPage,
  pageSize,
  setPageSize,
  totalPages,
  onSelectTask,
  onRetryTask,
  isRetryingTask,
  onDeleteTask,
  isDeleting,
  queueObserverRows,
  maxTasks,
}: TasksTableProps) {
  const { i18n, t } = useTranslation('tasksPage')
  const pageOffset = (page - 1) * pageSize
  const hasNext = page < totalPages

  const renderExecutionProgress = (task: TaskRecord) => {
    const taskId = task.task_id
    const dynamic = getTaskExecutionDynamic(
      task,
      queueObserverRows,
      i18n.language,
    )
    const effStatus = getEffectiveTaskStatus(task, allTasks)
    const status = normalizeTaskStatus(effStatus)
    const durationText = formatTaskDuration(task, i18n.language.startsWith('zh'))
    const isRetrying = isRetryingTask(taskId)

    // 1. 已完成：极致素雅（仅状态徽章 + 耗时，详情全部移至抽屉）
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

    // 2. 进行中：并发工序多胶囊并排呈现
    if (status === 'running') {
      const stepPairs = dynamic.activeStepPairs && dynamic.activeStepPairs.length > 0
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

    // 3. 排队中：干净单行等待态
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

  function renderTaskResourceCell(task: TaskRecord) {
    const meta = task.meta && typeof task.meta === 'object' ? task.meta : {}
    const sourceName = meta.source_name || (meta.source_path ? String(meta.source_path).split(/[\\/]/).pop() : null)
    const fileSize = meta.file_size !== undefined ? Number(meta.file_size) : undefined
    const resourceUri = task.resource_id || ''

    if (sourceName || fileSize !== undefined) {
      return (
        <div className="flex flex-col gap-0.5 max-w-72">
          <div className="flex items-center gap-1.5 min-w-0">
            <FileTextIcon className="size-3.5 shrink-0 text-muted-foreground" />
            <span className="truncate text-xs font-medium text-foreground">
              {sourceName || (resourceUri ? resourceUri.split('/').pop() : '-')}
            </span>
            {fileSize !== undefined && (
              <Badge
                variant="outline"
                className="text-[11px] px-1 py-0 h-4 border-border/50 text-muted-foreground bg-muted/20 font-mono shrink-0 tabular-nums"
              >
                {formatFileSize(fileSize)}
              </Badge>
            )}
          </div>
          {resourceUri && (
            <span className="font-mono text-[11px] text-muted-foreground/70 truncate" title={resourceUri}>
              {resourceUri}
            </span>
          )}
        </div>
      )
    }

    return (
      <div className="max-w-72 truncate text-xs text-muted-foreground" title={resourceUri || '-'}>
        {resourceUri || '-'}
      </div>
    )
  }

  if (isLoading) {
    return (
      <Card className="min-h-56 items-center justify-center">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <LoaderCircleIcon className="size-4 animate-spin" />
          {t('loading')}
        </div>
      </Card>
    )
  }

  if (isError) {
    return (
      <Card className="min-h-56 items-center justify-center px-6 text-center">
        <CircleXIcon className="size-8 text-destructive/70" />
        <div className="grid gap-1">
          <p className="font-medium">{t('loadFailed')}</p>
          <p className="max-w-xl text-sm text-muted-foreground">
            {error instanceof Error ? error.message : String(error)}
          </p>
        </div>
      </Card>
    )
  }

  if (tasks.length === 0) {
    return (
      <Card className="min-h-56 items-center justify-center px-6 text-center">
        <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <ClipboardListIcon className="size-5" />
        </div>
        <div className="grid max-w-md gap-1">
          <p className="font-medium">
            {t(hasActiveFilters ? 'emptyFiltered' : 'empty')}
          </p>
          <p className="text-sm text-muted-foreground">
            {t(hasActiveFilters ? 'emptyFilteredDescription' : 'emptyDescription')}
          </p>
        </div>
      </Card>
    )
  }

  return (
    <Card className="gap-0 overflow-hidden py-0">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/20 hover:bg-muted/20">
              <TableHead>{t('table.task')}</TableHead>
              <TableHead>{t('table.type')}</TableHead>
              <TableHead>{t('table.resource')}</TableHead>
              <TableHead>{t('pipeline.pipelineHeader')}</TableHead>
              <TableHead className="text-right">{t('table.createdAt')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks.map((task, index) => {
              const taskId = task.task_id
              return (
                <TableRow
                  key={taskId || String(index)}
                  tabIndex={taskId ? 0 : undefined}
                  aria-label={taskId ? t('detail.openLabel', { taskId }) : undefined}
                  className={cn(
                    taskId &&
                      'cursor-pointer outline-none hover:bg-muted/35 focus-visible:bg-muted/35 focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-inset transition-colors',
                    taskId && (taskId === selectedTaskId || taskId === urlTaskId) && 'ring-1 ring-cyan-500/80 bg-cyan-500/5 dark:bg-cyan-500/10',
                  )}
                  onClick={() => {
                    if (taskId) onSelectTask(taskId)
                  }}
                  onKeyDown={(event) => {
                    if (taskId && (event.key === 'Enter' || event.key === ' ')) {
                      event.preventDefault()
                      onSelectTask(taskId)
                    }
                  }}
                >
                  <TableCell>
                    <span className="flex items-center gap-2">
                      <code className="min-w-0 truncate text-xs">
                        {taskId || `#${pageOffset + index + 1}`}
                      </code>
                      {taskId ? (
                        <ChevronRightIcon className="size-3.5 shrink-0 text-muted-foreground" />
                      ) : null}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs font-medium text-foreground/90 whitespace-nowrap">
                    {task.task_type
                      ? t(`types.${task.task_type}`, {
                          defaultValue: task.task_type,
                        })
                      : '-'}
                  </TableCell>
                  <TableCell className="max-w-72">
                    {renderTaskResourceCell(task)}
                  </TableCell>
                  <TableCell>{renderExecutionProgress(task)}</TableCell>
                  <TableCell className="whitespace-nowrap text-right text-muted-foreground">
                    {formatTime(task)}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      {/* 分页控制栏 */}
      <div className="flex flex-col gap-3 border-t px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col items-center gap-1.5 sm:items-start">
          <div className="flex items-center justify-center gap-3 sm:justify-start">
            <p className="text-sm text-muted-foreground">
              {t('pagination.page', { page })}
            </p>
            <Select
              value={String(pageSize)}
              onValueChange={(value) => {
                setPageSize(Number(value))
                setPage(1)
              }}
            >
              <SelectTrigger size="sm" aria-label={t('pagination.pageSize')}>
                <SelectValue>
                  {t('pagination.pageSizeValue', { count: pageSize })}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZE_OPTIONS.map((option) => (
                  <SelectItem key={option} value={String(option)}>
                    {t('pagination.pageSizeValue', { count: option })}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <p className="text-xs text-muted-foreground">
            {t('pagination.scope', {
              count: allTasks.length,
              limit: maxTasks,
            })}
          </p>
        </div>
        <Pagination className="mx-0 w-auto justify-center sm:justify-end">
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                href="#"
                text={t('pagination.previous')}
                aria-disabled={page <= 1}
                className={cn(page <= 1 && 'pointer-events-none opacity-50')}
                onClick={(event) => {
                  event.preventDefault()
                  if (page > 1) setPage((current) => current - 1)
                }}
              />
            </PaginationItem>
            <PaginationItem>
              <PaginationNext
                href="#"
                text={t('pagination.next')}
                aria-disabled={!hasNext}
                className={cn(!hasNext && 'pointer-events-none opacity-50')}
                onClick={(event) => {
                  event.preventDefault()
                  if (hasNext) setPage((current) => current + 1)
                }}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      </div>
    </Card>
  )
}
