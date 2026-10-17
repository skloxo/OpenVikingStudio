import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Card } from '#/components/ui/card'
import { Badge } from '#/components/ui/badge'
import { LayersIcon, HashIcon, FileTextIcon, ZapIcon } from 'lucide-react'
import { ovClient } from '#/lib/ov-client'

interface HybridMetricsResponse {
  telemetry: {
    total_hybrid_queries: number
    dense_candidates_total: number
    sparse_candidates_total: number
    hybrid_fused_total: number
    hybrid_overlap_rate: number
    exact_symbol_boost_count: number
    avg_latency_ms: number
    is_bm25_ready: boolean
    rank_distribution: {
      hybrid_overlap?: number
      dense_only?: number
      sparse_only?: number
    }
  }
  index_stats: {
    total_documents: number
    db_size_bytes: number
    db_path: string
    is_ready: boolean
  }
}

export function BM25DenseRatioCard() {
  const { t } = useTranslation('retrieval')

  const { data, isLoading } = useQuery<HybridMetricsResponse>({
    queryKey: ['hybrid-search-metrics-telemetry'],
    queryFn: async () => {
      const res = await ovClient.instance.get<HybridMetricsResponse>('/api/v1/search/hybrid/metrics')
      return res.data
    },
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
    staleTime: 10_000,
  })

  const telemetry = data?.telemetry
  const indexStats = data?.index_stats
  const rankDist = telemetry?.rank_distribution ?? {}
  const overlapCount = rankDist.hybrid_overlap ?? 0
  const denseCount = rankDist.dense_only ?? 0
  const sparseCount = rankDist.sparse_only ?? 0
  const totalRankItems = Math.max(1, overlapCount + denseCount + sparseCount)

  const overlapPct = Number(((overlapCount / totalRankItems) * 100).toFixed(1))
  const densePct = Number(((denseCount / totalRankItems) * 100).toFixed(1))
  const sparsePct = Number((100 - overlapPct - densePct).toFixed(1))

  return (
    <Card className="flex flex-col gap-3 p-3.5 shadow-none border-border/60 bg-card">
      <div className="flex items-center justify-between border-b border-border/40 pb-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <LayersIcon className="size-3.5 text-cyan-600 dark:text-cyan-400 shrink-0" />
          <h4 className="text-xs font-semibold text-foreground tracking-tight truncate">
            {t('retrieval.operationalTelemetry.bm25VsDense', 'BM25 词法 vs 稠密向量命中比')}
          </h4>
        </div>
        <Badge variant="outline" className="text-xs font-mono border-cyan-500/30 text-cyan-600 dark:text-cyan-400">
          RRF k=60
        </Badge>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center py-0.5">
        <div className="p-2 rounded bg-muted/20 border border-border/40">
          <div className="text-xs text-muted-foreground truncate">
            {t('retrieval.operationalTelemetry.overlapRate', '双流重叠率')}
          </div>
          <div className="mt-0.5 font-mono text-base font-bold tabular-nums text-cyan-600 dark:text-cyan-400">
            {isLoading ? '--' : `${(telemetry?.hybrid_overlap_rate ?? 0) * 100}%`}
          </div>
        </div>
        <div className="p-2 rounded bg-muted/20 border border-border/40">
          <div className="text-xs text-muted-foreground truncate flex items-center justify-center gap-1">
            <HashIcon className="size-3 text-cyan-500" />
            {t('retrieval.operationalTelemetry.symbolBoosts', '符号精确提权')}
          </div>
          <div className="mt-0.5 font-mono text-base font-bold tabular-nums text-foreground">
            {isLoading ? '--' : (telemetry?.exact_symbol_boost_count ?? 0)}
          </div>
        </div>
        <div className="p-2 rounded bg-muted/20 border border-border/40">
          <div className="text-xs text-muted-foreground truncate flex items-center justify-center gap-1">
            <FileTextIcon className="size-3 text-muted-foreground" />
            {t('retrieval.operationalTelemetry.indexedDocs', '倒排在籍数')}
          </div>
          <div className="mt-0.5 font-mono text-base font-bold tabular-nums text-foreground">
            {isLoading ? '--' : (indexStats?.total_documents ?? 0)}
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>命中来源分布 (Hit Distribution)</span>
          <span className="font-mono tabular-nums">
            {telemetry ? `${telemetry.total_hybrid_queries} 次混合查询` : '--'}
          </span>
        </div>
        <div className="h-2 w-full rounded bg-muted/50 overflow-hidden flex">
          <div
            style={{ width: `${overlapPct}%` }}
            className="h-full bg-cyan-500 transition-all duration-300"
            title={`双流重叠: ${overlapPct}%`}
          />
          <div
            style={{ width: `${densePct}%` }}
            className="h-full bg-slate-500 transition-all duration-300"
            title={`稠密独占: ${densePct}%`}
          />
          <div
            style={{ width: `${sparsePct}%` }}
            className="h-full bg-sky-600 dark:bg-sky-400 transition-all duration-300"
            title={`BM25 独占: ${sparsePct}%`}
          />
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-0.5">
          <span className="flex items-center gap-1">
            <span className="size-2 rounded-full bg-cyan-500" />
            重叠 {overlapPct}%
          </span>
          <span className="flex items-center gap-1">
            <span className="size-2 rounded-full bg-slate-500" />
            稠密 {densePct}%
          </span>
          <span className="flex items-center gap-1">
            <span className="size-2 rounded-full bg-sky-600 dark:bg-sky-400" />
            BM25 {sparsePct}%
          </span>
        </div>
      </div>

      <div className="mt-auto pt-1 text-xs text-muted-foreground border-t border-border/30 flex items-center justify-between">
        <span className="flex items-center gap-1">
          <ZapIcon className="size-3 text-cyan-500" />
          平均召回时延
        </span>
        <span className="font-mono tabular-nums text-foreground">
          {telemetry ? `${telemetry.avg_latency_ms.toFixed(1)}ms` : '--'}
        </span>
      </div>
    </Card>
  )
}
