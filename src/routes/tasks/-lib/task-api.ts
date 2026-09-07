import { getOvResult, getTasks, ovClient } from '#/lib/ov-client'
import { postResources } from '#/gen/ov-client'
import { commitSession } from '#/lib/sessions/api'
import {
  normalizeTasks,
  normalizeTaskStatus,
} from '#/routes/tasks/-lib/task-record'
import type { TaskRecord, TaskStatus } from '#/routes/tasks/-lib/task-record'
import { getTaskDate } from '#/routes/tasks/-lib/task-time'
import type { ParsedQueueRow } from '#/routes/monitoring/-components/queue-status-card'
import type { TaskKpiData } from '#/routes/tasks/-components/tasks-metrics-cards'

export type TaskDataScope = '24h' | '7d' | 'all'

export type TaskStatusFilter = Exclude<TaskStatus, 'unknown'> | 'all'

export type TaskTypeFilter =
  | 'add_resource'
  | 'add_skill'
  | 'admin_reindex'
  | 'connector_import'
  | 'legacy_cleanup'
  | 'legacy_migration'
  | 'session_commit'
  | 'snapshot_restore_reindex'
  | 'all'

export const DEFAULT_PAGE_SIZE = 20
export const MAX_TASKS = 200
export const PAGE_SIZE_OPTIONS = [20, 50, 100] as const
export const TASK_TYPE_OPTIONS: Exclude<TaskTypeFilter, 'all'>[] = [
  'session_commit',
  'add_resource',
  'add_skill',
  'connector_import',
  'admin_reindex',
  'snapshot_restore_reindex',
  'legacy_migration',
  'legacy_cleanup',
]
export const TASK_STATUS_OPTIONS: Exclude<TaskStatusFilter, 'all'>[] = [
  'running',
  'pending',
  'completed',
  'failed',
  'cancelled',
]

/**
 * 根据 8 并发物理上限计算任务的物理有效状态 (前 8 个 running, 第 9 个及以后 pending)
 */
export function getEffectiveTaskStatus(taskItem: any, list: any[]): string {
  const rawStatus = normalizeTaskStatus(taskItem.status, taskItem.error)
  if (rawStatus !== 'running') {
    return rawStatus
  }
  const runningList = list
    .filter((t) => normalizeTaskStatus(t.status, t.error) === 'running')
    .sort((a, b) => Number(a.created_at || 0) - Number(b.created_at || 0))
  const idx = runningList.findIndex((t) => t.task_id === taskItem.task_id)
  return idx >= 8 ? 'pending' : 'running'
}

/**
 * 获取任务列表并执行时间范围保护过滤
 */
export async function fetchTasks(dataScope: TaskDataScope = '24h'): Promise<TaskRecord[]> {
  const query = {
    limit: MAX_TASKS,
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
    if (dataScope !== 'all') {
      const nowSec = Math.floor(Date.now() / 1000)
      const windowSec = dataScope === '24h' ? 86400 : 7 * 86400
      fetched = fetched.filter((t) => {
        const status = normalizeTaskStatus(t.status, t.error)
        // 未终结任务保护：进行中或排队中的任务，绝不可被时间范围过滤掉！
        if (status === 'running' || status === 'pending') {
          return true
        }
        const timeVal = Number(t.created_at || t.updated_at || 0)
        return timeVal > 0 && nowSec - timeVal <= windowSec
      })
    }
    return fetched
  } catch (error) {
    console.error('Failed to fetch tasks:', error)
    return []
  }
}

/**
 * 格式化任务创建时间
 */
