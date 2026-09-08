import {
  ActivityIcon,
  CalendarClockIcon,
  CircleDashedIcon,
  FileJson2Icon,
  FolderSearch2Icon,
  Layers3Icon,
  LoaderCircleIcon,
  RefreshCwIcon,
  TimerResetIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { formatTaskDuration } from '#/routes/tasks/-lib/task-time'
import type { TaskRecord } from '../../-lib/task-record'
import {
  hasTaskResult,
  normalizeTaskStatus,
} from '../../-lib/task-record'
import {
  DetailField,
  DetailSection,
  formatTaskResult,
  formatTaskTime,
} from './task-detail-common'

interface TaskOverviewGridProps {
  task: TaskRecord
}

export function TaskOverviewGrid({ task }: TaskOverviewGridProps) {
  const { i18n, t } = useTranslation('tasksPage')
  const status = normalizeTaskStatus(task.status)

  return (
    <>
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
            if (['completed', 'failed', 'pending', 'running', 'unknown'].includes(raw)) {
              return '-'
            }
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
    </>
  )
}

export function TaskResultOutcomeSummary({ task }: TaskOverviewGridProps) {
  const { t } = useTranslation('tasksPage')
  const status = normalizeTaskStatus(task.status)

  if (status === 'completed') {
    if (hasTaskResult(task.result)) {
      return (
        <DetailSection title={t('detail.result')}>
          <pre className="min-h-50 max-h-100 overflow-auto rounded-xl border bg-muted/30 p-4 font-mono text-xs leading-5">
            {formatTaskResult(task.result)}
          </pre>
        </DetailSection>
      )
    }
    return (
      <div className="flex items-start gap-3 rounded-xl border border-dashed bg-muted/10 p-4">
        <FileJson2Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        <div className="grid gap-0.5">
          <p className="text-sm font-medium">{t('detail.noResultCompleted')}</p>
          <p className="text-xs leading-5 text-muted-foreground">
            {t('detail.noResultCompletedDescription')}
          </p>
        </div>
      </div>
    )
  }

  if (status === 'running') {
    return (
      <div className="flex items-start gap-3 rounded-xl border border-primary/30 bg-primary/5 p-4">
        <LoaderCircleIcon className="mt-0.5 size-4 shrink-0 animate-spin text-primary" />
        <div className="grid gap-0.5">
          <p className="text-sm font-medium text-primary">
            {t('detail.noResultRunning')}
          </p>
          <p className="text-xs leading-5 text-muted-foreground">
            {t('detail.noResultRunningDescription')}
          </p>
        </div>
      </div>
    )
  }

  if (status === 'pending') {
    return (
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
    )
  }

  return null
}
