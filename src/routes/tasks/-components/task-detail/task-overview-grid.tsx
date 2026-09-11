import { useState } from 'react'
import {
  ActivityIcon,
  CalendarClockIcon,
  ChevronRightIcon,
  CircleDashedIcon,
  CopyIcon,
  ExternalLinkIcon,
  FileJson2Icon,
  FolderSearch2Icon,
  Layers3Icon,
  LoaderCircleIcon,
  RefreshCwIcon,
  SparklesIcon,
  TimerResetIcon,
  BotIcon,
  UserIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { cn } from '#/lib/utils'
import { formatTaskDuration } from '#/routes/tasks/-lib/task-time'
import type { TaskRecord } from '../../-lib/task-record'
import {
  hasTaskResult,
  normalizeTaskStatus,
  parseInitiator,
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
  const meta = task.meta && typeof task.meta === 'object' ? task.meta : {}
  const deliverableUri =
    (typeof meta.deliverable_uri === 'string' && meta.deliverable_uri) ||
    (typeof meta.deliverable_url === 'string' && meta.deliverable_url) ||
    (meta.deliverable && typeof meta.deliverable === 'object' && typeof meta.deliverable.uri === 'string' && meta.deliverable.uri) ||
    (task.result && typeof task.result === 'object' && typeof (task.result as Record<string, any>).deliverable_uri === 'string' && (task.result as Record<string, any>).deliverable_uri) ||
    (status === 'completed' && task.resource_id ? task.resource_id : null)

  const rawInitiator = meta.initiator || (meta.actor ? `User (${meta.actor})` : '')
  const initiatorInfo = parseInitiator(rawInitiator, task.task_type)

  return (
    <>
      {status === 'completed' && deliverableUri ? (
        <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/5 p-3.5 flex flex-col gap-2">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <SparklesIcon className="size-4 text-cyan-500 shrink-0" />
              <span className="text-xs font-semibold text-foreground">
                {t('deliverableCard.title', '成果物直达')}
              </span>
              <Badge
                variant="outline"
                className="text-[11px] px-1.5 py-0 h-4 border-cyan-500/40 text-cyan-600 dark:text-cyan-400 bg-cyan-500/10 font-mono shrink-0"
              >
                {deliverableUri.startsWith('http') ? 'Web URL' : 'VikingFS'}
              </Badge>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <Button
                variant="ghost"
                size="xs"
                className="h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground cursor-pointer"
                onClick={() => {
                  void navigator.clipboard.writeText(deliverableUri)
                  toast.success(t('deliverableCard.copied', '已复制成果物地址'))
                }}
              >
                <CopyIcon className="size-3 mr-1" />
                {t('deliverableCard.copyUri', '复制地址')}
              </Button>
              {deliverableUri.startsWith('http') ? (
                <Button
                  variant="outline"
                  size="xs"
                  className="h-6 px-2 text-[11px] border-cyan-500/40 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/10 cursor-pointer"
                  onClick={() => window.open(deliverableUri, '_blank', 'noopener,noreferrer')}
                >
                  <ExternalLinkIcon className="size-3 mr-1" />
                  {t('deliverableCard.openExternal', '新窗口打开')}
                </Button>
              ) : null}
            </div>
          </div>
          <div className="rounded-lg bg-background/60 border border-border/40 p-2 font-mono text-xs text-foreground/90 select-all break-all">
            {deliverableUri}
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-2">
        <DetailField
          icon={<ActivityIcon />}
          label={t('detail.fields.status')}
          value={t(`status.${status}`)}
        />
        <DetailField
          icon={initiatorInfo.isAgent ? <BotIcon className="text-cyan-500" /> : <UserIcon />}
          label={t('table.initiator', '提交方')}
          value={initiatorInfo.name}
        />
        <DetailField
          icon={<Layers3Icon />}
          label={t('detail.fields.type')}
          value={t(`types.${task.task_type}`) || task.task_type || '-'}
        />
        <DetailField
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
  const [expanded, setExpanded] = useState(false)

  if (status === 'completed') {
    if (hasTaskResult(task.result)) {
      const formattedResult = formatTaskResult(task.result)
      const isJson = typeof task.result === 'object' && task.result !== null

      return (
        <div className="rounded-xl border border-border/60 bg-muted/20 overflow-hidden transition-colors">
          <button
            type="button"
            onClick={() => setExpanded((prev) => !prev)}
            className="w-full flex items-center justify-between p-3 text-left hover:bg-muted/40 transition-colors cursor-pointer group"
          >
            <div className="flex items-center gap-2">
              <ChevronRightIcon
                className={cn(
                  'size-4 text-muted-foreground transition-transform duration-200',
                  expanded && 'rotate-90',
                )}
              />
              <span className="text-sm font-semibold text-foreground">
                {t('detail.result')}
              </span>
              <span className="px-1.5 py-0.5 rounded-md bg-muted text-[11px] font-mono text-muted-foreground">
                {isJson ? t('detail.payloadJson', 'JSON') : t('detail.payloadText', 'Text')}
              </span>
            </div>
            <div
              className="flex items-center gap-2"
              onClick={(e) => e.stopPropagation()}
            >
              <Button
                variant="ghost"
                size="xs"
                className="h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground hover:bg-muted/60 cursor-pointer"
                onClick={() => {
                  navigator.clipboard.writeText(formattedResult)
                  toast.success(t('detail.resultCopied'))
                }}
              >
                <CopyIcon className="size-3 mr-1" />
                {t('detail.copyResult')}
              </Button>
            </div>
          </button>

          {expanded ? (
            <div className="border-t border-border/40 p-3 bg-muted/30">
              <pre className="max-h-72 overflow-auto rounded-lg font-mono text-xs leading-5">
                {formattedResult}
              </pre>
            </div>
          ) : null}
        </div>
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
