// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  ActivityIcon,
  CheckCircleIcon,
  ClockIcon,
  FlaskConicalIcon,
  ListChecksIcon,
  PlayIcon,
  XCircleIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface JudgeResult {
  case_id: string
  skill_name: string
  judge_type: string
  verdict: 'pass' | 'fail' | 'skip'
  actual: string | null
  expected: string | null
  error: string | null
  duration_ms: number
}

interface EvalRunResult {
  run_id: string
  skill_name: string
  started_at: string
  finished_at: string | null
  total: number
  passed: number
  failed: number
  skipped: number
  pass_rate: number
  results: JudgeResult[]
  status: string
}

interface EvalSummary {
  total_cases: number
  total_runs: number
  global_pass_rate: number
  last_run_at: string | null
  skills_evaluated: string[]
  recent_runs: EvalRunResult[]
}

// ---------------------------------------------------------------------------
// KPI Tile (Dual-Theme Semantic Design)
// ---------------------------------------------------------------------------

interface KpiTileProps {
  icon: React.ElementType
  label: string
  value: string | number
  sub?: string
  accent?: boolean
  warn?: boolean
}

function KpiTile({ icon: Icon, label, value, sub, accent, warn }: KpiTileProps) {
  const valueColor = warn
    ? 'text-rose-600 dark:text-rose-400'
    : accent
      ? 'text-cyan-600 dark:text-cyan-400'
      : 'text-foreground'

  return (
    <div className="flex flex-col gap-1 rounded-md border border-border/70 bg-card p-3 shadow-xs">
      <div className="flex items-center gap-1.5 text-muted-foreground">
        <Icon className="size-3 shrink-0" />
        <span className="text-xs truncate">{label}</span>
      </div>
      <p className={`text-base font-mono font-semibold tabular-nums ${valueColor}`}>{value}</p>
      {sub && <p className="text-xs text-muted-foreground truncate">{sub}</p>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Verdict Badge
// ---------------------------------------------------------------------------

function VerdictBadge({ verdict }: { verdict: string }) {
  if (verdict === 'pass') {
    return (
      <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-mono bg-cyan-100/70 dark:bg-cyan-950/40 text-cyan-800 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-800/40">
        <CheckCircleIcon className="size-2.5" />
        PASS
      </span>
    )
  }
  if (verdict === 'fail') {
    return (
      <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-mono bg-rose-100/70 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-800/40">
        <XCircleIcon className="size-2.5" />
        FAIL
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-mono bg-muted text-muted-foreground border border-border/60">
      SKIP
    </span>
  )
}

// ---------------------------------------------------------------------------
// Result Row
// ---------------------------------------------------------------------------

function ResultRow({ r }: { r: JudgeResult }) {
  const [expanded, setExpanded] = React.useState(false)

  return (
    <div className="border-b border-border/40 last:border-0">
      <button
        type="button"
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-muted/40 transition-colors cursor-pointer"
        onClick={() => setExpanded((v) => !v)}
      >
        <VerdictBadge verdict={r.verdict} />
        <span className="text-xs font-mono text-muted-foreground shrink-0 w-24 truncate">{r.skill_name}</span>
        <span className="flex-1 text-xs text-foreground truncate">{r.case_id}</span>
        <span className="text-xs font-mono text-muted-foreground shrink-0">{r.duration_ms.toFixed(1)}ms</span>
        <span className="text-xs text-muted-foreground shrink-0 capitalize">{r.judge_type}</span>
      </button>
      {expanded && (r.error || r.actual) && (
        <div className="px-3 pb-2 text-xs font-mono space-y-1">
          {r.error && (
            <p className="text-rose-600 dark:text-rose-400 break-all">{r.error}</p>
          )}
          {r.actual && (
            <p className="text-muted-foreground break-all line-clamp-3">{r.actual}</p>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function SkillEvalCockpit() {
  const [latestRun, setLatestRun] = React.useState<EvalRunResult | null>(null)

  const { data: summary, refetch: refetchSummary } = useQuery<EvalSummary>({
    queryKey: ['skill-eval-summary'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/skill-eval/summary')
      return (res as { data: EvalSummary }).data
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    staleTime: 10_000,
  })

  const runMut = useMutation({
    mutationFn: async (skillName: string) => {
      const res = await ovClient.instance.post(`/api/v1/skill-eval/run?skill_name=${skillName}`)
      return (res as { data: EvalRunResult }).data
    },
    onSuccess: (data) => {
      setLatestRun(data)
      void refetchSummary()
    },
  })

  const passRate = summary?.global_pass_rate ?? 0
  const passPercent = `${(passRate * 100).toFixed(1)}%`
  const lastRunStr = summary?.last_run_at
    ? new Date(summary.last_run_at).toLocaleString()
    : '--'

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FlaskConicalIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
          <h2 className="text-sm font-semibold text-foreground">
            {'技能质量视网膜与自动化评测'}
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs"
            disabled={runMut.isPending}
            onClick={() => runMut.mutate('*')}
          >
            <PlayIcon className="size-3 mr-1" />
            {runMut.isPending ? '评测执行中…' : '▶ 运行全量评测'}
          </Button>
        </div>
      </div>

      {/* KPI Tiles */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <KpiTile
          icon={ActivityIcon}
          label={'全局通过率'}
          value={passPercent}
          accent={passRate > 0.8}
          warn={passRate > 0 && passRate < 0.6}
          sub={`${summary?.total_runs ?? '--'} 次评测`}
        />
        <KpiTile
          icon={ListChecksIcon}
          label={'已注册用例数'}
          value={summary?.total_cases ?? '--'}
          sub={'声明式 YAML 用例'}
        />
        <KpiTile
          icon={ClockIcon}
          label={'最后评测时间'}
          value={lastRunStr}
          sub={summary?.total_runs ? `第 ${summary.total_runs} 次` : '从未运行'}
        />
        <KpiTile
          icon={FlaskConicalIcon}
          label={'已评测技能'}
          value={summary?.skills_evaluated.length ?? '--'}
          sub={summary?.skills_evaluated.slice(0, 2).join(', ') ?? '--'}
        />
      </div>

      {/* Latest Run Results */}
      {latestRun && (
        <div className="rounded-md border border-border/70 bg-card">
          <div className="flex items-center gap-2 border-b border-border/50 px-3 py-2">
            <FlaskConicalIcon className="size-3 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">
              {`本次评测 #${latestRun.run_id} · ${latestRun.passed}/${latestRun.total} 通过`}
            </span>
            <span className={`ml-auto text-xs font-mono font-semibold ${latestRun.failed > 0 ? 'text-rose-600 dark:text-rose-400' : 'text-cyan-600 dark:text-cyan-400'}`}>
              {(latestRun.pass_rate * 100).toFixed(1)}%
            </span>
          </div>
          <div className="divide-y divide-border/30">
            {latestRun.results.map((r) => (
              <ResultRow key={`${r.skill_name}-${r.case_id}`} r={r} />
            ))}
          </div>
        </div>
      )}

      {/* Recent Runs History */}
      {!latestRun && summary?.recent_runs && summary.recent_runs.length > 0 && (
        <div className="rounded-md border border-border/70 bg-card">
          <div className="flex items-center gap-2 border-b border-border/50 px-3 py-2">
            <ClockIcon className="size-3 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">{'最近历史评测'}</span>
          </div>
          <div className="divide-y divide-border/30">
            {summary.recent_runs.slice(-5).reverse().map((run) => (
              <div key={run.run_id} className="flex items-center gap-2 px-3 py-2">
                <span className={`text-xs font-mono font-semibold ${run.failed > 0 ? 'text-rose-600 dark:text-rose-400' : 'text-cyan-600 dark:text-cyan-400'}`}>
                  {(run.pass_rate * 100).toFixed(1)}%
                </span>
                <span className="text-xs text-muted-foreground">
                  {`${run.passed}/${run.total}`}
                </span>
                <span className="flex-1 text-xs text-muted-foreground font-mono truncate">
                  {run.skill_name === '*' ? '全部技能' : run.skill_name}
                </span>
                <span className="text-xs text-muted-foreground">
                  {run.finished_at ? new Date(run.finished_at).toLocaleTimeString() : '--'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!latestRun && (!summary || summary.total_runs === 0) && (
        <div className="flex flex-col items-center justify-center gap-3 py-10 text-muted-foreground border border-dashed border-border/70 rounded-md bg-muted/10">
          <FlaskConicalIcon className="size-8 text-muted-foreground/60" />
          <p className="text-xs">{'尚无评测历史，点击「运行全量评测」开始'}</p>
        </div>
      )}
    </div>
  )
}
