import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { ActivityIcon, BarChart3Icon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { EmptyLogsState } from './-components/empty-logs-state'
import { EndpointFrequencyCockpit } from './-components/endpoint-frequency-cockpit'
import { MetricCard } from './-components/metric-card'
import { RequestLogPanel } from './-components/panel'
import { HarnessGuardrailsCockpit } from './-components/harness-guardrails-cockpit'
import { GatekeeperAuditStream } from '#/routes/retrieval/-components/gatekeeper-audit-stream'
import { DEFAULT_FILTERS, DEFAULT_PAGE_SIZE } from './-constants/audit'
import { fetchAuditLogs, fetchEndpointFrequency, isZeroResultCombination } from './-lib/api'
import { formatPercent } from './-lib/format'
import type { AuditFilters, EndpointFrequencyWindow, LogTypeFilter } from './-types/audit'
import { useAppConnection } from '#/hooks/use-app-connection'

export type RequestLogsTab = 'requests' | 'memory' | 'harness'

interface RequestLogsSearch {
  tab?: RequestLogsTab
}

export const Route = createFileRoute('/request-logs')({
  validateSearch: (search: Record<string, unknown>): RequestLogsSearch => ({
    tab: ['requests', 'memory', 'harness'].includes(String(search.tab))
      ? (search.tab as RequestLogsTab)
      : undefined,
  }),
  component: RequestLogsRoute,
})

function hashSecret(value: string): string {
  let hash = 0x811c9dc5
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index)
    hash = Math.imul(hash, 0x01000193)
  }
  return (hash >>> 0).toString(36)
}

