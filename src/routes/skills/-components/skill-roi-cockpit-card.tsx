// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ActivityIcon,
  AlertTriangleIcon,
  CheckCircle2Icon,
  ChevronDownIcon,
  ChevronUpIcon,
  LayersIcon,
  RefreshCwIcon,
  ShieldCheckIcon,
  SparklesIcon,
  TrendingUpIcon,
  ZapIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { ovClient } from '#/lib/ov-client'

export interface SkillRoiSummary {
  total_invocations: number
  total_tokens_saved: number
  avg_success_rate: number
  active_skills_count: number
  dormant_skills_count: number
  analyzed_days: number
}

export interface SkillRoiItem {
  skill_id: string
  bundle_name: string
  call_count: number
  success_rate: number
  tokens_saved: number
  avg_latency_ms: number
  last_used_at: string | null
  roi_score: number
  is_dormant?: boolean
}

export interface BundleRoiItem {
  bundle_name: string
  call_count: number
  success_rate: number
  tokens_saved: number
  skill_count: number
  roi_score: number
}

export interface DormantWarning {
  skill_id: string
  days_inactive: number
  reason: string
  suggestion: string
}

export interface SkillRoiData {
  summary: SkillRoiSummary
  top_roi_skills: SkillRoiItem[]
  bundle_rankings: BundleRoiItem[]
  dormant_warnings: DormantWarning[]
}

const DEFAULT_ROI_DATA: SkillRoiData = {
  summary: {
    total_invocations: 0,
    total_tokens_saved: 0,
    avg_success_rate: 1.0,
    active_skills_count: 0,
    dormant_skills_count: 0,
    analyzed_days: 30,
  },
  top_roi_skills: [],
  bundle_rankings: [],
  dormant_warnings: [],
}

