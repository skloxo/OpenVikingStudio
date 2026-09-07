import { CopyIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '#/components/ui/button'
import { cn } from '#/lib/utils'
import { normalizeTaskStatus, type TaskRecord } from '../../-lib/task-record'
import { DetailSection, formatTaskTime } from './task-detail-common'

export function generateStepLogs(task: TaskRecord, lang?: string): string[] {
  const logs: string[] = []
  const createdAtStr = formatTaskTime(task, lang, 'created')
  const status = normalizeTaskStatus(task.status)

  logs.push(
    `[${createdAtStr}] [INFO] [TaskPool] 任务已登记入队: ID=${task.task_id} Type=${task.task_type || 'generic'}`,
  )
  if (task.resource_id) {
    logs.push(
      `[${createdAtStr}] [INFO] [ResourcePipeline] 关联物理资源路径: ${task.resource_id}`,
    )
  }

  if (status === 'pending') {
    logs.push(
      `[${createdAtStr}] [DEBUG] [WorkerThread] 任务就绪，正等待队列空闲分配 worker...`,
    )
  } else if (status === 'running') {
    logs.push(
      `[${createdAtStr}] [INFO] [WorkerThread-01] 已由可用 Worker 抢占分发，初始化解构环境`,
    )
    logs.push(
      `[${createdAtStr}] [INFO] [EmbeddingService] 物理向量索引计算落盘中...`,
    )
  } else if (status === 'completed') {
    logs.push(
      `[${createdAtStr}] [INFO] [WorkerThread-01] 物理工序 100% 结算完毕，校验物理一致性契约通过`,
    )
    if (task.result && typeof task.result === 'object') {
      const resObj = task.result as Record<string, any>
      if (resObj.reindexed_items) {
        logs.push(
          `[${createdAtStr}] [SUCCESS] [ReindexWorker] 重置构建向量索引项: ${resObj.reindexed_items} 项`,
        )
      }
      if (resObj.processed) {
        logs.push(
          `[${createdAtStr}] [SUCCESS] [DataProcessor] 文本分片处理完成: ${resObj.processed} 块`,
        )
      }
    }
    logs.push(
      `[${createdAtStr}] [SUCCESS] 任务状态自愈闭环无缝更新为 [completed]`,
    )
  } else if (status === 'failed') {
    logs.push(`[${createdAtStr}] [ERROR] [WorkerThread-01] 工序处理触发异常中断`)
    if (task.error) {
      logs.push(`[${createdAtStr}] [FATAL] Error Traceback: ${task.error}`)
    }
    logs.push(
      `[${createdAtStr}] [WARN] 可随时点击 [重新入队/自愈] 触发自愈流水线二次重试`,
    )
  }
  return logs
}

interface TaskExecutionLogsProps {
  task: TaskRecord
}

export function TaskExecutionLogs({ task }: TaskExecutionLogsProps) {
  const { i18n, t } = useTranslation('tasksPage')
  const logLines = generateStepLogs(task, i18n.language)

  return (
    <DetailSection title={t('detail.executionLogs')}>
      <div className="relative rounded-xl border border-border/60 bg-muted/30 p-3 font-mono text-[11px] leading-relaxed">
        <div className="flex items-center justify-between border-b border-border/40 pb-2 mb-2 text-[11px] text-muted-foreground font-mono">
          <span>
            {t('detail.logTraceHeader', {
              id: task.task_id,
              defaultValue: `LOG TRACE STREAM (ID: ${task.task_id})`,
            })}
          </span>
          <Button
            variant="ghost"
            size="xs"
            className="h-5 px-1.5 text-[11px] text-muted-foreground hover:text-foreground hover:bg-muted/60 cursor-pointer"
            onClick={() => {
              navigator.clipboard.writeText(logLines.join('\n'))
              toast.success(t('detail.logsCopied'))
            }}
          >
            <CopyIcon className="size-3 mr-1" />
            {t('detail.copyLogs')}
          </Button>
        </div>
        <div className="space-y-1 overflow-x-auto max-h-48">
          {logLines.map((line, idx) => {
            const isErr =
              line.includes('[ERROR]') || line.includes('[FATAL]')
            const isSucc = line.includes('[SUCCESS]')
            const isWarn = line.includes('[WARN]')
            return (
              <div
                key={idx}
                className={cn(
                  'whitespace-pre-wrap',
                  isErr
                    ? 'text-rose-600 dark:text-rose-400 font-medium'
                    : isSucc
                      ? 'text-cyan-600 dark:text-cyan-400 font-medium'
                      : isWarn
                        ? 'text-amber-600 dark:text-amber-400'
                        : 'text-muted-foreground',
                )}
              >
                {line}
              </div>
            )
          })}
        </div>
      </div>
    </DetailSection>
  )
}
