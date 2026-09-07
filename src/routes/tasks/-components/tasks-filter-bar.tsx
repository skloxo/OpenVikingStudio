import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { LayersIcon, LoaderCircleIcon, Trash2Icon } from 'lucide-react'
import { Button } from '#/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import {
  TASK_STATUS_OPTIONS,
  TASK_TYPE_OPTIONS,
} from '#/routes/tasks/-lib/task-api'
import type {
  TaskDataScope,
  TaskStatusFilter,
  TaskTypeFilter,
} from '#/routes/tasks/-lib/task-api'

interface TasksFilterBarProps {
  dataScope: TaskDataScope
  setDataScope: (scope: TaskDataScope) => void
  taskType: TaskTypeFilter
  setTaskType: (type: TaskTypeFilter) => void
  statusFilter: TaskStatusFilter
  setStatusFilter: (status: TaskStatusFilter) => void
  dedupByResource: boolean
  setDedupByResource: React.Dispatch<React.SetStateAction<boolean>>
  hasFailedTasks: boolean
  isClearingFailed: boolean
  onClearFilters: () => void
  onClearFailed: () => void
}

export function TasksFilterBar({
  dataScope,
  setDataScope,
  taskType,
  setTaskType,
  statusFilter,
  setStatusFilter,
  dedupByResource,
  setDedupByResource,
  hasFailedTasks,
  isClearingFailed,
  onClearFilters,
  onClearFailed,
}: TasksFilterBarProps) {
  const { t } = useTranslation('tasksPage')
  const hasActiveFilters = taskType !== 'all' || statusFilter !== 'all'

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl border bg-card/60 p-2 shadow-xs">
      <span className="px-1 text-xs font-medium text-muted-foreground">
        {t('filters.label')}
      </span>
      <Select
        value={dataScope}
        onValueChange={(value) => setDataScope(value as TaskDataScope)}
      >
        <SelectTrigger
          size="sm"
          className="min-w-32 bg-background font-medium"
          aria-label={t('filters.scope')}
        >
          <SelectValue>
            {dataScope === '24h'
              ? t('filters.scope24h')
              : dataScope === '7d'
              ? t('filters.scope7d')
              : t('filters.scopeAll')}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="24h">{t('filters.scope24h')}</SelectItem>
          <SelectItem value="7d">{t('filters.scope7d')}</SelectItem>
          <SelectItem value="all">{t('filters.scopeAll')}</SelectItem>
        </SelectContent>
      </Select>

      <Select
        value={taskType}
        onValueChange={(value) => setTaskType(value as TaskTypeFilter)}
      >
        <SelectTrigger
          size="sm"
          className="min-w-40 bg-background"
          aria-label={t('filters.type')}
        >
          <SelectValue>
            {taskType === 'all'
              ? t('filters.allTypes')
              : t(`types.${taskType}`)}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">{t('filters.allTypes')}</SelectItem>
          {TASK_TYPE_OPTIONS.map((option) => (
            <SelectItem key={option} value={option}>
              {t(`types.${option}`)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={statusFilter}
        onValueChange={(value) => setStatusFilter(value as TaskStatusFilter)}
      >
        <SelectTrigger
          size="sm"
          className="min-w-32 bg-background"
          aria-label={t('filters.status')}
        >
          <SelectValue>
            {statusFilter === 'all'
              ? t('filters.allStatuses')
              : t(`status.${statusFilter}`)}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">{t('filters.allStatuses')}</SelectItem>
          {TASK_STATUS_OPTIONS.map((option) => (
            <SelectItem key={option} value={option}>
              {t(`status.${option}`)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {hasActiveFilters || dataScope !== 'all' ? (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="text-muted-foreground"
          onClick={onClearFilters}
        >
          {t('filters.clear')}
        </Button>
      ) : null}

      <Button
        type="button"
        variant={dedupByResource ? 'secondary' : 'outline'}
        size="sm"
        className="h-8 text-xs font-normal transition-all gap-1.5"
        onClick={() => setDedupByResource((prev) => !prev)}
      >
        <LayersIcon className="size-3.5 text-muted-foreground" />
        {dedupByResource ? t('pipeline.latestByResource') : t('pipeline.allHistory')}
      </Button>

      {hasFailedTasks ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={isClearingFailed}
          className="h-8 text-xs font-normal transition-all gap-1.5 text-destructive hover:bg-destructive/10 hover:text-destructive border-destructive/30"
          onClick={onClearFailed}
        >
          {isClearingFailed ? (
            <LoaderCircleIcon className="size-3.5 animate-spin" />
          ) : (
            <Trash2Icon className="size-3.5" />
          )}
          {t('pipeline.clearFailed', { defaultValue: 'Clear Failed/Cancelled' })}
        </Button>
      ) : null}
    </div>
  )
}
