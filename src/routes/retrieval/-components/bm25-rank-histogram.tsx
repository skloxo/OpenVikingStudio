import { useTranslation } from 'react-i18next'
import { BarChart3Icon } from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import type { FusedItem } from './bm25-hybrid-cockpit'

export interface BM25RankHistogramProps {
  fusedResults?: FusedItem[]
  distribution?: Record<string, number>
}

export function BM25RankHistogram({ fusedResults = [], distribution }: BM25RankHistogramProps) {
  const { t } = useTranslation('retrieval')

  const total = (distribution?.hybrid_overlap || 0) + (distribution?.dense_only || 0) + (distribution?.sparse_only || 0)
  const overlapPct = total > 0 ? Math.round(((distribution?.hybrid_overlap || 0) / total) * 100) : 0
  const sparsePct = total > 0 ? Math.round(((distribution?.sparse_only || 0) / total) * 100) : 0
  const densePct = total > 0 ? Math.max(0, 100 - overlapPct - sparsePct) : 0

  return (
    <div className="flex flex-col gap-2.5 rounded-md border border-border/50 bg-muted/5 p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3Icon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          <span className="text-xs font-medium text-foreground">
            {t('hybrid.histogramTitle', 'Dense vs Sparse 召回名次分布直方图')}
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="inline-block size-2 rounded-sm bg-cyan-500" />
            <span className="text-muted-foreground">双流重合</span>
            <span className="font-mono text-foreground font-semibold">{overlapPct}%</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="inline-block size-2 rounded-sm bg-primary/70" />
            <span className="text-muted-foreground">BM25专属</span>
            <span className="font-mono text-foreground font-semibold">{sparsePct}%</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="inline-block size-2 rounded-sm bg-muted-foreground/40" />
            <span className="text-muted-foreground">Dense专属</span>
            <span className="font-mono text-foreground font-semibold">{densePct}%</span>
          </div>
        </div>
      </div>

      {/* 比例分布条 */}
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-muted/30">
        <div
          style={{ width: `${overlapPct}%` }}
          className="h-full bg-cyan-500 transition-all duration-300"
          title={`双流重合: ${overlapPct}%`}
        />
        <div
          style={{ width: `${sparsePct}%` }}
          className="h-full bg-primary/70 transition-all duration-300"
          title={`BM25专属: ${sparsePct}%`}
        />
        <div
          style={{ width: `${densePct}%` }}
          className="h-full bg-muted-foreground/30 transition-all duration-300"
          title={`Dense专属: ${densePct}%`}
        />
      </div>

      {/* 探测候选名次对比列表 */}
      {fusedResults.length > 0 ? (
        <div className="mt-1 flex flex-col gap-1.5">
          <div className="grid grid-cols-12 text-xs text-muted-foreground px-1 pb-1 border-b border-border/30">
            <span className="col-span-1 font-mono">Rank</span>
            <span className="col-span-6 truncate">候选 URI / 符号</span>
            <span className="col-span-2 text-center font-mono">Dense 排名</span>
            <span className="col-span-2 text-center font-mono">BM25 排名</span>
            <span className="col-span-1 text-right font-mono">RRF</span>
          </div>
          {fusedResults.slice(0, 5).map((item, idx) => (
            <div
              key={item.uri}
              className="grid grid-cols-12 items-center text-xs p-1.5 rounded bg-card/30 border border-border/30"
            >
              <span className="col-span-1 font-mono font-bold text-muted-foreground">#{idx + 1}</span>
              <span className="col-span-6 font-mono text-foreground truncate pr-2" title={item.uri}>
                {item.uri}
              </span>
              <div className="col-span-2 text-center">
                {typeof item.dense_rank === 'number' ? (
                  <Badge variant="outline" className="h-4 px-1 text-xs font-mono border-border/50 text-muted-foreground">
                    #{item.dense_rank}
                  </Badge>
                ) : (
                  <span className="text-xs text-muted-foreground font-mono">未入前20</span>
                )}
              </div>
              <div className="col-span-2 text-center">
                {typeof item.sparse_rank === 'number' ? (
                  <Badge variant="outline" className="h-4 px-1 text-xs font-mono border-cyan-500/30 text-cyan-700 dark:text-cyan-400 bg-cyan-500/5">
                    #{item.sparse_rank}
                  </Badge>
                ) : (
                  <span className="text-xs text-muted-foreground font-mono">未入前20</span>
                )}
              </div>
              <span className="col-span-1 text-right font-mono tabular-nums text-foreground font-semibold">
                {item.rrf_score.toFixed(4)}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground text-center py-2">
          {t('hybrid.histogramEmpty', '在下方输入精确符号或点击预设按钮，触发双流探测直方图')}
        </p>
      )}
    </div>
  )
}
