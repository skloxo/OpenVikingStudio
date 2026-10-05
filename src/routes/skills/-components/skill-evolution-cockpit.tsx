// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  CheckCircle2Icon,
  ChevronRightIcon,
  LayersIcon,
  PlayIcon,
  RefreshCwIcon,
  RotateCcwIcon,
  SparklesIcon,
  ZapIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { ovClient } from '#/lib/ov-client'

interface ClusterCandidate {
  cluster_id: string
  domain_name: string
  cluster_name: string
  target_slug: string
  target_crystallized_slug: string
  candidate_slugs: string[]
  candidate_count: number
  reasons: string[]
  avg_health_score: number
}

interface PipelineStatusData {
  status: string
  metrics: {
    intent_collisions: number
    total_homogenous_skills: number
    average_health_score: number
    s_grade_ratio: number
    attempt_pass_rate: number
  }
  total_clusters?: number
  clusters_summary?: Array<{
    cluster_name: string
    domain: string
    candidate_count: number
    target_crystallized_slug: string
    avg_health_score: number
  }>
}

interface PipelineRunResponse {
  status: string
  dry_run: boolean
  report: {
    total_candidates: number
    clusters_identified: number
    processed_clusters: number
    clusters_crystallized: number
    total_crystallized: number
    clusters_blocked: number
    collisions_before: number
    collisions_after: number
    avg_health_before: number
    avg_health_after: number
    overall_attempt_pass_rate: number
    results: Array<{
      cluster_id: string
      domain_name: string
      target_slug: string
      success: boolean
      final_judge_score: number
      weight_boost: number
      absorbed_slugs: string[]
      inherited_files: string[]
      stages: Array<{
        stage: string
        passed: boolean
        score?: number
        diagnostics: string[]
      }>
      error?: string
    }>
  }
}

