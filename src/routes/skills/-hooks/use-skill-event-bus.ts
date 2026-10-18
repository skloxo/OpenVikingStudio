import * as React from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ovClient } from '#/lib/ov-client'
import { fetchSse } from '#/lib/sse'

export interface SkillEventPayload {
  event: string
  connection_id?: string
  reason?: string
  skill_name?: string
  scope?: string
  timestamp?: number
  [key: string]: unknown
}

export interface UseSkillEventBusOptions {
  enabled?: boolean
  onEvent?: (payload: SkillEventPayload) => void
}

export interface UseSkillEventBusReturn {
  isConnected: boolean
  lastEventTime: number | null
  lastEvent: SkillEventPayload | null
}

/**
 * ⚡ 全双工实时技能事件总线 Hook (Card-165 SSOT)
 * 毫秒级感知底层技能热更新、新增、删除与 B6 质检入库事件，
 * 触发 TanStack Query 精准 Invalidation，消灭历史 60 秒轮询延迟。
 */
export function useSkillEventBus(options: UseSkillEventBusOptions = {}): UseSkillEventBusReturn {
  const { enabled = true, onEvent } = options
  const queryClient = useQueryClient()

  const [isConnected, setIsConnected] = React.useState(false)
  const [lastEventTime, setLastEventTime] = React.useState<number | null>(null)
  const [lastEvent, setLastEvent] = React.useState<SkillEventPayload | null>(null)

  const onEventRef = React.useRef(onEvent)
  React.useEffect(() => {
    onEventRef.current = onEvent
  }, [onEvent])

  React.useEffect(() => {
    if (!enabled) {
      setIsConnected(false)
      return
    }

    let retryTimeoutId: ReturnType<typeof setTimeout> | null = null
    const abortController = new AbortController()
    const { signal } = abortController

    const connect = async () => {
      if (signal.aborted) return

      try {
        const baseUrl = ovClient.getOptions().baseUrl || ''
        const conn = ovClient.getConnection()
        const headers: Record<string, string> = {
          Accept: 'text/event-stream',
        }
        const token = conn.adminApiKey || conn.apiKey
        if (token) {
          headers.Authorization = `Bearer ${token}`
        }

        const eventsUrl = `${baseUrl}/api/v1/skills/events`
        const stream = fetchSse(eventsUrl, {
          headers,
          method: 'GET',
          signal,
        })

        for await (const message of stream) {
          if (signal.aborted) break
          if (!message.data) continue

          try {
            const payload = JSON.parse(message.data) as SkillEventPayload
            setLastEvent(payload)
            setLastEventTime(Date.now())

            if (payload.event === 'CONNECTED') {
              setIsConnected(true)
            } else if (payload.event === 'HEARTBEAT') {
              setIsConnected(true)
            } else if (
              payload.event === 'SKILLS_MUTATED' ||
              payload.event === 'SKILL_ADDED' ||
              payload.event === 'SKILL_UPDATED' ||
              payload.event === 'SKILL_DELETED' ||
              payload.event === 'PIPELINE_PULSE'
            ) {
              // 毫秒级使技能全域 React Query 缓存失效，实现静默自愈拉新
              void queryClient.invalidateQueries({ queryKey: ['skills'] })
              void queryClient.invalidateQueries({ queryKey: ['skills-ingestion-queue-depth'] })
              void queryClient.invalidateQueries({ queryKey: ['skills-ingestion-queue'] })
              void queryClient.invalidateQueries({ queryKey: ['skills-provenance-events'] })
              if (payload.skill_name) {
                void queryClient.invalidateQueries({ queryKey: ['skill-detail'] })
              }
            }

            onEventRef.current?.(payload)
          } catch {
            // 忽略非 JSON 数据脉冲
          }
        }
      } catch {
        // 连接异常或被阻断
      } finally {
        setIsConnected(false)
        if (!signal.aborted) {
          // 4秒后自动优雅重连退避
          retryTimeoutId = setTimeout(connect, 4000)
        }
      }
    }

    void connect()

    return () => {
      abortController.abort()
      if (retryTimeoutId) {
        clearTimeout(retryTimeoutId)
      }
      setIsConnected(false)
    }
  }, [enabled, queryClient])

  return {
    isConnected,
    lastEventTime,
    lastEvent,
  }
}
