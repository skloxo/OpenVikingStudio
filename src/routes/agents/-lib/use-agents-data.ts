/**
 * use-agents-data.ts
 * 智能体中心核心数据获取、过滤与生命周期 Mutation (Cockpit UI 规范)。
 * 严格防御：Array.isArray 护栏，断流休眠律 (refetchIntervalInBackground: false)。
 */
import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useAppConnection } from '#/hooks/use-app-connection'
import type {
  CreateAgentInput,
  UpdateAgentInput,
  UserAgentItem,
} from '#/lib/admin'
import {
  activateUserAgent,
  createUserAgent,
  deleteUserAgent,
  updateUserAgent,
} from '#/lib/admin'
import type { AgentsSummaryMetrics } from './agent-types'

export type TopologyFilter = 'all' | 'local' | 'remote'

async function fetchSafeAgents(userId: string): Promise<UserAgentItem[]> {
  try {
    const res = await fetch(`/api/v1/users/${encodeURIComponent(userId)}/agents?status=all`)
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data?.result)) {
        return data.result
      }
    }
  } catch {
    // 忽略异常，尝试全集群回退
  }

  try {
    const resAll = await fetch('/api/v1/agents?status=all')
    if (resAll.ok) {
      const dataAll = await resAll.json()
      if (Array.isArray(dataAll?.result)) {
        return dataAll.result
      }
    }
  } catch {
    // 兜底返回空数组
  }
  return []
}

export function useAgentsData() {
  const queryClient = useQueryClient()
  const { connection } = useAppConnection()
  const activeUserId = connection.userId || 'default'

  const [topologyFilter, setTopologyFilter] = React.useState<TopologyFilter>('all')
  const [searchQuery, setSearchQuery] = React.useState('')
  const [expandedAgentId, setExpandedAgentId] = React.useState<string | null>(null)
  const [showNewAgentCard, setShowNewAgentCard] = React.useState(false)
  const [pendingDeleteAgent, setPendingDeleteAgent] = React.useState<UserAgentItem | null>(null)

  const {
    data: rawAgents = [],
    isLoading,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['cluster-agents', activeUserId],
    queryFn: () => fetchSafeAgents(activeUserId),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    staleTime: 10_000,
  })

  // 严格确保为数组，彻底切除 $.filter is not a function 隐患
  const agents = React.useMemo<UserAgentItem[]>(() => {
    return Array.isArray(rawAgents) ? rawAgents : []
  }, [rawAgents])

  // 概览指标计算
  const metrics = React.useMemo<AgentsSummaryMetrics>(() => {
    let active = 0
    let local = 0
    let remote = 0
    for (const a of agents) {
      if (a.status === 'active') active++
      if (a.connection_mode === 'realtimeApi') {
        local++
      } else {
        remote++
      }
    }
    return {
      totalAgents: agents.length,
      activeCount: active,
      localDirectCount: local,
      remoteGatewayCount: remote,
    }
  }, [agents])

  // 拓扑与关键词过滤
  const filteredAgents = React.useMemo(() => {
    return agents.filter((a) => {
      if (topologyFilter === 'local' && a.connection_mode !== 'realtimeApi') return false
      if (topologyFilter === 'remote' && a.connection_mode === 'realtimeApi') return false
      if (!searchQuery.trim()) return true
      const q = searchQuery.toLowerCase()
      return (
        a.agent_name.toLowerCase().includes(q) ||
        a.agent_id.toLowerCase().includes(q) ||
        a.role_desc.toLowerCase().includes(q) ||
        a.user_id.toLowerCase().includes(q)
      )
    })
  }, [agents, topologyFilter, searchQuery])

  // 创建智能体
  const createMutation = useMutation({
    mutationFn: (input: CreateAgentInput) => createUserAgent(activeUserId, input),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['cluster-agents'] })
      queryClient.invalidateQueries({ queryKey: ['user-agents'] })
      toast.success(`智能体「${data.agent.agent_name}」已签发成功`)
      setShowNewAgentCard(false)
      setExpandedAgentId(data.agent.agent_id)
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '创建智能体失败')
    },
  })

  // 更新智能体
  const updateMutation = useMutation({
    mutationFn: ({ agentId, input }: { agentId: string; input: UpdateAgentInput }) =>
      updateUserAgent(activeUserId, agentId, input),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['cluster-agents'] })
      queryClient.invalidateQueries({ queryKey: ['user-agents'] })
      toast.success(`智能体「${updated.agent_name}」配置已就地生效`)
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '保存配置失败')
    },
  })

  // 软删除下线
  const deleteMutation = useMutation({
    mutationFn: (agentId: string) => deleteUserAgent(activeUserId, agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cluster-agents'] })
      queryClient.invalidateQueries({ queryKey: ['user-agents'] })
      toast.success('智能体已注销 (软删除)')
      setPendingDeleteAgent(null)
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '注销失败')
    },
  })

  // 恢复激活
  const activateMutation = useMutation({
    mutationFn: (agentId: string) => activateUserAgent(activeUserId, agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cluster-agents'] })
      queryClient.invalidateQueries({ queryKey: ['user-agents'] })
      toast.success('智能体已恢复启用')
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '激活失败')
    },
  })

  return {
    activeUserId,
    activateMutation,
    agents,
    createMutation,
    deleteMutation,
    expandedAgentId,
    filteredAgents,
    isFetching,
    isLoading,
    metrics,
    pendingDeleteAgent,
    refetch,
    searchQuery,
    setExpandedAgentId,
    setPendingDeleteAgent,
    setSearchQuery,
    setShowNewAgentCard,
    setTopologyFilter,
    showNewAgentCard,
    topologyFilter,
    updateMutation,
  }
}
