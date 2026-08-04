import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import {
  CheckIcon,
  CircleDashedIcon,
  CircleXIcon,
  ChevronRightIcon,
  ClipboardListIcon,
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
import { QueueStatusCard } from '#/routes/monitoring/-components/queue-status-card'
import { TaskDetailSheet } from '#/routes/tasks/-components/task-detail-sheet'
import {
  normalizeTasks,
  normalizeTaskStatus,
} from '#/routes/tasks/-lib/task-record'
import type { TaskRecord, TaskStatus } from '#/routes/tasks/-lib/task-record'
import { formatTaskDuration, getTaskDate } from '#/routes/tasks/-lib/task-time'

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
const MAX_TASKS = 300
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
  'pending',
  'running',
  'completed',
  'failed',
]

const TASK_HISTORY_STORAGE_KEY = 'ov_studio_task_history'

function getStoredTaskHistory(): TaskRecord[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(TASK_HISTORY_STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) return parsed
    }
  } catch {
    // Ignore storage errors
  }
  return []
}

function saveStoredTaskHistory(newTasks: TaskRecord[]) {
  if (typeof window === 'undefined' || !newTasks.length) return
  try {
    const existing = getStoredTaskHistory()
    const map = new Map<string, TaskRecord>()
    existing.forEach((t) => {
      if (t.task_id) map.set(t.task_id, t)
    })
    newTasks.forEach((t) => {
      if (t.task_id) map.set(t.task_id, t)
    })
    const merged = Array.from(map.values()).sort(
      (a, b) => Number(b.created_at || 0) - Number(a.created_at || 0),
    )
    localStorage.setItem(
      TASK_HISTORY_STORAGE_KEY,
      JSON.stringify(merged.slice(0, 500)),
    )
  } catch {
    // Ignore storage errors
  }
}

export type TaskDataScope = '24h' | 'all'

const REQUEUED_TASKS_STORAGE_KEY = 'ov_studio_requeued_task_ids'

function getStoredRequeuedTaskIds(): Set<string> {
  if (typeof window === 'undefined') return new Set()
  try {
    const raw = localStorage.getItem(REQUEUED_TASKS_STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) return new Set(parsed)
    }
  } catch {
    // Fallthrough to empty set on parse error
  }
  return new Set()
}

function getEffectiveTaskStatus(
  item: TaskRecord,
  requeuedIds?: Set<string>,
): TaskStatusFilter {
  const requeued = requeuedIds ?? getStoredRequeuedTaskIds()
  const isRequeued =
    Boolean(item.task_id && requeued.has(item.task_id)) ||
    Boolean(item.resource_id && requeued.has(item.resource_id))
  if (isRequeued) {
    return 'pending'
  }
  return normalizeTaskStatus(item.status) as TaskStatusFilter
}

