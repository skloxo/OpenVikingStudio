import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import {
  CheckCircle2Icon,
  CircleAlertIcon,
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
import { postContentReindex } from '#/gen/ov-client'
import { cn } from '#/lib/utils'
import { parseObserverStatus } from './-lib/parse-status'
import { parseObserverMetrics } from './-lib/parse-metrics'
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
import { AgentSensorsCard } from './-components/agent-sensors-card'

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
  components: Record<string, ObserverComponent | undefined>
  errors: string[]
  healthy: boolean
  version?: string
}

const MONITOR_TYPES = [
  ['overview', LayoutDashboardIcon],
  ['vikingdb', DatabaseIcon],
  ['filesystem', HardDriveIcon],
  ['lock', LockKeyholeIcon],
  ['retrieval', SearchIcon],
] as const


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

  for (const name of Object.keys(rawComponents)) {
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
  'Prompt': '输入 Token (Prompt)',
  'Completion': '输出 Token (Completion)',
  'Last Updated': '最后更新时间',
  'Metric': '监控指标',
  'Value': '当前数值',
  'Operation': '操作类型',
  'Count': '操作次数',
  'Avg (ms)': '均耗时 (ms)',
  'Min (ms)': '最小耗时 (ms)',
  'Max (ms)': '最大耗时 (ms)',
  'Context Type': '上下文类别',
  'Queries': '检索次数',
}

const CELL_TRANSLATIONS: Record<string, string> = {
  // Status & summaries
  'OK': '正常',
  'ERROR': '异常',
  'TOTAL': '总计',
  'context': '上下文主集合',

  // Operations (Filesystem & Storage)
  'mkdir': '创建目录',
  'read': '读取数据',
  'write': '写入数据',
  'read_dir': '列出目录',
  'stat': '查询状态',
  'rmdir': '删除目录',
  'delete': '删除文件',
  'unlink': '解除链接',
  'rename': '文件重命名',
  'copy': '复制数据',
  'move': '移动路径',
  'open': '打开句柄',
  'close': '关闭句柄',
  'flush': '刷盘同步',
  'lock': '申请互斥锁',
  'unlock': '释放互斥锁',
  'ensure_parent_dir': '确保父级目录',
  'ensure_parent_dirs': '确保父级目录',
  'tree_dir': '遍历目录树',
  'tree_directory': '遍历目录树',
  'ls': '列出清单',
  'cat': '读取文件',
  'rm': '删除路径',
  'mv': '移动路径',
  'grep': '内容匹配',
  'glob_directory': '模式匹配',
  'glob_dir': '模式匹配',
  'copy_within_mount': '卷内复制',
  'system_sync_status': '同步状态检查',
  'system_sync_retry': '同步重试',

  // Metrics (Filesystem & Retrieval)
  'Total Operations': '总操作执行数',
  'Total Time (s)': '总耗时 (秒)',
  'Overall Avg (ms)': '综合均耗时 (ms)',
  'Total Queries': '总检索请求次数',
  'Total Results': '总召回条目数',
  'Avg Results/Query': '单次平均召回数',
  'Zero-Result Queries': '零召回查询数',
  'Zero-Result Rate': '零召回率',
  'Avg Score': '平均语义相似度',
  'Score Range': '相似度区间',
  'Rerank Used': '重排引擎调用数',
  'Rerank Fallback': '重排降级回退数',
  'Avg Latency (ms)': '平均检索延迟 (ms)',
  'Max Latency (ms)': '最大峰值延迟 (ms)',

  // Context Types (Retrieval breakdown)
  'unknown': '未分类类别',
  'resource': '知识资源',
  'memory': '长期记忆',
  'skill': '技能协议',
  'file': '本地文件',
  'web': '网页抓取',
  'code': '代码仓库',
  'session': '会话上下文',
}

function translateHeader(header: string, isZh: boolean): string {
  if (!isZh) return header
  const trimmed = header.trim()
  return HEADER_TRANSLATIONS[trimmed] || HEADER_TRANSLATIONS[trimmed.toLowerCase()] || header
}

function translateCell(cell: string, isZh: boolean): string {
  if (!isZh) return cell
  const trimmed = cell.trim()
  return CELL_TRANSLATIONS[trimmed] || CELL_TRANSLATIONS[trimmed.toLowerCase()] || cell
}

