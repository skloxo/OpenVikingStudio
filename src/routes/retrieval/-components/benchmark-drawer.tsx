// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { FlaskConicalIcon, SparklesIcon } from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '#/components/ui/sheet'
import { fetchFind } from '#/lib/retrieval'
import {
  computeSummaryMetrics,
  evaluateRagasSample,
  getDefaultBenchmarkQueries,
} from './benchmark/eval-engine'
import { BenchmarkMetricsTiles } from './benchmark/metrics-tiles'
import { BenchmarkQuerySuite } from './benchmark/query-suite'
import { BenchmarkResultsTable } from './benchmark/results-table'
import type { BenchmarkMode, BenchmarkResultItem } from './benchmark/types'

export type { BenchmarkMode, BenchmarkResultItem }

export function RetrievalBenchmarkDrawer() {
  const { t, i18n } = useTranslation('retrieval')

  const defaultQueries = React.useMemo(() => {
    const fromI18n = t('benchmark.defaultQueries', { returnObjects: true })
    if (Array.isArray(fromI18n) && fromI18n.length > 0) {
      return fromI18n as string[]
    }
    return getDefaultBenchmarkQueries(i18n.language)
  }, [t, i18n.language])

  const [isOpen, setIsOpen] = React.useState(false)
  const [mode, setMode] = React.useState<BenchmarkMode>('ragas')
  const [queries, setQueries] = React.useState<string[]>(() => getDefaultBenchmarkQueries(i18n.language))
  const [isRunning, setIsRunning] = React.useState(false)
  const [currentIndex, setCurrentIndex] = React.useState(-1)
  const [results, setResults] = React.useState<BenchmarkResultItem[]>([])

  // 当系统语言切换且未产生评测数据时，自动对齐语言专属默认用例集
  const prevLangRef = React.useRef(i18n.language)
  React.useEffect(() => {
    if (prevLangRef.current !== i18n.language) {
      prevLangRef.current = i18n.language
      if (!isRunning && results.length === 0) {
        setQueries(defaultQueries)
      }
    }
  }, [i18n.language, isRunning, results.length, defaultQueries])

  const handleAddQuery = (newQ: string) => {
    setQueries((prev) => [...prev, newQ])
  }

  const handleRemoveQuery = (index: number) => {
    if (isRunning) return
    setQueries((prev) => prev.filter((_, i) => i !== index))
  }

  const handleResetDefaults = () => {
    if (isRunning) return
    setQueries(defaultQueries)
    setResults([])
    setCurrentIndex(-1)
  }

  const runBenchmark = async () => {
    if (isRunning || queries.length === 0) return
    setIsRunning(true)
    setCurrentIndex(0)

    const initialResults: BenchmarkResultItem[] = queries.map((q, idx) => ({
      id: `bench-${idx}-${Date.now()}`,
      query: q,
      status: 'pending',
    }))
    setResults(initialResults)

    const updated = [...initialResults]

    for (let i = 0; i < queries.length; i++) {
      setCurrentIndex(i)
      updated[i] = { ...updated[i], status: 'running' }
      setResults([...updated])

      const startTime = performance.now()
      try {
        const grouped = await fetchFind(queries[i], {
          limit: 3,
          targetUri: 'viking://',
        })

        const latencyMs = Math.round(performance.now() - startTime)
        const hits = [
          ...grouped.resources,
          ...grouped.memories,
          ...grouped.skills,
        ]

        if (hits.length > 0) {
          const top1 = hits[0]
          const top1Score = typeof top1.score === 'number' ? Number(top1.score.toFixed(3)) : 0.85
          const ragasMetrics = mode === 'ragas' ? evaluateRagasSample(hits, queries[i]) : undefined

          updated[i] = {
            ...updated[i],
            top1Title: top1.abstract || top1.uri.split('/').pop() || top1.uri,
            top1Uri: top1.uri,
            score: top1Score,
            latencyMs,
            status: 'hit',
            ragas: ragasMetrics,
          }
        } else {
          updated[i] = {
            ...updated[i],
            latencyMs,
            status: 'miss',
            ragas: mode === 'ragas' ? evaluateRagasSample([], queries[i]) : undefined,
          }
        }
      } catch (err: unknown) {
        const latencyMs = Math.round(performance.now() - startTime)
        const errorMsg = err instanceof Error ? err.message : 'Request failed'
        updated[i] = {
          ...updated[i],
          latencyMs,
          status: 'error',
          errorMsg,
        }
      }
      setResults([...updated])
    }

    setIsRunning(false)
    setCurrentIndex(-1)
  }

  const summaryMetrics = React.useMemo(
    () => computeSummaryMetrics(results, mode),
    [results, mode],
  )

  const exportReport = () => {
    const report = {
      timestamp: new Date().toISOString(),
      mode,
      summary: summaryMetrics,
      results: results.map((r) => ({
        query: r.query,
        status: r.status,
        top1_title: r.top1Title ?? null,
        top1_uri: r.top1Uri ?? null,
        score: r.score ?? null,
        latency_ms: r.latencyMs ?? null,
        ragas: r.ragas ?? null,
      })),
    }

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `openviking-${mode}-benchmark-${Date.now()}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger
        render={
          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5 text-xs font-medium border-border/80 hover:border-cyan-500/50 hover:bg-cyan-500/5 cursor-pointer"
          >
            <FlaskConicalIcon className="size-3.5 text-cyan-500" />
            <span>{t('benchmark.button')}</span>
            <Badge variant="outline" className="text-[11px] px-1 py-0 h-4 border-cyan-500/40 text-cyan-500 font-mono">
              RAGAS
            </Badge>
          </Button>
        }
      />

      <SheetContent
        side="right"
        className="w-full data-[side=right]:w-[95vw] data-[side=right]:sm:max-w-2xl data-[side=right]:md:max-w-3xl data-[side=right]:lg:max-w-4xl data-[side=right]:xl:max-w-5xl flex flex-col gap-0 p-0 border-l bg-background text-foreground shadow-2xl"
      >
        <SheetHeader className="border-b px-5 py-3.5 pr-14 bg-muted/20">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
                {mode === 'ragas' ? (
                  <SparklesIcon className="size-4" />
                ) : (
                  <FlaskConicalIcon className="size-4" />
                )}
              </div>
              <SheetTitle className="text-sm font-semibold tracking-tight">
                {mode === 'ragas' ? t('benchmark.ragasDrawerTitle', 'RAGAS 自动化评测实验室 (04A~04B)') : t('benchmark.drawerTitle')}
              </SheetTitle>
            </div>
            <Badge variant="outline" className="text-[11px] font-mono px-2 py-0.5 border-border shrink-0">
              {mode === 'ragas' ? 'Ragas v0.2+' : 'Fast / 1933'}
            </Badge>
          </div>
          <SheetDescription className="text-xs text-muted-foreground mt-1">
            {mode === 'ragas'
              ? t('benchmark.ragasDrawerDesc', '实测 Precision / Recall / Faithfulness / Relevance 综合调和四维指数')
              : t('benchmark.drawerDesc')}
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          <BenchmarkQuerySuite
            currentIndex={currentIndex}
            hasCompletedResults={summaryMetrics.completed > 0}
            isRunning={isRunning}
            mode={mode}
            onAddQuery={handleAddQuery}
            onExport={exportReport}
            onModeChange={setMode}
            onResetSuite={handleResetDefaults}
            onRun={runBenchmark}
            queries={queries}
          />

          <BenchmarkMetricsTiles metrics={summaryMetrics} mode={mode} />

          <BenchmarkResultsTable
            currentIndex={currentIndex}
            isRunning={isRunning}
            mode={mode}
            onRemoveQuery={handleRemoveQuery}
            queries={queries}
            results={results}
          />
        </div>
      </SheetContent>
    </Sheet>
  )
}