async function fetchTasks(
  taskType: TaskTypeFilter,
  status: TaskStatusFilter,
  dataScope: TaskDataScope = '24h',
): Promise<TaskRecord[]> {
  const query = {
    limit: dataScope === 'all' ? 10000 : MAX_TASKS,
    status: undefined,
    task_type: taskType === 'all' ? undefined : taskType,
    include_archived: dataScope === 'all' ? true : undefined,
  }
  const requeuedIds = getStoredRequeuedTaskIds()
  try {
    const result = await getOvResult<unknown>(
      getTasks({
        query: query as any,
      }),
    )
    const fetched = normalizeTasks(result)
    saveStoredTaskHistory(fetched)

    const history = getStoredTaskHistory()
    const map = new Map<string, TaskRecord>()
    history.forEach((t) => {
      if (t.task_id) map.set(t.task_id, t)
    })
    fetched.forEach((t) => {
      if (t.task_id) map.set(t.task_id, t)
    })
    let all = Array.from(map.values()).sort(
      (a, b) => Number(b.created_at || 0) - Number(a.created_at || 0),
    )
    if (dataScope === '24h') {
      const nowSec = Math.floor(Date.now() / 1000)
      all = all.filter((t) => {
        const timeVal = Number(t.created_at || t.updated_at || 0)
        return timeVal > 0 && nowSec - timeVal <= 86400
      })
    }
    if (status !== 'all') {
      all = all.filter((t) => getEffectiveTaskStatus(t, requeuedIds) === status)
    }
    if (taskType !== 'all') {
      all = all.filter((t) => t.task_type === taskType)
    }
    return all
  } catch (err) {
    console.warn(
      '[fetchTasks] Backend fetch failed, falling back to local history:',
      err,
    )
    let history = getStoredTaskHistory()
    if (dataScope === '24h') {
      const nowSec = Math.floor(Date.now() / 1000)
      history = history.filter((t) => {
        const timeVal = Number(t.created_at || t.updated_at || 0)
        return timeVal > 0 && nowSec - timeVal <= 86400
      })
    }
    if (status !== 'all') {
      history = history.filter((t) => getEffectiveTaskStatus(t, requeuedIds) === status)
    }
    if (taskType !== 'all') {
      history = history.filter((t) => t.task_type === taskType)
    }
    return history
  }
}

function saveStoredRequeuedTaskId(taskId: string) {
  if (typeof window === 'undefined') return
  try {
    const current = getStoredRequeuedTaskIds()
    current.add(taskId)
    localStorage.setItem(
      REQUEUED_TASKS_STORAGE_KEY,
      JSON.stringify(Array.from(current)),
    )
  } catch {
    // Ignore storage errors
  }
}

function clearStoredRequeuedTaskIds(): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.removeItem(REQUEUED_TASKS_STORAGE_KEY)
  } catch {
    // Ignore storage errors
  }
}

