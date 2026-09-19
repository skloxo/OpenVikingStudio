// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ActivityIcon,
  CheckCircleIcon,
  GitForkIcon,
  PlayIcon,
  RefreshCwIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CandidateRulePatch {
  patch_id: string
  rule_content: string
  applicable_scenario: string
  bifurcation_id: string
  derived_from_turn: number
  created_at: number
  verified_green: boolean
  verification_notes: string
}

interface ReexecutionResult {
  patch_id: string
  task_id: string
  student_model_id: string
  turned_green: boolean
  exit_code: number
  failing_assertions_remaining: number
  execution_time_sec: number
  gate_verdict: 'ACCEPTED' | 'REJECTED'
  rejection_reason?: string
}

interface ConsolidationSummary {
  initial_rule_count: number
  consolidated_rule_count: number
  compression_ratio_pct: number
  total_lines: number
  within_sweet_spot: boolean
  consolidated_rules: CandidateRulePatch[]
}

interface SkillKDMetrics {
  total_candidate_rules: number
  total_reexecutions: number
  turned_green_count: number
  reexecution_pass_rate_pct: number
  verified_rules_in_store: number
  estimated_rule_lines: number
  sweet_spot_compliant: boolean
}

// ---------------------------------------------------------------------------
// KPI Tile
// ---------------------------------------------------------------------------

