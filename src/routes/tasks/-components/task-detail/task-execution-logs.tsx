import { useState } from 'react'
import { ChevronRightIcon, CopyIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '#/components/ui/button'
import { cn } from '#/lib/utils'
import { normalizeTaskStatus } from '../../-lib/task-record'
import type { TaskRecord } from '../../-lib/task-record'
import { formatTaskTime } from './task-detail-common'

export function generateStepLogs(
  task: TaskRecord,
  t: (key: string, options?: any) => string,
  lang?: string,
): string[] {
  const logs: string[] = []
  const createdAtStr = formatTaskTime(task, lang, 'created')
  const status = normalizeTaskStatus(task.status)

  logs.push(
    t('detail.traceLogs.taskQueued', {
      time: createdAtStr,
      id: task.task_id,
      type: task.task_type || 'generic',
      defaultValue: `[${createdAtStr}] [INFO] [TaskPool] 任务已登记入队: ID=${task.task_id} Type=${task.task_type || 'generic'}`,
    }),
  )
  if (task.resource_id) {
    logs.push(
      t('detail.traceLogs.resourceAssociated', {
        time: createdAtStr,
        path: task.resource_id,
        defaultValue: `[${createdAtStr}] [INFO] [ResourcePipeline] 关联物理资源路径: ${task.resource_id}`,
      }),
    )
  }

  if (status === 'pending') {
    logs.push(
      t('detail.traceLogs.workerWaiting', {
        time: createdAtStr,
        defaultValue: `[${createdAtStr}] [DEBUG] [WorkerThread] 任务就绪，正等待队列空闲分配 worker...`,
      }),
    )
  } else if (status === 'running') {
    logs.push(
      t('detail.traceLogs.workerDispatched', {
        time: createdAtStr,
        defaultValue: `[${createdAtStr}] [INFO] [WorkerThread-01] 已由可用 Worker 抢占分发，初始化解构环境`,
      }),
    )
    logs.push(
      t('detail.traceLogs.vectorIndexing', {
        time: createdAtStr,
        defaultValue: `[${createdAtStr}] [INFO] [EmbeddingService] 物理向量索引计算落盘中...`,
      }),
    )
  } else if (status === 'completed') {
    logs.push(
      t('detail.traceLogs.pipelineSettled', {
        time: createdAtStr,
        defaultValue: `[${createdAtStr}] [INFO] [WorkerThread-01] 物理工序 100% 结算完毕，校验物理一致性契约通过`,
      }),
    )
    if (task.result && typeof task.result === 'object') {
      const resObj = task.result as Record<string, any>
      if (resObj.reindexed_items) {
        logs.push(
          t('detail.traceLogs.reindexSuccess', {
            time: createdAtStr,
            count: resObj.reindexed_items,
            defaultValue: `[${createdAtStr}] [SUCCESS] [ReindexWorker] 重置构建向量索引项: ${resObj.reindexed_items} 项`,
          }),
        )
      }
      if (resObj.processed) {
        logs.push(
          t('detail.traceLogs.chunkSuccess', {
            time: createdAtStr,
            count: resObj.processed,
            defaultValue: `[${createdAtStr}] [SUCCESS] [DataProcessor] 文本分片处理完成: ${resObj.processed} 块`,
          }),
        )
      }
    }
    logs.push(
      t('detail.traceLogs.taskCompleted', {
        time: createdAtStr,
        defaultValue: `[${createdAtStr}] [SUCCESS] 任务状态自愈闭环无缝更新为 [completed]`,
      }),
    )
  } else if (status === 'failed') {
    logs.push(
      t('detail.traceLogs.workerError', {
        time: createdAtStr,
        defaultValue: `[${createdAtStr}] [ERROR] [WorkerThread-01] 工序处理触发异常中断`,
      }),
    )
    if (task.error) {
      logs.push(`[${createdAtStr}] [FATAL] Error Traceback: ${task.error}`)
    }
    logs.push(
      t('detail.traceLogs.retryHint', {
        time: createdAtStr,
        defaultValue: `[${createdAtStr}] [WARN] 可随时点击 [重新入队/自愈] 触发自愈流水线二次重试`,
      }),
    )
  }
  return logs
}

interface TaskExecutionLogsProps {
  task: TaskRecord
  defaultExpanded?: boolean
}

export function TaskExecutionLogs({
  task,
  defaultExpanded = false,
}: TaskExecutionLogsProps) {
  const { i18n, t } = useTranslation('tasksPage')
  const [expanded, setExpanded] = useState(defaultExpanded)
  const logLines = generateStepLogs(task, t, i18n.language)

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
            {t('detail.executionLogs')}
          </span>
          <span className="px-1.5 py-0.5 rounded-md bg-muted text-[11px] font-mono text-muted-foreground">
            {logLines.length} {t('detail.lines')}
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
              navigator.clipboard.writeText(logLines.join('\n'))
              toast.success(t('detail.logsCopied'))
            }}
          >
            <CopyIcon className="size-3 mr-1" />
            {t('detail.copyLogs')}
          </Button>
        </div>
      </button>

      {expanded ? (
        <div className="border-t border-border/40 p-3 bg-muted/30 font-mono text-[11px] leading-relaxed">
          <div className="text-[11px] text-muted-foreground font-mono mb-2 pb-1.5 border-b border-border/30">
            {t('detail.logTraceHeader', {
              id: task.task_id,
              defaultValue: `LOG TRACE STREAM (ID: ${task.task_id})`,
            })}
          </div>
          <div className="space-y-1 overflow-x-auto max-h-56">
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
      ) : null}
    </div>
  )
}