function removeStoredRequeuedTaskId(id: string): void {
  if (typeof window === 'undefined') return
  try {
    const current = getStoredRequeuedTaskIds()
    current.delete(id)
    localStorage.setItem(
      REQUEUED_TASKS_STORAGE_KEY,
      JSON.stringify(Array.from(current)),
    )
  } catch {
    // Ignore storage errors
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
  const [dataScope, setDataScope] = React.useState<TaskDataScope>('24h')
  const [selectedTaskId, setSelectedTaskId] = React.useState<string | null>(
    null,
  )
  const [requeuedTaskIds, setRequeuedTaskIds] = React.useState<Set<string>>(
    () => getStoredRequeuedTaskIds(),
  )
  const tasksQuery = useQuery({
    queryFn: () => fetchTasks(taskType, statusFilter, dataScope),
    queryKey: ['tasks', identityScopeKey, taskType, statusFilter, dataScope],
    refetchInterval: 10_000,
  })
  const rawTasks = tasksQuery.data ?? []
  const allTasks = rawTasks
  const pageOffset = (page - 1) * pageSize
  const tasks = allTasks.slice(pageOffset, pageOffset + pageSize)
  const totalPages = Math.max(1, Math.ceil(allTasks.length / pageSize))
  const hasNext = page < totalPages
  const hasActiveFilters = taskType !== 'all' || statusFilter !== 'all'

  const retryMutation = useMutation({
    onMutate: (task: TaskRecord) => {
      const taskId = task.task_id
      if (taskId) {
        saveStoredRequeuedTaskId(taskId)
        setRequeuedTaskIds((prev) => new Set(prev).add(taskId))
        const updatedTask: TaskRecord = {
          ...task,
          status: 'pending',
          error: undefined,
        }
        saveStoredTaskHistory([updatedTask])
      }
      toast.success(
        i18n.language.startsWith('zh')
          ? '已提交重新入队指令，任务状态已修改恢复为 [等待中]'
          : 'Re-queue command submitted, task status reset to pending',
      )
    },
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
      if (task.resource_id.startsWith('viking://resources/')) {
        const resp = await ovClient.instance.post('/api/v1/content/reindex', {
          uri: task.resource_id,
          wait: false,
        })
        const json = resp.data
        if (json.error) {
          throw new Error(
            json.error?.message ||
              (i18n.language.startsWith('zh')
                ? '重新索引失败'
                : 'Reindex failed'),
          )
        }
        return { res: json, task }
      }
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
      if (task.task_type === 'add_resource') {
        const res = await postResources({
          body: {
            path: task.resource_id,
            reason: `Re-queued task: ${task.task_id}`,
          } as any,
        })
        return { res, task }
      }
      throw new Error(
        i18n.language.startsWith('zh')
          ? '此任务类型暂不支持直接重新入队'
          : 'Retry not supported for this task type',
      )
    },
    onError: (error, task) => {
      // Rollback optimistic localStorage state so the badge goes back to its real status
      if (task.task_id) {
        removeStoredRequeuedTaskId(task.task_id)
        const removedTaskId = task.task_id
        setRequeuedTaskIds((prev) => {
          const next = new Set(prev)
          next.delete(removedTaskId)
          return next
        })
      }
      if (task.resource_id) {
        removeStoredRequeuedTaskId(task.resource_id)
        const removedResourceId = task.resource_id
        setRequeuedTaskIds((prev) => {
          const next = new Set(prev)
          next.delete(removedResourceId)
          return next
        })
      }
      toast.error(error instanceof Error ? error.message : String(error))
    },
    onSuccess: async (_data) => {
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
    const status = normalizeTaskStatus(task.status)
    if (status === 'completed') return 100
    if (status === 'failed') return 35
    if (status === 'pending') return 0

    // Extract real queue metrics from task.result
    const resObj = (task.result && typeof task.result === 'object') ? (task.result as Record<string, any>) : {}
    const qStatus = resObj.queue_status
    const embeddingProcessed = qStatus?.Embedding?.processed
    const semanticProcessed = qStatus?.Semantic?.processed

    if (typeof embeddingProcessed === 'number') {
      const totalEmbedding = 20
      const embedRatio = Math.min(1, embeddingProcessed / totalEmbedding)
      // Step 1 (20%) + Step 2 (30%) + Step 3 (50% * embedRatio)
      return Math.round(20 + 30 + (50 * embedRatio))
    }

    if (typeof semanticProcessed === 'number') {
      const totalSemantic = 5
      const semRatio = Math.min(1, semanticProcessed / totalSemantic)
      // Step 1 (20%) + Step 2 (30% * semRatio)
      return Math.round(20 + (30 * semRatio))
    }

    const stage = task.stage?.toLowerCase()
    if (stage === 'completed') return 95
    if (stage === 'extracting') return 65
    if (stage === 'started') return 25
    return 45
  }

  const getTaskTotalSteps = (taskType?: string): number => {
    if (taskType === 'session_commit') return 1
    if (taskType === 'admin_reindex' || taskType === 'snapshot_restore_reindex') return 2
    if (taskType === 'connector_import') return 4
    return 3
  }

  const renderStatus = (task: TaskRecord) => {
    const taskId = task.task_id
    const rawStatus = normalizeTaskStatus(task.status)
    const isRequeued = Boolean(
      taskId && (requeuedTaskIds.has(taskId) || requeuedTaskIds.has(task.resource_id || ''))
    )
    const status = isRequeued ? 'pending' : rawStatus
    const pct = getTaskProgressPct(task)

    return (
      <Badge
        variant={
          status === 'failed'
            ? 'destructive'
            : status === 'completed'
              ? 'secondary'
              : 'outline'
        }
        className="gap-1.5 font-normal select-none"
      >
        <span>{t(`status.${status}`)}</span>
        {status === 'running' && (
          <span className="font-mono font-semibold ml-0.5">
            {pct}%
          </span>
        )}
        {status === 'failed' && (
          <button
            type="button"
            className="ml-1 inline-flex items-center justify-center rounded p-0.5 hover:bg-white/25 active:scale-95 transition-all cursor-pointer text-destructive-foreground"
            title={i18n.language.startsWith('zh') ? '重新加入等待队列' : 'Re-queue into Pending Queue'}
            onClick={(e) => {
              e.stopPropagation()
              if (taskId) {
                setRequeuedTaskIds((prev) => new Set([...prev, taskId]))
              }
              if (task.resource_id) {
                setRequeuedTaskIds((prev) => new Set([...prev, task.resource_id!]))
              }
              retryMutation.mutate(task)
              toast.success(
                i18n.language.startsWith('zh')
                  ? '已将该任务重新加入等待队列！'
                  : 'Task re-queued into pending queue!',
              )
            }}
          >
            <RotateCcwIcon className="size-3 shrink-0" />
          </button>
        )}
      </Badge>
    )
  }


  const renderQueuePipeline = (task: TaskRecord) => {
    const rawStatus = normalizeTaskStatus(task.status)
    const isRequeued = Boolean(
      task.task_id && (requeuedTaskIds.has(task.task_id) || requeuedTaskIds.has(task.resource_id || ''))
    )
    const status = isRequeued ? 'pending' : rawStatus
    const type = task.task_type

    interface StepItem {
      name: string
      state: 'completed' | 'running' | 'pending' | 'failed'
    }

    type PipelineGroup =
      | { type: 'serial'; step: StepItem }
      | { type: 'parallel'; steps: StepItem[] }

    // 从 result.queue_status 读取真实的子工序状态
    const resObj = (task.result && typeof task.result === 'object') ? (task.result as Record<string, any>) : {}
    const qStatus = resObj.queue_status as Record<string, { processed?: number; error_count?: number }> | undefined

    // 根据子工序真实数据推断单步状态
    const inferStepState = (
      qKey: string | null,
      fallback: StepItem['state'],
    ): StepItem['state'] => {
      if (status === 'pending') return 'pending'
      if (qKey && qStatus?.[qKey]) {
        const s = qStatus[qKey]
        if ((s.error_count ?? 0) > 0) return 'failed'
        if ((s.processed ?? 0) > 0) return 'completed'
        // has entry but 0 processed: running if task is running, else pending
        return status === 'running' ? 'running' : fallback
      }
      // no queue_status entry yet: fall back to overall task status
      return fallback
    }

    let groups: PipelineGroup[] = []

    if (type === 'session_commit') {
      groups = [
        { type: 'serial', step: { name: '会话提交', state: status === 'completed' ? 'completed' : (status as any) } },
      ]
    } else if (type === 'admin_reindex' || type === 'snapshot_restore_reindex') {
      const purgeState: StepItem['state'] = status === 'pending' ? 'pending' : 'completed'
      const rebuildState = inferStepState('Embedding', status === 'completed' ? 'completed' : (status as any))
      groups = [
        { type: 'serial', step: { name: '外部解析', state: purgeState } },
        { type: 'serial', step: { name: '嵌入向量', state: rebuildState } },
      ]
    } else if (type === 'connector_import') {
      const preState: StepItem['state'] = status === 'pending' ? 'pending' : 'completed'
      groups = [
        { type: 'serial', step: { name: '外部解析', state: preState } },
        {
          type: 'parallel',
          steps: [
            { name: '语义处理', state: inferStepState('Semantic', status === 'completed' ? 'completed' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'pending') },
            { name: '嵌入向量', state: inferStepState('Embedding', status === 'completed' ? 'completed' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'pending') },
          ],
        },
      ]
    } else {
      // add_resource / add_skill: 外部解析 -> 语义处理 + 嵌入向量
      const parseState: StepItem['state'] = status === 'pending' ? 'pending' : 'completed'
      groups = [
        { type: 'serial', step: { name: '外部解析', state: parseState } },
        {
          type: 'parallel',
          steps: [
            { name: '语义处理', state: inferStepState('Semantic', status === 'completed' ? 'completed' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'pending') },
            { name: '嵌入向量', state: inferStepState('Embedding', status === 'completed' ? 'completed' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'pending') },
          ],
        },
      ]
    }

    return (
      <div className="flex items-center gap-1.5 overflow-x-auto py-0.5 min-w-[210px]">
        {groups.map((grp: PipelineGroup, i: number) => {
          const stepsInGroup = grp.type === 'serial' ? [grp.step] : grp.steps

          return (
            <React.Fragment key={i}>
              {i > 0 && (
                <span title="串行工序流转" className="inline-flex shrink-0">
                  <ChevronRightIcon className="size-3 text-muted-foreground/40" />
                </span>
              )}
              <span
                className="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-medium leading-none shrink-0 border border-border/60 bg-secondary/80 text-foreground shadow-2xs transition-all"
                title={grp.type === 'parallel' ? '并发执行工序批次' : '串行工序批次'}
              >
                {stepsInGroup.map((st: StepItem, j: number) => {
                  const isDone = st.state === 'completed'
                  const isRun = st.state === 'running'
                  const isFail = st.state === 'failed'
                  const isPend = st.state === 'pending'

                  return (
                    <span
                      key={j}
                      className="inline-flex items-center gap-1 shrink-0 transition-colors text-foreground/90 font-medium"
                    >
                      {isDone && <CheckIcon className="size-3 text-foreground/75 shrink-0" />}
                      {isRun && <LoaderCircleIcon className="size-3 text-foreground/75 animate-spin shrink-0" />}
                      {isPend && <CircleDashedIcon className="size-3 text-foreground/75 shrink-0" />}
                      {isFail && <XIcon className="size-3 text-foreground/75 shrink-0" />}
                      <span>{st.name}</span>
                    </span>
                  )
                })}
              </span>
            </React.Fragment>
          )
        })}
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

  const queueRows = React.useMemo(() => {
    const map: Record<
      string,
      { processing: number; pending: number; completed: number; errors: number }
    > = {
      Embedding: { processing: 0, pending: 0, completed: 0, errors: 0 },
      Semantic: { processing: 0, pending: 0, completed: 0, errors: 0 },
      ExternalParse: { processing: 0, pending: 0, completed: 0, errors: 0 },
      SessionCommit: { processing: 0, pending: 0, completed: 0, errors: 0 },
      'Semantic-Nodes': { processing: 0, pending: 0, completed: 0, errors: 0 },
    }

    for (const item of allTasks) {
      const st = normalizeTaskStatus(item.status)
      const qStatus = (item.result as any)?.queue_status

      if (item.task_type === 'session_commit') {
        if (st === 'running') map.SessionCommit.processing++
        else if (st === 'pending') map.SessionCommit.pending++
        else if (st === 'completed') map.SessionCommit.completed++
        else if (st === 'failed') map.SessionCommit.errors++
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
        // add_resource / add_skill / connector_import 包含：解析 (ExternalParse) -> 语义提炼 (Semantic) + 向量落库 (Embedding)
        if (st === 'running') {
          map.ExternalParse.processing++
          map.Semantic.processing++
          map.Embedding.processing++
        } else if (st === 'pending') {
          map.ExternalParse.pending++
          map.Semantic.pending++
          map.Embedding.pending++
        } else if (st === 'completed') {
          map.ExternalParse.completed++
          map.Semantic.completed++
          map.Embedding.completed++
        } else if (st === 'failed') {
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

  const kpiData = React.useMemo(() => {
    const requeuedIds = getStoredRequeuedTaskIds()
    const total = allTasks.length
    const completed = allTasks.filter(
      (item) => getEffectiveTaskStatus(item, requeuedIds) === 'completed',
    ).length
    const running = allTasks.filter(
      (item) => getEffectiveTaskStatus(item, requeuedIds) === 'running',
    ).length
    const pending = allTasks.filter(
      (item) => getEffectiveTaskStatus(item, requeuedIds) === 'pending',
    ).length
    const failed = allTasks.filter(
      (item) => getEffectiveTaskStatus(item, requeuedIds) === 'failed',
    ).length

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
              {i18n.language.startsWith('zh') ? '任务成功率' : 'Success Rate'}
            </span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-xl font-bold tabular-nums text-foreground">
              {kpiData.successRate.toFixed(1)}%
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {i18n.language.startsWith('zh')
              ? `共 ${kpiData.total} 条任务 (${kpiData.failed} 异常)`
              : `Total ${kpiData.total} (${kpiData.failed} Failed)`}
          </p>
        </Card>

        <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">
              {i18n.language.startsWith('zh') ? '平均处理耗时' : 'Avg Duration'}
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
            {i18n.language.startsWith('zh')
              ? '全流程平均处理时长'
              : 'Avg Processing Time'}
          </p>
        </Card>

        <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">
              {i18n.language.startsWith('zh') ? '任务总数' : 'Total Tasks'}
            </span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-xl font-bold tabular-nums text-foreground">
              {kpiData.total} 条
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {i18n.language.startsWith('zh')
              ? `已完成 ${kpiData.completed} 条`
              : `Completed ${kpiData.completed} Tasks`}
          </p>
        </Card>

        <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">
              {i18n.language.startsWith('zh') ? '并发与排队' : 'Active/Pending'}
            </span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-xl font-bold tabular-nums text-foreground">
              {kpiData.running} / {kpiData.pending}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {i18n.language.startsWith('zh')
              ? '进行中 / 等待中任务'
              : 'Running / Pending Workloads'}
          </p>
        </Card>
      </div>

      {/* 任务队列 (上层) 与 工序队列 (下层) 50/50 并排观测行 */}
      <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-2">
        {/* 左侧 (50% 宽度 - 优先看上层任务): 任务队列状态 (Task Queues) */}
        <div>
          <QueueStatusCard
            title={i18n.language.startsWith('zh') ? '任务队列状态' : 'Task Queue Status'}
            customRows={kpiData.typeRows}
            isHealthy={kpiData.failed === 0}
          />
        </div>

        {/* 右侧 (50% 宽度 - 拆分出的下层工序): 工序队列状态 (Process Queues) */}
        <div>
          <QueueStatusCard
            title={i18n.language.startsWith('zh') ? '工序队列状态' : 'Process Queue Status'}
            customRows={queueRows}
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
        {requeuedTaskIds.size > 0 ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="text-xs text-muted-foreground hover:text-foreground border-dashed"
            onClick={() => {
              clearStoredRequeuedTaskIds()
              setRequeuedTaskIds(new Set())
              toast.success(
                i18n.language.startsWith('zh')
                  ? '已物理还原后端真实数据库状态 (清除单机重试标记)'
                  : 'Restored real backend database status',
              )
            }}
          >
            🔄 {i18n.language.startsWith('zh') ? '还原真实状态' : 'Reset Local Overrides'}
          </Button>
        ) : null}
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
                  <TableHead>{i18n.language.startsWith('zh') ? '工序队列流转' : 'Queue Pipeline'}</TableHead>
                  <TableHead>{t('table.status')}</TableHead>
                  <TableHead>{i18n.language.startsWith('zh') ? '耗时' : 'Duration'}</TableHead>
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
                      <TableCell>{renderQueuePipeline(task)}</TableCell>
                      <TableCell>{renderStatus(task)}</TableCell>
                      <TableCell className="whitespace-nowrap font-mono text-xs text-muted-foreground">
                        {formatTaskDuration(task, i18n.language.startsWith('zh'))}
                      </TableCell>
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
