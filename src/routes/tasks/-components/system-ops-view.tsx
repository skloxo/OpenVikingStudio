import * as React from 'react'
import { useTranslation } from 'react-i18next'
import {
  ChevronDownIcon,
  ChevronRightIcon,
  CpuIcon,
  ClockIcon,
  RotateCcwIcon,
  Trash2Icon,
} from 'lucide-react'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'
import { cn } from '#/lib/utils'

export interface SystemOpItem {
  task_id: string
  task_type: string
  status: string
  human_title: string
  created_at: number
  updated_at: number
  stage?: string
  error?: string
}

interface SystemOpsViewProps {
  ops: SystemOpItem[]
  onSelectTask: (taskId: string) => void
  onRetryTask?: (task: any) => void
  onDeleteTask?: (taskId: string) => void
}

export function SystemOpsView({
  ops,
  onSelectTask,
  onRetryTask,
  onDeleteTask,
}: SystemOpsViewProps) {
  const { t } = useTranslation('tasksPage')
  const [isOpen, setIsOpen] = React.useState(true)

  if (ops.length === 0) {
    return null
  }

  return (
    <Card className="flex flex-col border bg-muted/5 overflow-hidden">
      {/* Collapsible Header */}
      <div
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-muted/10 transition-colors select-none"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-2">
          <div className="size-6 rounded bg-muted flex items-center justify-center text-muted-foreground">
            <CpuIcon className="size-3.5" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-foreground">
                {t('dualTrack.systemTrackTitle', '系统底层运维工序')}
              </span>
              <Badge variant="outline" className="px-1.5 py-px text-[11px] leading-none font-mono">
                {ops.length}
              </Badge>
            </div>
            <span className="text-[11px] text-muted-foreground">
              {t('dualTrack.systemTrackSubtitle', '后台增量重排、周期质检与空间压缩工序')}
            </span>
          </div>
        </div>

        <Button type="button" variant="ghost" size="sm" className="h-7 text-xs gap-1 text-muted-foreground">
          {isOpen ? t('dualTrack.collapseSystemOps', '折叠底层工序') : t('dualTrack.toggleSystemOps', '展开底层运维工序', { count: ops.length })}
          {isOpen ? <ChevronDownIcon className="size-3.5" /> : <ChevronRightIcon className="size-3.5" />}
        </Button>
      </div>

      {/* Collapsible Body */}
      {isOpen && (
        <div className="border-t border-border/40">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent text-[11px]">
                <TableHead className="h-8 py-1">{t('dualTrack.colOpName', '工序名称与摘要')}</TableHead>
                <TableHead className="h-8 py-1">{t('dualTrack.colStatus', '状态')}</TableHead>
                <TableHead className="h-8 py-1">{t('dualTrack.colStage', '阶段')}</TableHead>
                <TableHead className="h-8 py-1">{t('dualTrack.colTime', '执行时间')}</TableHead>
                <TableHead className="h-8 py-1 text-right">{t('dualTrack.colActions', '操作')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {ops.slice(0, 30).map((op) => {
                const isCompleted = op.status === 'completed'
                const isRunning = op.status === 'running'
                const isFailed = op.status === 'failed' || op.status === 'cancelled'

                return (
                  <TableRow
                    key={op.task_id}
                    className="cursor-pointer hover:bg-muted/20 text-xs py-1"
                    onClick={() => onSelectTask(op.task_id)}
                  >
                    <TableCell className="py-1.5 font-medium max-w-xs truncate">
                      <div className="flex flex-col gap-0.5">
                        <span className="truncate">{op.human_title}</span>
                        <span className="text-[11px] text-muted-foreground font-mono truncate">{op.task_id}</span>
                      </div>
                    </TableCell>
                    <TableCell className="py-1.5">
                      <Badge
                        variant="outline"
                        className={cn(
                          'px-1.5 py-px text-[11px] font-medium leading-none',
                          isCompleted && 'bg-primary/10 text-primary border-primary/20',
                          isRunning && 'bg-muted text-foreground border-border',
                          isFailed && 'bg-destructive/10 text-destructive border-destructive/20'
                        )}
                      >
                        {op.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="py-1.5 text-[11px] text-muted-foreground font-mono">
                      {op.stage || '--'}
                    </TableCell>
                    <TableCell className="py-1.5 text-[11px] text-muted-foreground font-mono">
                      <span className="flex items-center gap-1">
                        <ClockIcon className="size-2.5" />
                        {new Date(op.created_at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </TableCell>
                    <TableCell className="py-1.5 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1">
                        {isFailed && onRetryTask && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="size-6 text-muted-foreground hover:text-foreground"
                            onClick={() => onRetryTask(op)}
                          >
                            <RotateCcwIcon className="size-3" />
                          </Button>
                        )}
                        {onDeleteTask && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="size-6 text-muted-foreground hover:text-destructive"
                            onClick={() => onDeleteTask(op.task_id)}
                          >
                            <Trash2Icon className="size-3" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </Card>
  )
}
