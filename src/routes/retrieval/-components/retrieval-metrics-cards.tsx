import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Card } from '#/components/ui/card'
import { ShieldCheckIcon, ZapIcon, TargetIcon, SparklesIcon } from 'lucide-react'
import { ovClient } from '#/lib/ov-client'

export interface RetrievalMetricsCardsProps {
  compositeScore?: number
  avgLatencyMs?: number
  hitRate?: number
  contextPrecision?: number
  onOpenBenchmark?: () => void
}

interface RAGMetricsResponse {
  total_verifications: number
  total_abstained: number
  abstention_rate: number
  avg_confidence: number
  avg_latency_ms: number
}

export function RetrievalMetricsCards({
  compositeScore: propComposite,
  avgLatencyMs: propLatency,
  hitRate: propHitRate,
  contextPrecision: propPrecision,
  onOpenBenchmark,
}: RetrievalMetricsCardsProps) {
  const { t } = useTranslation('retrieval')

  const { data: ragMetrics } = useQuery<RAGMetricsResponse>({
    queryKey: ['retrieval-rag-metrics-overview'],
    queryFn: async () => {
      const res = await ovClient.instance.get<RAGMetricsResponse>('/api/v1/rag/metrics')
      return res.data
    },
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
    staleTime: 10_000,
  })

  const hasTelemetry = (ragMetrics?.total_verifications ?? 0) > 0
  const totalVerifications = ragMetrics?.total_verifications ?? 0

  const resolvedLatency = propLatency ?? (hasTelemetry ? ragMetrics?.avg_latency_ms : undefined)
  const resolvedPrecision = propPrecision ?? (hasTelemetry ? ragMetrics?.avg_confidence : undefined)
  const resolvedHitRate = propHitRate ?? (hasTelemetry && ragMetrics
    ? (ragMetrics.total_verifications - ragMetrics.total_abstained) / ragMetrics.total_verifications
    : undefined)
  const resolvedComposite = propComposite ?? (hasTelemetry && resolvedPrecision != null && resolvedHitRate != null
    ? Number(((resolvedPrecision * 0.5) + (resolvedHitRate * 0.5)).toFixed(3))
    : undefined)

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4 select-none">
      {/* 1. RAGAS 综合质量指数 */}
      <Card
        onClick={onOpenBenchmark}
        className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40 cursor-pointer group"
      >
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="font-medium group-hover:text-primary transition-colors">
            {t('retrieval.metrics.compositeIndex', 'RAGAS 综合指数')}
          </span>
          <ShieldCheckIcon className="size-3.5 text-primary shrink-0" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="font-mono text-xl font-bold tabular-nums text-foreground">
            {resolvedComposite != null ? resolvedComposite.toFixed(3) : '--'}
          </span>
          <span className="font-mono text-xs text-muted-foreground ml-1">
            / {resolvedComposite != null ? '1.000' : '--'}
          </span>
        </div>
        <p className="text-xs text-muted-foreground truncate">
          {resolvedComposite != null
            ? (resolvedComposite >= 0.700
                ? t('retrieval.metrics.compositeNote', '门禁基准 ≥ 0.700 · 状态健康')
                : t('retrieval.metrics.compositeWarning', '低于门禁基准 0.700 · 需调优'))
            : t('retrieval.metrics.compositeEmpty', '暂无评测数据 · 可启动 Benchmark')}
        </p>
      </Card>

      {/* 2. 平均检索耗时 */}
      <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="font-medium">
            {t('retrieval.metrics.avgLatency', '平均检索耗时')}
          </span>
          <ZapIcon className="size-3.5 text-muted-foreground shrink-0" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="font-mono text-xl font-bold tabular-nums text-foreground">
            {resolvedLatency != null ? `${resolvedLatency.toFixed(1)}ms` : '--'}
          </span>
        </div>
        <p className="text-xs text-muted-foreground truncate">
          {resolvedLatency != null
            ? `${t('retrieval.metrics.avgLatencyNote', '端到端实测验证耗时')} · ${resolvedLatency.toFixed(1)}ms`
            : t('retrieval.metrics.noData', '暂无采样')}
        </p>
      </Card>

      {/* 3. 金标用例命中率 */}
      <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="font-medium">
            {t('retrieval.metrics.hitRate', '金标命中召回率')}
          </span>
          <TargetIcon className="size-3.5 text-muted-foreground shrink-0" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="font-mono text-xl font-bold tabular-nums text-foreground">
            {resolvedHitRate != null ? `${(resolvedHitRate * 100).toFixed(1)}%` : '--'}
          </span>
        </div>
        <p className="text-xs text-muted-foreground truncate">
          {resolvedHitRate != null
            ? `${t('retrieval.metrics.hitRateNote', '金标用例真实精准召回率')}${totalVerifications > 0 ? ` · ${totalVerifications} 次采样` : ''}`
            : t('retrieval.metrics.noData', '暂无采样')}
        </p>
      </Card>

      {/* 4. 上下文纯净度 */}
      <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="font-medium">
            {t('retrieval.metrics.purityRate', '上下文纯净度')}
          </span>
          <SparklesIcon className="size-3.5 text-primary shrink-0" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="font-mono text-xl font-bold tabular-nums text-foreground">
            {resolvedPrecision != null ? `${(resolvedPrecision * 100).toFixed(1)}%` : '--'}
          </span>
        </div>
        <p className="text-xs text-muted-foreground truncate">
          {resolvedPrecision != null
            ? `${t('retrieval.metrics.purityRateNote', '上下文证据切片真实纯净度')} · ${(resolvedPrecision * 100).toFixed(1)}%`
            : t('retrieval.metrics.noData', '暂无采样')}
        </p>
      </Card>
    </div>
  )
}