export function formatTime(task: TaskRecord): string {
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

/**
 * 计算任务执行百分比进度
 */
export function getTaskProgressPct(
  task: TaskRecord,
  allTasks: TaskRecord[],
  queueObserverRows: ParsedQueueRow[],
): number {
  const effStatus = getEffectiveTaskStatus(task, allTasks)
  const status = normalizeTaskStatus(effStatus)
  if (status === 'completed') return 100
  if (status === 'failed') return 0
  if (status === 'pending') return 0

  const meta = (task.meta && typeof task.meta === 'object') ? task.meta : {}
  if (typeof meta.progress_pct === 'number') {
    return Math.min(99, Math.max(1, Math.round(meta.progress_pct)))
  }
  if (typeof meta.processed_chunks === 'number' && typeof meta.total_chunks === 'number' && meta.total_chunks > 0) {
    return Math.min(99, Math.max(1, Math.round((meta.processed_chunks / meta.total_chunks) * 100)))
  }

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

  const stage = task.stage?.toLowerCase()
  if (stage === 'completed' || stage === 'finalizing' || stage === 'committing') return 95
  if (stage === 'embedding_chunks' || stage === 'embedding') return 75
  if (stage === 'extracting_semantics' || stage === 'extracting') return 45
  if (stage === 'scanning' || stage === 'started') return 20

  const createdAtSec = typeof task.created_at === 'number'
    ? task.created_at
    : typeof task.created_at === 'string'
      ? (new Date(task.created_at).getTime() / 1000)
      : (Date.now() / 1000)
  const elapsedSec = Math.max(0, (Date.now() / 1000) - createdAtSec)
  const smoothPct = Math.min(88, Math.round(15 + (1 - Math.exp(-elapsedSec / 25)) * 73))
  return Math.max(10, smoothPct)
}

/**
 * 重新触发任务
 */
export async function executeTaskRetry(
  task: TaskRecord,
  isZh: boolean,
): Promise<{ res: any; task: TaskRecord; newTaskId?: string; skipped?: boolean; reason?: string }> {
  if (task.task_id?.startsWith('mock_task_')) {
    return { res: { ok: true }, task }
  }

  // 质量门禁重新执行 (Retry Quality Gate)
  if (task.task_type === 'quality_gate' || task.task_type === 'benchmark_eval') {
    const resp = await ovClient.instance.post('/api/v1/tasks/quality_gate', {
      mode: task.meta?.mode || 'smoke',
      resource_id: task.resource_id || undefined,
      threshold: task.meta?.threshold ?? 0.7,
      queries: task.meta?.queries,
    })
    const json = resp.data
    return { res: json, task, newTaskId: json?.result?.task_id }
  }

  if (!task.resource_id) {
    throw new Error(isZh ? '任务缺少关联资源 ID，无法重新入队' : 'Missing resource ID for task')
  }

  if (task.task_type === 'session_commit') {
    const res = await commitSession(task.resource_id)
    const resAny = res as any
    const resultData = resAny?.result || resAny
    if (resultData?.status === 'skipped' || resultData?.reason === 'no_messages') {
      return { res, task, skipped: true, reason: 'no_messages' }
    }
    return { res, task, newTaskId: resultData?.task_id }
  }

  const resourceUri = task.resource_id || ''
  if (resourceUri.startsWith('http://') || resourceUri.startsWith('https://')) {
    const res = await postResources({
      body: {
        url: resourceUri,
        reason: `Re-queued task: ${task.task_id}`,
      } as any,
    })
    const resAny = res as any
    return { res, task, newTaskId: resAny?.result?.task_id }
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
        (isZh ? '重新入队失败' : 'Re-queue failed'),
    )
  }
  return { res: json, task, newTaskId: json.result?.task_id }
}

/**
 * 计算 Task KPI 指标与工序队列统计行
 */
export function computeTaskKpiData(
  allTasks: TaskRecord[],
  t: (key: string, options?: any) => string,
): TaskKpiData {
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
      const pendingCount = matchingTasks.filter(
        (taskItem) => normalizeTaskStatus(taskItem.status) === 'pending',
      ).length
      const completedCount = matchingTasks.filter(
        (taskItem) => normalizeTaskStatus(taskItem.status) === 'completed',
      ).length
      const errors = matchingTasks.filter(
        (taskItem) => normalizeTaskStatus(taskItem.status) === 'failed',
      ).length
      return {
        name: t(`types.${typeKey}`, { defaultValue: typeKey }),
        typeKey,
        processing,
        pending: pendingCount,
        completed: completedCount,
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
}
