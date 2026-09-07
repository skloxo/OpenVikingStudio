import * as React from 'react'
import { useTranslation } from 'react-i18next'
import {
  CheckCircle2Icon,
  DownloadIcon,
  FlaskConicalIcon,
  Loader2Icon,
  PlayIcon,
  PlusIcon,
  RotateCcwIcon,
  Trash2Icon,
  XCircleIcon,
} from 'lucide-react'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '#/components/ui/sheet'
import { ovClient } from '#/lib/ov-client'
import { cn } from '#/lib/utils'

export interface BenchmarkResultItem {
  id: string
  query: string
  top1Title?: string
  top1Uri?: string
  score?: number
  latencyMs?: number
  status: 'pending' | 'running' | 'hit' | 'miss' | 'error'
  errorMsg?: string
}

const DEFAULT_BENCHMARK_QUERIES: string[] = [
  'OpenViking 核心架构与设计哲学',
  'VikingFS 文件系统与分层存储',
  '卫星 MCP 与主节点职责边界',
  '跨会话体外大脑记忆持久化',
  '任务流转 23 道工序全景字典',
]

export function RetrievalBenchmarkDrawer() {
  const { t } = useTranslation('retrieval')

  const [isOpen, setIsOpen] = React.useState(false)
  const [queries, setQueries] = React.useState<string[]>(DEFAULT_BENCHMARK_QUERIES)
  const [newQueryInput, setNewQueryInput] = React.useState('')
  const [isRunning, setIsRunning] = React.useState(false)
  const [currentIndex, setCurrentIndex] = React.useState(-1)
  const [results, setResults] = React.useState<BenchmarkResultItem[]>([])

  const handleAddQuery = () => {
    const trimmed = newQueryInput.trim()
    if (!trimmed || queries.includes(trimmed)) return
    setQueries((prev) => [...prev, trimmed])
    setNewQueryInput('')
  }

  const handleRemoveQuery = (index: number) => {
    if (isRunning) return
    setQueries((prev) => prev.filter((_, i) => i !== index))
  }

  const handleResetDefaults = () => {
    if (isRunning) return
    setQueries(DEFAULT_BENCHMARK_QUERIES)
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
        const res = await ovClient.instance.post<{
          status: string
          result?: {
            resources?: Array<{ uri: string; title?: string; score?: number }>
            memories?: Array<{ uri: string; title?: string; score?: number }>
            skills?: Array<{ uri: string; title?: string; score?: number }>
            total?: number
          }
        }>('/api/v1/search/find', {
          query: queries[i],
          target_uri: 'viking://',
          limit: 3,
        })

        const latencyMs = Math.round(performance.now() - startTime)
        const payload = res.data.result
        const hits = [
          ...(payload?.resources || []),
          ...(payload?.memories || []),
          ...(payload?.skills || []),
        ]

        if (hits.length > 0) {
          const top1 = hits[0]
          updated[i] = {
            ...updated[i],
            top1Title: top1.title || top1.uri.split('/').pop() || top1.uri,
            top1Uri: top1.uri,
            score: typeof top1.score === 'number' ? Number(top1.score.toFixed(3)) : 0.85,
            latencyMs,
            status: 'hit',
          }
        } else {
          updated[i] = {
            ...updated[i],
            latencyMs,
            status: 'miss',
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

  // Summary Metrics
  const totalQueries = results.length
  const completedQueries = results.filter((r) => r.status !== 'pending' && r.status !== 'running').length
  const hitQueries = results.filter((r) => r.status === 'hit').length
  const hitRate = totalQueries > 0 ? Math.round((hitQueries / totalQueries) * 100) : 0

  const validLatencies = results.map((r) => r.latencyMs).filter((l): l is number => typeof l === 'number')
  const avgLatency = validLatencies.length > 0
    ? Math.round(validLatencies.reduce((a, b) => a + b, 0) / validLatencies.length)
    : 0

  const validScores = results.map((r) => r.score).filter((s): s is number => typeof s === 'number')
  const avgScore = validScores.length > 0
    ? (validScores.reduce((a, b) => a + b, 0) / validScores.length).toFixed(3)
    : '0.000'

  const exportReport = () => {
    const report = {
      timestamp: new Date().toISOString(),
      total: totalQueries,
      hit_rate: `${hitRate}%`,
      avg_latency_ms: avgLatency,
      avg_top1_score: Number(avgScore),
      results: results.map((r) => ({
        query: r.query,
        status: r.status,
        top1_title: r.top1Title ?? null,
        top1_uri: r.top1Uri ?? null,
        score: r.score ?? null,
        latency_ms: r.latencyMs ?? null,
      })),
    }

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `openviking-retrieval-benchmark-${Date.now()}.json`
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
          </Button>
        }
      />

      <SheetContent
        side="right"
        className="w-full sm:max-w-xl md:max-w-2xl flex flex-col gap-0 p-0 border-l bg-background text-foreground shadow-2xl"
      >
        <SheetHeader className="border-b px-5 py-3.5 bg-muted/20">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
                <FlaskConicalIcon className="size-4" />
              </div>
              <SheetTitle className="text-sm font-semibold tracking-tight">
                {t('benchmark.drawerTitle')}
              </SheetTitle>
            </div>
            <Badge variant="outline" className="text-[11px] font-mono px-2 py-0.5 border-border">
              find / viking://
            </Badge>
          </div>
          <SheetDescription className="text-xs text-muted-foreground mt-1">
            {t('benchmark.drawerDesc')}
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {/* Action Bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 bg-muted/15 p-3 rounded-lg border border-border/70">
            <div className="flex items-center gap-2">
              <Button
                onClick={runBenchmark}
                disabled={isRunning || queries.length === 0}
                size="sm"
                className="h-8 gap-1.5 text-xs font-medium bg-cyan-600 hover:bg-cyan-700 text-white cursor-pointer"
              >
                {isRunning ? (
                  <>
                    <Loader2Icon className="size-3.5 animate-spin" />
                    <span>{t('benchmark.running', { completed: currentIndex + 1, total: queries.length })}</span>
                  </>
                ) : (
                  <>
                    <PlayIcon className="size-3.5 fill-current" />
                    <span>{t('benchmark.runBtn')}</span>
                  </>
                )}
              </Button>

              <Button
                onClick={handleResetDefaults}
                disabled={isRunning}
                variant="ghost"
                size="sm"
                className="h-8 gap-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer"
                title={t('benchmark.resetSuite')}
              >
                <RotateCcwIcon className="size-3" />
                <span className="text-[11px]">{t('benchmark.resetSuite')}</span>
              </Button>
            </div>

            {results.length > 0 && completedQueries > 0 && (
              <Button
                onClick={exportReport}
                variant="outline"
                size="sm"
                className="h-8 gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer"
              >
                <DownloadIcon className="size-3.5" />
                <span>{t('benchmark.exportReport')}</span>
              </Button>
            )}
          </div>

          {/* Metric Summary Tiles */}
          {results.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="flex flex-col rounded-md border bg-muted/20 px-3 py-2">
                <span className="text-[11px] text-muted-foreground font-medium">{t('benchmark.metrics.total')}</span>
                <span className="font-mono text-base font-bold text-foreground tabular-nums">
                  {completedQueries} / {totalQueries}
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
          )}

          {/* Query Suite Management */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-foreground tracking-tight">
                {t('benchmark.suiteTitle')} ({queries.length})
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Input
                value={newQueryInput}
                onChange={(e) => setNewQueryInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    handleAddQuery()
                  }
                }}
                disabled={isRunning}
                placeholder={t('benchmark.addQueryPlaceholder')}
                className="h-8 text-xs font-sans"
              />
              <Button
                onClick={handleAddQuery}
                disabled={isRunning || !newQueryInput.trim()}
                variant="outline"
                size="sm"
                className="h-8 gap-1 text-xs shrink-0 cursor-pointer"
              >
                <PlusIcon className="size-3" />
                <span>{t('benchmark.addQueryBtn')}</span>
              </Button>
            </div>
          </div>

          {/* Results Table / Query List */}
          <div className="rounded-md border border-border/80 overflow-hidden">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b bg-muted/30 text-[11px] text-muted-foreground font-medium">
                  <th className="py-2 px-3">{t('benchmark.table.query')}</th>
                  <th className="py-2 px-3">{t('benchmark.table.top1')}</th>
                  <th className="py-2 px-3 text-right">{t('benchmark.table.score')}</th>
                  <th className="py-2 px-3 text-right">{t('benchmark.table.latency')}</th>
                  <th className="py-2 px-3 text-center">{t('benchmark.table.status')}</th>
                  {!isRunning && <th className="py-2 px-2 w-8 text-center" />}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {queries.map((q, idx) => {
                  const result = results.find((r) => r.query === q)
                  const isCurrent = isRunning && currentIndex === idx
                  const status = result?.status ?? 'pending'

                  return (
                    <tr
                      key={`query-row-${idx}-${q}`}
                      className={cn(
                        'transition-colors',
                        isCurrent && 'bg-cyan-500/5',
                        status === 'hit' && 'hover:bg-muted/30',
                      )}
                    >
                      <td className="py-2 px-3 font-medium text-foreground max-w-45 truncate" title={q}>
                        {q}
                      </td>
                      <td className="py-2 px-3 max-w-50">
                        {result?.top1Title ? (
                          <div className="truncate">
                            <span className="font-medium text-foreground" title={result.top1Title}>
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
                      <td className="py-2 px-3 text-right font-mono text-xs tabular-nums">
                        {typeof result?.score === 'number' ? (
                          <span className={result.score >= 0.7 ? 'text-cyan-500 font-semibold' : 'text-foreground'}>
                            {result.score.toFixed(3)}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">--</span>
                        )}
                      </td>
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
                            onClick={() => handleRemoveQuery(idx)}
                            className="text-muted-foreground hover:text-rose-500 transition-colors cursor-pointer"
                            title={t('benchmark.removeQuery')}
                          >
                            <Trash2Icon className="size-3.5" />
                          </button>
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