export function SkillRoiCockpitCard() {
  const [showDormant, setShowDormant] = React.useState(false)

  const { data, isLoading, isFetching, refetch } = useQuery<SkillRoiData>({
    queryKey: ['skills-telemetry-roi', 30],
    queryFn: async () => {
      try {
        const res = await ovClient.instance.get<{ status: string; result?: SkillRoiData }>(
          '/api/v1/skills/telemetry/roi?days=30'
        )
        return res.data?.result || DEFAULT_ROI_DATA
      } catch {
        return DEFAULT_ROI_DATA
      }
    },
    staleTime: 60_000,
  })

  const telemetry = data || DEFAULT_ROI_DATA
  const { summary, top_roi_skills, bundle_rankings, dormant_warnings } = telemetry

  const formattedTokens = React.useMemo(() => {
    const tokens = summary.total_tokens_saved || 0
    if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`
    if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}k`
    return `${tokens}`
  }, [summary.total_tokens_saved])

  return (
    <div
      data-testid="skill-roi-cockpit"
      className="flex flex-col gap-3 rounded-lg border border-border/80 bg-card p-3 shadow-2xs transition-all"
    >
      {/* 顶部标题栏与全局遥测状态 */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-2.5">
        <div className="flex items-center gap-2">
          <ActivityIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
          <span className="text-xs font-semibold font-mono text-foreground">
            📈 技能中心使用频次遥测与 ROI 价值度量中枢
          </span>
          <Badge
            variant="outline"
            className="text-xs font-mono text-cyan-800 bg-cyan-50 border-cyan-300 dark:text-cyan-300 dark:bg-cyan-950/40 dark:border-cyan-800 font-medium"
          >
            近 30 天滚动采样 (30D Rolling)
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="h-7 px-2.5 text-xs font-mono text-muted-foreground hover:text-foreground cursor-pointer"
          >
            <RefreshCwIcon className={`size-3 mr-1 ${isFetching ? 'animate-spin text-cyan-500' : ''}`} />
            <span>刷新遥测</span>
          </Button>
        </div>
      </div>

      {/* 4 维核心 KPI 瓦片 */}
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        {/* KPI 1: 30天调用总量 */}
        <Card
          data-testid="metric-tile-invocations"
          className="flex flex-col gap-1 p-2.5 shadow-none hover:border-border transition-colors"
        >
          <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
            <span className="flex items-center gap-1.5 text-foreground font-medium">
              <ZapIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              30天调用总量
            </span>
            <Badge variant="outline" className="text-xs font-mono border-border bg-muted/40 text-foreground px-1 py-0">
              唤醒频次
            </Badge>
          </div>
          <div className="font-mono text-lg font-bold tabular-nums text-foreground flex items-baseline gap-1">
            {summary.total_invocations.toLocaleString()}
            <span className="text-xs font-normal text-muted-foreground">次</span>
          </div>
          <p className="text-xs text-muted-foreground truncate font-mono">
            活跃技能覆盖: {summary.active_skills_count} 项
          </p>
        </Card>

        {/* KPI 2: 累计节省 Token */}
        <Card
          data-testid="metric-tile-tokens"
          className="flex flex-col gap-1 p-2.5 shadow-none hover:border-border transition-colors"
        >
          <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
            <span className="flex items-center gap-1.5 text-foreground font-medium">
              <SparklesIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              累计节省 Token
            </span>
            <Badge variant="outline" className="text-xs font-mono border-border bg-muted/40 text-foreground px-1 py-0">
              JIT 效益
            </Badge>
          </div>
          <div className="font-mono text-lg font-bold tabular-nums text-foreground flex items-baseline gap-1">
            {formattedTokens}
            <span className="text-xs font-normal text-muted-foreground">Tokens</span>
          </div>
          <p className="text-xs text-muted-foreground truncate font-mono">
            零全量注入 · 渐进式注脑
          </p>
        </Card>

        {/* KPI 3: 综合执行成功率 */}
        <Card
          data-testid="metric-tile-success-rate"
          className="flex flex-col gap-1 p-2.5 shadow-none hover:border-border transition-colors"
        >
          <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
            <span className="flex items-center gap-1.5 text-foreground font-medium">
              <ShieldCheckIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              综合成功率
            </span>
            <Badge variant="outline" className="text-xs font-mono border-border bg-muted/40 text-foreground px-1 py-0">
              物理闭环
            </Badge>
          </div>
          <div className="font-mono text-lg font-bold tabular-nums text-foreground flex items-baseline gap-1">
            {`${(summary.avg_success_rate * 100).toFixed(1)}%`}
            <span className="text-xs font-normal text-muted-foreground">
              {summary.avg_success_rate >= 0.95 ? '极高契约' : '受控运行'}
            </span>
          </div>
          <p className="text-xs text-muted-foreground truncate font-mono">
            门禁阻断与红绿双验守护
          </p>
        </Card>

        {/* KPI 4: 沉睡工序预警 */}
        <Card
          data-testid="metric-tile-dormant"
          className="flex flex-col gap-1 p-2.5 shadow-none hover:border-border transition-colors"
        >
          <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
            <span className="flex items-center gap-1.5 text-foreground font-medium">
              <AlertTriangleIcon className="size-3.5 text-amber-500" />
              沉睡工序预警
            </span>
            <Badge variant="outline" className="text-xs font-mono border-amber-300 bg-amber-50/70 text-amber-800 dark:border-amber-700/60 dark:bg-amber-950/40 dark:text-amber-200 px-1 py-0">
              待激活
            </Badge>
          </div>
          <div className="font-mono text-lg font-bold tabular-nums text-foreground flex items-baseline gap-1">
            {summary.dormant_skills_count}
            <span className="text-xs font-normal text-muted-foreground">项工序</span>
          </div>
          <p className="text-xs text-muted-foreground truncate font-mono">
            {summary.dormant_skills_count > 0 ? '建议母包归档或熔炼' : '全域工序处于活跃态'}
          </p>
        </Card>
      </div>

      {/* Top ROI 领域母包推荐与单体技能排行榜 */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {/* 左侧：领域母包排行榜 */}
        <div className="rounded border border-border/70 bg-muted/15 p-2.5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5">
              <LayersIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              <span className="text-xs font-semibold font-mono text-foreground">
                🏆 Top 领域母包 ROI 排名
              </span>
            </div>
            <span className="text-xs font-mono text-muted-foreground">频次 × 成功率 × 节省Token</span>
          </div>

          <div className="flex flex-col gap-1.5">
            {bundle_rankings.length === 0 ? (
              <div className="py-4 text-center text-xs font-mono text-muted-foreground">
                暂无母包遥测数据
              </div>
            ) : (
              bundle_rankings.slice(0, 5).map((bundle, idx) => (
                <div
                  key={bundle.bundle_name}
                  className="flex items-center justify-between rounded border border-border/50 bg-card px-2.5 py-1 text-xs font-mono"
                >
                  <div className="flex items-center gap-2 truncate">
                    <span className="font-semibold text-cyan-700 dark:text-cyan-400">
                      #{idx + 1}
                    </span>
                    <span className="font-medium text-foreground truncate">
                      {bundle.bundle_name}
                    </span>
                    <Badge variant="outline" className="text-xs font-mono px-1 py-0 text-muted-foreground">
                      {bundle.skill_count}工序
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-muted-foreground">{bundle.call_count} 次</span>
                    <span className="text-muted-foreground">
                      {(bundle.success_rate * 100).toFixed(0)}% 成功
                    </span>
                    <Badge className="bg-cyan-100 text-cyan-800 dark:bg-cyan-950/60 dark:text-cyan-200 border border-cyan-300 dark:border-cyan-800 text-xs font-mono font-semibold px-1.5 py-0">
                      {bundle.roi_score.toFixed(1)} 分
                    </Badge>
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="mt-2 text-xs font-mono text-muted-foreground/80 flex items-center gap-1">
            <CheckCircle2Icon className="size-3 text-cyan-600 dark:text-cyan-400" />
            <span>高频领域母包自动置顶推荐并参与 JIT 预热</span>
          </div>
        </div>

        {/* 右侧：单体工序排行榜 */}
        <div className="rounded border border-border/70 bg-muted/15 p-2.5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5">
              <TrendingUpIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              <span className="text-xs font-semibold font-mono text-foreground">
                ⚡ Top 5 高频工序 ROI 标杆
              </span>
            </div>
            <span className="text-xs font-mono text-muted-foreground">动态加权归一化 (0~100)</span>
          </div>

          <div className="flex flex-col gap-1.5">
            {top_roi_skills.length === 0 ? (
              <div className="py-4 text-center text-xs font-mono text-muted-foreground">
                暂无工序遥测数据
              </div>
            ) : (
              top_roi_skills.slice(0, 5).map((skill, idx) => (
                <div
                  key={skill.skill_id}
                  className="flex items-center justify-between rounded border border-border/50 bg-card px-2.5 py-1 text-xs font-mono"
                >
                  <div className="flex items-center gap-2 truncate">
                    <span className="font-semibold text-cyan-700 dark:text-cyan-400">
                      #{idx + 1}
                    </span>
                    <span className="font-medium text-foreground truncate">{skill.skill_id}</span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-muted-foreground">{skill.call_count} 次</span>
                    <span className="text-muted-foreground">{skill.tokens_saved} tok</span>
                    <Badge className="bg-cyan-100 text-cyan-800 dark:bg-cyan-950/60 dark:text-cyan-200 border border-cyan-300 dark:border-cyan-800 text-xs font-mono font-semibold px-1.5 py-0">
                      {skill.roi_score.toFixed(1)} 分
                    </Badge>
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="mt-2 text-xs font-mono text-muted-foreground/80 flex items-center gap-1">
            <CheckCircle2Icon className="size-3 text-cyan-600 dark:text-cyan-400" />
            <span>自动反哺 /api/v1/skills 排序引擎</span>
          </div>
        </div>
      </div>

      {/* 沉睡工序预警折叠面板 */}
      {dormant_warnings.length > 0 && (
        <div className="rounded border border-amber-300/80 bg-amber-50/50 dark:border-amber-700/60 dark:bg-amber-950/20 px-3 py-2 text-xs font-mono">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-amber-800 dark:text-amber-200">
              <AlertTriangleIcon className="size-3.5 text-amber-500" />
              <span className="font-semibold">
                ⚠️ 检测到 {dormant_warnings.length} 项工序在过去 30 天内零唤醒调用 (Dormant)
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDormant((prev) => !prev)}
              className="h-6 px-2 text-xs font-mono text-amber-800 border-amber-300 hover:bg-amber-100 dark:text-amber-200 dark:border-amber-700 dark:hover:bg-amber-950/60 cursor-pointer"
            >
              {showDormant ? (
                <>
                  收起明细 <ChevronUpIcon className="size-3 ml-1" />
                </>
              ) : (
                <>
                  查看沉睡工序 <ChevronDownIcon className="size-3 ml-1" />
                </>
              )}
            </Button>
          </div>

          {showDormant && (
            <div className="mt-2.5 pt-2 border-t border-amber-200 dark:border-amber-800/60 flex flex-col gap-1.5">
              <div className="text-muted-foreground text-xs mb-1">
                以下工序长期未被任何 Agent 隐式或显式唤醒，建议核验其关键词触发规则，或归并至父母包/下线归档：
              </div>
              <div className="max-h-48 overflow-y-auto flex flex-col gap-1">
                {dormant_warnings.map((dw) => (
                  <div
                    key={dw.skill_id}
                    className="flex items-center justify-between bg-card/80 border border-border/60 rounded px-2 py-1 text-xs font-mono"
                  >
                    <span className="font-medium text-foreground">{dw.skill_id}</span>
                    <span className="text-muted-foreground">{dw.suggestion}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
