import * as React from 'react'
import { useTranslation } from 'react-i18next'
import {
  ExternalLinkIcon,
  CheckCircle2Icon,
  ClockIcon,
  SparklesIcon,
  BotIcon,
  UserIcon,
  InboxIcon,
  FileCheckIcon,
} from 'lucide-react'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { Progress } from '#/components/ui/progress'
import { cn } from '#/lib/utils'

export interface BusinessJobItem {
  task_id: string
  task_type: string
  status: string
  human_title: string
  initiator?: string
  created_at: number
  updated_at: number
  deliverable?: {
    uri: string
    label?: string
    action_type?: string
  }
  progress?: {
    completed: number
    total: number
    unit?: string
  }
  result?: any
}

interface BusinessJobsViewProps {
  jobs: BusinessJobItem[]
  onSelectTask: (taskId: string) => void
  onOpenDeliverable?: (uri: string) => void
}

export function BusinessJobsView({
  jobs,
  onSelectTask,
  onOpenDeliverable,
}: BusinessJobsViewProps) {
  const { t } = useTranslation('tasksPage')

  if (!jobs || jobs.length === 0) {
    return (
      <Card className="flex flex-col items-center justify-center p-8 text-center border-dashed bg-muted/10">
        <div className="size-10 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-3">
          <InboxIcon className="size-5" />
        </div>
        <h3 className="text-sm font-semibold text-foreground">
          {t('dualTrack.emptyBusiness', '暂无活动业务作业')}
        </h3>
        <p className="text-xs text-muted-foreground mt-1 max-w-sm">
          {t('dualTrack.emptyBusinessSub', '所有提交任务均已完成异步托管入库，知识库秩序井然。')}
        </p>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
      {jobs.map((job) => {
        const isCompleted = job.status === 'completed'
        const isRunning = job.status === 'running'
        const isFailed = job.status === 'failed' || job.status === 'cancelled'

        const comp = job.progress?.completed ?? (isCompleted ? 1 : 0)
        const tot = job.progress?.total ?? 1
        const pct = tot > 0 ? Math.min(100, Math.round((comp / tot) * 100)) : (isCompleted ? 100 : 0)
        const unit = job.progress?.unit ?? '个节点'

        return (
          <Card
            key={job.task_id}
            className={cn(
              'flex flex-col p-3.5 gap-3 border transition-colors hover:border-primary/50 relative overflow-hidden',
              isCompleted ? 'bg-card' : 'bg-muted/10 border-primary/30'
            )}
          >
            {/* Header: Title & Badges */}
            <div className="flex items-start justify-between gap-2">
              <div className="flex flex-col gap-1 min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-sm font-semibold text-foreground truncate cursor-pointer hover:underline" onClick={() => onSelectTask(job.task_id)}>
                    {job.human_title || job.task_id}
                  </span>
                  {job.task_type === 'valet_parking' && (
                    <Badge variant="outline" className="px-1.5 py-px text-[11px] leading-none bg-primary/10 text-primary border-primary/20">
                      <InboxIcon className="size-2.5 mr-1" />
                      {t('dualTrack.valetTag', '托管入库')}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2 text-[11px] text-muted-foreground font-mono">
                  <span className="flex items-center gap-1">
                    {job.initiator?.toLowerCase().includes('agent') ? <BotIcon className="size-3" /> : <UserIcon className="size-3" />}
                    {job.initiator || 'Agent'}
                  </span>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <ClockIcon className="size-3" />
                    {new Date(job.created_at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                </div>
              </div>

              {/* Status Badge */}
              <Badge
                variant="outline"
                className={cn(
                  'px-2 py-0.5 text-[11px] font-medium shrink-0',
                  isCompleted && 'bg-primary/10 text-primary border-primary/30',
                  isRunning && 'bg-muted text-foreground animate-pulse border-border',
                  isFailed && 'bg-destructive/10 text-destructive border-destructive/30'
                )}
              >
                {isCompleted ? t('dualTrack.statusCompleted', '已入库') : isRunning ? t('dualTrack.statusProcessing', '处理中') : job.status}
              </Badge>
            </div>

            {/* Middle: Truthful Progress Bar */}
            <div className="flex flex-col gap-1.5 mt-auto pt-1">
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="text-muted-foreground">物理流转进度</span>
                <span className="text-foreground font-medium tabular-nums">
                  {comp} / {tot} {unit} ({pct}%)
                </span>
              </div>
              <Progress value={pct} className="h-1.5" />
            </div>

            {/* Deliverable Link Closure */}
            {job.deliverable && isCompleted && (
              <div className="pt-2 border-t border-border/40 flex items-center justify-between gap-2 mt-1">
                <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground truncate font-mono">
                  <FileCheckIcon className="size-3 text-primary shrink-0" />
                  <span className="truncate">{job.deliverable.uri}</span>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-[11px] text-primary hover:text-primary hover:bg-primary/10 shrink-0 font-medium"
                  onClick={() => {
                    if (onOpenDeliverable && job.deliverable?.uri) {
                      onOpenDeliverable(job.deliverable.uri)
                    } else {
                      onSelectTask(job.task_id)
                    }
                  }}
                >
                  {job.deliverable.label || t('dualTrack.deliverableLabel', '成果物直达')}
                  <ExternalLinkIcon className="size-2.5 ml-1" />
                </Button>
              </div>
            )}
          </Card>
        )
      })}
    </div>
  )
}
