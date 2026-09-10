import * as React from 'react'

import type { ParsedQueueRow } from '#/routes/monitoring/-components/queue-status-card'
import { TasksFilterBar } from '#/routes/tasks/-components/tasks-filter-bar'
import { TasksTable } from '#/routes/tasks/-components/tasks-table'
import type { TaskDataScope, TaskStatusFilter, TaskTypeFilter } from '#/routes/tasks/-lib/task-api'
import { MAX_TASKS } from '#/routes/tasks/-lib/task-api'
import { normalizeTaskStatus } from '#/routes/tasks/-lib/task-record'
import type { TaskRecord } from '#/routes/tasks/-lib/task-record'

export interface TasksTableSectionProps {
  filters: {
    dataScope: TaskDataScope
    setDataScope: (scope: TaskDataScope) => void
    taskType: TaskTypeFilter
    setTaskType: (type: TaskTypeFilter) => void
    statusFilter: TaskStatusFilter
    setStatusFilter: (status: TaskStatusFilter) => void
    dedupByResource: boolean
    setDedupByResource: (dedup: boolean) => void
  }
  tasks: {
    all: TaskRecord[]
    paginated: TaskRecord[]
    query: { isLoading: boolean; isError: boolean; error: unknown }
    queueRows: ParsedQueueRow[]
  }
  pagination: {
    page: number
    setPage: React.Dispatch<React.SetStateAction<number>>
    pageSize: number
    setPageSize: (size: number) => void
    totalPages: number
  }
  selection: {
    selectedTaskId: string | null
    urlTaskId?: string
    onSelectTask: (taskId: string) => void
  }
  mutations: {
    retryMutation: { mutate: (task: TaskRecord) => void; isPending: boolean; variables?: unknown }
    clearFailedMutation: { mutate: () => void; isPending: boolean }
    deleteTaskMutation: { mutate: (id: string) => void; isPending: boolean }
  }
  onOpenDeliverable?: (uri: string) => void
}

export function TasksTableSection({
  filters,
  tasks,
  pagination,
  selection,
  mutations,
  onOpenDeliverable,
}: TasksTableSectionProps) {
  const hasActiveFilters =
    filters.taskType !== 'all' || filters.statusFilter !== 'all' || filters.dataScope !== 'all'
  const hasFailed = tasks.all.some((it) =>
    ['failed', 'cancelled'].includes(normalizeTaskStatus(it.status)),
  )

  return (
    <>
      <TasksFilterBar
        dataScope={filters.dataScope}
        setDataScope={(scope) => {
          filters.setDataScope(scope)
          pagination.setPage(1)
        }}
        taskType={filters.taskType}
        setTaskType={(type) => {
          filters.setTaskType(type)
          pagination.setPage(1)
        }}
        statusFilter={filters.statusFilter}
        setStatusFilter={(status) => {
          filters.setStatusFilter(status)
          pagination.setPage(1)
        }}
        dedupByResource={filters.dedupByResource}
        setDedupByResource={filters.setDedupByResource}
        hasFailedTasks={hasFailed}
        isClearingFailed={mutations.clearFailedMutation.isPending}
        onClearFilters={() => {
          filters.setTaskType('all')
          filters.setStatusFilter('all')
          filters.setDataScope('all')
          pagination.setPage(1)
        }}
        onClearFailed={() => mutations.clearFailedMutation.mutate()}
      />
      <TasksTable
        tasks={tasks.paginated}
        allTasks={tasks.all}
        isLoading={tasks.query.isLoading}
        isError={tasks.query.isError}
        error={tasks.query.error}
        hasActiveFilters={hasActiveFilters}
        selectedTaskId={selection.selectedTaskId}
        urlTaskId={selection.urlTaskId}
        page={pagination.page}
        setPage={pagination.setPage}
        pageSize={pagination.pageSize}
        setPageSize={(size) => {
          pagination.setPageSize(size)
          pagination.setPage(1)
        }}
        totalPages={pagination.totalPages}
        onSelectTask={selection.onSelectTask}
        onRetryTask={(task) => mutations.retryMutation.mutate(task)}
        isRetryingTask={(id) =>
          mutations.retryMutation.isPending &&
          (mutations.retryMutation.variables as TaskRecord | undefined)?.task_id === id
        }
        onDeleteTask={(id) => mutations.deleteTaskMutation.mutate(id)}
        isDeleting={mutations.deleteTaskMutation.isPending}
        queueObserverRows={tasks.queueRows}
        maxTasks={MAX_TASKS}
        onOpenDeliverable={onOpenDeliverable}
      />
    </>
  )
}
