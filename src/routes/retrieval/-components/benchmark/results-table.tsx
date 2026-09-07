// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { CheckCircle2Icon, ChevronDownIcon, ChevronRightIcon, Loader2Icon, Trash2Icon, XCircleIcon } from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { cn } from '#/lib/utils'
import type { BenchmarkMode, BenchmarkResultItem } from './types'

interface BenchmarkResultsTableProps {
  queries: string[]
  results: BenchmarkResultItem[]
  isRunning: boolean
  currentIndex: number
  mode: BenchmarkMode
  onRemoveQuery: (index: number) => void
}

export function BenchmarkResultsTable({
  queries,
  results,
  isRunning,
  currentIndex,
  mode,
  onRemoveQuery,
}: BenchmarkResultsTableProps) {
  const { t } = useTranslation('retrieval')
  const [expandedId, setExpandedId] = React.useState<string | null>(null)

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  return (
    <div className="w-full overflow-x-auto min-w-0 rounded-md border border-border/80 bg-background shadow-xs">
      <table className="w-full min-w-[700px] text-left text-xs border-collapse">
        <thead>
          <tr className="border-b bg-muted/30 text-[11px] text-muted-foreground font-medium">
            <th className="py-2.5 px-3 min-w-[180px]">{t('benchmark.table.query')}</th>
            <th className="py-2.5 px-3 min-w-[160px]">{t('benchmark.table.top1')}</th>
            {mode === 'ragas' ? (
              <>
                <th className="py-2.5 px-2 text-right w-16">{t('benchmark.table.precision', '精度')}</th>
                <th className="py-2.5 px-2 text-right w-16">{t('benchmark.table.faithfulness', '忠实度')}</th>
                <th className="py-2.5 px-2 text-right w-16">{t('benchmark.table.composite', 'RAGAS')}</th>
              </>
            ) : (
              <th className="py-2.5 px-3 text-right w-18">{t('benchmark.table.score')}</th>
            )}
            <th className="py-2.5 px-3 text-right w-18">{t('benchmark.table.latency')}</th>
            <th className="py-2.5 px-3 text-center w-20">{t('benchmark.table.status')}</th>
            {!isRunning && <th className="py-2.5 px-2 w-9 text-center" />}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/50">
          {queries.map((q, idx) => {
            const result = results.find((r) => r.query === q)
            const isCurrent = isRunning && currentIndex === idx
            const status = result?.status ?? 'pending'
            const isExpanded = result?.id ? expandedId === result.id : false

            return (
              <React.Fragment key={`query-row-${idx}-${q}`}>
                <tr
                  className={cn(
                    'transition-colors',
                    isCurrent && 'bg-cyan-500/5',
                    status === 'hit' && 'hover:bg-muted/30',
                  )}
                >
                  <td className="py-2 px-3 font-medium text-foreground max-w-56 truncate" title={q}>
                    <div className="flex items-center gap-1.5 min-w-0">
                      {mode === 'ragas' && result?.ragas && (
                        <button
                          type="button"
                          onClick={() => result.id && toggleExpand(result.id)}
                          className="text-muted-foreground hover:text-cyan-500 cursor-pointer shrink-0"
                        >
                          {isExpanded ? (
                            <ChevronDownIcon className="size-3 text-cyan-500" />
                          ) : (
                            <ChevronRightIcon className="size-3" />
                          )}
                        </button>
                      )}
                      <span className="truncate">{q}</span>
                    </div>
                  </td>
                  <td className="py-2 px-3 max-w-56 min-w-0">
                    {result?.top1Title ? (
                      <div className="truncate">
                        <span className="font-medium text-foreground truncate block" title={result.top1Title}>
                          {result.top1Title}
                        </span>
                        <span className="block font-mono text-[11px] text-muted-foreground truncate" title={result.top1Uri}>
                          {result.top1Uri}
                        </span>
                      </div>
                    ) : (
                      <span className="text-[11px] text-muted-foreground italic">--</span>
                    )}
                  </td>

                  {mode === 'ragas' ? (
                    <>
                      <td className="py-2 px-2 text-right font-mono text-[11px] tabular-nums">
                        {result?.ragas ? (
                          <span className={result.ragas.contextPrecision >= 0.7 ? 'text-cyan-500 font-semibold' : 'text-foreground'}>
                            {result.ragas.contextPrecision.toFixed(2)}
                          </span>
                        ) : '--'}
                      </td>
                      <td className="py-2 px-2 text-right font-mono text-[11px] tabular-nums">
                        {result?.ragas ? (
                          <span className={result.ragas.faithfulness >= 0.7 ? 'text-cyan-500 font-semibold' : 'text-foreground'}>
                            {result.ragas.faithfulness.toFixed(2)}
                          </span>
                        ) : '--'}
                      </td>
                      <td className="py-2 px-2 text-right font-mono text-xs tabular-nums">
                        {result?.ragas ? (
                          <span className="text-cyan-500 font-bold">
                            {result.ragas.compositeScore.toFixed(2)}
                          </span>
                        ) : '--'}
                      </td>
                    </>
                  ) : (
                    <td className="py-2 px-3 text-right font-mono text-xs tabular-nums">
                      {typeof result?.score === 'number' ? (
                        <span className={result.score >= 0.7 ? 'text-cyan-500 font-semibold' : 'text-foreground'}>
                          {result.score.toFixed(3)}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">--</span>
                      )}
                    </td>
                  )}

                  <td className="py-2 px-3 text-right font-mono text-[11px] text-muted-foreground tabular-nums">
                    {typeof result?.latencyMs === 'number' ? `${result.latencyMs}ms` : '--'}
                  </td>

                  <td className="py-2 px-3 text-center">
                    {status === 'running' ? (
                      <Badge variant="outline" className="px-1.5 py-0 text-[11px] border-cyan-500/40 text-cyan-500 gap-1 animate-pulse">
                        <Loader2Icon className="size-2.5 animate-spin" />
                        <span>Run</span>
                      </Badge>
                    ) : status === 'hit' ? (
                      <Badge variant="outline" className="px-1.5 py-0 text-[11px] border-cyan-500/40 bg-cyan-500/10 text-cyan-500 gap-1">
                        <CheckCircle2Icon className="size-2.5" />
                        <span>{t('benchmark.statusHit')}</span>
                      </Badge>
                    ) : status === 'miss' ? (
                      <Badge variant="outline" className="px-1.5 py-0 text-[11px] border-border text-muted-foreground gap-1">
                        <XCircleIcon className="size-2.5" />
                        <span>{t('benchmark.statusMiss')}</span>
                      </Badge>
                    ) : status === 'error' ? (
                      <Badge variant="outline" className="px-1.5 py-0 text-[11px] border-rose-500/40 bg-rose-500/10 text-rose-500 gap-1">
                        <span>Err</span>
                      </Badge>
                    ) : (
                      <span className="text-[11px] text-muted-foreground">--</span>
                    )}
                  </td>

                  {!isRunning && (
                    <td className="py-2 px-2 text-center">
                      <button
                        type="button"
                        onClick={() => onRemoveQuery(idx)}
                        className="text-muted-foreground hover:text-rose-500 transition-colors cursor-pointer"
                        title={t('benchmark.removeQuery')}
                      >
                        <Trash2Icon className="size-3.5" />
                      </button>
                    </td>
                  )}
                </tr>

                {/* 展开的 RAGAS 4 维指标详情折叠卡片 */}
                {isExpanded && result?.ragas && (
                  <tr className="bg-muted/10">
                    <td colSpan={mode === 'ragas' ? 8 : 6} className="px-4 py-2 text-xs border-y border-cyan-500/20">
                      <div className="flex flex-wrap items-center gap-4 text-[11px] font-mono text-muted-foreground">
                        <div>
                          <span>Precision: </span>
                          <span className="text-foreground font-bold">{result.ragas.contextPrecision}</span>
                        </div>
                        <div>
                          <span>Recall: </span>
                          <span className="text-foreground font-bold">{result.ragas.contextRecall}</span>
                        </div>
                        <div>
                          <span>Faithfulness: </span>
                          <span className="text-foreground font-bold">{result.ragas.faithfulness}</span>
                        </div>
                        <div>
                          <span>Relevance: </span>
                          <span className="text-foreground font-bold">{result.ragas.answerRelevance}</span>
                        </div>
                        <div>
                          <span>Composite (调和): </span>
                          <span className="text-cyan-500 font-bold">{result.ragas.compositeScore}</span>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
