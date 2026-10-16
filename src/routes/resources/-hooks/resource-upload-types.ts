/**
 * resource-upload-types.ts
 * 资源上传通道任务模型、状态枚举与上下文契约定义。
 */
export type ResourceUploadTaskStatus =
  | 'pending'
  | 'uploading'
  | 'processing'
  | 'success'
  | 'failed'
  | 'cancelled'

export type ResourceUploadTask = {
  id: string
  source: 'local' | 'remote' | 'server'
  serverTaskId: string | null
  fileName: string
  fileSize: number | null
  fileType: string | null
  status: ResourceUploadTaskStatus
  progress: number | null
  createdAt: number
  finishedAt: number | null
  errorCode: string | null
  errorMessage: string | null
  rootUri: string | null
}

export type RemoteUploadPhase = 'idle' | 'processing' | 'done'

export type RemoteUploadState = {
  phase: RemoteUploadPhase
  skippedFiles: string[]
  error: string | null
  remoteUrl: string
  taskId: string | null
}

export type UploadBatchItem = {
  file: File
  fileType: string | null
}

export type UploadBatchParams = {
  files: UploadBatchItem[]
  commonBody: Record<string, unknown>
}

export type RemoteStartParams = {
  url: string
  commonBody: Record<string, unknown>
}

export type ResourceUploadContextValue = {
  tasks: ResourceUploadTask[]
  remoteState: RemoteUploadState
  enqueueUploads: (params: UploadBatchParams) => void
  startRemote: (params: RemoteStartParams) => void
  resetRemote: () => void
  refreshTasks: () => Promise<void>
  clearTasks: () => Promise<void>
  isRefreshingTasks: boolean
  hasActiveTasks: boolean
  activeTaskCount: number
}

export type RefreshTasksOptions = {
  notifyOnError?: boolean
  silent?: boolean
}

export const INITIAL_REMOTE_STATE: RemoteUploadState = {
  phase: 'idle',
  skippedFiles: [],
  error: null,
  remoteUrl: '',
  taskId: null,
}

export const RESOURCE_ADD_TASK_TYPE = 'add_resource'
export const TASK_REFRESH_INTERVAL_MS = 3_000
export const TASK_REFRESH_LIMIT = 50