function RequestLogsRoute() {
  const { t } = useTranslation('requestLogs')
  const { connection, connectionRole, isConnectionRoleLoading } =
    useAppConnection()
  const searchParams = Route.useSearch()
  const [activeTab, setActiveTab] =
    React.useState<RequestLogsTab>(searchParams.tab || 'requests')

  React.useEffect(() => {
    if (searchParams.tab && ['requests', 'memory', 'harness'].includes(searchParams.tab)) {
      setActiveTab(searchParams.tab)
    }
  }, [searchParams.tab])

  const [draftFilters, setDraftFilters] =
    React.useState<AuditFilters>(DEFAULT_FILTERS)
  const [filters, setFilters] = React.useState<AuditFilters>(DEFAULT_FILTERS)
  const [page, setPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(DEFAULT_PAGE_SIZE)
  const [viewMode, setViewMode] =
    React.useState<'frequency' | 'stream'>('frequency')
  const [freqWindow, setFreqWindow] =
    React.useState<EndpointFrequencyWindow>('all')

  const zeroResult = isZeroResultCombination(filters)
  const canQueryAudit = !isConnectionRoleLoading && connectionRole !== 'unknown'
  const auditScopeKey = {
    accountId: connection.accountId,
    baseUrl: connection.baseUrl,
    keyHash: hashSecret(connection.adminApiKey || connection.apiKey),
    role: connectionRole,
    userId: connection.userId,
  }

  const frequency = useQuery({
    enabled: canQueryAudit && activeTab === 'requests',
    queryFn: () => fetchEndpointFrequency(freqWindow),
    queryKey: ['console-endpoint-frequency', auditScopeKey, freqWindow],
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    staleTime: 15_000,
  })

  const audit = useQuery({
    enabled: canQueryAudit && !zeroResult && activeTab === 'requests',
    queryFn: () => fetchAuditLogs(filters, page, pageSize),
    queryKey: ['console-audit-logs', auditScopeKey, filters, page, pageSize],
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    staleTime: 15_000,
  })


  const logs = zeroResult ? [] : (audit.data?.items ?? [])
  const disabled = audit.data?.enabled === false
  const total = zeroResult ? 0 : (audit.data?.total ?? 0)
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  const identityParts = [connection.accountId, connection.userId].filter(
    Boolean,
  )
  const scopeLabel =
    identityParts.length > 0
      ? t('scope.currentIdentityWithName', {
          identity: identityParts.join(' / '),
        })
      : t('scope.currentIdentity')

  const handleSearch = () => {
    setFilters({ ...draftFilters })
    setPage(1)
  }

  const handleReset = () => {
    setDraftFilters(DEFAULT_FILTERS)
    setFilters(DEFAULT_FILTERS)
    setPage(1)
  }

  const handleLogTypeChange = (logType: LogTypeFilter) => {
    const nextFilters = { ...draftFilters, logType }
    setDraftFilters(nextFilters)
    setFilters(nextFilters)
    setPage(1)
  }

  const handleRefresh = () => {
    if (zeroResult) return
    void audit.refetch()
  }

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize)
    setPage(1)
  }

  return (
    <div className="flex w-full min-w-0 flex-col gap-4">
      {/* 顶层三大审计总账 Tab */}
      <div className="flex items-center gap-1.5 border-b border-border/60 pb-1">
        {[
          { id: 'requests', label: '🌐 API 请求与端点审计', icon: <ActivityIcon className="size-3.5 mr-1 text-cyan-400" /> },
          { id: 'memory', label: '🧠 记忆治理审计总账', icon: <BarChart3Icon className="size-3.5 mr-1 text-cyan-400" /> },
          { id: 'harness', label: '🛡️ Agent 门禁与安全装甲', icon: <ActivityIcon className="size-3.5 mr-1 text-cyan-400" /> },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id as RequestLogsTab)}
            className={`flex items-center rounded-t-md px-3.5 py-1.5 text-xs font-medium transition-all cursor-pointer ${
              activeTab === tab.id
                ? 'border-b-2 border-cyan-400 bg-card text-foreground font-semibold'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'memory' && (
        <div className="pt-1">
          <GatekeeperAuditStream />
        </div>
      )}

      {activeTab === 'harness' && (
        <div className="pt-1">
          <HarnessGuardrailsCockpit />
        </div>
      )}

      {activeTab === 'requests' && (
        <div className="flex flex-col gap-4">
          <div className="rounded-md border border-border/70 bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
            {scopeLabel}
          </div>

          <div className="flex border-b border-border/60">
            <button
              type="button"
              onClick={() => setViewMode('frequency')}
              className={`border-b-2 px-4 py-2 text-xs font-medium transition-colors cursor-pointer ${
                viewMode === 'frequency'
                  ? 'border-cyan-500 text-cyan-500 font-semibold'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {t('viewMode.frequency')}
            </button>
            <button
              type="button"
              onClick={() => setViewMode('stream')}
              className={`border-b-2 px-4 py-2 text-xs font-medium transition-colors cursor-pointer ${
                viewMode === 'stream'
                  ? 'border-cyan-500 text-cyan-500 font-semibold'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {t('viewMode.stream')}
            </button>
          </div>

          {!canQueryAudit ? (
            <EmptyLogsState
              title={t('accessRequired.title')}
              description={t('accessRequired.description')}
            />
          ) : viewMode === 'frequency' ? (
            <EndpointFrequencyCockpit
              data={frequency.data}
              isLoading={isConnectionRoleLoading || frequency.isLoading}
              isFetching={frequency.isFetching}
              window={freqWindow}
              onWindowChange={setFreqWindow}
              onRefresh={() => void frequency.refetch()}
            />
          ) : (
            <>
              <div className="grid gap-3 md:grid-cols-2">
                <MetricCard
                  icon={<ActivityIcon className="size-4" />}
                  label={t('metrics.total')}
                  value={total}
                />
                <MetricCard
                  icon={<BarChart3Icon className="size-4" />}
                  label={t('metrics.errorRate')}
                  value={
                    audit.data?.success_rate !== undefined
                      ? formatPercent(1 - audit.data.success_rate)
                      : '--'
                  }
                />
              </div>

              <RequestLogPanel
                draftFilters={draftFilters}
                filters={filters}
                logs={logs}
                disabled={disabled}
                disabledMessage={audit.data?.message}
                isLoading={isConnectionRoleLoading || audit.isLoading}
                isFetching={audit.isFetching}
                isError={audit.isError}
                page={page}
                pageCount={pageCount}
                pageSize={pageSize}
                total={total}
                zeroResult={zeroResult}
                onDraftFiltersChange={setDraftFilters}
                onLogTypeChange={handleLogTypeChange}
                onPageChange={setPage}
                onPageSizeChange={handlePageSizeChange}
                onRefresh={handleRefresh}
                onReset={handleReset}
                onSearch={handleSearch}
              />
            </>
          )}
        </div>
      )}
    </div>
  )
}
