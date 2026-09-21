import { AgentSensorsCard } from './agent-sensors-card'
import { DeepMetricsGrid } from './deep-metrics-grid'
import { RerankLatencyChart } from './rerank-latency-chart'
import { EmbeddingLatencyChart } from './embedding-latency-chart'
import { SlaTrendChart } from './sla-trend-chart'
import { RetrievalAccuracyTrendChart } from './retrieval-accuracy-trend-chart'
import { TokenBreakdownPieChart } from './token-breakdown-pie-chart'
import { ModelMonitoringCard } from './model-monitoring-card'
import { HarnessEngineCard } from './harness-engine-card'
import { SystemResourceChart } from './system-resource-chart'
import { HttpStatusChart } from './http-status-chart'
import type { TimeWindow } from './system-health-banner'

export interface MonitoringAnalyticsSectionProps {
  deepMetrics: any
  isLoading: boolean
  timeWindow: TimeWindow
  modelsStatus?: string
  isModelsHealthy?: boolean
  harnessStatus?: string
  isHarnessHealthy?: boolean
  hostResources?: any
  totalAuditRequests: number
  successRate: number
  codeMap: Record<number, number>
  isHealthy: boolean
  todayTokens?: any
}

export function MonitoringAnalyticsSection({
  deepMetrics,
  isLoading,
  timeWindow,
  modelsStatus = '',
  isModelsHealthy = true,
  harnessStatus = '',
  isHarnessHealthy = true,
  hostResources,
  totalAuditRequests,
  successRate,
  codeMap,
  isHealthy,
  todayTokens,
}: MonitoringAnalyticsSectionProps) {
  return (
    <div className="flex flex-col gap-4">
      {/* 智能体三维效能物理探针 (Token SNR, P@5, 人工介入率) */}
      <AgentSensorsCard />

      {/* 16 张深层监控指标网格 (Deep Metrics Grid) */}
      <DeepMetricsGrid metrics={deepMetrics} isLoading={isLoading} />

      {/* 50/50 对称双分位数图表 — RER 重排延迟分位 + EMB 向量生成延迟分位 */}
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

      {/* 分析大图表 — SLA 趋势 + 召回准确率演进 + Token 构成饼图 */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <SlaTrendChart currentSuccessRate={deepMetrics.httpSuccessRate} window={timeWindow} />
        <RetrievalAccuracyTrendChart
          currentAccuracy={deepMetrics.top1Accuracy}
          currentCosine={deepMetrics.avgCosineScore}
          window={timeWindow}
        />
        <TokenBreakdownPieChart
          tokenDistribution={todayTokens}
          totalTokens={deepMetrics.tokenStats?.total}
        />
      </div>

      {/* AI 模型消耗监控卡片 */}
      <ModelMonitoringCard
        status={modelsStatus}
        isHealthy={isModelsHealthy}
      />

      {/* Harness 技能自演进引擎监控卡片 */}
      <HarnessEngineCard
        status={harnessStatus}
        isHealthy={isHarnessHealthy}
      />

      {/* 系统硬件资源 + HTTP 状态码分布 */}
      <SystemResourceChart
        isLoading={isLoading}
        vectorCount={deepMetrics.vectorCount}
        hostResources={hostResources}
      />
      <HttpStatusChart
        total={totalAuditRequests}
        successRate={successRate}
        codeMap={codeMap}
        isHealthy={isHealthy}
      />
    </div>
  )
}
