import * as React from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Card } from '#/components/ui/card'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { ovClient } from '#/lib/ov-client'
import {
  BinaryIcon,
  SparklesIcon,
  ZapIcon,
  SearchIcon,
  CpuIcon,
  ArrowUpRightIcon,
  CheckCircle2Icon,
} from 'lucide-react'
import { BM25RankHistogram } from './bm25-rank-histogram'

export interface HybridTelemetrySnapshot {
  total_hybrid_queries: number
  dense_candidates_total: number
  sparse_candidates_total: number
  hybrid_fused_total: number
  hybrid_overlap_rate: number
  exact_symbol_boost_count: number
  avg_latency_ms: number
  is_bm25_ready: boolean
  rank_distribution?: Record<string, number>
}

export interface BM25IndexStats {
  total_documents: number
  db_size_bytes: number
  db_path: string
  is_ready: boolean
}

export interface HybridMetricsResponse {
  telemetry: HybridTelemetrySnapshot
  index_stats: BM25IndexStats
}

export interface FusedItem {
  uri: string
  title: string
  level: number
  context_type: string
  rrf_score: number
  dense_rank?: number | null
  sparse_rank?: number | null
  origin: 'hybrid' | 'dense_only' | 'sparse_only'
  snippet: string
}

export interface HybridProbeResponse {
  query: string
  sparse_bm25_count: number
  dense_count: number
  fused_count: number
  latency_ms: number
  sparse_results: Array<{ uri: string; title: string; bm25_score: number; snippet: string }>
  dense_results: Array<{ uri: string; title: string; score: number }>
  fused_results: FusedItem[]
}

const PRESET_SYMBOLS = [
  '_query_endpoint_frequency_sync',
  'HierarchicalRetriever',
  'VikingFS.commit',
  '1933',
  'sqlite3.OperationalError',
]

