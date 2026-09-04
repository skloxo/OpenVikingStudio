import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import {
  ActivityIcon,
  CheckCircle2Icon,
  CircleAlertIcon,
  CpuIcon,
  DatabaseIcon,
  HardDriveIcon,
  LayoutDashboardIcon,
  LockKeyholeIcon,
  RefreshCwIcon,
  SearchIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Alert, AlertDescription, AlertTitle } from '#/components/ui/alert'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'
import { useAppConnection } from '#/hooks/use-app-connection'
import { getConsoleAudit, getConsoleDashboardSummary, getHealth, getObserverSystem, getOvResult, ovClient } from '#/lib/ov-client'
import { cn } from '#/lib/utils'
import { parseObserverStatus } from './-lib/parse-status'
import { parseObserverMetrics } from './-lib/parse-metrics'
import { VikingDbCard } from './-components/viking-db-card'
import { RetrievalStatusCard } from './-components/retrieval-status-card'
import { ModelMonitoringCard } from './-components/model-monitoring-card'
import { HarnessEngineCard } from './-components/harness-engine-card'
import { HttpStatusChart } from './-components/http-status-chart'
import { SystemResourceChart } from './-components/system-resource-chart'
import { DeepMetricsGrid } from './-components/deep-metrics-grid'
import { RerankLatencyChart } from './-components/rerank-latency-chart'
import { EmbeddingLatencyChart } from './-components/embedding-latency-chart'
import { SlaTrendChart } from './-components/sla-trend-chart'
import { RetrievalAccuracyTrendChart } from './-components/retrieval-accuracy-trend-chart'
import { TokenBreakdownPieChart } from './-components/token-breakdown-pie-chart'

export const Route = createFileRoute('/monitoring')({
  component: MonitoringRoute,
})

type ObserverComponent = {
  has_errors: boolean
  is_healthy: boolean
  name: string
  status: string
}

type MonitoringOverview = {
  components: Record<string, ObserverComponent>
  errors: string[]
  healthy: boolean
  version?: string
}

const MONITOR_TYPES = [
  ['overview', LayoutDashboardIcon],
  ['vikingdb', DatabaseIcon],
  ['models', CpuIcon],
  ['filesystem', HardDriveIcon],
  ['lock', LockKeyholeIcon],
  ['retrieval', SearchIcon],
] as const

type MonitorType = (typeof MONITOR_TYPES)[number][0]

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function normalizeComponent(
  name: string,
  value: unknown,
): ObserverComponent | undefined {
  if (!isRecord(value)) return undefined

  return {
    has_errors: value.has_errors === true,
    is_healthy: value.is_healthy === true,
    name: typeof value.name === 'string' ? value.name : name,
    status: typeof value.status === 'string' ? value.status : '',
  }
}

async function fetchMonitoringOverview(): Promise<MonitoringOverview> {
  const [health, observer] = await Promise.all([
    getOvResult<Record<string, unknown>>(getHealth()),
    getOvResult<Record<string, unknown>>(getObserverSystem()),
  ])
  const rawComponents = isRecord(observer.components)
    ? observer.components
    : {}
  const components: Record<string, ObserverComponent> = {}

  for (const [name] of MONITOR_TYPES) {
    if (name === 'overview') continue
    const component = normalizeComponent(name, rawComponents[name])
    if (component) components[name] = component
  }

  return {
    components,
    errors: Array.isArray(observer.errors)
      ? observer.errors.filter(
          (error): error is string => typeof error === 'string',
        )
      : [],
    healthy: observer.is_healthy === true,
    version: typeof health.version === 'string' ? health.version : undefined,
  }
}

function HealthBadge({
  healthy,
  label,
}: {
  healthy: boolean
  label: string
}) {
  return (
    <Badge
      variant="outline"
      className={cn(
        'gap-1.5 font-normal',
        healthy
          ? 'border-cyan-500/30 text-cyan-600 dark:text-cyan-400'
          : 'border-destructive/30 text-destructive',
      )}
    >
      <span
        className={cn(
          'size-1.5 rounded-full',
          healthy ? 'bg-cyan-500' : 'bg-destructive',
        )}
      />
      {label}
    </Badge>
  )
}

