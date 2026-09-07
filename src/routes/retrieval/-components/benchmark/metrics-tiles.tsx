// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { useTranslation } from 'react-i18next'
import { cn } from '#/lib/utils'
import type { BenchmarkMode, BenchmarkSummaryMetrics } from './types'

interface BenchmarkMetricsTilesProps {
  metrics: BenchmarkSummaryMetrics
  mode: BenchmarkMode
}

export function BenchmarkMetricsTiles({ metrics, mode }: BenchmarkMetricsTilesProps) {
  const { t } = useTranslation('retrieval')
  const { total, completed, hitRate, avgLatency, avgScore, ragas } = metrics

  if (completed === 0) {
    return null
  }

  if (mode === 'ragas' && ragas) {
    const precNum = Number(ragas.avgPrecision)
    const recNum = Number(ragas.avgRecall)
    const faithNum = Number(ragas.avgFaithfulness)
    const relNum = Number(ragas.avgRelevance)

    return (
      <div className="space-y-2">
        {/* RAGAS 主综合指数看板 */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg border border-cyan-500/30 bg-cyan-500/5">
          <div className="flex items-center gap-3">
            <div className="flex size-11 items-center justify-center rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-500 font-mono text-2xl font-bold tabular-nums">
              {ragas.compositeScore}
            </div>
            <div className="flex flex-col">
              <span className="text-xs font-semibold text-cyan-500 tracking-tight">
                {t('benchmark.metrics.compositeScore', 'RAGAS 综合指数 (Harmonic Mean)')}
              </span>
              <span className="text-[11px] text-muted-foreground">
                {t('benchmark.metrics.compositeDesc', '调和平均四维综合评分 (0.00 ~ 1.00)')}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono text-muted-foreground">
            <div>
              <span className="text-[11px] block">{t('benchmark.metrics.total', '已测用例')}</span>
              <span className="text-foreground font-bold">{completed}/{total}</span>
            </div>
            <div>
              <span className="text-[11px] block">{t('benchmark.metrics.avgLatency', '平均时延')}</span>
              <span className="text-foreground font-bold">{avgLatency}ms</span>
            </div>
            <div>
              <span className="text-[11px] block">{t('benchmark.metrics.hitRate', '命中率')}</span>
              <span className={cn(
                'font-bold',
                hitRate >= 80 ? 'text-cyan-500' : hitRate >= 50 ? 'text-foreground' : 'text-rose-500'
              )}>
                {hitRate}%
              </span>
            </div>
          </div>
        </div>

        {/* 4 维微瓦片 */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {/* Precision */}
          <div className="flex flex-col rounded-md border bg-muted/20 px-3 py-2 min-w-0" title={t('benchmark.metrics.precision')}>
            <span className="text-[11px] text-muted-foreground font-medium truncate">
              {t('benchmark.metrics.precision')}
            </span>
            <span className={cn(
              'font-mono text-base font-bold tabular-nums',
              precNum >= 0.7 ? 'text-cyan-500' : precNum >= 0.4 ? 'text-foreground' : 'text-amber-500'
            )}>
              {ragas.avgPrecision}
            </span>
          </div>

          {/* Recall */}
          <div className="flex flex-col rounded-md border bg-muted/20 px-3 py-2 min-w-0" title={t('benchmark.metrics.recall')}>
            <span className="text-[11px] text-muted-foreground font-medium truncate">
              {t('benchmark.metrics.recall')}
            </span>
            <span className={cn(
              'font-mono text-base font-bold tabular-nums',
              recNum >= 0.7 ? 'text-cyan-500' : recNum >= 0.4 ? 'text-foreground' : 'text-amber-500'
            )}>
              {ragas.avgRecall}
            </span>
          </div>

          {/* Faithfulness */}
          <div className="flex flex-col rounded-md border bg-muted/20 px-3 py-2 min-w-0" title={t('benchmark.metrics.faithfulness')}>
            <span className="text-[11px] text-muted-foreground font-medium truncate">
              {t('benchmark.metrics.faithfulness')}
            </span>
            <span className={cn(
              'font-mono text-base font-bold tabular-nums',
              faithNum >= 0.7 ? 'text-cyan-500' : faithNum >= 0.4 ? 'text-foreground' : 'text-amber-500'
            )}>
              {ragas.avgFaithfulness}
            </span>
          </div>

          {/* Answer Relevance */}
          <div className="flex flex-col rounded-md border bg-muted/20 px-3 py-2 min-w-0" title={t('benchmark.metrics.relevance')}>
            <span className="text-[11px] text-muted-foreground font-medium truncate">
              {t('benchmark.metrics.relevance')}
            </span>
            <span className={cn(
              'font-mono text-base font-bold tabular-nums',
              relNum >= 0.7 ? 'text-cyan-500' : relNum >= 0.4 ? 'text-foreground' : 'text-amber-500'
            )}>
              {ragas.avgRelevance}
            </span>
          </div>
        </div>
      </div>
    )
  }

  // Fast 模式标准四瓦片
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
      <div className="flex flex-col rounded-md border bg-muted/20 px-3 py-2">
        <span className="text-[11px] text-muted-foreground font-medium">{t('benchmark.metrics.total')}</span>
        <span className="font-mono text-base font-bold text-foreground tabular-nums">
          {completed} / {total}
        </span>
      </div>
      <div className="flex flex-col rounded-md border bg-muted/20 px-3 py-2">
        <span className="text-[11px] text-muted-foreground font-medium">{t('benchmark.metrics.hitRate')}</span>
        <span className={cn(
          'font-mono text-base font-bold tabular-nums',
          hitRate >= 80 ? 'text-cyan-500' : hitRate >= 50 ? 'text-foreground' : 'text-rose-500',
        )}>
          {hitRate}%
        </span>
      </div>
      <div className="flex flex-col rounded-md border bg-muted/20 px-3 py-2">
        <span className="text-[11px] text-muted-foreground font-medium">{t('benchmark.metrics.avgLatency')}</span>
        <span className="font-mono text-base font-bold text-foreground tabular-nums">
          {avgLatency} <span className="text-[11px] font-normal text-muted-foreground">ms</span>
        </span>
      </div>
      <div className="flex flex-col rounded-md border bg-muted/20 px-3 py-2">
        <span className="text-[11px] text-muted-foreground font-medium">{t('benchmark.metrics.avgScore')}</span>
        <span className="font-mono text-base font-bold text-cyan-500 tabular-nums">
          {avgScore}
        </span>
      </div>
    </div>
  )
}
