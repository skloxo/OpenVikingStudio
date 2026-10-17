/**
 * use-resource-upload.tsx
 * 资源上传通道与任务状态管理 Provider 及 Hook。
 * 遵循 Agent 编码规范与黄金甜点区（<= 500 行，目标 300 行）。
 */
import * as React from 'react'
import { toast } from 'sonner'

import { getOvResult, getTasks, ovClient } from '#/lib/ov-client'
import { parseUploadError } from '../-lib/upload'
import type { TaskListResult } from '@ov-server/api/v1/tasks'

import {
  INITIAL_REMOTE_STATE,
  RESOURCE_ADD_TASK_TYPE,
  TASK_REFRESH_INTERVAL_MS,
  TASK_REFRESH_LIMIT,
} from './resource-upload-types'
import type {
  RefreshTasksOptions,
  RemoteStartParams,
  RemoteUploadPhase,
  RemoteUploadState,
  ResourceUploadContextValue,
  ResourceUploadTask,
  ResourceUploadTaskStatus,
  UploadBatchItem,
  UploadBatchParams,
} from './resource-upload-types'
import {
  createRemoteTaskName,
  createTaskId,
  getErrorMessage,
  isUploadStatusActive,
  mergeServerTasks,
  normalizeTaskList,
} from './resource-upload-utils'
import {
  executeRemoteUpload,
  executeTempFileUpload,
} from './upload-processors'

// Re-export types for backward compatibility
export type {
  RefreshTasksOptions,
  RemoteStartParams,
  RemoteUploadPhase,
  RemoteUploadState,
  ResourceUploadContextValue,
  ResourceUploadTask,
  ResourceUploadTaskStatus,
  UploadBatchItem,
  UploadBatchParams,
}

const ResourceUploadContext =
  React.createContext<ResourceUploadContextValue | null>(null)

export function useResourceUpload(): ResourceUploadContextValue {
  const context = React.useContext(ResourceUploadContext)
  if (!context) {
    throw new Error(
      'useResourceUpload must be used within ResourceUploadProvider.',
    )
  }
  return context
}

