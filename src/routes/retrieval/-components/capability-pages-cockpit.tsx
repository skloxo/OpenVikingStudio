// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ActivityIcon,
  CheckCircleIcon,
  CompassIcon,
  FilterIcon,
  LayersIcon,
  PlayIcon,
  RefreshCwIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DiscriminativeBody {
  summary: string
  prerequisites: string[]
  inputs: Record<string, string>
  outputs: Record<string, string>
}

interface CapabilityPage {
  skill_id: string
  skill_name: string
  cluster_id: string
  positive_triggers: string[]
  negative_boundaries: string[]
  discriminative_body: DiscriminativeBody
}

interface CandidateAdjudication {
  skill_id: string
  skill_name: string
  stage1_score: number
  violated_boundaries: string[]
  negative_penalty: number
  final_score: number
  is_blocked: boolean
  verdict_reason: string
}

interface RouteDecision {
  query: string
  selected_skill_id: string | null
  selected_skill_name: string | null
  confidence: number
  candidates: CandidateAdjudication[]
  latency_ms: number
  cluster_id: string | null
}

interface RouterMetrics {
  total_routes: number
  boundary_interceptions: number
  interception_rate_pct: number
  top1_discrimination_gain_pct: number
  total_capability_pages: number
  total_clusters: number
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

export function CapabilityPagesCockpit() {
  const queryClient = useQueryClient()
  const [selectedCluster, setSelectedCluster] = React.useState<string>('all')
  const [routeQueryText, setRouteQueryText] = React.useState<string>('重启容器')

  // 1. Fetch Metrics
  const { data: metrics } = useQuery<RouterMetrics>({
    queryKey: ['capability-router-metrics'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/capability-pages/metrics/summary')
      return (res as { data: RouterMetrics }).data
    },
    refetchInterval: 10000,
  })

  // 2. Fetch Capability Pages
  const { data: pages = [], isLoading: isPagesLoading } = useQuery<CapabilityPage[]>({
    queryKey: ['capability-pages', selectedCluster],
    queryFn: async () => {
      const url =
        selectedCluster === 'all'
          ? '/api/v1/capability-pages'
          : `/api/v1/capability-pages?cluster_id=${selectedCluster}`
      const res = await ovClient.instance.get(url)
      return (res as { data: CapabilityPage[] }).data
    },
  })

  // 3. Route Mutation
  const routeMutation = useMutation<RouteDecision, Error, string>({
    mutationFn: async (queryText: string) => {
      const res = await ovClient.instance.post('/api/v1/capability-pages/route', {
        query: queryText,
        cluster_id: selectedCluster === 'all' ? undefined : selectedCluster,
      })
      return (res as { data: RouteDecision }).data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['capability-router-metrics'] })
    },
  })

  // 4. Contrast Neighbors Mutation
  const contrastMutation = useMutation<{ suggested_negative_boundaries: string[] }, Error, string>({
    mutationFn: async (skillId: string) => {
      const res = await ovClient.instance.post('/api/v1/capability-pages/contrast-neighbors', {
        target_skill_id: skillId,
      })
      return (res as { data: { suggested_negative_boundaries: string[] } }).data
    },
  })

  return (
    <div className="flex flex-col gap-3 text-slate-200">
      {/* 4 KPI Tiles */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <KpiTile
          icon={LayersIcon}
          label="三段式档案总数"
          value={metrics?.total_capability_pages ?? '--'}
          sub="T+ / T- / B 结构化"
          accent
        />
        <KpiTile
          icon={CompassIcon}
          label="领域能力簇"
          value={metrics?.total_clusters ?? '--'}
          sub="簇级近邻拓扑"
        />
        <KpiTile
          icon={ShieldAlertIcon}
          label="负向边界拦截率"
          value={metrics ? `${metrics.interception_rate_pct.toFixed(1)}%` : '--'}
          sub={`累计拦截 ${metrics?.boundary_interceptions ?? 0} 次越界`}
          accent
        />
        <KpiTile
          icon={ActivityIcon}
          label="Top-1 区分率增益"
          value={metrics ? `+${metrics.top1_discrimination_gain_pct.toFixed(1)}%` : '--'}
          sub="对比单纯向量检索基线"
        />
      </div>

      {/* Main Dual Panels */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {/* Panel 1: Capability Profiles & Neighbor Contrast */}
        <div className="flex flex-col gap-2 rounded-md border border-slate-700/60 bg-slate-800/40 p-3">
          <div className="flex items-center justify-between border-b border-slate-700/40 pb-2">
            <div className="flex items-center gap-2">
              <LayersIcon className="size-3.5 text-cyan-400" />
              <span className="text-xs font-semibold text-slate-100">
                腾讯 Capability Pages 三段式档案
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-slate-400">领域簇:</span>
              <select
                value={selectedCluster}
                onChange={(e) => setSelectedCluster(e.target.value)}
                aria-label="筛选领域簇"
                className="rounded border border-slate-700 bg-slate-900 px-2 py-0.5 text-xs text-slate-200 focus:outline-none"
              >
                <option value="all">全部簇 (All)</option>
                <option value="container_ops">容器运维 (container_ops)</option>
                <option value="code_quality">代码质量 (code_quality)</option>
              </select>
            </div>
          </div>

          <div className="flex flex-col gap-2 max-h-115 overflow-y-auto pr-1">
            {isPagesLoading ? (
              <div className="py-8 text-center text-xs text-slate-400">正在加载三段式档案...</div>
            ) : pages.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-400">暂无能力档案</div>
            ) : (
              pages.map((p) => (
                <div
                  key={p.skill_id}
                  className="flex flex-col gap-1.5 rounded border border-slate-700/50 bg-slate-900/60 p-2.5"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-semibold text-slate-100">{p.skill_name}</span>
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-xs text-cyan-400 font-mono">
                        {p.cluster_id}
                      </span>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 px-2 text-xs text-slate-300 hover:text-cyan-300"
                      onClick={() => contrastMutation.mutate(p.skill_id)}
                      disabled={contrastMutation.isPending}
                    >
                      <RefreshCwIcon className="mr-1 size-3" />
                      邻居对比
                    </Button>
                  </div>

                  <p className="text-xs text-slate-400">{p.discriminative_body.summary}</p>

                  {/* T+ Positive Triggers */}
                  <div className="flex flex-col gap-0.5">
                    <span className="text-xs font-medium text-cyan-400">
                      T+ 正向触发 ({p.positive_triggers.length}):
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {p.positive_triggers.map((trig, idx) => (
                        <span
                          key={idx}
                          className="rounded bg-cyan-950/40 border border-cyan-800/40 px-1.5 py-0.5 text-xs text-cyan-300"
                        >
                          {trig}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* T- Negative Boundaries */}
                  <div className="flex flex-col gap-0.5">
                    <span className="text-xs font-medium text-rose-400">
                      T- 负向边界 ({p.negative_boundaries.length}) [仅裁判阶段使用]:
                    </span>
                    <div className="flex flex-col gap-1">
                      {p.negative_boundaries.map((neg, idx) => (
                        <span
                          key={idx}
                          className="rounded bg-rose-950/30 border border-rose-800/30 px-1.5 py-0.5 text-xs text-rose-300"
                        >
                          {neg}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Panel 2: Two-Stage Router Playground */}
        <div className="flex flex-col gap-2 rounded-md border border-slate-700/60 bg-slate-800/40 p-3">
          <div className="flex items-center justify-between border-b border-slate-700/40 pb-2">
            <div className="flex items-center gap-2">
              <ShieldCheckIcon className="size-3.5 text-cyan-400" />
              <span className="text-xs font-semibold text-slate-100">
                双阶段负向边界路由试验台
              </span>
            </div>
            <span className="text-xs text-slate-400">防装 10+ 技能误选</span>
          </div>

          {/* Quick Presets */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-400">快捷意图:</span>
            {['重启容器', '查看 Docker 容器运行日志', '分析 Python 代码性能瓶颈'].map((txt) => (
              <button
                key={txt}
                type="button"
                onClick={() => setRouteQueryText(txt)}
                className="rounded border border-slate-700 bg-slate-900/80 px-2 py-0.5 text-xs text-slate-300 hover:border-cyan-500 hover:text-cyan-300"
              >
                {txt}
              </button>
            ))}
          </div>

          {/* Input & Action */}
          <div className="flex gap-2">
            <input
              type="text"
              value={routeQueryText}
              onChange={(e) => setRouteQueryText(e.target.value)}
              placeholder="输入待测试的用户指令，如：重启某个 Docker 容器..."
              className="flex-1 rounded border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs text-slate-100 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
            />
            <Button
              size="sm"
              className="h-7 px-3 text-xs bg-cyan-600 hover:bg-cyan-500 text-white"
              onClick={() => routeMutation.mutate(routeQueryText)}
              disabled={routeMutation.isPending || !routeQueryText.trim()}
            >
              <PlayIcon className="mr-1 size-3" />
              执行隔离路由
            </Button>
          </div>

          {/* Routing Decision Output */}
          <div className="flex flex-col gap-2 rounded border border-slate-700/50 bg-slate-900/60 p-2.5 min-h-75 overflow-y-auto">
            {routeMutation.data ? (
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                  <div className="flex items-center gap-1.5">
                    <CheckCircleIcon className="size-3.5 text-cyan-400" />
                    <span className="text-xs font-semibold text-slate-200">
                      最终命中:{' '}
                      <span className="text-cyan-300">
                        {routeMutation.data.selected_skill_name ?? '无匹配技能 (安全拒绝)'}
                      </span>
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                    <span>耗时: {routeMutation.data.latency_ms}ms</span>
                    <span>置信度: {(routeMutation.data.confidence * 100).toFixed(1)}%</span>
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <span className="text-xs text-slate-400 font-medium">候选技能双阶段裁决:</span>
                  {routeMutation.data.candidates.map((c) => (
                    <div
                      key={c.skill_id}
                      className={`flex flex-col gap-1 rounded border p-2 text-xs ${
                        c.is_blocked
                          ? 'border-rose-800/40 bg-rose-950/20 text-rose-300'
                          : 'border-slate-700/40 bg-slate-800/30 text-slate-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-100">{c.skill_name}</span>
                        <div className="flex items-center gap-2 font-mono">
                          <span>Stage 1: {c.stage1_score.toFixed(2)}</span>
                          {c.is_blocked ? (
                            <span className="text-rose-400 font-bold">
                              T- 拦截 (-{c.negative_penalty.toFixed(2)})
                            </span>
                          ) : (
                            <span className="text-cyan-400 font-bold">通过</span>
                          )}
                          <span className="text-slate-300">最终: {c.final_score.toFixed(2)}</span>
                        </div>
                      </div>
                      <p className="text-xs text-slate-400">{c.verdict_reason}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-48 text-center text-xs text-slate-500">
                <FilterIcon className="size-6 mb-2 text-slate-600" />
                <span>点击「执行隔离路由」测试双阶段负向边界如何识别并拦截相似技能误选</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