function KpiTile({
  icon: Icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: React.ElementType
  label: string
  value: string | number
  sub?: string
  accent?: boolean
}) {
  return (
    <div className="flex flex-col gap-1 rounded-md border border-slate-700/60 bg-slate-800/50 p-3">
      <div className="flex items-center gap-1.5 text-slate-400">
        <Icon className="size-3.5 shrink-0" />
        <span className="text-xs truncate">{label}</span>
      </div>
      <div
        className={`text-lg font-bold font-mono tabular-nums ${
          accent ? 'text-cyan-400' : 'text-slate-100'
        }`}
      >
        {value}
      </div>
      {sub && <span className="text-xs text-slate-400">{sub}</span>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Cockpit Component
// ---------------------------------------------------------------------------

export function SkillKDCockpit() {
  const queryClient = useQueryClient()
  const activeTaskScenario = 'asyncio_concurrency'

  // 1. Fetch Metrics
  const { data: metrics } = useQuery<SkillKDMetrics>({
    queryKey: ['skill-kd-metrics'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/skill-kd/metrics')
      return (res as { data: SkillKDMetrics }).data
    },
    refetchInterval: 10000,
  })

  // 2. Fetch Rules
  const { data: rules = [], isLoading: isRulesLoading } = useQuery<CandidateRulePatch[]>({
    queryKey: ['skill-kd-rules'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/skill-kd/rules')
      return (res as { data: CandidateRulePatch[] }).data
    },
  })

  // 3. Re-execution Mutation
  const reexecuteMutation = useMutation<ReexecutionResult, Error, string>({
    mutationFn: async (patchId: string) => {
      const res = await ovClient.instance.post('/api/v1/skill-kd/reexecute', {
        patch_id: patchId,
        task_id: 'task_sandbox_verify',
        student_model_id: 'student_local_7b',
      })
      return (res as { data: ReexecutionResult }).data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skill-kd-metrics'] })
      queryClient.invalidateQueries({ queryKey: ['skill-kd-rules'] })
    },
  })

  // 4. Consolidate Mutation
  const consolidateMutation = useMutation<ConsolidationSummary, Error, void>({
    mutationFn: async () => {
      const res = await ovClient.instance.post('/api/v1/skill-kd/rules/consolidate', {
        max_lines_limit: 300,
      })
      return (res as { data: ConsolidationSummary }).data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skill-kd-metrics'] })
      queryClient.invalidateQueries({ queryKey: ['skill-kd-rules'] })
    },
  })

  return (
    <div className="flex flex-col gap-3 text-slate-200">
      {/* 4 KPI Tiles */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <KpiTile
          icon={GitForkIcon}
          label="分叉决策提炼数"
          value={metrics?.total_candidate_rules ?? '--'}
          sub="师生分叉点提纯"
          accent
        />
        <KpiTile
          icon={ShieldCheckIcon}
          label="重跑变绿通过率"
          value={metrics ? `${metrics.reexecution_pass_rate_pct.toFixed(1)}%` : '--'}
          sub={`累计沙箱验证 ${metrics?.total_reexecutions ?? 0} 次`}
          accent
        />
        <KpiTile
          icon={CheckCircleIcon}
          label="准入高精纯规则"
          value={metrics?.verified_rules_in_store ?? '--'}
          sub="严禁未经验证反思入库"
        />
        <KpiTile
          icon={ActivityIcon}
          label="规则黄金甜点区"
          value={metrics ? `${metrics.estimated_rule_lines} 行` : '--'}
          sub={metrics?.sweet_spot_compliant ? '合规 (<= 300行)' : '需压缩'}
        />
      </div>

      {/* Main Dual Panels */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {/* Panel 1: Teacher-Student Bifurcations & Candidate Rules */}
        <div className="flex flex-col gap-2 rounded-md border border-slate-700/60 bg-slate-800/40 p-3">
          <div className="flex items-center justify-between border-b border-slate-700/40 pb-2">
            <div className="flex items-center gap-2">
              <GitForkIcon className="size-3.5 text-cyan-400" />
              <span className="text-xs font-semibold text-slate-100">
                师生决策分叉点与候选规则 (SKILL-KD)
              </span>
            </div>
            <span className="text-xs text-slate-400">
              场景: <span className="text-cyan-400 font-mono">{activeTaskScenario}</span>
            </span>
          </div>

          <div className="flex flex-col gap-2 max-h-115 overflow-y-auto pr-1">
            {isRulesLoading ? (
              <div className="py-8 text-center text-xs text-slate-400">正在加载分叉规则...</div>
            ) : rules.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-400">暂无候选规则</div>
            ) : (
              rules.map((rule) => (
                <div
                  key={rule.patch_id}
                  className="flex flex-col gap-1.5 rounded border border-slate-700/50 bg-slate-900/60 p-2.5"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-xs text-slate-400">{rule.patch_id}</span>
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-xs text-cyan-400 font-mono">
                        Turn #{rule.derived_from_turn}
                      </span>
                    </div>
                    {rule.verified_green ? (
                      <span className="rounded bg-cyan-950/40 border border-cyan-800/40 px-1.5 py-0.5 text-xs text-cyan-300 font-semibold">
                        已变绿准入
                      </span>
                    ) : (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 px-2 text-xs text-slate-300 hover:text-cyan-300"
                        onClick={() => reexecuteMutation.mutate(rule.patch_id)}
                        disabled={reexecuteMutation.isPending}
                      >
                        <PlayIcon className="mr-1 size-3" />
                        沙箱重跑验证
                      </Button>
                    )}
                  </div>

                  <p className="text-xs text-slate-200 font-mono bg-slate-950/40 p-2 rounded border border-slate-800">
                    {rule.rule_content}
                  </p>

                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>适用场景: {rule.applicable_scenario}</span>
                    <span>{rule.verification_notes || '待沙箱物理验证'}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Panel 2: Re-execution Sandbox Gate & Consolidation */}
        <div className="flex flex-col gap-2 rounded-md border border-slate-700/60 bg-slate-800/40 p-3">
          <div className="flex items-center justify-between border-b border-slate-700/40 pb-2">
            <div className="flex items-center gap-2">
              <ShieldAlertIcon className="size-3.5 text-cyan-400" />
              <span className="text-xs font-semibold text-slate-100">
                沙箱重跑变绿门禁与规则合并 (VeriSkill)
              </span>
            </div>
            <Button
              size="sm"
              variant="outline"
              className="h-6 px-2 text-xs border-slate-700 text-slate-300 hover:text-cyan-300"
              onClick={() => consolidateMutation.mutate()}
              disabled={consolidateMutation.isPending}
            >
              <RefreshCwIcon className="mr-1 size-3" />
              规则去重合并
            </Button>
          </div>

          {/* Verification / Consolidation Display */}
          <div className="flex flex-col gap-2 rounded border border-slate-700/50 bg-slate-900/60 p-2.5 min-h-75 overflow-y-auto">
            {reexecuteMutation.data ? (
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                  <div className="flex items-center gap-1.5">
                    {reexecuteMutation.data.turned_green ? (
                      <CheckCircleIcon className="size-3.5 text-cyan-400" />
                    ) : (
                      <ShieldAlertIcon className="size-3.5 text-rose-400" />
                    )}
                    <span className="text-xs font-semibold text-slate-200">
                      沙箱门禁裁决:{' '}
                      <span
                        className={
                          reexecuteMutation.data.turned_green ? 'text-cyan-300' : 'text-rose-400'
                        }
                      >
                        {reexecuteMutation.data.gate_verdict}
                      </span>
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                    <span>耗时: {reexecuteMutation.data.execution_time_sec}s</span>
                    <span>Exit Code: {reexecuteMutation.data.exit_code}</span>
                  </div>
                </div>

                <div className="flex flex-col gap-1 text-xs text-slate-300">
                  <p>
                    测试用例状态:{' '}
                    {reexecuteMutation.data.turned_green ? (
                      <span className="text-cyan-300 font-bold">
                        原题红变绿 (Turned Green) ✅ 准入入库
                      </span>
                    ) : (
                      <span className="text-rose-400 font-bold">
                        仍未变绿 (Turn Red) 🚫 物理阻断入库
                      </span>
                    )}
                  </p>
                  {reexecuteMutation.data.rejection_reason && (
                    <p className="text-rose-400">
                      拒绝理由: {reexecuteMutation.data.rejection_reason}
                    </p>
                  )}
                </div>
              </div>
            ) : consolidateMutation.data ? (
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                  <span className="text-xs font-semibold text-slate-200">
                    规则合并完成 (Drift-Aware Consolidation)
                  </span>
                  <span className="text-xs font-mono text-cyan-400">
                    压缩率: {consolidateMutation.data.compression_ratio_pct}%
                  </span>
                </div>
                <div className="flex flex-col gap-1 text-xs text-slate-300">
                  <p>
                    规则条数: {consolidateMutation.data.initial_rule_count} 条 ➔{' '}
                    {consolidateMutation.data.consolidated_rule_count} 条
                  </p>
                  <p>
                    预估总行数: {consolidateMutation.data.total_lines} 行 (
                    {consolidateMutation.data.within_sweet_spot ? '符合 <=300 行黄金甜点区' : '超出'}
                    )
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-48 text-center text-xs text-slate-500">
                <SparklesIcon className="size-6 mb-2 text-slate-600" />
                <span>
                  点击左侧候选规则的「沙箱重跑验证」，体验弱学生携带规则原题红变绿的准入过程
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
