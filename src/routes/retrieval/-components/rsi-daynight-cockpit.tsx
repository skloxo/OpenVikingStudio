// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ActivityIcon,
  CheckCircleIcon,
  CodeIcon,
  MoonIcon,
  PlayIcon,
  RefreshCwIcon,
  ShieldCheckIcon,
  SunIcon,
  ZapIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RSISummary {
  current_phase: 'daytime_collection' | 'nighttime_dreaming'
  phase_switched_at: number
  total_trajectories_collected: number
  total_turns_collected: number
  total_credit_evaluations: number
  dual_split_verifications: number
  gate_pass_rate: number
}

interface DualSplitResult {
  passed: boolean
  train_pass_rate: number
  holdout_pass_rate: number
  baseline_holdout_pass_rate: number
  regression_detected: boolean
  details: string
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
    <div className="flex flex-col gap-1 rounded-md border border-border/70 bg-card p-3 shadow-xs">
      <div className="flex items-center gap-1.5 text-muted-foreground">
        <Icon className="size-3.5 shrink-0" />
        <span className="text-xs truncate">{label}</span>
      </div>
      <p className={`text-base font-mono font-semibold tabular-nums ${accent ? 'text-cyan-600 dark:text-cyan-400' : 'text-foreground'}`}>
        {value}
      </p>
      {sub && <p className="text-xs text-muted-foreground truncate">{sub}</p>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Cockpit Component
// ---------------------------------------------------------------------------

export function RSIDayNightCockpit() {
  const queryClient = useQueryClient()

  // 1. 全局统计
  const summaryQuery = useQuery<RSISummary>({
    queryKey: ['rsi', 'status'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/rsi/status')
      return (res as { data: RSISummary }).data
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  })

  // 2. 昼夜模式切换
  const switchPhaseMutation = useMutation({
    mutationFn: async () => {
      const res = await ovClient.instance.post('/api/v1/rsi/phase/switch', {})
      return (res as { data: unknown }).data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rsi'] })
    },
  })

  // 3. 双 Split 门禁测试
  const [gateResult, setGateResult] = React.useState<DualSplitResult | null>(null)
  const verifyGateMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        train_results: [true, true, true, true],
        holdout_results: [true, true, true, false, true],
        baseline_holdout_pass_rate: 0.8,
      }
      const res = await ovClient.instance.post('/api/v1/rsi/gate/verify_split', payload)
      return (res as { data: DualSplitResult }).data
    },
    onSuccess: (data) => {
      setGateResult(data)
      queryClient.invalidateQueries({ queryKey: ['rsi'] })
    },
  })

  const summary = summaryQuery.data
  const isDaytime = summary?.current_phase === 'daytime_collection'

  return (
    <div className="flex flex-col gap-4">
      {/* 头部标题与模式切换按钮 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
            {isDaytime ? (
              <SunIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
            ) : (
              <MoonIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
            )}
            RSI 昼夜双轮与可训练技能策略座舱
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Skill-MDP 外部策略 · # EVOLVE-BLOCK 有界可编辑 · AgentOPSD 局部信用 · 双 Split 零退化
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={switchPhaseMutation.isPending}
            onClick={() => switchPhaseMutation.mutate()}
            className="text-xs h-7 gap-1 border-cyan-300 dark:border-cyan-800/60 bg-cyan-50 dark:bg-cyan-950/40 hover:bg-cyan-100 dark:hover:bg-cyan-900/50 text-cyan-800 dark:text-cyan-300 cursor-pointer"
          >
            {isDaytime ? <MoonIcon className="size-3" /> : <SunIcon className="size-3" />}
            切换至 {isDaytime ? '夜间离线自演进' : '白昼轨迹收集'}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['rsi'] })}
            className="text-xs h-7 gap-1"
          >
            <RefreshCwIcon className="size-3" />
            刷新
          </Button>
        </div>
      </div>

      {/* 4 块 KPI 瓦片 */}
      <div className="grid grid-cols-4 gap-3">
        <KpiTile
          icon={isDaytime ? SunIcon : MoonIcon}
          label="当前演进阶段"
          value={isDaytime ? '白昼轨迹收集' : '夜间离线优化'}
          sub={isDaytime ? '确定性执行 · 收集真实轨迹' : '弱点聚类 · 局部信用分配'}
          accent
        />
        <KpiTile
          icon={ActivityIcon}
          label="收集轨迹回合数"
          value={summary?.total_turns_collected ?? '--'}
          sub={`累计会话: ${summary?.total_trajectories_collected ?? '--'}`}
        />
        <KpiTile
          icon={ZapIcon}
          label="局部信用评估数"
          value={summary?.total_credit_evaluations ?? '--'}
          sub="AgentOPSD 关键回合标定"
          accent
        />
        <KpiTile
          icon={ShieldCheckIcon}
          label="双 Split 门禁通过率"
          value={summary ? `${Math.round(summary.gate_pass_rate * 100)}%` : '--'}
          sub={`验证次数: ${summary?.dual_split_verifications ?? '--'} · 零退化硬门禁`}
          accent
        />
      </div>

      {/* 主体并排卡片 */}
      <div className="grid grid-cols-2 gap-3">
        {/* 左栏: 局部信用分配与关键回合标定 */}
        <div className="rounded-md border border-border/70 bg-card p-3 flex flex-col gap-2 shadow-xs">
          <div className="flex items-center justify-between pb-1 border-b border-border/50">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <ZapIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              AgentOPSD 局部信用分配机制 (Local Credit Assignment)
            </span>
          </div>

          <div className="text-xs text-muted-foreground leading-relaxed">
            通过计算 Student 在无技能下的 Rollout 轨迹与携带技能的 Self-Teacher 之间的期望对数概率差值 (
            <span className="font-mono text-cyan-700 dark:text-cyan-400">gap = teacher - student</span>
            )，仅将演进微补丁精确限制在诱发失误的关键 Seam，防止全局过度拟合。
          </div>

          <div className="rounded border border-border/60 bg-muted/30 p-2 flex flex-col gap-1.5">
            <div className="text-xs font-mono text-cyan-700 dark:text-cyan-300 font-semibold flex items-center justify-between">
              <span>Turn 1 [关键回合 · Critical Turn]</span>
              <span className="text-rose-600 dark:text-rose-400">Gap: +2.50</span>
            </div>
            <div className="text-xs text-muted-foreground font-mono bg-muted/60 p-1.5 rounded">
              Student: 手搓冒泡排序 (缺少流程指南)
              <br />
              Teacher: 调用原生高效排序接口
            </div>
          </div>

          <div className="rounded border border-border/60 bg-muted/30 p-2 flex flex-col gap-1.5">
            <div className="text-xs font-mono text-muted-foreground flex items-center justify-between">
              <span>Turn 2 [普通回合]</span>
              <span className="text-muted-foreground">Gap: +0.02</span>
            </div>
            <div className="text-xs text-muted-foreground font-mono bg-muted/60 p-1.5 rounded">
              执行结果提取与常规返回 (无需打补丁)
            </div>
          </div>
        </div>

        {/* 右栏: # EVOLVE-BLOCK 有界 Surface 与双 Split 门禁 */}
        <div className="rounded-md border border-border/70 bg-card p-3 flex flex-col gap-2 shadow-xs">
          <div className="flex items-center justify-between pb-1 border-b border-border/50">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <CodeIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              # EVOLVE-BLOCK 有界 Surface & 双 Split 门禁
            </span>
            <Button
              size="sm"
              variant="outline"
              disabled={verifyGateMutation.isPending}
              onClick={() => verifyGateMutation.mutate()}
              className="h-6 px-2 text-xs border-cyan-300 dark:border-cyan-800/60 bg-cyan-50 dark:bg-cyan-950/40 text-cyan-800 dark:text-cyan-300 hover:bg-cyan-100 dark:hover:bg-cyan-900/50"
            >
              <PlayIcon className="size-2.5 mr-1" />
              测试门禁
            </Button>
          </div>

          <div className="text-xs font-mono bg-muted/50 border border-border/60 p-2 rounded text-foreground">
            <span className="text-muted-foreground"># 冻结区: 系统架构与强类型接口</span>
            <br />
            <span className="text-cyan-600 dark:text-cyan-400 font-semibold"># EVOLVE-BLOCK-START</span>
            <br />
            <span className="text-foreground">
              def execute_policy(ctx):
              <br />
              &nbsp;&nbsp;&nbsp;&nbsp;# 仅此区域允许夜间递归自演进
              <br />
              &nbsp;&nbsp;&nbsp;&nbsp;return optimize_step(ctx)
            </span>
            <br />
            <span className="text-cyan-600 dark:text-cyan-400 font-semibold"># EVOLVE-BLOCK-END</span>
            <br />
            <span className="text-muted-foreground"># 冻结区: YAML Frontmatter 与门禁契约</span>
          </div>

          {gateResult && (
            <div
              className={`rounded border p-2 text-xs flex flex-col gap-1 ${
                gateResult.passed
                  ? 'border-cyan-300 dark:border-cyan-800/50 bg-cyan-50 dark:bg-cyan-950/30 text-cyan-800 dark:text-cyan-300'
                  : 'border-rose-300 dark:border-rose-800/50 bg-rose-50 dark:bg-rose-950/30 text-rose-800 dark:text-rose-300'
              }`}
            >
              <div className="font-semibold flex items-center gap-1">
                <CheckCircleIcon className="size-3" />
                {gateResult.details}
              </div>
              <div className="font-mono text-muted-foreground">
                Train: {(gateResult.train_pass_rate * 100).toFixed(1)}% · Holdout:{' '}
                {(gateResult.holdout_pass_rate * 100).toFixed(1)}% · 零退化检测:{' '}
                {gateResult.regression_detected ? 'FAIL' : 'PASS'}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