function translateText(text: string, isZh: boolean): string {
  if (!isZh) return text
  const trimmed = text.trim()

  // Unready Directories: 3701
  const unreadyMatch = trimmed.match(/^Unready Directories:\s*(\d+)$/i)
  if (unreadyMatch) {
    return `未就绪目录数: ${unreadyMatch[1]}`
  }

  // Active locks: 0
  const activeLocksMatch = trimmed.match(/^Active locks:\s*(\d+)$/i)
  if (activeLocksMatch) {
    return `活跃互斥锁: ${activeLocksMatch[1]}`
  }

  // Waiting locks: 0
  const waitingLocksMatch = trimmed.match(/^Waiting locks:\s*(\d+)$/i)
  if (waitingLocksMatch) {
    return `等待队列锁: ${waitingLocksMatch[1]}`
  }

  // Stale locks removed: 0
  const staleLocksMatch = trimmed.match(/^Stale locks removed:\s*(\d+)$/i)
  if (staleLocksMatch) {
    return `已清理过期锁: ${staleLocksMatch[1]}`
  }

  // Conflicts: 0
  const conflictsMatch = trimmed.match(/^Conflicts:\s*(\d+)$/i)
  if (conflictsMatch) {
    return `锁冲突次数: ${conflictsMatch[1]}`
  }

  // Mount: /local (plugin: localfs)
  const mountMatch = trimmed.match(/^Mount:\s*([^\s]+)\s*\(plugin:\s*([^)]+)\)$/i)
  if (mountMatch) {
    return `挂载路径: ${mountMatch[1]} (驱动插件: ${mountMatch[2]})`
  }

  if (/^No operation statistics recorded yet\.?$/i.test(trimmed)) {
    return '暂无文件系统操作统计记录。'
  }
  if (/^No filesystem statistics available\.?$/i.test(trimmed)) {
    return '暂无可用文件系统统计数据。'
  }
  if (/^No retrieval queries recorded\.?$/i.test(trimmed)) {
    return '暂无检索查询记录。'
  }
  if (/^No collections found\.?$/i.test(trimmed)) {
    return '暂无可用向量集合。'
  }
  if (/^VikingDB manager not initialized\.?$/i.test(trimmed)) {
    return 'VikingDB 向量数据库管理器尚未初始化。'
  }
  if (/^Not initialized\.?$/i.test(trimmed)) {
    return '服务尚未初始化。'
  }
  if (trimmed.startsWith('Error retrieving filesystem statistics:')) {
    return trimmed.replace(/^Error retrieving filesystem statistics:/i, '获取文件系统统计异常:')
  }

  return text
}

