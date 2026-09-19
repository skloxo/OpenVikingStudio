// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ActivityIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  LayersIcon,
  PlayIcon,
  RefreshCwIcon,
  ShieldCheckIcon,
  XCircleIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AHEAssumption {
  assumption_id: string
  description: string
  validation_command?: string
  frozen_surface?: string
  verified_at?: number
}

interface FileSnapshot {
  path: string
  sha256: string
}

interface AHEManifest {
  manifest_id: string
  skill_name: string
  status: 'active' | 'verified' | 'violated' | 'retired'
  assumptions: AHEAssumption[]
  snapshots: FileSnapshot[]
  violation_cause?: string
  violation_detail?: string
}

interface ClusterEntry {
  cluster_id: string
  mechanism: string
  description: string
  occurrence_count: number
  patched: boolean
  patch_commit?: string
}

interface AHESummary {
  manifests: {
    total: number
    active: number
    verified: number
    violated: number
    retired: number
  }
  clusters: {
    total_clusters: number
    patched_clusters: number
    unpatched_clusters: number
    top_mechanism?: string
    total_occurrences: number
  }
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
  warn,
}: {
  icon: React.ElementType
  label: string
  value: string | number
  sub?: string
  accent?: boolean
  warn?: boolean
}) {
  const valueColor = warn
    ? 'text-rose-400'
    : accent
      ? 'text-cyan-400'
      : 'text-slate-200'

  return (
    <div className="flex flex-col gap-1 rounded-md border border-slate-700/60 bg-slate-800/50 p-3">
      <div className="flex items-center gap-1.5 text-slate-400">
        <Icon className="size-3.5 shrink-0" />
        <span className="text-xs truncate">{label}</span>
      </div>
      <p className={`text-base font-mono font-semibold tabular-nums ${valueColor}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500 truncate">{sub}</p>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Status & Mechanism Badges
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  if (status === 'verified') {
    return (
      <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-700/40">
        <CheckCircleIcon className="size-3" />
        VERIFIED
      </span>
    )
  }
  if (status === 'violated') {
    return (
      <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-mono bg-rose-950/60 text-rose-300 border border-rose-700/40">
        <XCircleIcon className="size-3" />
        VIOLATED
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-mono bg-slate-800 text-slate-300 border border-slate-700">
      <ActivityIcon className="size-3" />
      {status.toUpperCase()}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Main Cockpit Component
// ---------------------------------------------------------------------------

export function AHECockpit() {
  const queryClient = useQueryClient()

  // 1. 全局汇总
  const summaryQuery = useQuery<AHESummary>({
    queryKey: ['ahe', 'summary'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/ahe/summary')
      return (res as { data: AHESummary }).data
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  })

  // 2. Manifest 列表
  const manifestsQuery = useQuery<AHEManifest[]>({
    queryKey: ['ahe', 'manifests'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/ahe/manifest')
      return (res as { data: AHEManifest[] }).data
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  })

  // 3. 根因聚类目录
  const clustersQuery = useQuery<{ clusters: ClusterEntry[] }>({
    queryKey: ['ahe', 'clusters'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/ahe/clusters')
      return (res as { data: { clusters: ClusterEntry[] } }).data
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  })

  // 4. Polar 验证 Mutation
  const verifyMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await ovClient.instance.post(`/api/v1/ahe/manifest/${id}/verify`)
      return (res as { data: unknown }).data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ahe'] })
    },
  })

  const summary = summaryQuery.data
  const manifests = manifestsQuery.data ?? []
  const clusters = clustersQuery.data?.clusters ?? []

  return (
    <div className="flex flex-col gap-4">
      {/* 顶栏操作区 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
            <ShieldCheckIcon className="size-4 text-cyan-400" />
            AHE 契约自演进与 Polar 环境判官座舱
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            可证伪假设 · 根因机制聚类 · 冻结面排他 · 真实沙箱 Exit Code 真理判定
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => queryClient.invalidateQueries({ queryKey: ['ahe'] })}
          className="text-xs h-7 gap-1 border-slate-700 bg-slate-800/80 hover:bg-slate-700/80 text-slate-200"
        >
          <RefreshCwIcon className="size-3" />
          刷新数据
        </Button>
      </div>

      {/* KPI 瓦片阵列 */}
      <div className="grid grid-cols-4 gap-3">
        <KpiTile
          icon={ShieldCheckIcon}
          label="契约 Manifest 总数"
          value={summary?.manifests.total ?? '--'}
          sub={`活跃: ${summary?.manifests.active ?? '--'} · 验证: ${summary?.manifests.verified ?? '--'}`}
          accent
        />
        <KpiTile
          icon={CheckCircleIcon}
          label="Polar 验证通过率"
          value={
            summary?.manifests.total
              ? `${Math.round(((summary.manifests.verified || 0) / summary.manifests.total) * 100)}%`
              : '--'
          }
          sub="不可伪造沙箱 Exit Code 判定"
          accent
        />
        <KpiTile
          icon={LayersIcon}
          label="根因机制聚类"
          value={summary?.clusters.total_clusters ?? '--'}
          sub={`主根因: ${summary?.clusters.top_mechanism ?? '无'}`}
        />
        <KpiTile
          icon={AlertTriangleIcon}
          label="冻结面排他拦截"
          value={summary?.clusters.patched_clusters ?? '--'}
          sub={`未修复: ${summary?.clusters.unpatched_clusters ?? '--'} · 杜绝叠代码`}
          warn={(summary?.clusters.unpatched_clusters ?? 0) > 0}
        />
      </div>

      {/* 主体并排卡片: 左侧 Manifest 契约列表, 右侧 根因聚类目录 */}
      <div className="grid grid-cols-2 gap-3">
        {/* 左卡片: Manifest 契约中心 */}
        <div className="rounded-md border border-slate-700/60 bg-slate-800/40 p-3 flex flex-col gap-2">
          <div className="flex items-center justify-between pb-1 border-b border-slate-700/60">
            <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
              <ShieldCheckIcon className="size-3.5 text-cyan-400" />
              契约 Manifest 列表 ({manifests.length})
            </span>
          </div>

          <div className="flex flex-col gap-2 max-h-72 overflow-y-auto pr-1">
            {manifests.length === 0 ? (
              <div className="p-4 text-center text-xs text-slate-500">暂无活跃 Manifest 契约</div>
            ) : (
              manifests.map((m) => (
                <div
                  key={m.manifest_id}
                  className="rounded border border-slate-700/50 bg-slate-800/70 p-2.5 flex flex-col gap-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-cyan-300 font-semibold">{m.manifest_id}</span>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={m.status} />
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={verifyMutation.isPending}
                        onClick={() => {
                          verifyMutation.mutate(m.manifest_id)
                        }}
                        className="h-6 px-2 text-xs text-cyan-400 hover:text-cyan-300 hover:bg-cyan-950/40"
                      >
                        <PlayIcon className="size-2.5 mr-1" />
                        验证
                      </Button>
                    </div>
                  </div>
                  <div className="text-xs text-slate-400">
                    技能: <span className="text-slate-200">{m.skill_name}</span> · 假设条数:{' '}
                    <span className="font-mono text-slate-200">{m.assumptions?.length || 0}</span> · 快照数:{' '}
                    <span className="font-mono text-slate-200">{m.snapshots?.length || 0}</span>
                  </div>
                  {m.assumptions?.[0] && (
                    <div className="text-xs font-mono text-slate-500 truncate bg-slate-900/60 px-2 py-1 rounded">
                      CMD: {m.assumptions[0].validation_command || '--'}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* 右卡片: 根因聚类目录与冻结面 */}
        <div className="rounded-md border border-slate-700/60 bg-slate-800/40 p-3 flex flex-col gap-2">
          <div className="flex items-center justify-between pb-1 border-b border-slate-700/60">
            <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
              <LayersIcon className="size-3.5 text-cyan-400" />
              根因机制聚类目录 ({clusters.length})
            </span>
          </div>

          <div className="flex flex-col gap-2 max-h-72 overflow-y-auto pr-1">
            {clusters.length === 0 ? (
              <div className="p-4 text-center text-xs text-slate-500">暂无聚合根因事件</div>
            ) : (
              clusters.map((c) => (
                <div
                  key={c.cluster_id}
                  className="rounded border border-slate-700/50 bg-slate-800/70 p-2.5 flex flex-col gap-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-slate-300 font-semibold">{c.cluster_id}</span>
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded font-mono ${
                        c.patched
                          ? 'bg-slate-800 text-slate-400 border border-slate-700'
                          : 'bg-rose-950/60 text-rose-300 border border-rose-700/40'
                      }`}
                    >
                      {c.patched ? '已冻结补丁' : '待自愈'}
                    </span>
                  </div>
                  <div className="text-xs text-slate-300">
                    机制: <span className="font-mono text-cyan-400">{c.mechanism}</span> · 出现频次:{' '}
                    <span className="font-mono font-semibold text-slate-200">{c.occurrence_count}</span>
                  </div>
                  <div className="text-xs text-slate-400 truncate">{c.description}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
