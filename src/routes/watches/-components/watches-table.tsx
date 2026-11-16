import {
  EllipsisIcon,
  HistoryIcon,
  PencilIcon,
  RotateCwIcon,
  Trash2Icon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '#/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '#/components/ui/dropdown-menu'
import { Switch } from '#/components/ui/switch'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'

import type { WatchTask } from '../-lib/api'

function formatInterval(
  minutes: number,
  t: (k: string, o?: Record<string, unknown>) => string,
): string {
  if (minutes % 1440 === 0) {
    const count = minutes / 1440
    return t(count === 1 ? 'interval.days_one' : 'interval.days_other', {
      count,
    })
  }
  if (minutes % 60 === 0) {
    const count = minutes / 60
    return t(count === 1 ? 'interval.hours_one' : 'interval.hours_other', {
      count,
    })
  }
  return t(minutes === 1 ? 'interval.minutes_one' : 'interval.minutes_other', {
    count: minutes,
  })
}

function formatDateTime(
  value: string | null,
  locale: string | undefined,
  fallback: string,
): string {
  if (!value) return fallback
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(d)
}

export function WatchesTable({
  watches,
  pendingSyncTaskId,
  togglingTaskId,
  onToggleActive,
  onTrigger,
  onEdit,
  onHistory,
  onDelete,
}: {
  watches: WatchTask[]
  pendingSyncTaskId: string | null
  togglingTaskId: string | null
  onToggleActive: (watch: WatchTask, active: boolean) => void
  onTrigger: (watch: WatchTask) => void
  onEdit: (watch: WatchTask) => void
  onHistory: (watch: WatchTask) => void
  onDelete: (watch: WatchTask) => void
}) {
  const { i18n, t } = useTranslation('watchesPage')

  return (
    <Table className="table-fixed">
      <TableHeader>
        <TableRow className="bg-muted/15 hover:bg-muted/15">
          <TableHead className="pl-4 text-xs">{t('columns.resource')}</TableHead>
          <TableHead className="hidden md:table-cell text-xs">
            {t('columns.source')}
          </TableHead>
          <TableHead className="w-28 text-xs">{t('columns.status')}</TableHead>
          <TableHead className="hidden sm:table-cell w-32 text-xs">
            {t('columns.interval')}
          </TableHead>
          <TableHead className="hidden lg:table-cell w-40 text-xs">
            {t('columns.lastRun')}
          </TableHead>
          <TableHead className="hidden xl:table-cell w-40 text-xs">
            {t('columns.nextRun')}
          </TableHead>
          <TableHead className="w-40 pr-4 text-right text-xs">
            {t('columns.actions')}
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {watches.map((watch) => {
          const isSyncing = pendingSyncTaskId === watch.taskId
          const isToggling = togglingTaskId === watch.taskId
          return (
            <TableRow key={watch.taskId} className="border-border/50">
              <TableCell className="min-w-0 truncate pl-4 font-mono text-xs">
                <span title={watch.toUri}>{watch.toUri}</span>
              </TableCell>
              <TableCell className="hidden min-w-0 truncate md:table-cell font-mono text-xs text-muted-foreground">
                <span title={watch.path}>{watch.path}</span>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <Switch
                    checked={watch.isActive}
                    disabled={isToggling}
                    aria-label={
                      watch.isActive
                        ? t('actions.disable')
                        : t('actions.enable')
                    }
                    onCheckedChange={(checked) => onToggleActive(watch, checked)}
                  />
                  <span
                    className={`text-xs ${
                      watch.isActive
                        ? 'font-medium text-cyan-600 dark:text-cyan-400'
                        : 'text-muted-foreground'
                    }`}
                  >
                    {watch.isActive ? t('status.active') : t('status.disabled')}
                  </span>
                </div>
              </TableCell>
              <TableCell className="hidden sm:table-cell text-xs text-muted-foreground">
                {formatInterval(watch.watchInterval, t)}
              </TableCell>
              <TableCell className="hidden lg:table-cell text-xs text-muted-foreground">
                {formatDateTime(
                  watch.lastExecutionTime,
                  i18n.resolvedLanguage,
                  t('never'),
                )}
              </TableCell>
              <TableCell className="hidden xl:table-cell text-xs text-muted-foreground">
                {formatDateTime(
                  watch.nextExecutionTime,
                  i18n.resolvedLanguage,
                  '-',
                )}
              </TableCell>
              <TableCell className="pr-4 text-right">
                <div className="flex items-center justify-end gap-1">
                  <Button
                    type="button"
                    size="xs"
                    variant="outline"
                    disabled={isSyncing}
                    onClick={() => onTrigger(watch)}
                  >
                    <RotateCwIcon
                      className={isSyncing ? 'size-3.5 animate-spin' : 'size-3.5'}
                    />
                    {isSyncing ? t('actions.syncing') : t('actions.trigger')}
                  </Button>
                  <DropdownMenu>
                    <DropdownMenuTrigger
                      render={
                        <Button
                          type="button"
                          size="icon-xs"
                          variant="ghost"
                          aria-label={t('actions.more')}
                        />
                      }
                    >
                      <EllipsisIcon className="size-4" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => onHistory(watch)}>
                        <HistoryIcon className="size-4" />
                        {t('actions.history')}
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => onEdit(watch)}>
                        <PencilIcon className="size-4" />
                        {t('actions.edit')}
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="text-rose-500 focus:text-rose-500"
                        onClick={() => onDelete(watch)}
                      >
                        <Trash2Icon className="size-4" />
                        {t('actions.delete')}
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
