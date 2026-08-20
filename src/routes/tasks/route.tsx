import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import {
  CheckIcon,
  CircleDashedIcon,
  CircleXIcon,
  ChevronRightIcon,
  ClipboardListIcon,
  LayersIcon,
  LoaderCircleIcon,
  RefreshCwIcon,
  RotateCcwIcon,
  XIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from '#/components/ui/pagination'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'
import { useAppConnection } from '#/hooks/use-app-connection'
import { getOvResult, getTasks, ovClient } from '#/lib/ov-client'
import { postResources } from '#/gen/ov-client'
import { commitSession } from '#/lib/sessions/api'
import { cn } from '#/lib/utils'
import {
  QueueStatusCard,
  parseQueueStatus,
} from '#/routes/monitoring/-components/queue-status-card'
import type { ParsedQueueRow } from '#/routes/monitoring/-components/queue-status-card'
import { TaskDetailSheet } from '#/routes/tasks/-components/task-detail-sheet'
import {
  normalizeTasks,
  normalizeTaskStatus,
} from '#/routes/tasks/-lib/task-record'
import type { TaskRecord, TaskStatus } from '#/routes/tasks/-lib/task-record'
import { formatTaskDuration, getTaskDate } from '#/routes/tasks/-lib/task-time'
import {
  getTaskPipelineGroups,
  getTaskPipelineSteps,
  getTaskQuantifiedWorkload,
  getTaskExecutionDynamic,
} from './-lib/task-pipeline'

export const Route = createFileRoute('/tasks')({
  component: TasksRoute,
})

type TaskStatusFilter = Exclude<TaskStatus, 'unknown'> | 'all'

type TaskTypeFilter =
  | 'add_resource'
  | 'add_skill'
  | 'admin_reindex'
  | 'connector_import'
  | 'legacy_cleanup'
  | 'legacy_migration'
  | 'session_commit'
  | 'snapshot_restore_reindex'
  | 'all'

const DEFAULT_PAGE_SIZE = 20
const MAX_TASKS = 200
const PAGE_SIZE_OPTIONS = [20, 50, 100] as const
const TASK_TYPE_OPTIONS: Exclude<TaskTypeFilter, 'all'>[] = [
  'session_commit',
  'add_resource',
  'add_skill',
  'connector_import',
  'admin_reindex',
  'snapshot_restore_reindex',
  'legacy_migration',
  'legacy_cleanup',
]
const TASK_STATUS_OPTIONS: Exclude<TaskStatusFilter, 'all'>[] = [
  'running',
  'pending',
  'completed',
  'failed',
  'cancelled',
]

// 根据 8 并发物理上限计算任务的物理有效状态 (前 8 个 running, 第 9 个及以后 pending)
export function getEffectiveTaskStatus(taskItem: any, list: any[]): string {
  const rawStatus = normalizeTaskStatus(taskItem.status)
  if (rawStatus !== 'running') {
    return rawStatus
  }
  const runningList = list
    .filter((t) => normalizeTaskStatus(t.status) === 'running')
    .sort((a, b) => Number(a.created_at || 0) - Number(b.created_at || 0))
  const idx = runningList.findIndex((t) => t.task_id === taskItem.task_id)
  return idx >= 8 ? 'pending' : 'running'
}

export type TaskDataScope = '24h' | 'all'

async function fetchTasks(
  taskType: TaskTypeFilter,
  status: TaskStatusFilter,
  dataScope: TaskDataScope = '24h',
): Promise<TaskRecord[]> {
  const query = {
    limit: MAX_TASKS,
    status: undefined,
    task_type: taskType === 'all' ? undefined : taskType,
  }
  try {
    const result = await getOvResult<unknown>(
      getTasks({
        query: query as any,
      }),
    )
    let fetched = normalizeTasks(result).sort(
      (a, b) => Number(b.created_at || 0) - Number(a.created_at || 0),
    )
    if (dataScope === '24h') {
      const nowSec = Math.floor(Date.now() / 1000)
      fetched = fetched.filter((t) => {
        const timeVal = Number(t.created_at || t.updated_at || 0)
        return timeVal > 0 && nowSec - timeVal <= 86400
      })
    }
    // 根据 8 并发物理上限计算任务的物理有效状态 (前 8 个 running, 第 9 个及以后 pending)
    const getEffectiveTaskStatus = (taskItem: any, list: any[]): string => {
      const rawStatus = normalizeTaskStatus(taskItem.status)
      if (rawStatus !== 'running') {
        return rawStatus
      }
      const runningList = list
        .filter((t) => normalizeTaskStatus(t.status) === 'running')
        .sort((a, b) => Number(a.created_at || 0) - Number(b.created_at || 0))
      const idx = runningList.findIndex((t) => t.task_id === taskItem.task_id)
      return idx >= 8 ? 'pending' : 'running'
    }

    if (status !== 'all') {
      fetched = fetched.filter((t) => getEffectiveTaskStatus(t, fetched) === status)
    }
    if (taskType !== 'all') {
      fetched = fetched.filter((t) => t.task_type === taskType)
    }
    return fetched
  } catch (err) {
    console.warn('[fetchTasks] Backend fetch failed:', err)
    return []
  }
}

function TasksRoute() {
  const { i18n, t } = useTranslation('tasksPage')
  const { identityScopeKey } = useAppConnection()
  const queryClient = useQueryClient()
  const [page, setPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(DEFAULT_PAGE_SIZE)
  const [taskType, setTaskType] = React.useState<TaskTypeFilter>('all')
  const [statusFilter, setStatusFilter] =
    React.useState<TaskStatusFilter>('all')
  const [dataScope, setDataScope] = React.useState<TaskDataScope>('all')
  const [dedupByResource, setDedupByResource] = React.useState<boolean>(true)
  const [selectedTaskId, setSelectedTaskId] = React.useState<string | null>(
    null,
  )
  const tasksQuery = useQuery({
    queryFn: () => fetchTasks(taskType, statusFilter, dataScope),
    queryKey: ['tasks', identityScopeKey, taskType, statusFilter, dataScope],
    refetchInterval: 5_000,
  })
  const rawTasks = tasksQuery.data ?? []

  // Real-time QueueFS queue telemetry linkage
  const queueObserverQuery = useQuery({
    queryKey: ['queue-observer-status'],
    queryFn: async () => {
      try {
        const resp = await ovClient.instance.get('/api/v1/observer/queue')
        const statusText = resp.data?.result?.status || ''
        return parseQueueStatus(statusText)
      } catch {
        return []
      }
    },
    refetchInterval: () => {
      const hasActive = rawTasks.some((t) => {
        const s = normalizeTaskStatus(t.status)
        return s === 'running' || s === 'pending'
      })
      return hasActive ? 2000 : 15000
    },
  })
  const queueObserverRows = queueObserverQuery.data || []
  const allTasks = React.useMemo(() => {
    if (!dedupByResource) return rawTasks
    const map = new Map<string, TaskRecord>()
    for (const t of rawTasks) {
      const key = t.resource_id ? `res:${t.resource_id}` : `task:${t.task_id}`
      if (!map.has(key)) {
        map.set(key, t)
      }
    }
    return Array.from(map.values())
  }, [rawTasks, dedupByResource])
  const pageOffset = (page - 1) * pageSize
  const tasks = allTasks.slice(pageOffset, pageOffset + pageSize)
  const totalPages = Math.max(1, Math.ceil(allTasks.length / pageSize))
  const hasNext = page < totalPages
  const hasActiveFilters = taskType !== 'all' || statusFilter !== 'all'

  const retryMutation = useMutation({
    mutationFn: async (task: TaskRecord) => {
      if (task.task_id?.startsWith('mock_task_')) {
        return { res: { ok: true }, task }
      }
      if (!task.resource_id) {
        throw new Error(
          i18n.language.startsWith('zh')
            ? '任务缺少关联资源 ID，无法重新入队'
            : 'Missing resource ID for task',
        )
      }

      // ── 1. task_type 精确匹配优先（不受 URI 前缀干扰）──────────────────────
      if (task.task_type === 'session_commit') {
        const res = await commitSession(task.resource_id)
        const resAny = res as any
        if (resAny?.result?.reason === 'no_messages' || resAny?.reason === 'no_messages') {
          toast.info(
            i18n.language.startsWith('zh')
              ? '该会话无未提交消息，已无需重复入队'
              : 'Session has no pending uncommitted messages',
          )
        }
        return { res, task }
      }
      const resourceUri = task.resource_id || ''

      if (resourceUri.startsWith('viking://')) {
        // Use semantic_and_vectors (not the default vectors_only) so that:
        // 1. Semantic abstracts are regenerated (short summaries, never trigger INPUT_TOO_LARGE)
        // 2. Vectors are rebuilt from the fresh abstracts
        // vectors_only would re-send the same raw oversized chunk to the embedder → infinite failure loop
        const resp = await ovClient.instance.post('/api/v1/content/reindex', {
          uri: resourceUri,
          mode: 'semantic_and_vectors',
          wait: false,
        })
        const json = resp.data
        if (json.status === 'error' || json.error) {
          throw new Error(
            json.error?.message ||
              json.message ||
              (i18n.language.startsWith('zh')
                ? '重新入队失败'
                : 'Re-queue failed'),
          )
        }
        return { res: json, task }
      }

      if (
        resourceUri.startsWith('http://') ||
        resourceUri.startsWith('https://')
      ) {
        const res = await postResources({
          body: {
            url: resourceUri,
            reason: `Re-queued task: ${task.task_id}`,
          } as any,
        })
        return { res, task }
      }

      const resp = await ovClient.instance.post('/api/v1/content/reindex', {
        uri: resourceUri,
        mode: 'semantic_and_vectors',
        wait: false,
      })
      const json = resp.data
      if (json.status === 'error' || json.error) {
        throw new Error(
          json.error?.message ||
            json.message ||
            (i18n.language.startsWith('zh')
              ? '重新入队失败'
              : 'Re-queue failed'),
        )
      }
      return { res: json, task }
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : String(error))
    },
    onSuccess: async () => {
      toast.success(
        i18n.language.startsWith('zh')
          ? '重新入队请求已发送，后端正在处理新任务！'
          : 'Re-queue request submitted successfully!',
      )
      await queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })

  React.useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages)
    }
  }, [page, totalPages])

  const formatTime = (task: TaskRecord) => {
    const date = getTaskDate(task)
    if (!date) return '-'
    const y = date.getFullYear()
    const m = date.getMonth() + 1
    const d = date.getDate()
    const hh = String(date.getHours()).padStart(2, '0')
    const mm = String(date.getMinutes()).padStart(2, '0')
    const ss = String(date.getSeconds()).padStart(2, '0')
    return `${y}/${m}/${d} ${hh}:${mm}:${ss}`
  }

  const getTaskProgressPct = (task: TaskRecord): number => {
    const effStatus = getEffectiveTaskStatus(task, allTasks)
    const status = normalizeTaskStatus(effStatus)
    if (status === 'completed') return 100
    if (status === 'failed') return 0
    if (status === 'pending') return 0

    // 1. Direct explicit progress from task.meta (highest priority)
    const meta = (task.meta && typeof task.meta === 'object') ? (task.meta as Record<string, any>) : {}
    if (typeof meta.progress_pct === 'number') {
      return Math.min(99, Math.max(1, Math.round(meta.progress_pct)))
    }
    if (typeof meta.processed_chunks === 'number' && typeof meta.total_chunks === 'number' && meta.total_chunks > 0) {
      return Math.min(99, Math.max(1, Math.round((meta.processed_chunks / meta.total_chunks) * 100)))
    }

    // 2. Real-time QueueFS observer queue linkage
    const totalRow = queueObserverRows.find((r) => r.name.toUpperCase() === 'TOTAL')
    const embeddingRow = queueObserverRows.find((r) => r.name.toLowerCase().includes('embedding'))
    const semanticRow = queueObserverRows.find((r) => r.name.toLowerCase().includes('semantic'))

    if (embeddingRow && embeddingRow.total > 0) {
      const embedRatio = Math.min(1, embeddingRow.completed / embeddingRow.total)
      return Math.min(99, Math.max(10, Math.round(50 + (45 * embedRatio))))
    }
    if (semanticRow && semanticRow.total > 0) {
      const semRatio = Math.min(1, semanticRow.completed / semanticRow.total)
      return Math.min(60, Math.max(10, Math.round(15 + (40 * semRatio))))
    }
    if (totalRow && totalRow.total > 0) {
      const totalRatio = Math.min(1, totalRow.completed / totalRow.total)
      return Math.min(99, Math.max(10, Math.round(totalRatio * 95)))
    }

    // 3. Stage-based estimation
    const stage = task.stage?.toLowerCase()
    if (stage === 'completed' || stage === 'finalizing' || stage === 'committing') return 95
    if (stage === 'embedding_chunks' || stage === 'embedding') return 75
    if (stage === 'extracting_semantics' || stage === 'extracting') return 45
    if (stage === 'scanning' || stage === 'started') return 20

    // 4. Smooth asymptotic curve based on elapsed time (replaces hardcoded 45%)
    const createdAtSec = typeof task.created_at === 'number'
      ? task.created_at
      : typeof task.created_at === 'string'
        ? (new Date(task.created_at).getTime() / 1000)
        : (Date.now() / 1000)
    const elapsedSec = Math.max(0, (Date.now() / 1000) - createdAtSec)
    // Smooth saturation curve: 1 - exp(-t/30) scaled from 15% to 88%
    const smoothPct = Math.min(88, Math.round(15 + (1 - Math.exp(-elapsedSec / 25)) * 73))
    return Math.max(10, smoothPct)
  }

  const renderExecutionProgress = (task: TaskRecord) => {
    const taskId = task.task_id
    const dynamic = getTaskExecutionDynamic(
      task,
      queueObserverRows,
      i18n.language,
      getTaskProgressPct,
    )
    const effStatus = getEffectiveTaskStatus(task, allTasks)
    const status = normalizeTaskStatus(effStatus)
    const durationText = formatTaskDuration(task, i18n.language.startsWith('zh'))
    const isRetrying =
      retryMutation.isPending &&
      (retryMutation.variables as TaskRecord | undefined)?.task_id === taskId

    // 1. 已完成：极致素雅（仅状态徽章 + 耗时，详情全部移至抽屉）
    if (status === 'completed') {
      return (
        <div className="flex items-center gap-2 py-0.5 select-none text-foreground/85">
          <Badge
            variant="outline"
            className="text-[11px] px-1.5 py-0 h-5 border-border/60 text-muted-foreground bg-muted/30 font-sans font-medium shrink-0"
          >
            <CheckIcon className="size-2.5 stroke-[2.5] mr-1 text-primary" />
            {t('status.completed')}
          </Badge>
          {durationText && (
            <span className="font-mono text-[11px] text-muted-foreground/70 shrink-0 select-none tabular-nums">
              · {durationText}
            </span>
          )}
        </div>
      )
    }

    // 2. 进行中：一体化动态工序与工作量胶囊 [进行中] 耗时 [工序 3/4: 语义提取 · 0 / 5 节点]
    if (status === 'running') {
      return (
        <div className="flex items-center gap-2 py-0.5 select-none whitespace-nowrap text-xs">
          <Badge
            variant="outline"
            className="text-[11px] px-1.5 py-0 h-5 border-primary/30 text-primary bg-primary/10 font-sans font-medium shrink-0"
          >
            <LoaderCircleIcon className="size-2.5 shrink-0 animate-spin mr-1 text-primary" />
            {t('status.running')}
          </Badge>
          {durationText && (
            <span className="font-mono text-[11px] text-muted-foreground/70 tabular-nums shrink-0">
              · {durationText}
            </span>
          )}
          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs bg-muted/40 text-foreground/85 border border-border/50 font-sans shrink-0">
            <span className="font-medium text-foreground/90">
              {dynamic.activeStepName}
            </span>
            {dynamic.workloadText && (
              <>
                <span className="text-muted-foreground/40 font-mono text-[10px] select-none">·</span>
                <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
                  {dynamic.workloadText}
                </span>
              </>
            )}
          </div>
        </div>
      )
    }

    // 3. 排队中：单行等待态 (带等待工序胶囊)
    if (status === 'pending') {
      return (
        <div className="flex items-center gap-2 py-0.5 text-muted-foreground select-none whitespace-nowrap text-xs">
          <Badge
            variant="outline"
            className="text-[11px] px-1.5 py-0 h-5 border-border/60 text-muted-foreground bg-muted/20 font-sans font-medium shrink-0"
          >
            <CircleDashedIcon className="size-2.5 mr-1 text-muted-foreground/60" />
            {t('pipeline.queued')}
          </Badge>
          {durationText && (
            <span className="font-mono text-[11px] text-muted-foreground/60 shrink-0 select-none tabular-nums">
              · {durationText}
            </span>
          )}
          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs bg-muted/20 text-muted-foreground border border-border/40 font-sans shrink-0">
            <span>{dynamic.activeStepName || dynamic.summaryText || t('pipeline.queued')}</span>
          </div>
        </div>
      )
    }

    // 4. 失败：精准定位中断工序 (带失败徽章、重试按钮与异常工序胶囊)
    return (
      <div className="flex items-center gap-2 py-0.5 text-destructive select-none whitespace-nowrap text-xs">
        <Badge
          variant="destructive"
          className="text-[11px] px-1.5 py-0 h-5 font-sans font-medium shrink-0 gap-1"
        >
          <CircleXIcon className="size-2.5 mr-0.5" />
          {t('status.failed')}
          <button
            type="button"
            disabled={isRetrying}
            className="ml-1 inline-flex items-center justify-center rounded p-0.5 hover:bg-white/25 active:scale-95 transition-all cursor-pointer text-destructive-foreground disabled:opacity-50"
            title={t('pipeline.retrigger')}
            onClick={(e) => {
              e.stopPropagation()
              retryMutation.mutate(task)
            }}
          >
            {isRetrying ? (
              <LoaderCircleIcon className="size-2.5 shrink-0 animate-spin" />
            ) : (
              <RotateCcwIcon className="size-2.5 shrink-0" />
            )}
          </button>
        </Badge>
        {durationText && (
          <span className="font-mono text-[11px] text-destructive/70 shrink-0 select-none tabular-nums">
            · {durationText}
          </span>
        )}
        <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs bg-destructive/5 text-destructive border border-destructive/20 font-sans shrink-0">
          <span>{dynamic.activeStepName || dynamic.summaryText}</span>
        </div>
      </div>
    )
  }

  const taskStatsQuery = useQuery({
    queryFn: async () => {
      try {
        const resp = await ovClient.instance.get('/api/v1/tasks/stats')
        const json = resp.data
        if (json.result) {
          return json.result as {
            total: number
            completed: number
            pending: number
            running: number
            failed: number
          }
        }
      } catch {
        // Fallback to local counts if endpoint fails
      }
      return null
    },
    queryKey: ['taskStats', identityScopeKey],
    refetchInterval: 5_000,
  })

  const localCalculatedQueueRows = React.useMemo(() => {
    const map: Record<
      string,
      { processing: number; pending: number; completed: number; errors: number }
    > = {
      Embedding: { processing: 0, pending: 0, completed: 0, errors: 0 },
      Semantic: { processing: 0, pending: 0, completed: 0, errors: 0 },
      ExternalParse: { processing: 0, pending: 0, completed: 0, errors: 0 },
      AddResource: { processing: 0, pending: 0, completed: 0, errors: 0 },
      SessionCommit: { processing: 0, pending: 0, completed: 0, errors: 0 },
      UserDeletion: { processing: 0, pending: 0, completed: 0, errors: 0 },
      'Semantic-Nodes': { processing: 0, pending: 0, completed: 0, errors: 0 },
    }

    for (const item of allTasks) {
      const st = normalizeTaskStatus(item.status)

      if (item.task_type === 'session_commit') {
        if (st === 'running') map.SessionCommit.processing++
        else if (st === 'pending') map.SessionCommit.pending++
        else if (st === 'completed') map.SessionCommit.completed++
        else if (st === 'failed') map.SessionCommit.errors++
      } else if (item.task_type === 'user_delete' || item.task_type === 'user_deletion') {
        if (st === 'running') map.UserDeletion.processing++
        else if (st === 'pending') map.UserDeletion.pending++
        else if (st === 'completed') map.UserDeletion.completed++
        else if (st === 'failed') map.UserDeletion.errors++
      } else if (
        item.task_type === 'admin_reindex' ||
        item.task_type === 'snapshot_restore_reindex'
      ) {
        if (st === 'pending') map.ExternalParse.pending++
        else map.ExternalParse.completed++

        if (st === 'running') map.Embedding.processing++
        else if (st === 'pending') map.Embedding.pending++
        else if (st === 'completed') map.Embedding.completed++
        else if (st === 'failed') map.Embedding.errors++
      } else {
        // add_resource / add_skill / connector_import 包含：资源入库 -> 解析 -> 语义提炼 -> 向量落库
        if (st === 'running') {
          map.AddResource.processing++
          map.ExternalParse.processing++
          map.Semantic.processing++
          map.Embedding.processing++
        } else if (st === 'pending') {
          map.AddResource.pending++
          map.ExternalParse.pending++
          map.Semantic.pending++
          map.Embedding.pending++
        } else if (st === 'completed') {
          map.AddResource.completed++
          map.ExternalParse.completed++
          map.Semantic.completed++
          map.Embedding.completed++
        } else if (st === 'failed') {
          map.AddResource.errors++
          map.ExternalParse.errors++
          map.Semantic.errors++
          map.Embedding.errors++
        }
      }
    }

    let totProc = 0
    let totPend = 0
    let totComp = 0
    let totErr = 0
    const rows = Object.entries(map).map(([name, data]) => {
      totProc += data.processing
      totPend += data.pending
      totComp += data.completed
      totErr += data.errors
      return {
        name,
        processing: data.processing,
        pending: data.pending,
        completed: data.completed,
        errors: data.errors,
        total: data.processing + data.pending + data.completed,
      }
    })

    rows.push({
      name: 'TOTAL',
      processing: totProc,
      pending: totPend,
      completed: totComp,
      errors: totErr,
      total: totProc + totPend + totComp,
    })

    return rows
  }, [allTasks])

  const displayQueueRows = queueObserverRows.length > 0 ? queueObserverRows : localCalculatedQueueRows

  const kpiData = React.useMemo(() => {
    const total = allTasks.length
    const completed = allTasks.filter(
      (item) => normalizeTaskStatus(item.status) === 'completed',
    ).length
    const rawRunning = allTasks.filter(
      (item) => normalizeTaskStatus(item.status) === 'running',
    ).length
    const rawPending = allTasks.filter(
      (item) => normalizeTaskStatus(item.status) === 'pending',
    ).length
    const failed = allTasks.filter(
      (item) => normalizeTaskStatus(item.status) === 'failed',
    ).length

    // 物理硬件与底层并发槽位限制：Embedding 槽位上限为 8
    const MAX_CONCURRENT_CAP = 8
    const running = Math.min(rawRunning, MAX_CONCURRENT_CAP)
    const pending = rawPending + Math.max(0, rawRunning - MAX_CONCURRENT_CAP)

    const successRate = total > 0 ? (completed / total) * 100 : 100

    const durations = allTasks
      .map((item) => {
        const start = Number(item.created_at || 0)
        const end = Number(item.updated_at || start)
        return start > 0 && end >= start ? end - start : null
      })
      .filter((d): d is number => d !== null && d >= 0)

    const avgDurationSec =
      durations.length > 0
        ? durations.reduce((a, b) => a + b, 0) / durations.length
        : 0

    const ALL_TASK_TYPES = [
      'add_resource',
      'session_commit',
      'admin_reindex',
      'snapshot_restore_reindex',
      'add_skill',
      'connector_import',
      'legacy_migration',
      'legacy_cleanup',
    ]

    const typeCounts: Record<string, number> = {}
    for (const typeKey of ALL_TASK_TYPES) {
      typeCounts[typeKey] = 0
    }
    for (const item of allTasks) {
      if (item.task_type) {
        typeCounts[item.task_type] = (typeCounts[item.task_type] || 0) + 1
      }
    }
    let topType = '--'
    let topCount = 0
    for (const [typeKey, count] of Object.entries(typeCounts)) {
      if (count > topCount) {
        topCount = count
        topType = typeKey
      }
    }

    const baseTypeRows = Object.entries(typeCounts)
      .map(([typeKey, count]) => {
        const matchingTasks = allTasks.filter((taskItem) => taskItem.task_type === typeKey)
        const processing = matchingTasks.filter(
          (taskItem) => normalizeTaskStatus(taskItem.status) === 'running',
        ).length
        const pending = matchingTasks.filter(
          (taskItem) => normalizeTaskStatus(taskItem.status) === 'pending',
        ).length
        const completed = matchingTasks.filter(
          (taskItem) => normalizeTaskStatus(taskItem.status) === 'completed',
        ).length
        const errors = matchingTasks.filter(
          (taskItem) => normalizeTaskStatus(taskItem.status) === 'failed',
        ).length
        return {
          name: t(`types.${typeKey}` as any, { defaultValue: typeKey }),
          typeKey,
          processing,
          pending,
          completed,
          errors,
          total: count,
        }
      })
      .sort((a, b) => b.total - a.total)

    const typeRows = [
      ...baseTypeRows,
      {
        name: 'TOTAL',
        processing: baseTypeRows.reduce((sum, item) => sum + item.processing, 0),
        pending: baseTypeRows.reduce((sum, item) => sum + item.pending, 0),
        completed: baseTypeRows.reduce((sum, item) => sum + item.completed, 0),
        errors: baseTypeRows.reduce((sum, item) => sum + item.errors, 0),
        total: baseTypeRows.reduce((sum, item) => sum + item.total, 0),
      },
    ]

    return {
      total,
      completed,
      running,
      pending,
      failed,
      successRate,
      avgDurationSec,
      topType,
      topCount,
      typeRows,
    }
  }, [allTasks, t])

  return (
    <div className="flex w-full min-w-0 flex-col gap-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="grid gap-1.5">
          <h1 className="text-2xl font-semibold tracking-tight">
            {t('title')}
          </h1>
          <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
            {t('description')}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={tasksQuery.isFetching || taskStatsQuery.isFetching}
            onClick={() => {
              void tasksQuery.refetch()
              void taskStatsQuery.refetch()
            }}
          >
            <RefreshCwIcon
              className={
                tasksQuery.isFetching || taskStatsQuery.isFetching
                  ? 'animate-spin'
                  : undefined
              }
            />
            {t('refresh')}
          </Button>
        </div>
      </header>

      {/* 4 大 Task 核心运行 KPI 观察行 */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">
              {t('pipeline.kpi.successRate')}
            </span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-xl font-bold tabular-nums text-foreground">
              {kpiData.successRate.toFixed(1)}%
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {t('pipeline.kpi.scopeNote', { total: kpiData.total, failed: kpiData.failed })}
          </p>
        </Card>

        <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">
              {t('pipeline.kpi.avgDuration')}
            </span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-xl font-bold tabular-nums text-foreground">
              {kpiData.avgDurationSec < 1
                ? `${(kpiData.avgDurationSec * 1000).toFixed(0)}ms`
                : `${kpiData.avgDurationSec.toFixed(1)}s`}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {t('pipeline.kpi.avgNote')}
          </p>
        </Card>

        <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">
              {t('pipeline.kpi.totalTasks')}
            </span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-xl font-bold tabular-nums text-foreground">
              {t('pipeline.kpi.tasksCount', { count: kpiData.total })}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {t('pipeline.kpi.completedNote', { completed: kpiData.completed })}
          </p>
        </Card>

        <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">
              {t('pipeline.kpi.activePending')}
            </span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-xl font-bold tabular-nums text-foreground">
              {kpiData.running} / {kpiData.pending}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {t('pipeline.kpi.activeNote')}
          </p>
        </Card>
      </div>

      {/* 业务任务状态 (8 种任务) 与 执行引擎状态 (7 大引擎) 50/50 并排观测行 */}
      <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-2">
        {/* 左侧 (50% 宽度 - 优先看上层任务): 业务任务状态 (8 种任务) */}
        <div>
          <QueueStatusCard
            title={t('pipeline.taskQueueStatus')}
            customRows={kpiData.typeRows}
            isHealthy={kpiData.failed === 0}
            isTaskCard={true}
          />
        </div>

        {/* 右侧 (50% 宽度 - 拆分出的下层工序): 执行引擎状态 (7 大引擎) */}
        <div>
          <QueueStatusCard
            title={t('pipeline.processQueueStatus')}
            customRows={displayQueueRows}
            isHealthy={kpiData.failed === 0}
          />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded-xl border bg-card/60 p-2 shadow-xs">
        <span className="px-1 text-xs font-medium text-muted-foreground">
          {t('filters.label')}
        </span>
        <Select
          value={dataScope}
          onValueChange={(value) => {
            setDataScope(value as TaskDataScope)
            setPage(1)
          }}
        >
          <SelectTrigger
            size="sm"
            className="min-w-32 bg-background font-medium"
            aria-label={t('filters.scope')}
          >
            <SelectValue>
              {dataScope === '24h'
                ? t('filters.scope24h')
                : t('filters.scopeAll')}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="24h">{t('filters.scope24h')}</SelectItem>
            <SelectItem value="all">{t('filters.scopeAll')}</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={taskType}
          onValueChange={(value) => {
            setTaskType(value as TaskTypeFilter)
            setPage(1)
          }}
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
          onValueChange={(value) => {
            setStatusFilter(value as TaskStatusFilter)
            setPage(1)
          }}
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
        {hasActiveFilters || dataScope !== '24h' ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="text-muted-foreground"
            onClick={() => {
              setTaskType('all')
              setStatusFilter('all')
              setDataScope('24h')
              setPage(1)
            }}
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
      </div>

      {tasksQuery.isLoading ? (
        <Card className="min-h-56 items-center justify-center">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <LoaderCircleIcon className="size-4 animate-spin" />
            {t('loading')}
          </div>
        </Card>
      ) : tasksQuery.isError ? (
        <Card className="min-h-56 items-center justify-center px-6 text-center">
          <CircleXIcon className="size-8 text-destructive/70" />
          <div className="grid gap-1">
            <p className="font-medium">{t('loadFailed')}</p>
            <p className="max-w-xl text-sm text-muted-foreground">
              {tasksQuery.error instanceof Error
                ? tasksQuery.error.message
                : String(tasksQuery.error)}
            </p>
          </div>
        </Card>
      ) : tasks.length === 0 ? (
        <Card className="min-h-56 items-center justify-center px-6 text-center">
          <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <ClipboardListIcon className="size-5" />
          </div>
          <div className="grid max-w-md gap-1">
            <p className="font-medium">
              {t(hasActiveFilters ? 'emptyFiltered' : 'empty')}
            </p>
            <p className="text-sm text-muted-foreground">
              {t(
                hasActiveFilters
                  ? 'emptyFilteredDescription'
                  : 'emptyDescription',
              )}
            </p>
          </div>
        </Card>
      ) : (
        <Card className="gap-0 overflow-hidden py-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/20 hover:bg-muted/20">
                  <TableHead>{t('table.task')}</TableHead>
                  <TableHead>{t('table.type')}</TableHead>
                  <TableHead>{t('table.resource')}</TableHead>
                  <TableHead>{t('pipeline.pipelineHeader')}</TableHead>
                  <TableHead className="text-right">
                    {t('table.createdAt')}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tasks.map((task, index) => {
                  const taskId = task.task_id
                  return (
                    <TableRow
                      key={taskId || String(index)}
                      tabIndex={taskId ? 0 : undefined}
                      aria-label={
                        taskId ? t('detail.openLabel', { taskId }) : undefined
                      }
                      className={cn(
                        taskId &&
                          'cursor-pointer outline-none hover:bg-muted/35 focus-visible:bg-muted/35 focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-inset',
                      )}
                      onClick={() => {
                        if (taskId) setSelectedTaskId(taskId)
                      }}
                      onKeyDown={(event) => {
                        if (
                          taskId &&
                          (event.key === 'Enter' || event.key === ' ')
                        ) {
                          event.preventDefault()
                          setSelectedTaskId(taskId)
                        }
                      }}
                    >
                      <TableCell>
                        <span className="flex items-center gap-2">
                          <code className="min-w-0 truncate text-xs">
                            {taskId || `#${pageOffset + index + 1}`}
                          </code>
                          {taskId ? (
                            <ChevronRightIcon className="size-3.5 shrink-0 text-muted-foreground" />
                          ) : null}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs font-medium text-foreground/90 whitespace-nowrap">
                        {task.task_type
                          ? t(`types.${task.task_type}`, {
                              defaultValue: task.task_type,
                            })
                          : '-'}
                      </TableCell>
                      <TableCell className="max-w-72 truncate text-muted-foreground">
                        {task.resource_id || '-'}
                      </TableCell>
                      <TableCell>{renderExecutionProgress(task)}</TableCell>
                      <TableCell className="whitespace-nowrap text-right text-muted-foreground">
                        {formatTime(task)}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
          <div className="flex flex-col gap-3 border-t px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-col items-center gap-1.5 sm:items-start">
              <div className="flex items-center justify-center gap-3 sm:justify-start">
                <p className="text-sm text-muted-foreground">
                  {t('pagination.page', { page })}
                </p>
                <Select
                  value={String(pageSize)}
                  onValueChange={(value) => {
                    setPageSize(Number(value))
                    setPage(1)
                  }}
                >
                  <SelectTrigger
                    size="sm"
                    aria-label={t('pagination.pageSize')}
                  >
                    <SelectValue>
                      {t('pagination.pageSizeValue', { count: pageSize })}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {PAGE_SIZE_OPTIONS.map((option) => (
                      <SelectItem key={option} value={String(option)}>
                        {t('pagination.pageSizeValue', { count: option })}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <p className="text-xs text-muted-foreground">
                {t('pagination.scope', {
                  count: allTasks.length,
                  limit: MAX_TASKS,
                })}
              </p>
            </div>
            <Pagination className="mx-0 w-auto justify-center sm:justify-end">
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    href="#"
                    text={t('pagination.previous')}
                    aria-disabled={page <= 1}
                    className={cn(
                      page <= 1 && 'pointer-events-none opacity-50',
                    )}
                    onClick={(event) => {
                      event.preventDefault()
                      if (page > 1) setPage((current) => current - 1)
                    }}
                  />
                </PaginationItem>
                <PaginationItem>
                  <PaginationNext
                    href="#"
                    text={t('pagination.next')}
                    aria-disabled={!hasNext}
                    className={cn(!hasNext && 'pointer-events-none opacity-50')}
                    onClick={(event) => {
                      event.preventDefault()
                      if (hasNext) setPage((current) => current + 1)
                    }}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          </div>
        </Card>
      )}

      <TaskDetailSheet
        identityScopeKey={identityScopeKey}
        open={Boolean(selectedTaskId)}
        taskId={selectedTaskId}
        onOpenChange={(open) => {
          if (!open) setSelectedTaskId(null)
        }}
      />
    </div>
  )
}
