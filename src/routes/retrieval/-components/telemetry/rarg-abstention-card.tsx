import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Card } from '#/components/ui/card'
import { Badge } from '#/components/ui/badge'
import { ShieldAlertIcon, ActivityIcon } from 'lucide-react'
import { ovClient } from '#/lib/ov-client'

interface RAGTelemetryResponse {
  total_verifications: number
  total_abstained: number
  abstention_rate: number
  avg_confidence: number
  avg_latency_ms: number
  confidence_distribution?: {
    low?: number
    medium?: number
    high?: number
  }
  recent_verifications?: Array<{
    query: string
    confidence: number
    should_abstain: boolean
    latency_ms: number
    timestamp: number
  }>
}

export function RARGAbstentionCard() {
  const { t } = useTranslation('retrieval')

  const { data, isLoading } = useQuery<RAGTelemetryResponse>({
    queryKey: ['rag-abstention-telemetry-overview'],
    queryFn: async () => {
      const res = await ovClient.instance.get<RAGTelemetryResponse>('/api/v1/rag/metrics')
      return res.data
    },
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
    staleTime: 10_000,
  })

  const total = data?.total_verifications ?? 0
  const abstained = data?.total_abstained ?? 0
  const ratePct = Number(((data?.abstention_rate ?? 0) * 100).toFixed(1))
  const avgConf = data?.avg_confidence != null ? data.avg_confidence.toFixed(3) : '--'
  const dist = data?.confidence_distribution ?? {}
  const lowCount = dist.low ?? 0
  const medCount = dist.medium ?? 0
  const highCount = dist.high ?? 0
  const totalBuckets = Math.max(1, lowCount + medCount + highCount)

  const lowPct = Math.round((lowCount / totalBuckets) * 100)
  const medPct = Math.round((medCount / totalBuckets) * 100)
  const highPct = Math.max(0, 100 - lowPct - medPct)

  const recent = data?.recent_verifications ?? []

  return (
    <Card className="flex flex-col gap-3 p-3.5 shadow-none border-border/60 bg-card">
      <div className="flex items-center justify-between border-b border-border/40 pb-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <ShieldAlertIcon className="size-3.5 text-cyan-600 dark:text-cyan-400 shrink-0" />
          <h4 className="text-xs font-semibold text-foreground tracking-tight truncate">
            {t('retrieval.operationalTelemetry.ragAbstention', 'RARG 弃答率与置信度分布')}
          </h4>
        </div>
        <Badge variant="outline" className="text-xs font-mono border-cyan-500/30 text-cyan-600 dark:text-cyan-400">
          Threshold 0.40
        </Badge>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center py-0.5">
        <div className="p-2 rounded bg-muted/20 border border-border/40">
          <div className="text-xs text-muted-foreground truncate">
            {t('retrieval.operationalTelemetry.abstentionRate', '弃答拦截率')}
          </div>
          <div className="mt-0.5 font-mono text-base font-bold tabular-nums text-foreground">
            {isLoading ? '--' : `${ratePct}%`}
          </div>
        </div>
        <div className="p-2 rounded bg-muted/20 border border-border/40">
          <div className="text-xs text-muted-foreground truncate">
            {t('retrieval.operationalTelemetry.avgConfidence', '平均证据置信度')}
          </div>
          <div className="mt-0.5 font-mono text-base font-bold tabular-nums text-cyan-600 dark:text-cyan-400">
            {isLoading ? '--' : avgConf}
          </div>
        </div>
        <div className="p-2 rounded bg-muted/20 border border-border/40">
          <div className="text-xs text-muted-foreground truncate">
            {t('retrieval.operationalTelemetry.totalVerifications', '累积判定次数')}
          </div>
          <div className="mt-0.5 font-mono text-base font-bold tabular-nums text-foreground">
            {isLoading ? '--' : total}
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>置信度阶梯分布 (Confidence Tiers)</span>
          <span className="font-mono tabular-nums">
            {total > 0 ? `${abstained} 次拦截弃答` : '暂无拦截'}
          </span>
        </div>
        <div className="h-2 w-full rounded bg-muted/50 overflow-hidden flex">
          <div
            style={{ width: `${lowPct}%` }}
            className="h-full bg-rose-500 transition-all duration-300"
            title={`低置信/弃答: ${lowPct}%`}
          />
          <div
            style={{ width: `${medPct}%` }}
            className="h-full bg-amber-500 transition-all duration-300"
            title={`过渡边缘: ${medPct}%`}
          />
          <div
            style={{ width: `${highPct}%` }}
            className="h-full bg-cyan-500 transition-all duration-300"
            title={`高信证据: ${highPct}%`}
          />
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-0.5">
          <span className="flex items-center gap-1">
            <span className="size-2 rounded-full bg-rose-500" />
            &lt;0.30 ({lowPct}%)
          </span>
          <span className="flex items-center gap-1">
            <span className="size-2 rounded-full bg-amber-500" />
            0.3-0.7 ({medPct}%)
          </span>
          <span className="flex items-center gap-1">
            <span className="size-2 rounded-full bg-cyan-500" />
            &ge;0.70 ({highPct}%)
          </span>
        </div>
      </div>

      <div className="mt-auto pt-1 text-xs text-muted-foreground border-t border-border/30">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1">
            <ActivityIcon className="size-3 text-cyan-500" />
            最近判定切片
          </span>
          <span className="font-mono tabular-nums text-foreground">
            {recent.length > 0 ? (
              <span className="text-cyan-600 dark:text-cyan-400">
                {recent[recent.length - 1].should_abstain ? '拦截弃答' : '证据充分通过'}
              </span>
            ) : (
              '--'
            )}
          </span>
        </div>
      </div>
    </Card>
  )
}