export function SkillEvolutionCockpit() {
  const [lastReport, setLastReport] = React.useState<PipelineRunResponse | null>(null)
  const [selectedClusterDomain, setSelectedClusterDomain] = React.useState<string | null>(null)
  const [actionNotice, setActionNotice] = React.useState<string | null>(null)

  // 1. Query pipeline status & objective metrics
  const { data: statusData, refetch: refetchStatus, isLoading: isStatusLoading } = useQuery({
    queryKey: ['skill-evolution-status'],
    queryFn: async () => {
      const res = await ovClient.instance.get<PipelineStatusData>('/api/v1/skills/evolution/pipeline/status')
      return res.data
    },
    staleTime: 30_000,
  })

  // 2. Query candidates list
  const { data: clustersData, refetch: refetchClusters } = useQuery({
    queryKey: ['skill-evolution-clusters'],
    queryFn: async () => {
      const res = await ovClient.instance.get<{ status: string; total_clusters: number; clusters: ClusterCandidate[] }>(
        '/api/v1/skills/evolution/pipeline/clusters?min_cluster_size=2'
      )
      return res.data
    },
    staleTime: 30_000,
  })

  // 3. Mutation: Run pipeline (dry-run or physical commit)
  const runMutation = useMutation({
    mutationFn: async ({ dryRun, targetDomain }: { dryRun: boolean; targetDomain?: string }) => {
      const res = await ovClient.instance.post<PipelineRunResponse>('/api/v1/skills/evolution/pipeline/run', {
        dry_run: dryRun,
        target_domain: targetDomain || null,
        max_clusters: 10,
      })
      return res.data
    },
    onSuccess: (data) => {
      setLastReport(data)
      setActionNotice(data.dry_run ? '📋 影响面清单扫描完成 (待确认执行)' : '🔥 全域物理结晶完成！旧技能已归档至隔离区！')
      refetchStatus()
      refetchClusters()
    },
    onError: (err: any) => {
      setActionNotice(`❌ 执行失败: ${err.message || String(err)}`)
    },
  })

  // 4. Mutation: Rollback from quarantine
  const rollbackMutation = useMutation({
    mutationFn: async () => {
      const res = await ovClient.instance.post<{ status: string; restored_skills: number }>('/api/v1/skills/evolution/pipeline/rollback', {})
      return res.data
    },
    onSuccess: (data) => {
      setActionNotice(`↩️ 已恢复 ${data.restored_skills} 项隔离技能原貌！`)
      setLastReport(null)
      refetchStatus()
      refetchClusters()
    },
    onError: (err: any) => {
      setActionNotice(`❌ 回滚失败: ${err.message || String(err)}`)
    },
  })

  const metrics = statusData?.metrics ?? {
    intent_collisions: 5,
    total_homogenous_skills: 28,
    average_health_score: 75.0,
    s_grade_ratio: 0.12,
    attempt_pass_rate: 0.88,
  }

  const clusters = clustersData?.clusters ?? []

  return (
    <div className="flex flex-col gap-3.5 w-full min-w-0">
      {/* Top Banner: 4 Objective Metric Tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Metric 1: Intent Collisions */}
        <Card className="p-3 border-border/60 bg-muted/10 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground">意图冲突簇数</span>
            <Badge variant="outline" className={metrics.intent_collisions > 0 ? 'border-amber-500/40 text-amber-400' : 'border-cyan-500/40 text-cyan-400'}>
              {metrics.intent_collisions > 0 ? '待收敛' : '零冲突'}
            </Badge>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-mono font-bold tabular-nums text-foreground">{metrics.intent_collisions}</span>
            <span className="text-xs text-muted-foreground font-mono">簇 ({metrics.total_homogenous_skills} 碎片)</span>
          </div>
          <div className="mt-2 text-xs text-muted-foreground font-mono border-t border-border/40 pt-1.5 flex justify-between">
            <span>基准 58 簇</span>
            <span className="text-cyan-400">目标 0 冲突</span>
          </div>
        </Card>

        {/* Metric 2: Average Health Score */}
        <Card className="p-3 border-border/60 bg-muted/10 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground">全域平均健康分</span>
            <Badge variant="outline" className={metrics.average_health_score >= 80 ? 'border-cyan-500/40 text-cyan-400' : 'border-border text-muted-foreground'}>
              四维标准
            </Badge>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-mono font-bold tabular-nums text-foreground">{metrics.average_health_score}</span>
            <span className="text-xs text-muted-foreground font-mono">分</span>
          </div>
          <div className="mt-2 text-xs text-muted-foreground font-mono border-t border-border/40 pt-1.5 flex justify-between">
            <span>基准 71.2 分</span>
            <span className="text-cyan-400">目标 85+ 分</span>
          </div>
        </Card>

        {/* Metric 3: S-Grade Ratio */}
        <Card className="p-3 border-border/60 bg-muted/10 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground">S 级特种兵占比</span>
            <Badge variant="outline" className="border-cyan-500/40 text-cyan-400">
              结晶跃升
            </Badge>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-mono font-bold tabular-nums text-foreground">{Math.round(metrics.s_grade_ratio * 100)}%</span>
            <span className="text-xs text-muted-foreground font-mono">高胜率</span>
          </div>
          <div className="mt-2 text-xs text-muted-foreground font-mono border-t border-border/40 pt-1.5 flex justify-between">
            <span>基准 9.5%</span>
            <span className="text-cyan-400">目标 60%+</span>
          </div>
        </Card>

        {/* Metric 4: Attempt Pass Rate */}
        <Card className="p-3 border-border/60 bg-muted/10 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground">Attempt 门禁放行率</span>
            <Badge variant="outline" className="border-cyan-500/40 text-cyan-400">
              质量契约门禁
            </Badge>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-mono font-bold tabular-nums text-foreground">{Math.round(metrics.attempt_pass_rate * 100)}%</span>
            <span className="text-xs text-muted-foreground font-mono">首解通过</span>
          </div>
          <div className="mt-2 text-xs text-muted-foreground font-mono border-t border-border/40 pt-1.5 flex justify-between">
            <span>熔断限频 2 次</span>
            <span className="text-cyan-400">目标 &ge;85%</span>
          </div>
        </Card>
      </div>

      {/* Control Action Bar */}
      <Card className="p-3.5 border-border/60 bg-muted/10 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <ZapIcon className="size-4 text-cyan-400" />
          <div className="grid gap-0.5">
            <span className="text-xs font-semibold">技能演进与结晶 7 阶自动化流水线</span>
            <span className="text-xs font-mono text-muted-foreground">
              识别重合簇 ➔ 四维体检 ➔ 补丁补齐 ➔ 脚本遗产迁移 ➔ 质量门禁 ➔ VikingFS 提权上架
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {actionNotice && (
            <span className="text-xs font-mono text-cyan-400 mr-2 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/30">
              {actionNotice}
            </span>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={() => runMutation.mutate({ dryRun: true, targetDomain: selectedClusterDomain || undefined })}
            disabled={runMutation.isPending}
            className="text-xs h-7 font-mono border-border text-foreground hover:border-cyan-500/40"
          >
            <PlayIcon className="size-3.5 mr-1 text-cyan-400" />
            📋 扫描影响面清单
          </Button>

          <Button
            size="sm"
            onClick={() => {
              if (window.confirm('确认执行全域技能演进结晶？旧同质化碎片将安全备份至隔离区并从技能目录移出，结晶主技能将提权发布至 VikingFS。')) {
                runMutation.mutate({ dryRun: false, targetDomain: selectedClusterDomain || undefined })
              }
            }}
            disabled={runMutation.isPending}
            className="text-xs h-7 font-mono bg-cyan-600 hover:bg-cyan-500 text-white"
          >
            <SparklesIcon className="size-3.5 mr-1" />
            🔥 执行物理结晶收敛
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              if (window.confirm('确认从隔离快照回滚所有被结晶合并的原始技能？')) {
                rollbackMutation.mutate()
              }
            }}
            disabled={rollbackMutation.isPending}
            className="text-xs h-7 font-mono border-border text-muted-foreground hover:text-rose-400 hover:border-rose-500/40"
          >
            <RotateCcwIcon className="size-3.5 mr-1" />
            ↩️ 一键无悔回滚
          </Button>

          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              refetchStatus()
              refetchClusters()
            }}
            disabled={isStatusLoading}
            className="h-7 px-2 text-xs text-muted-foreground hover:text-cyan-400"
          >
            <RefreshCwIcon className={`size-3.5 ${isStatusLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </Card>

      {/* Evolution Pipeline Execution Echo (if report available) */}
      {lastReport && (
        <Card className="p-3.5 border-cyan-500/30 bg-cyan-500/5 flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-cyan-500/20 pb-2">
            <div className="flex items-center gap-2">
              <CheckCircle2Icon className="size-4 text-cyan-400" />
              <span className="text-xs font-semibold text-cyan-300">
                {lastReport.dry_run ? '影响面扫描明细 (Pre-flight)' : '物理结晶流水线执行回显 (Committed)'}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs font-mono">
              <span>识别: <strong className="text-foreground">{lastReport.report.clusters_identified} 簇</strong></span>
              <span>收敛: <strong className="text-cyan-400">{lastReport.report.clusters_crystallized} 簇</strong></span>
              <span>阻断: <strong className="text-amber-400">{lastReport.report.clusters_blocked} 簇</strong></span>
              <span>首解率: <strong className="text-cyan-400">{Math.round(lastReport.report.overall_attempt_pass_rate * 100)}%</strong></span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {lastReport.report.results.map((res) => (
              <div key={res.cluster_id} className="p-2.5 rounded border border-border/60 bg-background/50 flex flex-col gap-1.5 text-xs font-mono">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-foreground">{res.domain_name}</span>
                  <Badge variant="outline" className={res.success ? 'border-cyan-500/40 text-cyan-400' : 'border-rose-500/40 text-rose-400'}>
                    {res.success ? `结晶成功 (${res.final_judge_score}分)` : '门禁阻断'}
                  </Badge>
                </div>
                <div className="text-muted-foreground flex items-center gap-1.5">
                  <span>目标中枢:</span>
                  <span className="text-cyan-400">{res.target_slug}</span>
                  <span>(提权 x{res.weight_boost})</span>
                </div>
                <div className="text-muted-foreground text-xs">
                  吸收碎片 ({res.absorbed_slugs.length}): {res.absorbed_slugs.join(', ')}
                </div>
                {res.inherited_files.length > 0 && (
                  <div className="text-muted-foreground text-xs">
                    继承脚本 ({res.inherited_files.length}): {res.inherited_files.slice(0, 3).join(', ')}
                  </div>
                )}
                {res.error && <div className="text-rose-400 text-xs">原因: {res.error}</div>}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Candidate Clusters List */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <LayersIcon className="size-4 text-cyan-400" />
            <span className="text-xs font-semibold">待结晶同质化重合簇 ({clusters.length} 个领域)</span>
          </div>
          {selectedClusterDomain && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setSelectedClusterDomain(null)}
              className="text-xs h-6 text-muted-foreground hover:text-foreground"
            >
              清除过滤 (当前: {selectedClusterDomain})
            </Button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {clusters.map((cluster) => {
            const isSelected = selectedClusterDomain === cluster.domain_name
            return (
              <Card
                key={cluster.cluster_id}
                className={`p-3 border-border/60 bg-muted/10 flex flex-col justify-between cursor-pointer transition-colors ${
                  isSelected ? 'border-cyan-500/60 bg-cyan-500/5' : 'hover:border-border'
                }`}
                onClick={() => setSelectedClusterDomain(isSelected ? null : cluster.domain_name)}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-foreground">{cluster.domain_name}</span>
                    <Badge variant="outline" className="border-border font-mono text-xs">
                      {cluster.candidate_count} 项碎片
                    </Badge>
                  </div>
                  <div className="mt-2 text-xs font-mono text-muted-foreground flex items-center gap-1">
                    <span>收敛目标:</span>
                    <strong className="text-cyan-400">{cluster.target_slug}</strong>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {cluster.candidate_slugs.map((slug) => (
                      <span key={slug} className="text-xs font-mono bg-background/80 px-1.5 py-0.5 rounded border border-border/40 text-muted-foreground">
                        {slug}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="mt-3 pt-2 border-t border-border/40 flex items-center justify-between text-xs font-mono">
                  <span className="text-muted-foreground">均分: {cluster.avg_health_score}</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation()
                      runMutation.mutate({ dryRun: false, targetDomain: cluster.domain_name })
                    }}
                    disabled={runMutation.isPending}
                    className="h-6 px-1.5 text-xs text-cyan-400 hover:text-cyan-300"
                  >
                    定向结晶 <ChevronRightIcon className="size-3 ml-0.5" />
                  </Button>
                </div>
              </Card>
            )
          })}
        </div>
      </div>
    </div>
  )
}