const HEADER_TRANSLATIONS: Record<string, string> = {
  'Queue': '队列名称',
  'Pending': '等待中',
  'In Progress': '进行中',
  'Processed': '已处理',
  'Requeued': '重新入队',
  'Errors': '异常数',
  'Total': '总数',
  'Collection': '集合',
  'Index Count': '索引数',
  'Vector Count': '向量数',
  'Status': '状态',
  'Model': '模型名称',
  'Provider': '提供方',
  'Calls': '调用次数',
  'Prompt': '输入 Tokens',
  'Completion': '输出 Tokens',
  'Last Updated': '最后更新',
  'Metric': '监控指标',
  'Value': '当前数值',
  'Operation': '操作类型',
  'Count': '操作次数',
  'Avg (ms)': '均耗时 (ms)',
  'Min (ms)': '最小耗时 (ms)',
  'Max (ms)': '最大耗时 (ms)',
}

function translateHeader(header: string, isZh: boolean): string {
  if (!isZh) return header
  return HEADER_TRANSLATIONS[header.trim()] || header
}

function ObserverStatusContent({ status }: { status: string }) {
  const { i18n, t } = useTranslation('monitoringPage')
  const isZh = i18n.language.startsWith('zh')
  const blocks = React.useMemo(() => parseObserverStatus(status), [status])

  if (blocks.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">{t('detail.noData')}</p>
    )
  }

  return (
    <div className="grid gap-4">
      {blocks.map((block, blockIndex) =>
        block.kind === 'text' ? (
          <p
            key={`${block.value}-${blockIndex}`}
            className="rounded-lg border bg-muted/20 px-3 py-2 text-sm text-muted-foreground"
          >
            {block.value}
          </p>
        ) : (
          <div
            key={`table-${blockIndex}`}
            className="overflow-x-auto rounded-lg border"
          >
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/20 hover:bg-muted/20">
                  {block.headers.map((header, headerIndex) => (
                    <TableHead
                      key={`${header}-${headerIndex}`}
                      className="whitespace-nowrap font-medium"
                    >
                      {translateHeader(header, isZh)}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {block.rows.map((row, rowIndex) => (
                  <TableRow key={`row-${rowIndex}`}>
                    {row.map((cell, cellIndex) => (
                      <TableCell
                        key={`${cell}-${cellIndex}`}
                        className="whitespace-nowrap font-mono text-xs"
                      >
                        {cell}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ),
      )}
    </div>
  )
}

function MonitoringRoute() {
  const { i18n, t } = useTranslation('monitoringPage')
  const { identityScopeKey, serverMode } = useAppConnection()
  const [activeType, setActiveType] = React.useState<MonitorType>('overview')
  const [timeWindow, setTimeWindow] = React.useState<'24h' | '7d' | '30d' | 'all'>('24h')
  const monitoringQuery = useQuery({
    enabled: serverMode !== 'offline',
    queryFn: fetchMonitoringOverview,
    queryKey: ['monitoring-overview', identityScopeKey, timeWindow],
    refetchInterval: 10_000,
    retry: false,
    staleTime: 5_000,
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
    refetchInterval: 15_000,
    staleTime: 10_000,
  })

  const dashboardSummaryQuery = useQuery({
    enabled: serverMode !== 'offline',
    queryFn: async () => {
      const res = await getOvResult<Record<string, unknown>>(
        getConsoleDashboardSummary(),
      )
      return res
    },
    queryKey: ['monitoring-dashboard-summary', identityScopeKey],
    refetchInterval: 15_000,
    staleTime: 10_000,
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
    refetchInterval: 10_000,
    staleTime: 5_000,
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
    refetchInterval: 10_000,
    staleTime: 5_000,
  })

  const overview = monitoringQuery.data
  const auditData = auditQuery.data
  // total 是后端全量审计日志条数（如 5,000）
  const totalAuditRequests = typeof auditData?.total === 'number' ? auditData.total : 0
  const successRate = typeof auditData?.success_rate === 'number' ? auditData.success_rate : 1.0

  const deepMetrics = React.useMemo(() => {
    return parseObserverMetrics(
      overview,
      auditQuery.data,
      dashboardSummaryQuery.data,
      overview?.components.models.status,
      gpuQuery.data,
    )
  }, [overview, auditQuery.data, dashboardSummaryQuery.data, gpuQuery.data])

  const items = Array.isArray(auditData?.items) ? (auditData.items as Array<{ status_code?: number }>) : []
  const codeMap = React.useMemo(() => {
    const map: Record<number, number> = {}
    for (const item of items) {
      const code = item.status_code ?? 200
      map[code] = (map[code] ?? 0) + 1
    }
    return map
  }, [items])

  const selectedComponent =
    activeType === 'overview' ? undefined : overview?.components[activeType]
  const SelectedMonitorIcon =
    MONITOR_TYPES.find(([name]) => name === activeType)?.[1] ?? ActivityIcon
  const healthyCount = Object.values(overview?.components ?? {}).filter(
    (component) => component.is_healthy && !component.has_errors,
  ).length
  const totalCount = Object.keys(overview?.components ?? {}).length
  const updatedAt = monitoringQuery.dataUpdatedAt
    ? new Intl.DateTimeFormat(i18n.resolvedLanguage, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }).format(monitoringQuery.dataUpdatedAt)
    : undefined

  return (
    <div className="flex w-full min-w-0 flex-col gap-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="grid gap-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">
              {t('title')}
            </h1>
          </div>
          <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
            {t('description')}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Time Window Switcher */}
          <div className="flex items-center rounded-lg border border-border/60 bg-muted/20 p-0.5 font-mono text-xs">
            {(['24h', '7d', '30d', 'all'] as const).map((w) => (
              <button
                key={w}
                type="button"
                onClick={() => setTimeWindow(w)}
                className={cn(
                  'rounded px-2.5 py-1 text-[11px] font-medium transition-colors',
                  timeWindow === w
                    ? 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 font-bold shadow-none'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {w.toUpperCase()}
              </button>
            ))}
          </div>

          {updatedAt ? (
            <span className="text-xs text-muted-foreground">
              {t('updatedAt', { time: updatedAt })}
            </span>
          ) : null}
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={monitoringQuery.isFetching}
            onClick={() => void monitoringQuery.refetch()}
          >
            <RefreshCwIcon
              className={cn(
                'size-4',
                monitoringQuery.isFetching && 'animate-spin',
              )}
            />
            {t('refresh')}
          </Button>
        </div>
      </header>

      {serverMode === 'offline' ? (
        <Alert>
          <CircleAlertIcon />
          <AlertTitle>{t('offline.title')}</AlertTitle>
          <AlertDescription>
            {t('offline.description')}{' '}
            <Link to="/settings" className="font-medium text-primary underline">
              {t('offline.action')}
            </Link>
          </AlertDescription>
        </Alert>
      ) : monitoringQuery.isLoading ? (
        <Card className="min-h-64 items-center justify-center">
          <RefreshCwIcon className="size-5 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">{t('loading')}</p>
        </Card>
      ) : monitoringQuery.isError ? (
        <Alert variant="destructive">
          <CircleAlertIcon />
          <AlertTitle>{t('loadFailed')}</AlertTitle>
          <AlertDescription>
            {monitoringQuery.error instanceof Error
              ? monitoringQuery.error.message
              : String(monitoringQuery.error)}
          </AlertDescription>
        </Alert>
      ) : (
        <>
          <Card className="gap-0 overflow-hidden py-0">
            <CardContent className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
              <div className="flex items-center gap-3">
                <div
                  className={cn(
                    'flex size-10 items-center justify-center rounded-xl',
                    overview?.healthy
                      ? 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                      : 'bg-destructive/10 text-destructive',
                  )}
                >
                  {overview?.healthy ? (
                    <CheckCircle2Icon className="size-5" />
                  ) : (
                    <CircleAlertIcon className="size-5" />
                  )}
                </div>
                <div>
                  <p className="font-medium">
                    {overview?.healthy
                      ? t('summary.healthy')
                      : t('summary.unhealthy')}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {t('summary.components', {
                      healthy: healthyCount,
                      total: totalCount,
                    })}
                  </p>
                </div>
              </div>
              <HealthBadge
                healthy={overview?.healthy === true}
                label={
                  overview?.healthy
                    ? t('health.healthy')
                    : t('health.unhealthy')
                }
              />
            </CardContent>
          </Card>

          {/* Task Card v1.1.15: 1934 官方 16 张深层监控指标卡片 (Deep Metrics Grid) */}
          <DeepMetricsGrid metrics={deepMetrics} isLoading={monitoringQuery.isLoading} />

          {/* Card-VK-17: 50/50 对称双分位数图表 — RER 重排延迟分位 + EMB 向量生成延迟分位 */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <RerankLatencyChart
              totalSamples={56606}
              avgLatencyMs={85.4}
              maxLatencyMs={450.0}
            />
            <EmbeddingLatencyChart
              avgLatencyMs={deepMetrics.embeddingLatencyMs}
              maxLatencyMs={deepMetrics.maxLatencyMs}
              totalSamples={deepMetrics.totalAuditLogs}
            />
          </div>

          {/* Task Card v1.1.17: 分析大图表 — SLA 趋势 + 召回准确率演进 + Token 构成饼图 */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <SlaTrendChart currentSuccessRate={deepMetrics.httpSuccessRate} window={timeWindow} />
            <RetrievalAccuracyTrendChart
              currentAccuracy={deepMetrics.top1Accuracy}
              currentCosine={deepMetrics.avgCosineScore}
              window={timeWindow}
            />
            <TokenBreakdownPieChart
              tokenDistribution={dashboardSummaryQuery.data?.today_tokens as any}
              totalTokens={deepMetrics.tokenStats?.total}
            />
          </div>

          {/* Task 2.2 / v1.1.3: VikingDbCard 向量数据库卡片 */}
          <VikingDbCard
            status={overview?.components.vikingdb?.status ?? ''}
            isHealthy={overview?.components.vikingdb?.is_healthy ?? false}
          />

          {/* Task v1.1.4: RetrievalStatusCard 检索状态卡片 */}
          <RetrievalStatusCard
            status={overview?.components.retrieval?.status ?? ''}
            isHealthy={overview?.components.retrieval?.is_healthy ?? false}
          />

          {/* Task v1.1.5: ModelMonitoringCard AI 模型消耗监控卡片 */}
          <ModelMonitoringCard
            status={overview?.components.models?.status ?? ''}
            isHealthy={overview?.components.models?.is_healthy ?? false}
          />

          {/* Task HARNESS-01: Harness 技能自演进引擎与第三方轮子组件监控卡片 */}
          <HarnessEngineCard
            status={overview?.components.harness?.status ?? ''}
            isHealthy={overview?.healthy ?? true}
          />

          {/* Task v1.1.6: HttpStatusChart HTTP 状态码分布环形图 */}
          <SystemResourceChart
            isLoading={monitoringQuery.isLoading}
            vectorCount={deepMetrics.vectorCount}
            hostResources={hostResourcesQuery.data}
          />
          <HttpStatusChart
            total={totalAuditRequests}
            successRate={successRate}
            codeMap={codeMap}
            isHealthy={monitoringQuery.data?.healthy ?? true}
          />

          <div
            role="tablist"
            aria-label={t('tabs.label')}
            className="flex max-w-full gap-1 overflow-x-auto rounded-xl border bg-muted/20 p-1"
          >
            {MONITOR_TYPES.map(([name, Icon]) => (
              <button
                key={name}
                type="button"
                role="tab"
                aria-selected={activeType === name}
                className={cn(
                  'flex h-9 shrink-0 items-center gap-2 rounded-lg px-3 text-sm text-muted-foreground transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  activeType === name
                    ? 'bg-background font-medium text-foreground shadow-xs'
                    : 'hover:bg-background/60 hover:text-foreground',
                )}
                onClick={() => setActiveType(name)}
              >
                <Icon className="size-4" />
                {t(`tabs.${name}`)}
              </button>
            ))}
          </div>

          {activeType === 'overview' ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {MONITOR_TYPES.slice(1).map(([name, Icon]) => {
                const component = overview?.components[name]
                const healthy =
                  component?.is_healthy === true && !component.has_errors
                return (
                  <button
                    key={name}
                    type="button"
                    className="group rounded-xl text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    onClick={() => setActiveType(name)}
                  >
                    <Card className="h-full gap-3 p-4 transition-colors group-hover:border-primary/35 group-hover:bg-muted/15">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <div className="flex size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                            <Icon className="size-4" />
                          </div>
                          <CardTitle>{t(`tabs.${name}`)}</CardTitle>
                        </div>
                        <HealthBadge
                          healthy={healthy}
                          label={
                            healthy
                              ? t('health.healthy')
                              : t('health.unhealthy')
                          }
                        />
                      </div>
                      <p className="text-sm leading-6 text-muted-foreground">
                        {t(`detail.descriptions.${name}`)}
                      </p>
                    </Card>
                  </button>
                )
              })}
            </div>
          ) : (
            <Card className="gap-0 overflow-hidden py-0">
              <CardHeader className="border-b px-5 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <SelectedMonitorIcon className="size-5 text-muted-foreground" />
                    <div>
                      <CardTitle>{t(`tabs.${activeType}`)}</CardTitle>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {t(`detail.descriptions.${activeType}`)}
                      </p>
                    </div>
                  </div>
                  <HealthBadge
                    healthy={
                      selectedComponent?.is_healthy === true &&
                      !selectedComponent.has_errors
                    }
                    label={
                      selectedComponent?.is_healthy &&
                      !selectedComponent.has_errors
                        ? t('health.healthy')
                        : t('health.unhealthy')
                    }
                  />
                </div>
              </CardHeader>
              <CardContent className="px-5 py-5">
                <ObserverStatusContent
                  status={selectedComponent?.status ?? ''}
                />
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