function ObserverStatusContent({ status }: { status: string }) {
  const { i18n, t } = useTranslation('monitoringPage')
  const isZh = i18n.language.startsWith('zh')
  const blocks = React.useMemo(() => parseObserverStatus(status), [status])

  const [isReindexing, setIsReindexing] = React.useState(false)
  const [reindexSuccessMsg, setReindexSuccessMsg] = React.useState<string | null>(null)

  const handleTriggerReindex = async () => {
    setIsReindexing(true)
    setReindexSuccessMsg(null)
    try {
      await postContentReindex({
        body: {
          uri: 'viking://resources',
          mode: 'prune_orphans',
          wait: false,
        },
      })
      setReindexSuccessMsg(t('vikingdb.reindexSuccess'))
    } catch (e) {
      console.error('Failed to trigger reindex:', e)
    } finally {
      setIsReindexing(false)
    }
  }

  if (blocks.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">{t('detail.noData')}</p>
    )
  }

  return (
    <div className="grid gap-3">
      {blocks.map((block, blockIndex) => {
        if (block.kind === 'text') {
          const trimmed = block.value.trim()
          const unreadyMatch = trimmed.match(/^Unready Directories:\s*(\d+)$/i)
          if (unreadyMatch) {
            const count = unreadyMatch[1]
            return (
              <div
                key={`${block.value}-${blockIndex}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-muted/20 px-3 py-2 text-xs font-mono text-muted-foreground"
              >
                <div className="flex items-center gap-2">
                  <span>{isZh ? `未就绪目录数: ${count}` : `Unready Directories: ${count}`}</span>
                  {reindexSuccessMsg && (
                    <span className="text-cyan-500 font-sans text-xs">({reindexSuccessMsg})</span>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-6 px-2.5 text-xs font-sans hover:bg-background"
                  onClick={handleTriggerReindex}
                  disabled={isReindexing}
                >
                  {isReindexing ? t('vikingdb.reindexing') : t('vikingdb.triggerReindex')}
                </Button>
              </div>
            )
          }

          return (
            <p
              key={`${block.value}-${blockIndex}`}
              className="rounded-lg border bg-muted/20 px-3 py-2 text-xs font-mono text-muted-foreground"
            >
              {translateText(block.value, isZh)}
            </p>
          )
        }

        return (
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
                      className="whitespace-nowrap font-medium text-xs"
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
                        {translateCell(cell, isZh)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )
      })}
    </div>
  )
}

function MonitoringRoute() {
  const { i18n, t } = useTranslation('monitoringPage')
  const { identityScopeKey, serverMode } = useAppConnection()
  const [timeWindow, setTimeWindow] = React.useState<'24h' | '7d' | '30d' | 'all'>('24h')
  const monitoringQuery = useQuery({
    enabled: serverMode !== 'offline',
    queryFn: fetchMonitoringOverview,
    queryKey: ['monitoring-overview', identityScopeKey, timeWindow],
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    retry: false,
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

  const dashboardSummaryQuery = useQuery({
    enabled: serverMode !== 'offline',
    queryFn: async () => {
      const res = await getOvResult<Record<string, unknown>>(
        getConsoleDashboardSummary(),
      )
      return res
    },
    queryKey: ['monitoring-dashboard-summary', identityScopeKey],
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
  const auditData = auditQuery.data
  // total 是后端全量审计日志条数（如 5,000）
  const totalAuditRequests = typeof auditData?.total === 'number' ? auditData.total : 0
  const successRate = typeof auditData?.success_rate === 'number' ? auditData.success_rate : 1.0

  const deepMetrics = React.useMemo(() => {
    return parseObserverMetrics(
      overview,
      auditQuery.data,
      dashboardSummaryQuery.data,
      overview?.components.models?.status,
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

  const healthyCount = Object.values(overview?.components ?? {}).filter(
    (component): component is ObserverComponent =>
      Boolean(component && component.is_healthy && !component.has_errors),
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
                  'rounded px-2.5 py-1 text-xs font-medium transition-colors',
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

          {/* Card-Metrics-AgentSensors: 智能体三维效能物理探针 (Token SNR, P@5, 人工介入率) */}
          <AgentSensorsCard />

          {/* Task Card v1.1.15: 1934 官方 16 张深层监控指标卡片 (Deep Metrics Grid) */}
          <DeepMetricsGrid metrics={deepMetrics} isLoading={monitoringQuery.isLoading} />

          {/* Card-VK-17: 50/50 对称双分位数图表 — RER 重排延迟分位 + EMB 向量生成延迟分位 */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <RerankLatencyChart
              totalSamples={deepMetrics.rerankTotalSamples}
              avgLatencyMs={deepMetrics.rerankLatencyMs}
              maxLatencyMs={deepMetrics.rerankMaxLatencyMs}
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


          {/* Task v1.1.5: ModelMonitoringCard AI 模型消耗监控卡片 */}
          <ModelMonitoringCard
            status={overview?.components.models?.status ?? ''}
            isHealthy={overview?.components.models?.is_healthy ?? true}
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

          {/* 原始观测详情 — 4 张组件卡片平铺展示（VikingDB / 文件系统 / 锁 / 检索） */}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {MONITOR_TYPES.slice(1).map(([name, Icon]) => {
              const component = overview?.components[name]
              const healthy = component?.is_healthy === true && !component.has_errors
              return (
                <Card key={name} className="gap-0 overflow-hidden py-0">
                  <CardHeader className="border-b px-5 py-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <Icon className="size-5 text-muted-foreground" />
                        <div>
                          <CardTitle>{t(`tabs.${name}`)}</CardTitle>
                          <p className="mt-1 text-sm text-muted-foreground">
                            {t(`detail.descriptions.${name}`)}
                          </p>
                        </div>
                      </div>
                      <HealthBadge
                        healthy={healthy}
                        label={healthy ? t('health.healthy') : t('health.unhealthy')}
                      />
                    </div>
                  </CardHeader>
                  <CardContent className="px-5 py-5">
                    <ObserverStatusContent status={component?.status ?? ''} />
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
