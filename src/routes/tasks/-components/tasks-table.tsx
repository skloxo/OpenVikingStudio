import * as React from 'react'
import { useTranslation } from 'react-i18next'
import {
  ClipboardListIcon,
  CircleXIcon,
  FileTextIcon,
  LoaderCircleIcon,
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
import type { ParsedQueueRow } from '#/routes/monitoring/-components/queue-status-card'
import { formatFileSize } from '#/routes/resources/-lib/upload'
import { TaskExecutionCell } from '#/routes/tasks/-components/task-execution-cell'
import { TaskHumanCell } from '#/routes/tasks/-components/task-human-cell'
import {
  PAGE_SIZE_OPTIONS,
  formatTime,
} from '#/routes/tasks/-lib/task-api'
import type { TaskRecord } from '#/routes/tasks/-lib/task-record'

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
  onOpenDeliverable?: (uri: string) => void
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
  onOpenDeliverable,
}: TasksTableProps) {
  const { t } = useTranslation('tasksPage')
  const pageOffset = (page - 1) * pageSize
  const hasNext = page < totalPages

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
          <p className="font-medium">{t(hasActiveFilters ? 'emptyFiltered' : 'empty')}</p>
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
                    <TaskHumanCell
                      task={task}
                      index={index}
                      pageOffset={pageOffset}
                      onOpenDeliverable={onOpenDeliverable}
                    />
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
                  <TableCell>
                    <TaskExecutionCell
                      task={task}
                      allTasks={allTasks}
                      queueObserverRows={queueObserverRows}
                      isRetryingTask={isRetryingTask}
                      onRetryTask={onRetryTask}
                      onDeleteTask={onDeleteTask}
                      isDeleting={isDeleting}
                    />
                  </TableCell>
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
