import { useTranslation } from 'react-i18next'
import {
  BotIcon,
  ChevronRightIcon,
  ExternalLinkIcon,
  FileCheckIcon,
  UserIcon,
} from 'lucide-react'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import type { TaskRecord } from '#/routes/tasks/-lib/task-record'

interface TaskHumanCellProps {
  task: TaskRecord
  index: number
  pageOffset: number
  onOpenDeliverable?: (uri: string) => void
}

export function TaskHumanCell({
  task,
  index,
  pageOffset,
  onOpenDeliverable,
}: TaskHumanCellProps) {
  const { t } = useTranslation('tasksPage')
  const meta = task.meta ?? {}
  const result = (task.result ?? {}) as Record<string, any>
  const shortId = task.task_id
    ? task.task_id.length > 12
      ? task.task_id.slice(-8)
      : task.task_id
    : String(pageOffset + index + 1)

  // Derive human-readable title
  const rawType = task.task_type || ''
  const sourceName = meta.source_name || (meta.source_path ? String(meta.source_path).split(/[\\/]/).pop() : null)
  const resourceName = sourceName || (task.resource_id ? task.resource_id.split('/').pop()?.replace('.md', '') : null)

  let humanTitle = meta.human_title
  if (!humanTitle) {
    if (rawType === 'valet_parking') {
      humanTitle = resourceName ? `原子入库：${resourceName}` : '原子入库'
    } else if (rawType === 'session_commit') {
      humanTitle = resourceName ? `会话归档：${resourceName}` : '会话上下文与经验归档'
    } else if (rawType === 'admin_reindex') {
      humanTitle = '全量索引与切片重构'
    } else if (rawType === 'add_skill') {
      humanTitle = resourceName ? `技能注册：${resourceName}` : '技能规范审计与注册'
    } else if (resourceName) {
      humanTitle = `${t(`types.${rawType}`, { defaultValue: rawType })}：${resourceName}`
    } else {
      humanTitle = t(`types.${rawType}`, { defaultValue: rawType || `工序 #${shortId}` })
    }
  }

  const initiator = String(meta.initiator || 'Agent')
  const isAgent = initiator.toLowerCase().includes('agent')

  // Deliverable link
  const deliverable = (result.deliverable || meta.deliverable) as { uri?: string; label?: string } | undefined
  const deliverableUri = deliverable?.uri || (task.status === 'completed' && task.resource_id ? task.resource_id : null)

  return (
    <div className="flex flex-col gap-1 min-w-0 max-w-sm py-0.5">
      <div className="flex items-center gap-1.5 min-w-0">
        <span className="truncate text-xs font-medium text-foreground hover:text-primary transition-colors">
          {humanTitle}
        </span>
        {task.task_id && (
          <ChevronRightIcon className="size-3 shrink-0 text-muted-foreground/60" />
        )}
      </div>

      <div className="flex items-center gap-2 text-[11px] font-mono text-muted-foreground/70 flex-wrap">
        <Badge
          variant="outline"
          className="px-1 py-0 h-4 text-[11px] font-sans border-border/50 text-muted-foreground bg-muted/20 shrink-0"
        >
          {isAgent ? <BotIcon className="size-2.5 mr-0.5" /> : <UserIcon className="size-2.5 mr-0.5" />}
          {initiator}
        </Badge>

        <span className="tabular-nums select-all text-muted-foreground/50">
          #{shortId}
        </span>

        {task.status === 'completed' && deliverableUri && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-4 px-1.5 text-[11px] text-primary hover:text-primary hover:bg-primary/10 shrink-0 font-sans gap-0.5 font-normal"
            onClick={(e) => {
              e.stopPropagation()
              if (onOpenDeliverable) {
                onOpenDeliverable(deliverableUri)
              }
            }}
          >
            <FileCheckIcon className="size-2.5 text-primary shrink-0" />
            <span>{deliverable?.label || t('dualTrack.deliverableLabel', '成果物直达')}</span>
            <ExternalLinkIcon className="size-2 shrink-0" />
          </Button>
        )}
      </div>
    </div>
  )
}