export function ResourceUploadProvider({
  children,
}: {
  children: React.ReactNode
}) {
  const [tasks, setTasks] = React.useState<ResourceUploadTask[]>([])
  const [remoteState, setRemoteState] =
    React.useState<RemoteUploadState>(INITIAL_REMOTE_STATE)
  const [isRefreshingTasks, setIsRefreshingTasks] = React.useState(false)
  const remoteAbortRef = React.useRef<AbortController | null>(null)
  const refreshInFlightRef = React.useRef(false)
  const notifiedServerTaskIdsRef = React.useRef<Set<string>>(new Set())
  const uploadQueueRef = React.useRef<Promise<void>>(Promise.resolve())

  const updateTask = React.useCallback(
    (
      taskId: string,
      updater: (task: ResourceUploadTask) => ResourceUploadTask,
    ) => {
      setTasks((prev) =>
        prev.map((task) => (task.id === taskId ? updater(task) : task)),
      )
    },
    [],
  )

  const refreshTasks = React.useCallback(
    async (options: RefreshTasksOptions = {}) => {
      if (refreshInFlightRef.current) return

      refreshInFlightRef.current = true
      if (!options.silent) setIsRefreshingTasks(true)

      try {
        const result = await getOvResult<TaskListResult>(
          getTasks({
            query: {
              limit: TASK_REFRESH_LIMIT,
              task_type: RESOURCE_ADD_TASK_TYPE,
            },
          }),
        )
        const serverTasks = normalizeTaskList(result)
        setTasks((prev) => mergeServerTasks(prev, serverTasks))
      } catch (error) {
        if (options.notifyOnError !== false) {
          toast.error(getErrorMessage(error), { duration: 5000 })
        }
      } finally {
        refreshInFlightRef.current = false
        if (!options.silent) setIsRefreshingTasks(false)
      }
    },
    [],
  )

  const clearTasks = React.useCallback(async () => {
    try {
      await ovClient.instance.post('/api/v1/tasks/clear-failed')
      setTasks((prev) => prev.filter((t) => isUploadStatusActive(t.status)))
    } catch (error) {
      toast.error(getErrorMessage(error))
    }
  }, [])

  const processFileUpload = React.useCallback(
    async (
      taskId: string,
      params: UploadBatchItem,
      commonBody: Record<string, unknown>,
    ) => {
      try {
        updateTask(taskId, (task) => ({
          ...task,
          status: 'uploading',
          progress: 0,
        }))

        const { rootUri, serverTaskId } = await executeTempFileUpload(
          params,
          commonBody,
          (progress) => {
            updateTask(taskId, (task) => ({
              ...task,
              status: 'uploading',
              progress,
            }))
          },
        )

        if (serverTaskId) {
          updateTask(taskId, (task) => ({
            ...task,
            serverTaskId,
            status: 'processing',
            progress: null,
            rootUri,
          }))
          void refreshTasks({ notifyOnError: false, silent: true })
          return
        }

        updateTask(taskId, (task) => ({
          ...task,
          status: 'success',
          progress: 100,
          finishedAt: Date.now(),
          rootUri,
        }))
        toast.success(params.file.name)
      } catch (error) {
        const { errorCode, errorMessage } = parseUploadError(
          getErrorMessage(error),
        )
        updateTask(taskId, (task) => ({
          ...task,
          status: 'failed',
          progress: null,
          finishedAt: Date.now(),
          errorCode,
          errorMessage,
        }))
        toast.error(errorMessage, { duration: 5000 })
      }
    },
    [refreshTasks, updateTask],
  )

  const enqueueUploads = React.useCallback(
    (params: UploadBatchParams) => {
      if (params.files.length === 0) return

      const createdAt = Date.now()
      const nextTasks = params.files.map((item, index) => ({
        id: createTaskId(),
        source: 'local' as const,
        serverTaskId: null,
        fileName: item.file.name,
        fileSize: item.file.size,
        fileType: item.fileType,
        status: 'pending' as const,
        progress: 0,
        createdAt: createdAt + index,
        finishedAt: null,
        errorCode: null,
        errorMessage: null,
        rootUri: null,
      }))

      setTasks((prev) => [...nextTasks, ...prev])

      for (const [index, item] of params.files.entries()) {
        const task = nextTasks[index]
        uploadQueueRef.current = uploadQueueRef.current.then(() =>
          processFileUpload(task.id, item, params.commonBody),
        )
      }
    },
    [processFileUpload],
  )

  const startRemote = React.useCallback(
    (params: RemoteStartParams) => {
      if (remoteAbortRef.current) return

      const controller = new AbortController()
      remoteAbortRef.current = controller
      const taskId = createTaskId()

      setTasks((prev) => [
        {
          id: taskId,
          source: 'remote',
          serverTaskId: null,
          fileName: createRemoteTaskName(params.url),
          fileSize: null,
          fileType: null,
          status: 'processing',
          progress: null,
          createdAt: Date.now(),
          finishedAt: null,
          errorCode: null,
          errorMessage: null,
          rootUri: null,
        },
        ...prev,
      ])

      setRemoteState({
        phase: 'processing',
        skippedFiles: [],
        error: null,
        remoteUrl: params.url,
        taskId: null,
      })

      void (async () => {
        try {
          const { rootUri, serverTaskId, warnings } = await executeRemoteUpload(
            params.url,
            params.commonBody,
            controller.signal,
          )

          if (serverTaskId) {
            updateTask(taskId, (task) => ({
              ...task,
              serverTaskId,
              status: 'processing',
              progress: null,
              rootUri,
            }))

            setRemoteState({
              phase: 'processing',
              skippedFiles: warnings,
              error: null,
              remoteUrl: params.url,
              taskId: serverTaskId,
            })
            void refreshTasks({ notifyOnError: false, silent: true })
            return
          }

          updateTask(taskId, (task) => ({
            ...task,
            status: 'success',
            progress: 100,
            finishedAt: Date.now(),
            rootUri,
          }))

          setRemoteState({
            phase: 'done',
            skippedFiles: warnings,
            error: null,
            remoteUrl: params.url,
            taskId: null,
          })
          toast.success(params.url)
        } catch (error) {
          if (controller.signal.aborted) {
            updateTask(taskId, (task) => ({
              ...task,
              status: 'failed',
              progress: null,
              finishedAt: Date.now(),
              errorCode: 'CANCELED',
              errorMessage: 'Canceled',
            }))
            return
          }
          const message = getErrorMessage(error)
          const { errorCode, errorMessage } = parseUploadError(message)

          updateTask(taskId, (task) => ({
            ...task,
            status: 'failed',
            progress: null,
            finishedAt: Date.now(),
            errorCode,
            errorMessage,
          }))

          setRemoteState({
            phase: 'idle',
            skippedFiles: [],
            error: message,
            remoteUrl: params.url,
            taskId: null,
          })
          toast.error(errorMessage, { duration: 5000 })
        } finally {
          remoteAbortRef.current = null
        }
      })()
    },
    [refreshTasks, updateTask],
  )

  const resetRemote = React.useCallback(() => {
    if (remoteAbortRef.current) {
      remoteAbortRef.current.abort()
      remoteAbortRef.current = null
    }
    setRemoteState(INITIAL_REMOTE_STATE)
  }, [])

  React.useEffect(() => {
    void refreshTasks({ notifyOnError: false, silent: true })
  }, [refreshTasks])

  const hasActiveServerTasks = React.useMemo(
    () =>
      tasks.some(
        (task) => task.serverTaskId && isUploadStatusActive(task.status),
      ),
    [tasks],
  )

  React.useEffect(() => {
    if (!hasActiveServerTasks) return undefined

    const interval = window.setInterval(() => {
      void refreshTasks({ notifyOnError: false, silent: true })
    }, TASK_REFRESH_INTERVAL_MS)

    return () => window.clearInterval(interval)
  }, [hasActiveServerTasks, refreshTasks])

  React.useEffect(() => {
    if (remoteState.phase !== 'processing' || !remoteState.taskId) return

    const remoteTask = tasks.find(
      (task) => task.serverTaskId === remoteState.taskId,
    )
    if (!remoteTask || isUploadStatusActive(remoteTask.status)) return

    if (remoteTask.status === 'success') {
      setRemoteState((prev) =>
        prev.taskId === remoteTask.serverTaskId
          ? { ...prev, phase: 'done', error: null }
          : prev,
      )
      return
    }

    if (remoteTask.status === 'failed') {
      setRemoteState((prev) =>
        prev.taskId === remoteTask.serverTaskId
          ? {
              ...prev,
              phase: 'idle',
              error: remoteTask.errorMessage || 'Processing failed',
            }
          : prev,
      )
    }
  }, [remoteState.phase, remoteState.taskId, tasks])

  React.useEffect(() => {
    for (const task of tasks) {
      if (
        !task.serverTaskId ||
        task.source === 'server' ||
        isUploadStatusActive(task.status) ||
        notifiedServerTaskIdsRef.current.has(task.serverTaskId)
      ) {
        continue
      }

      notifiedServerTaskIdsRef.current.add(task.serverTaskId)
      if (task.status === 'success') {
        toast.success(task.fileName)
      } else if (task.status === 'failed') {
        toast.error(task.errorMessage || task.fileName, { duration: 5000 })
      }
    }
  }, [tasks])

  const activeTaskCount = React.useMemo(
    () => tasks.filter((task) => isUploadStatusActive(task.status)).length,
    [tasks],
  )
  const hasActiveTasks = activeTaskCount > 0

  const value = React.useMemo<ResourceUploadContextValue>(
    () => ({
      tasks,
      remoteState,
      enqueueUploads,
      startRemote,
      resetRemote,
      refreshTasks,
      clearTasks,
      isRefreshingTasks,
      hasActiveTasks,
      activeTaskCount,
    }),
    [
      tasks,
      remoteState,
      enqueueUploads,
      startRemote,
      resetRemote,
      refreshTasks,
      clearTasks,
      isRefreshingTasks,
      hasActiveTasks,
      activeTaskCount,
    ],
  )

  return (
    <ResourceUploadContext.Provider value={value}>
      {children}
    </ResourceUploadContext.Provider>
  )
}
