import * as React from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { RefreshCwIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '#/components/ui/button'
import { useAppConnection } from '#/hooks/use-app-connection'
import { TaskDetailSheet } from '#/routes/tasks/-components/task-detail-sheet'
import { TasksMetricsCards } from '#/routes/tasks/-components/tasks-metrics-cards'
import { TasksTableSection } from '#/routes/tasks/-components/tasks-table-section'
import { DEFAULT_PAGE_SIZE } from '#/routes/tasks/-lib/task-api'
import type { TaskDataScope, TaskStatusFilter, TaskTypeFilter } from '#/routes/tasks/-lib/task-api'
import { useTasks } from '#/routes/tasks/-lib/use-tasks'

interface TasksSearch {
  taskId?: string
  dataScope?: TaskDataScope
}

export const Route = createFileRoute('/tasks')({
  validateSearch: (search: Record<string, unknown>): TasksSearch => ({
    taskId: typeof search.taskId === 'string' ? search.taskId : undefined,
    dataScope: ['24h', '7d', 'all'].includes(String(search.dataScope)) ? (search.dataScope as TaskDataScope) : undefined,
  }),
  component: TasksRoute,
})

function TasksRoute() {
  const { t } = useTranslation('tasksPage')
  const { identityScopeKey } = useAppConnection()
  const searchParams = Route.useSearch()
  const navigate = useNavigate()
  const urlTaskId = searchParams.taskId

  const [page, setPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(DEFAULT_PAGE_SIZE)
  const [taskType, setTaskType] = React.useState<TaskTypeFilter>('all')
  const [statusFilter, setStatusFilter] = React.useState<TaskStatusFilter>('all')
  const [dataScope, setDataScope] = React.useState<TaskDataScope>(searchParams.dataScope || 'all')
  const [dedupByResource, setDedupByResource] = React.useState<boolean>(true)
  const [selectedTaskId, setSelectedTaskId] = React.useState<string | null>(urlTaskId || null)

  const {
    tasksQuery,
    queueObserverQuery,
    queueObserverRows,
    allTasks,
    kpiData,
    retryMutation,
    clearFailedMutation,
    deleteTaskMutation,
  } = useTasks({ dataScope, taskType, statusFilter, dedupByResource })

  React.useEffect(() => {
    if (urlTaskId && allTasks.length > 0) {
      setSelectedTaskId(urlTaskId)
      const idx = allTasks.findIndex((item) => item.task_id === urlTaskId)
      if (idx >= 0) setPage(Math.floor(idx / pageSize) + 1)
    }
  }, [urlTaskId, allTasks, pageSize])

  const totalPages = Math.max(1, Math.ceil(allTasks.length / pageSize))
  const pageOffset = (page - 1) * pageSize
  const paginatedTasks = allTasks.slice(pageOffset, pageOffset + pageSize)
  const openDeliverable = (uri: string) => void navigate({ to: '/resources', search: { uri } as any })

  return (
    <div className="flex w-full min-w-0 flex-col gap-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="grid gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="max-w-3xl text-sm leading-6 text-muted-foreground">{t('description')}</p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={tasksQuery.isFetching}
          onClick={() => { void tasksQuery.refetch() }}
        >
          <RefreshCwIcon className={tasksQuery.isFetching ? 'animate-spin' : undefined} />
          {t('refresh')}
        </Button>
      </header>

      <TasksMetricsCards kpiData={kpiData} queueObserverRows={queueObserverRows} isQueueLoading={queueObserverQuery.isLoading} />

      <TasksTableSection
        filters={{ dataScope, setDataScope, taskType, setTaskType, statusFilter, setStatusFilter, dedupByResource, setDedupByResource }}
        tasks={{ all: allTasks, paginated: paginatedTasks, query: tasksQuery, queueRows: queueObserverRows }}
        pagination={{ page, setPage, pageSize, setPageSize, totalPages }}
        selection={{ selectedTaskId, urlTaskId, onSelectTask: setSelectedTaskId }}
        mutations={{ retryMutation, clearFailedMutation, deleteTaskMutation }}
        onOpenDeliverable={openDeliverable}
      />

      <TaskDetailSheet
        identityScopeKey={identityScopeKey}
        open={Boolean(selectedTaskId)}
        taskId={selectedTaskId}
        queueRows={queueObserverRows}
        onOpenChange={(open) => { if (!open) setSelectedTaskId(null) }}
      />
    </div>
  )
}

