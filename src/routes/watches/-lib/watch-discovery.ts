import type { TaskRecord } from '#/routes/tasks/-lib/task-record'

import type { WatchTask } from './api'

export const WATCH_DISCOVERY_INTERVAL_MS = 1_000

export function isActiveTaskStatus(status: string | undefined): boolean {
  return status === 'pending' || status === 'running' || status === 'cancelling'
}

export function getWatchRefetchInterval(
  isDiscovering: boolean,
): number | false {
  return isDiscovering ? WATCH_DISCOVERY_INTERVAL_MS : false
}

export function normalizeWatchUri(uri: string): string {
  return uri.replace(/\/+$/, '')
}

export function hasDiscoveredWatch(
  watches: WatchTask[],
  targetUri: string,
): boolean {
  const normalizedTarget = normalizeWatchUri(targetUri)
  return watches.some(
    (watch) => normalizeWatchUri(watch.toUri) === normalizedTarget,
  )
}

export function hasCompletedTriggeredWatchSync(
  tasks: TaskRecord[],
  baselineTaskIds: string[],
): boolean {
  const baseline = new Set(baselineTaskIds)
  const triggeredTasks = tasks.filter(
    (task) => task.task_id && !baseline.has(task.task_id),
  )
  if (triggeredTasks.length === 0) return false
  if (triggeredTasks.some((task) => isActiveTaskStatus(task.status))) {
    return false
  }
  return triggeredTasks.every(
    (task) =>
      task.status === 'completed' ||
      task.status === 'failed' ||
      task.status === 'cancelled',
  )
}

export function hasWatchExecutionAdvanced(
  currentExecutionTime: string | null,
  baselineExecutionTime: string | null,
): boolean {
  if (!currentExecutionTime) return false
  if (!baselineExecutionTime) return true

  const currentTime = Date.parse(currentExecutionTime)
  const baselineTime = Date.parse(baselineExecutionTime)
  if (Number.isFinite(currentTime) && Number.isFinite(baselineTime)) {
    return currentTime > baselineTime
  }
  return currentExecutionTime !== baselineExecutionTime
}
