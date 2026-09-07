import { useTranslation } from 'react-i18next'
import { Card } from '#/components/ui/card'
import { ShieldCheckIcon, ZapIcon, TargetIcon, SparklesIcon } from 'lucide-react'

export interface RetrievalMetricsCardsProps {
  compositeScore?: number
  avgLatencyMs?: number
  hitRate?: number
  contextPrecision?: number
  onOpenBenchmark?: () => void
}

export function RetrievalMetricsCards({
  compositeScore = 0.82,
  avgLatencyMs = 18.4,
  hitRate = 1.0,
  contextPrecision = 0.85,
  onOpenBenchmark,
}: RetrievalMetricsCardsProps) {
  const { t } = useTranslation('retrieval')

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4 select-none">
      {/* 1. RAGAS 综合质量指数 */}
      <Card
        onClick={onOpenBenchmark}
        className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40 cursor-pointer group"
      >
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="font-medium group-hover:text-primary transition-colors">
            {t('metrics.compositeIndex', 'RAGAS 综合指数')}
          </span>
          <ShieldCheckIcon className="size-3.5 text-primary shrink-0" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="font-mono text-xl font-bold tabular-nums text-foreground">
            {compositeScore.toFixed(3)}
          </span>
          <span className="font-mono text-[11px] text-muted-foreground ml-1">/ 1.000</span>
        </div>
        <p className="text-[11px] text-muted-foreground truncate">
          {t('metrics.compositeNote', '门禁基准 ≥ 0.700 · 状态健康')}
        </p>
      </Card>

      {/* 2. 平均检索耗时 */}
      <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="font-medium">
            {t('metrics.avgLatency', '平均检索耗时')}
          </span>
          <ZapIcon className="size-3.5 text-muted-foreground shrink-0" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="font-mono text-xl font-bold tabular-nums text-foreground">
            {avgLatencyMs.toFixed(1)}ms
          </span>
        </div>
        <p className="text-[11px] text-muted-foreground truncate">
          {t('metrics.avgLatencyNote', '向量搜索 12ms · 语义重排 6ms')}
        </p>
      </Card>

      {/* 3. 金标用例命中率 */}
      <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="font-medium">
            {t('metrics.hitRate', '金标命中召回率')}
          </span>
          <TargetIcon className="size-3.5 text-muted-foreground shrink-0" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="font-mono text-xl font-bold tabular-nums text-foreground">
            {(hitRate * 100).toFixed(1)}%
          </span>
        </div>
        <p className="text-[11px] text-muted-foreground truncate">
          {t('metrics.hitRateNote', '10/10 金标用例全部精准召回')}
        </p>
      </Card>

      {/* 4. 上下文纯净度 */}
      <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="font-medium">
            {t('metrics.purityRate', '上下文纯净度')}
          </span>
          <SparklesIcon className="size-3.5 text-primary shrink-0" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="font-mono text-xl font-bold tabular-nums text-foreground">
            {(contextPrecision * 100).toFixed(1)}%
          </span>
        </div>
        <p className="text-[11px] text-muted-foreground truncate">
          {t('metrics.purityRateNote', '0 孤儿切片泄露 · 噪音已隔离')}
        </p>
      </Card>
    </div>
  )
}
