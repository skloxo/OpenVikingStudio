/**
 * resource-upload-utils.ts
 * 资源上传任务状态归一化、解析、时间戳转换与服务端任务合并纯函数工具。
 */
import { isOvClientError } from '#/lib/ov-client'
import type { TaskListResult, TaskRecord } from '@ov-server/api/v1/tasks'
import type {
  ResourceUploadTask,
  ResourceUploadTaskStatus,
} from './resource-upload-types'

export function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

export function getErrorMessage(error: unknown): string {
  if (isOvClientError(error)) {
    return `${error.code}: ${error.message}`
  }
  if (error instanceof Error) {
    return error.message
  }
  return String(error)
}

export function createTaskId(): string {
  if (
    typeof crypto !== 'undefined' &&
    typeof crypto.randomUUID === 'function'
  ) {
    return crypto.randomUUID()
  }
  return `upload-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function createRemoteTaskName(url: string): string {
  const trimmed = url.trim()
  const sshMatch = trimmed.match(/^git@[^:]+:([^/]+\/[^/]+?)(?:\.git)?$/)
  if (sshMatch) {
    return sshMatch[1]
  }

  try {
    const parsed = new URL(trimmed)
    const parts = parsed.pathname.split('/').filter(Boolean)
    if (parts.length >= 2 && parsed.hostname.includes('github.com')) {
      return `${parts[0]}/${parts[1].replace(/\.git$/, '')}`
    }
    if (parts.length > 0) {
      return parts[parts.length - 1].replace(/\.git$/, '')
    }
    return parsed.hostname
  } catch {
    return trimmed
  }
}

export function isTaskRecord(value: unknown): value is TaskRecord {
  return (
    isRecord(value) &&
    typeof value.task_id === 'string' &&
    typeof value.task_type === 'string' &&
    typeof value.status === 'string'
  )
}

export function normalizeTaskList(value: unknown): TaskListResult {
  return Array.isArray(value) ? value.filter(isTaskRecord) : []
}

export function isUploadStatusActive(status: ResourceUploadTaskStatus): boolean {
  return (
    status === 'pending' || status === 'uploading' || status === 'processing'
  )
}

export function toEpochMillis(value: unknown, fallback: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return fallback
  }
  return value > 10_000_000_000 ? Math.round(value) : Math.round(value * 1000)
}

export function getResultString(record: TaskRecord, key: string): string | null {
  const value = record.result?.[key]
  return typeof value === 'string' && value.trim() ? value : null
}

export function getTaskRootUri(record: TaskRecord): string | null {
  if (typeof record.resource_id === 'string' && record.resource_id.trim()) {
    return record.resource_id
  }
  return getResultString(record, 'root_uri')
}

export function getNameFromUri(uri: string): string {
  const normalized = uri.replace(/\/+$/, '')
  const parts = normalized.split('/').filter(Boolean)
  return parts[parts.length - 1] || uri
}

export function getServerTaskName(record: TaskRecord): string {
  const sourceName = getResultString(record, 'source_name')
  if (sourceName) {
    return sourceName
  }

  const rootUri = getTaskRootUri(record)
  if (rootUri) {
    return getNameFromUri(rootUri)
  }

  return record.task_id
}

export function toUploadStatus(
  status: TaskRecord['status'],
): ResourceUploadTaskStatus {
  if (status === 'completed') {
    return 'success'
  }
  if (status === 'failed') {
    return 'failed'
  }
  if (status === 'cancelled' || status === 'cancelling') {
    return 'cancelled'
  }
  return 'processing'
}

export function mergeServerTask(
  record: TaskRecord,
  existing?: ResourceUploadTask,
): ResourceUploadTask {
  const status = toUploadStatus(record.status)
  const rootUri = getTaskRootUri(record) ?? existing?.rootUri ?? null
  const createdAt =
    existing?.createdAt ?? toEpochMillis(record.created_at, Date.now())
  const updatedAt = toEpochMillis(record.updated_at, Date.now())
  const fileName =
    existing && existing.source !== 'server'
      ? existing.fileName
      : getServerTaskName(record)
  const isFinished =
    status === 'success' || status === 'failed' || status === 'cancelled'

  return {
    id: existing?.id ?? `server-${record.task_id}`,
    source: existing?.source ?? 'server',
    serverTaskId: record.task_id,
    fileName,
    fileSize: existing?.fileSize ?? null,
    fileType: existing?.fileType ?? null,
    status,
    progress: status === 'success' ? 100 : null,
    createdAt,
    finishedAt: isFinished ? (existing?.finishedAt ?? updatedAt) : null,
    errorCode:
      status === 'failed'
        ? (existing?.errorCode ?? 'SERVER_TASK_FAILED')
        : null,
    errorMessage:
      status === 'failed'
        ? record.error || existing?.errorMessage || 'Processing failed'
        : null,
    rootUri,
  }
}

export function mergeServerTasks(
  previous: ResourceUploadTask[],
  serverTasks: TaskRecord[],
): ResourceUploadTask[] {
  const previousByServerId = new Map<string, ResourceUploadTask>()
  for (const task of previous) {
    if (task.serverTaskId) {
      previousByServerId.set(task.serverTaskId, task)
    }
  }

  const serverTaskIds = new Set(serverTasks.map((task) => task.task_id))
  const consumedLocalIds = new Set<string>()
  const nextTasks = serverTasks.map((record) => {
    const existing = previousByServerId.get(record.task_id)
    if (existing) {
      consumedLocalIds.add(existing.id)
    }
    return mergeServerTask(record, existing)
  })

  for (const task of previous) {
    if (consumedLocalIds.has(task.id)) {
      continue
    }
    if (
      task.source === 'server' &&
      task.serverTaskId &&
      !serverTaskIds.has(task.serverTaskId)
    ) {
      continue
    }
    nextTasks.push(task)
  }

  return nextTasks
}
