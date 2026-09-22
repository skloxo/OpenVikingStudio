import { useTranslation } from 'react-i18next'
import { createFileRoute } from '@tanstack/react-router'

import { SystemHealthBanner } from '../monitoring/-components/system-health-banner'
import { KnowledgeBaseOverview } from './-components/knowledge-base-overview'
import { PeerMemoryGrid } from './-components/peer-memory-grid'
import {
  ContextDataPanel,
  TodayRetrievalsPanel,
  TodayTokensPanel,
} from './-components/metric-panels'
import { TokenTrendPanel } from './-components/token-trend-panel'
import { ContextCommitsPanel } from './-components/context-commits-panel'
import { MonitoringAnalyticsSection } from '../monitoring/-components/monitoring-analytics-section'
import { ObserverComponentsSection } from '../monitoring/-components/observer-components-section'
import { Tier2CacheCard } from '../monitoring/-components/tier2-cache-card'
import { isDisabledPayload } from './-lib/format'
import { useCockpitQueries } from './-hooks/use-cockpit-queries'

export const Route = createFileRoute('/home')({
  component: HomePage,
})

function HomePage() {
  const { i18n, t } = useTranslation('home')
  const q = useCockpitQueries()

  const missingPrivilegedRole = !q.isConnectionRoleLoading && q.connectionRole === 'unknown'
  const metricsUnavailable = missingPrivilegedRole || isDisabledPayload(q.summary)
  const unavailableMessage = missingPrivilegedRole ? t('usageAccessRequired') : t('usageDisabled')

  const isMetricsLoading = q.isConnectionRoleLoading || q.dashboard.isLoading
  const isSeriesLoading = q.isConnectionRoleLoading || q.tokenSeries.isLoading
  const isCommitsLoading = q.isConnectionRoleLoading || q.contextCommits.isLoading

  const updatedAt = q.monitoringQuery.dataUpdatedAt
    ? new Intl.DateTimeFormat(i18n.resolvedLanguage, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }).format(q.monitoringQuery.dataUpdatedAt)
    : undefined

  const totalAssets =
    (q.summary?.context_counts?.files ?? 0) +
    (q.skillsCountQuery.data ?? q.summary?.context_counts?.skills ?? 0) +
    (q.summary?.context_counts?.memories ?? 0)

  return (
    <div className="flex flex-col gap-5 pb-10">
      {/* 1. 顶层全局健康度与态势控制 Bar */}
      <SystemHealthBanner
        healthy={q.overview?.healthy}
        healthyCount={q.healthyCount}
        totalCount={q.totalCount}
        version={q.overview?.version}
        timeWindow={q.timeWindow}
        onTimeWindowChange={q.setTimeWindow}
        isFetching={q.monitoringQuery.isFetching}
        onRefresh={() => {
          void q.monitoringQuery.refetch()
          void q.dashboard.refetch()
          void q.auditQuery.refetch()
        }}
        updatedAt={updatedAt}
      />

      {/* 2. VikingDB 向量引擎与核心资产全景 */}
      <KnowledgeBaseOverview
        vectorCount={q.vectorCount}
        collectionCount={q.collectionCount}
        totalAssets={totalAssets}
        isLoading={isMetricsLoading || q.monitoringQuery.isLoading}
      />

      {/* 3. 多节点协同智能体网络 (PeerMemoryGrid) */}
      <PeerMemoryGrid
        isLoading={isMetricsLoading || q.monitoringQuery.isLoading || q.peersQuery.isLoading}
        peerList={q.peersQuery.data}
      />

      {/* 4. 业务效能三维关键面板 */}
      <div className="grid gap-4 md:grid-cols-3">
        <ContextDataPanel
          data={
            q.summary?.context_counts
              ? {
                  ...q.summary.context_counts,
                  skills: q.skillsCountQuery.data ?? q.summary.context_counts.skills,
                  total: totalAssets,
                }
              : q.summary?.context_counts
          }
          disabled={metricsUnavailable}
          disabledMessage={unavailableMessage}
          isError={q.dashboard.isError}
          isLoading={isMetricsLoading}
          t={t}
        />
        <TodayTokensPanel
          data={q.summary?.today_tokens}
          disabled={metricsUnavailable}
          disabledMessage={unavailableMessage}
          isError={q.dashboard.isError}
          isLoading={isMetricsLoading}
          t={t}
        />
        <TodayRetrievalsPanel
          data={q.summary?.today_retrievals}
          disabled={metricsUnavailable}
          disabledMessage={unavailableMessage}
          isError={q.dashboard.isError}
          isLoading={isMetricsLoading}
          t={t}
        />
      </div>

      {/* 5. 14 天 Token 消耗走势 */}
      <TokenTrendPanel
        data={q.tokenSeries.data}
        disabled={metricsUnavailable}
        disabledMessage={unavailableMessage}
        isError={q.tokenSeries.isError}
        isLoading={isSeriesLoading}
        t={t}
      />

      {/* 6. 365 天记忆提交热力图 */}
      <ContextCommitsPanel
        data={q.contextCommits.data}
        disabled={metricsUnavailable}
        disabledMessage={unavailableMessage}
        isError={q.contextCommits.isError}
        isLoading={isCommitsLoading}
        t={t}
      />

      {/* 7. 深入观测分析大盘（探针、16张深层指标、延迟双分位、SLA趋势、模型消耗与硬件资源） */}
      <MonitoringAnalyticsSection
        deepMetrics={q.deepMetrics}
        isLoading={q.monitoringQuery.isLoading}
        timeWindow={q.timeWindow}
        modelsStatus={q.overview?.components.models?.status}
        isModelsHealthy={q.overview?.components.models?.is_healthy}
        harnessStatus={q.overview?.components.harness?.status}
        isHarnessHealthy={q.overview?.healthy}
        hostResources={q.hostResourcesQuery.data}
        totalAuditRequests={q.totalAuditRequests}
        successRate={q.successRate}
        codeMap={q.codeMap}
        isHealthy={q.overview?.healthy ?? true}
        todayTokens={q.summary?.today_tokens}
      />

      {/* 8. 高并发 LRU 本地二级缓存 (Tier-2 FastHit) 观测与压测 */}
      <Tier2CacheCard />

      {/* 9. 底层 4 大组件运行详情（VikingDB / 文件系统 / 锁 / 检索） */}
      <ObserverComponentsSection components={q.overview?.components} />
    </div>
  )
}
