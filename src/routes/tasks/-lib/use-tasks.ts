import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { useAppConnection } from '#/hooks/use-app-connection'
import { ovClient } from '#/lib/ov-client'
import { parseQueueStatus } from '#/routes/monitoring/-components/queue-status-card'
import {
  computeTaskKpiData,
  executeTaskRetry,
  fetchTasks,
  getEffectiveTaskStatus,
} from '#/routes/tasks/-lib/task-api'
import type {
  TaskDataScope,
  TaskStatusFilter,
  TaskTypeFilter,
} from '#/routes/tasks/-lib/task-api'
import { normalizeTaskStatus } from '#/routes/tasks/-lib/task-record'
import type { TaskRecord } from '#/routes/tasks/-lib/task-record'

interface UseTasksOptions {
  dataScope: TaskDataScope
  taskType: TaskTypeFilter
  statusFilter: TaskStatusFilter
  dedupByResource: boolean
}

export function useTasks({
  dataScope,
  taskType,
  statusFilter,
  dedupByResource,
}: UseTasksOptions) {
  const { i18n, t } = useTranslation('tasksPage')
  const { identityScopeKey } = useAppConnection()
  const queryClient = useQueryClient()

  const tasksQuery = useQuery({
    queryFn: () => fetchTasks(dataScope),
    queryKey: ['tasks', identityScopeKey, dataScope],
    refetchInterval: (query) => {
      const currentTasks = query.state.data || []
      const hasActive = currentTasks.some((item) => {
        const s = normalizeTaskStatus(item.status, item.error)
        return s === 'running' || s === 'pending'
      })
      return hasActive ? 3000 : 10000
    },
  })
  const rawTasks = tasksQuery.data ?? []

  const queueObserverQuery = useQuery({
    queryKey: ['queue-observer-status'],
    queryFn: async () => {
      try {
        const resp = await ovClient.instance.get('/api/v1/observer/queue')
        return parseQueueStatus(resp.data?.result?.status || '')
      } catch {
        return []
      }
    },
    refetchInterval: () => {
      const hasActive = rawTasks.some((item) => {
        const s = normalizeTaskStatus(item.status, item.error)
        return s === 'running' || s === 'pending'
      })
      return hasActive ? 2000 : 15000
    },
  })
  const queueObserverRows = queueObserverQuery.data || []

  const allTasks = React.useMemo(() => {
    let list = rawTasks
    if (dedupByResource) {
      const map = new Map<string, TaskRecord>()
      const sorted = [...rawTasks].sort((a, b) => {
        const aStatus = normalizeTaskStatus(a.status, a.error)
        const bStatus = normalizeTaskStatus(b.status, b.error)
        const aActive = aStatus === 'running' ? 2 : aStatus === 'pending' ? 1 : 0
        const bActive = bStatus === 'running' ? 2 : bStatus === 'pending' ? 1 : 0
        if (aActive !== bActive) return bActive - aActive
        return Number(b.created_at || 0) - Number(a.created_at || 0)
      })
      for (const item of sorted) {
        const key = item.resource_id ? `res:${item.resource_id}` : `task:${item.task_id}`
        if (!map.has(key)) map.set(key, item)
      }
      list = Array.from(map.values())
    }
    if (taskType !== 'all') list = list.filter((item) => item.task_type === taskType)
    if (statusFilter !== 'all') list = list.filter((item) => getEffectiveTaskStatus(item, list) === statusFilter)
    return list
  }, [rawTasks, dedupByResource, taskType, statusFilter])

  const kpiData = React.useMemo(() => computeTaskKpiData(allTasks, t), [allTasks, t])

  const retryMutation = useMutation({
    mutationFn: (task: TaskRecord) => executeTaskRetry(task, i18n.language.startsWith('zh')),
    onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
    onSuccess: async (data) => {
      if (data?.skipped) {
        toast.info(
          i18n.language.startsWith('zh')
            ? '该会话消息此前已完成阶段一归档，无新增未提交消息。'
            : 'Session messages already archived.',
        )
      } else {
        const newTaskId = data?.newTaskId
        toast.success(
          i18n.language.startsWith('zh')
            ? `重新入队成功！${newTaskId ? `已生成新任务 (${newTaskId.slice(0, 8)}...)` : '后端正在调度处理。'}`
            : `Re-queued successfully! ${newTaskId ? `New task ID: ${newTaskId.slice(0, 8)}...` : ''}`,
        )
      }
      await queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })

  const clearFailedMutation = useMutation({
    mutationFn: async () => (await ovClient.instance.post('/api/v1/tasks/clear-failed')).data,
    onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
    onSuccess: async (data) => {
      const count = data?.result?.deleted_count ?? 0
      toast.success(
        i18n.language.startsWith('zh')
          ? `已成功清除 ${count} 条失败与取消任务！`
          : `Successfully cleared ${count} failed & cancelled tasks!`,
      )
      await queryClient.invalidateQueries({ queryKey: ['tasks'] })
      await queryClient.invalidateQueries({ queryKey: ['taskStats'] })
    },
  })

  const deleteTaskMutation = useMutation({
    mutationFn: async (taskId: string) => (await ovClient.instance.delete(`/api/v1/tasks/${taskId}`)).data,
    onError: (err) => toast.error(err instanceof Error ? err.message : String(err)),
    onSuccess: async () => {
      toast.success(i18n.language.startsWith('zh') ? '已删除该任务记录' : 'Task record deleted')
      await queryClient.invalidateQueries({ queryKey: ['tasks'] })
      await queryClient.invalidateQueries({ queryKey: ['taskStats'] })
    },
  })

  return {
    tasksQuery,
    queueObserverQuery,
    queueObserverRows,
    allTasks,
    kpiData,
    retryMutation,
    clearFailedMutation,
    deleteTaskMutation,
  }
}
