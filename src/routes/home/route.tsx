import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'

import { ContextCommitsPanel } from './-components/context-commits-panel'
import {
  ContextDataPanel,
  TodayRetrievalsPanel,
  TodayTokensPanel,
} from './-components/metric-panels'
import { TokenTrendPanel } from './-components/token-trend-panel'
import { KnowledgeBaseOverview } from './-components/knowledge-base-overview'
import {
  fetchConsoleContextCommits,
  fetchConsoleDashboardSummary,
  fetchConsoleTokenSeries,
} from './-lib/api'
import { isDisabledPayload } from './-lib/format'
import { useAppConnection } from '#/hooks/use-app-connection'
import type {
  ConnectionDraft,
  ConnectionRole,
} from '#/hooks/use-app-connection'
import { getObserverSystem, getOvResult } from '#/lib/ov-client'
import { parseObserverStatus } from '../monitoring/-lib/parse-status'

export const Route = createFileRoute('/home')({
  component: HomePage,
})

function hashSecret(value: string): string {
  let hash = 0x811c9dc5
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index)
    hash = Math.imul(hash, 0x01000193)
  }
  return (hash >>> 0).toString(36)
}

function getMetricsScopeKey(
  connection: ConnectionDraft,
  connectionRole: ConnectionRole,
) {
  const metricsKey = connection.apiKey || connection.adminApiKey
  return {
    accountId: connection.accountId,
    baseUrl: connection.baseUrl,
    keyHash: metricsKey ? hashSecret(metricsKey) : 'none',
    keySource: connection.apiKey
      ? 'api'
      : connection.adminApiKey
        ? 'admin'
        : 'none',
    role: connectionRole,
    userId: connection.userId,
  }
}

function HomePage() {
  const { t } = useTranslation('home')
  const { connection, connectionRole, isConnectionRoleLoading, identityScopeKey } =
    useAppConnection()
  const canQueryMetrics =
    !isConnectionRoleLoading && connectionRole !== 'unknown'
  const metricsScopeKey = getMetricsScopeKey(connection, connectionRole)

  const dashboard = useQuery({
    enabled: canQueryMetrics,
    queryFn: fetchConsoleDashboardSummary,
    queryKey: ['console-dashboard-summary', metricsScopeKey],
    refetchInterval: 30_000,
  })

  const observerQuery = useQuery({
    queryFn: () => getOvResult<Record<string, unknown>>(getObserverSystem()),
    queryKey: ['home-observer-system', identityScopeKey],
    refetchInterval: 15_000,
  })

  const tokenSeries = useQuery({
    enabled: canQueryMetrics,
    queryFn: fetchConsoleTokenSeries,
    queryKey: ['console-token-series', 'last-14-days', metricsScopeKey],
    refetchInterval: 60_000,
  })

  const contextCommits = useQuery({
    enabled: canQueryMetrics,
    queryFn: fetchConsoleContextCommits,
    queryKey: ['console-context-commits', 'last-365-days', metricsScopeKey],
    refetchInterval: 60_000,
  })

  const summary = dashboard.data
  const observerData = observerQuery.data

  // 解析真实 VikingDB 向量总数
  let vectorCount = 0
  let collectionCount = 1
  if (observerData && typeof observerData === 'object') {
    const rawComponents = (observerData as { components?: Record<string, { status?: string }> }).components
    const vikingStatus = rawComponents?.vikingdb?.status ?? ''
    const blocks = parseObserverStatus(vikingStatus)
    for (const block of blocks) {
      if (block.kind === 'table') {
        const colIdx = block.headers.findIndex((h) => /vectors/i.test(h) || /数量/i.test(h))
        if (colIdx >= 0) {
          collectionCount = block.rows.length
          vectorCount = block.rows.reduce((sum, row) => {
            const val = parseInt(row[colIdx]?.replace(/,/g, '') ?? '0', 10) || 0
            return sum + val
          }, 0)
        }
      }
    }
  }

  const missingPrivilegedRole =
    !isConnectionRoleLoading && connectionRole === 'unknown'
  const metricsUnavailable = missingPrivilegedRole || isDisabledPayload(summary)
  const unavailableMessage = missingPrivilegedRole
    ? t('usageAccessRequired')
    : t('usageDisabled')
  const isMetricsLoading = isConnectionRoleLoading || dashboard.isLoading
  const isSeriesLoading = isConnectionRoleLoading || tokenSeries.isLoading
  const isCommitsLoading = isConnectionRoleLoading || contextCommits.isLoading

  return (
    <div className="flex flex-col gap-5 pb-8">
      {/* Task v1.1.7: KnowledgeBaseOverview 知识库全景与向量引擎卡片 */}
      <KnowledgeBaseOverview
        memoryCount={summary?.context_counts?.memories ?? 0}
        resourceCount={summary?.context_counts?.files ?? 0}
        skillCount={summary?.context_counts?.skills ?? 0}
        vectorCount={vectorCount}
        collectionCount={collectionCount}
        isLoading={isMetricsLoading || observerQuery.isLoading}
      />

      <div className="grid gap-4 md:grid-cols-3">
        <ContextDataPanel
          data={summary?.context_counts}
          disabled={metricsUnavailable}
          disabledMessage={unavailableMessage}
          isError={dashboard.isError}
          isLoading={isMetricsLoading}
          t={t}
        />
        <TodayTokensPanel
          data={summary?.today_tokens}
          disabled={metricsUnavailable}
          disabledMessage={unavailableMessage}
          isError={dashboard.isError}
          isLoading={isMetricsLoading}
          t={t}
        />
        <TodayRetrievalsPanel
          data={summary?.today_retrievals}
          disabled={metricsUnavailable}
          disabledMessage={unavailableMessage}
          isError={dashboard.isError}
          isLoading={isMetricsLoading}
          t={t}
        />
      </div>

      <TokenTrendPanel
        data={tokenSeries.data}
        disabled={metricsUnavailable}
        disabledMessage={unavailableMessage}
        isError={tokenSeries.isError}
        isLoading={isSeriesLoading}
        t={t}
      />

      <ContextCommitsPanel
        data={contextCommits.data}
        disabled={metricsUnavailable}
        disabledMessage={unavailableMessage}
        isError={contextCommits.isError}
        isLoading={isCommitsLoading}
        t={t}
      />
    </div>
  )
}
