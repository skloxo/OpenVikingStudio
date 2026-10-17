import * as React from 'react'
import { useQuery } from '@tanstack/react-query'

import { useAppConnection } from '#/hooks/use-app-connection'
import type { ConnectionDraft, ConnectionRole } from '#/hooks/use-app-connection'
import { getConsoleAudit, getOvResult, ovClient } from '#/lib/ov-client'
import {
  fetchConsoleContextCommits,
  fetchConsoleDashboardSummary,
  fetchConsolePeers,
  fetchConsoleTokenSeries,
} from '../-lib/api'
import { parseObserverStatus } from '../../monitoring/-lib/parse-status'
import { parseObserverMetrics } from '../../monitoring/-lib/parse-metrics'
import { fetchMonitoringOverview } from '../../monitoring/-lib/fetch-overview'
import type { TimeWindow } from '../../monitoring/-components/system-health-banner'

function hashSecret(value: string): string {
  let hash = 0x811c9dc5
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index)
    hash = Math.imul(hash, 0x01000193)
  }
  return (hash >>> 0).toString(36)
}

function getMetricsScopeKey(connection: ConnectionDraft, connectionRole: ConnectionRole) {
  const metricsKey = connection.apiKey || connection.adminApiKey
  return {
    accountId: connection.accountId,
    baseUrl: connection.baseUrl,
    keyHash: metricsKey ? hashSecret(metricsKey) : 'none',
    keySource: connection.apiKey ? 'api' : connection.adminApiKey ? 'admin' : 'none',
    role: connectionRole,
    userId: connection.userId,
  }
}

export function useCockpitQueries() {
  const { connection, connectionRole, isConnectionRoleLoading, identityScopeKey, serverMode } = useAppConnection()
  const [timeWindow, setTimeWindow] = React.useState<TimeWindow>('24h')

  const canQueryMetrics = !isConnectionRoleLoading && connectionRole !== 'unknown'
  const metricsScopeKey = getMetricsScopeKey(connection, connectionRole)

  const monitoringQuery = useQuery({
    enabled: serverMode !== 'offline',
    queryFn: fetchMonitoringOverview,
    queryKey: ['home-monitoring-overview', identityScopeKey, timeWindow],
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    staleTime: 15_000,
  })

  const dashboard = useQuery({
    enabled: canQueryMetrics,
    queryFn: fetchConsoleDashboardSummary,
    queryKey: ['console-dashboard-summary', metricsScopeKey],
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    staleTime: 15_000,
  })

  const tokenSeries = useQuery({
    enabled: canQueryMetrics,
    queryFn: fetchConsoleTokenSeries,
    queryKey: ['console-token-series', 'last-14-days', metricsScopeKey],
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    staleTime: 30_000,
  })

  const contextCommits = useQuery({
    enabled: canQueryMetrics,
    queryFn: fetchConsoleContextCommits,
    queryKey: ['console-context-commits', 'last-365-days', metricsScopeKey],
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    staleTime: 30_000,
  })

  const skillsCountQuery = useQuery({
    queryFn: async () => {
      const result = await getOvResult<{ skills?: unknown[]; total?: number }>(
        ovClient.client.get({
          query: { node_limit: 2000 },
          url: '/api/v1/skills',
        }),
      )
      return result.total ?? (Array.isArray(result.skills) ? result.skills.length : (dashboard.data?.context_counts?.skills ?? 0))
    },
    queryKey: ['skills-count-summary'],
    staleTime: 60_000,
  })

  const peersQuery = useQuery({
    queryFn: fetchConsolePeers,
    queryKey: ['console-peers', metricsScopeKey],
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    staleTime: 15_000,
  })

  const auditQuery = useQuery({
    enabled: serverMode !== 'offline',
    queryFn: async () => {
      const res = await getOvResult<Record<string, unknown>>(
        getConsoleAudit({ query: { page: 1, page_size: 100 } }),
      )
      return res
    },
    queryKey: ['monitoring-audit-summary', identityScopeKey],
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    staleTime: 15_000,
  })

  const gpuQuery = useQuery({
    enabled: serverMode !== 'offline',
    queryFn: async () => {
      try {
        const res = await ovClient.instance.get<{ used_gb: number; total_gb: number; gpu_percent: number }>(
          '/api/v1/system/gpu',
        )
        return res.data
      } catch {
        return null
      }
    },
    queryKey: ['system-gpu-telemetry', identityScopeKey],
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    staleTime: 15_000,
  })

  const hostResourcesQuery = useQuery({
    enabled: serverMode !== 'offline',
    queryFn: async () => {
      try {
        const res = await ovClient.instance.get<{
          status: string
          cpu_percent: number
          memory_percent: number
          memory_used_gb: number
          memory_total_gb: number
        }>('/api/v1/system/resources')
        return res.data
      } catch {
        return null
      }
    },
    queryKey: ['system-host-resources', identityScopeKey],
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    staleTime: 15_000,
  })

  const overview = monitoringQuery.data
  const summary = dashboard.data
  const auditData = auditQuery.data

  let vectorCount = summary?.context_counts?.total ?? 0
  let collectionCount = 1
  const vikingStatus = overview?.components.vikingdb?.status
  if (vikingStatus) {
    const blocks = parseObserverStatus(vikingStatus)
    for (const block of blocks) {
      if (block.kind === 'table') {
        const colIdx = block.headers.findIndex((h) => /vector/i.test(h) || /数量/i.test(h))
        if (colIdx >= 0) {
          const nonTotalRows = block.rows.filter((r) => !/total/i.test(r[0] ?? ''))
          collectionCount = Math.max(1, nonTotalRows.length)
          const parsed = nonTotalRows.reduce((sum, row) => {
            const val = parseInt(row[colIdx]?.replace(/,/g, '') ?? '0', 10) || 0
            return sum + val
          }, 0)
          if (parsed > 0) vectorCount = parsed
        }
      }
    }
  }

  const deepMetrics = React.useMemo(() => {
    return parseObserverMetrics(
      overview,
      auditQuery.data,
      summary,
      overview?.components.models?.status,
      gpuQuery.data,
    )
  }, [overview, auditQuery.data, summary, gpuQuery.data])

  const items = Array.isArray(auditData?.items) ? (auditData.items as Array<{ status_code?: number }>) : []
  const codeMap = React.useMemo(() => {
    const map: Record<number, number> = {}
    for (const item of items) {
      const code = item.status_code ?? 200
      map[code] = (map[code] ?? 0) + 1
    }
    return map
  }, [items])

  const healthyCount = Object.values(overview?.components ?? {}).filter(
    (c) => Boolean(c && c.is_healthy && !c.has_errors),
  ).length
  const totalCount = Object.keys(overview?.components ?? {}).length

  const totalAssets =
    (summary?.context_counts?.files ?? 0) +
    (skillsCountQuery.data ?? summary?.context_counts?.skills ?? 0) +
    (summary?.context_counts?.memories ?? 0)

  return {
    connectionRole,
    isConnectionRoleLoading,
    canQueryMetrics,
    timeWindow,
    setTimeWindow,
    monitoringQuery,
    dashboard,
    tokenSeries,
    contextCommits,
    skillsCountQuery,
    peersQuery,
    auditQuery,
    hostResourcesQuery,
    overview,
    summary,
    vectorCount,
    collectionCount,
    totalAssets,
    deepMetrics,
    codeMap,
    healthyCount,
    totalCount,
    totalAuditRequests: typeof auditData?.total === 'number' ? auditData.total : 0,
    successRate: typeof auditData?.success_rate === 'number' ? auditData.success_rate : 1.0,
  }
}