export function BM25HybridCockpit() {
  const { t } = useTranslation('retrieval')
  const [probeQuery, setProbeQuery] = React.useState('_query_endpoint_frequency_sync')
  const [probeResult, setProbeResult] = React.useState<HybridProbeResponse | null>(null)

  // Fetch telemetry & index stats
  const metricsQuery = useQuery({
    queryKey: ['hybrid-retrieval-metrics'],
    queryFn: async () => {
      const res = await ovClient.instance.get<HybridMetricsResponse>(
        '/api/v1/search/hybrid_metrics',
      )
      return res.data
    },
    refetchInterval: 15000,
    refetchIntervalInBackground: false,
  })

  // Probe mutation
  const probeMutation = useMutation({
    mutationFn: async (q: string) => {
      const res = await ovClient.instance.post<HybridProbeResponse>(
        '/api/v1/search/hybrid_probe',
        { query: q, limit: 5 },
      )
      return res.data
    },
    onSuccess: (data) => {
      setProbeResult(data)
    },
  })

  const telemetry = metricsQuery.data?.telemetry
  const indexStats = metricsQuery.data?.index_stats

  return (
    <Card className="flex flex-col gap-3 p-3.5 border-border/60 bg-card/60 shadow-none">
      {/* 1. 标题与状态指示 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex size-6 items-center justify-center rounded-md bg-cyan-50 text-cyan-700 dark:bg-cyan-500/10 dark:text-cyan-400 border border-cyan-200 dark:border-transparent">
            <BinaryIcon className="size-3.5" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-foreground">
              {t('hybrid.title', 'BM25 + 向量双流融合座舱 (RRF k=60)')}
            </h3>
            <p className="text-xs text-muted-foreground">
              {t('hybrid.subtitle', '消除代码精确符号与端口盲区 · SQLite FTS5 倒排索引加速')}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className="h-5 px-2 text-xs font-mono tabular-nums border-border/60 bg-muted/30"
          >
            <CpuIcon className="mr-1 size-3 text-cyan-600 dark:text-cyan-400" />
            {indexStats?.is_ready ? 'FTS5: READY' : 'FTS5: INIT'}
          </Badge>
          <Badge
            variant="outline"
            className="h-5 px-2 text-xs font-mono tabular-nums border-cyan-200 bg-cyan-50 text-cyan-800 dark:border-cyan-500/30 dark:text-cyan-400 dark:bg-cyan-500/5"
          >
            RRF k=60
          </Badge>
        </div>
      </div>

      {/* 2. 四大核心客观指标瓦片 */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 select-none">
        {/* 倒排文档总数 */}
        <div className="flex flex-col gap-0.5 rounded-md border border-border/50 bg-muted/10 p-2.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{t('hybrid.indexedDocs', '倒排索引文档')}</span>
            <BinaryIcon className="size-3 text-muted-foreground" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-base font-bold tabular-nums text-foreground">
              {indexStats?.total_documents ?? '--'}
            </span>
            <span className="text-xs text-muted-foreground">篇</span>
          </div>
          <p className="text-xs text-muted-foreground truncate">
            {indexStats ? `WAL 模式 · ${((indexStats.db_size_bytes || 0) / 1024).toFixed(1)} KB` : '加载中...'}
          </p>
        </div>

        {/* 精确符号增强计数 */}
        <div className="flex flex-col gap-0.5 rounded-md border border-border/50 bg-muted/10 p-2.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{t('hybrid.symbolBoosts', '精确符号召回提权')}</span>
            <ArrowUpRightIcon className="size-3 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-base font-bold tabular-nums text-cyan-700 dark:text-cyan-400">
              {telemetry?.exact_symbol_boost_count ?? 0}
            </span>
            <span className="text-xs text-muted-foreground">次</span>
          </div>
          <p className="text-xs text-muted-foreground truncate">
            snake_case / 端口 / 异常全命中
          </p>
        </div>

        {/* 双流重合覆盖率 */}
        <div className="flex flex-col gap-0.5 rounded-md border border-border/50 bg-muted/10 p-2.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{t('hybrid.overlapRate', '双流重合增强率')}</span>
            <SparklesIcon className="size-3 text-muted-foreground" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-base font-bold tabular-nums text-foreground">
              {telemetry ? `${(telemetry.hybrid_overlap_rate * 100).toFixed(1)}%` : '--'}
            </span>
          </div>
          <p className="text-xs text-muted-foreground truncate">
            Dense 与 BM25 互相印证
          </p>
        </div>

        {/* 融合计算耗时 */}
        <div className="flex flex-col gap-0.5 rounded-md border border-border/50 bg-muted/10 p-2.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{t('hybrid.avgLatency', '平均融合开销')}</span>
            <ZapIcon className="size-3 text-muted-foreground" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-base font-bold tabular-nums text-foreground">
              {telemetry?.avg_latency_ms ? `${telemetry.avg_latency_ms.toFixed(1)}ms` : '< 1.5ms'}
            </span>
          </div>
          <p className="text-xs text-muted-foreground truncate">
            纯单调时钟归并 · 零额外 RPC
          </p>
        </div>
      </div>

      {/* 2.5 Dense vs Sparse 召回名次分布直方图 */}
      <BM25RankHistogram
        fusedResults={probeResult?.fused_results}
        distribution={telemetry?.rank_distribution}
      />

      {/* 3. 交互式双流 RRF 试验台 */}
      <div className="flex flex-col gap-2 rounded-md border border-border/50 bg-muted/5 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-xs font-medium text-foreground">
            {t('hybrid.probeTitle', '精确符号双流检索验证台')}
          </span>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-muted-foreground">快速预设:</span>
            {PRESET_SYMBOLS.map((sym) => (
              <button
                key={sym}
                type="button"
                onClick={() => {
                  setProbeQuery(sym)
                  probeMutation.mutate(sym)
                }}
                className="rounded border border-border/60 bg-muted/20 px-1.5 py-0.5 font-mono text-xs text-muted-foreground hover:border-cyan-500/40 hover:text-cyan-400 transition-colors"
              >
                {sym}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Input
            value={probeQuery}
            onChange={(e) => setProbeQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && probeQuery.trim()) {
                probeMutation.mutate(probeQuery.trim())
              }
            }}
            placeholder="输入精确代码符号、类名、端口或错误栈..."
            className="h-8 text-xs font-mono"
          />
          <Button
            size="sm"
            onClick={() => {
              if (probeQuery.trim()) {
                probeMutation.mutate(probeQuery.trim())
              }
            }}
            disabled={probeMutation.isPending || !probeQuery.trim()}
            className="h-8 px-3 text-xs shrink-0"
          >
            <SearchIcon className="mr-1.5 size-3.5" />
            {probeMutation.isPending ? '探测中...' : '双流探测'}
          </Button>
        </div>

        {/* 探测结果回显 */}
        {probeResult && (
          <div className="flex flex-col gap-2 pt-2 border-t border-border/40">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>
                探测耗时:{' '}
                <span className="font-mono text-foreground font-semibold">
                  {probeResult.latency_ms}ms
                </span>{' '}
                · BM25 命中:{' '}
                <span className="font-mono text-foreground">{probeResult.sparse_bm25_count}</span>{' '}
                · 向量命中:{' '}
                <span className="font-mono text-foreground">{probeResult.dense_count}</span>{' '}
                · RRF 融合总数:{' '}
                <span className="font-mono text-cyan-700 dark:text-cyan-400 font-semibold">{probeResult.fused_count}</span>
              </span>
              <span className="text-xs text-muted-foreground">Top-5 融合排名</span>
            </div>

            <div className="flex flex-col gap-1.5">
              {probeResult.fused_results.length === 0 ? (
                <div className="py-3 text-center text-xs text-muted-foreground">
                  未匹配到测试候选，可先通过 POST /api/v1/search/hybrid_index_doc 录入或使用预设符号
                </div>
              ) : (
                probeResult.fused_results.map((item, idx) => (
                  <div
                    key={item.uri}
                    className="flex flex-col gap-1 rounded border border-border/40 bg-card/40 p-2 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className="font-mono font-bold text-muted-foreground">#{idx + 1}</span>
                        <span className="font-mono font-medium text-foreground truncate">
                          {item.uri}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        {item.origin === 'hybrid' && (
                          <Badge
                            variant="outline"
                            className="h-4 px-1.5 text-xs font-mono border-cyan-200 bg-cyan-50 text-cyan-800 dark:border-cyan-500/30 dark:text-cyan-400 dark:bg-cyan-500/5"
                          >
                            <CheckCircle2Icon className="mr-1 size-2.5" />
                            双流重合增强
                          </Badge>
                        )}
                        {item.origin === 'sparse_only' && (
                          <Badge
                            variant="outline"
                            className="h-4 px-1.5 text-xs font-mono border-primary/30 text-primary bg-primary/5"
                          >
                            BM25 精确命中
                          </Badge>
                        )}
                        {item.origin === 'dense_only' && (
                          <Badge
                            variant="outline"
                            className="h-4 px-1.5 text-xs font-mono border-border/60 text-muted-foreground bg-muted/20"
                          >
                            Dense 语义泛化
                          </Badge>
                        )}
                        <span className="font-mono tabular-nums text-xs text-muted-foreground">
                          RRF: {item.rrf_score.toFixed(4)}
                        </span>
                      </div>
                    </div>
                    {item.snippet && (
                      <p
                        className="text-xs text-muted-foreground font-mono bg-muted/20 px-1.5 py-0.5 rounded truncate"
                        dangerouslySetInnerHTML={{ __html: item.snippet }}
                      />
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </Card>
  )
}
