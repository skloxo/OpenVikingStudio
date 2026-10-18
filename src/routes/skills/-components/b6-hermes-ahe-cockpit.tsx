// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  CodeIcon,
  DatabaseIcon,
  LayersIcon,
  RefreshCwIcon,
  SearchIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { ovClient } from '#/lib/ov-client'
import { B6AheManifestPanel } from './b6-ahe-manifest-panel'
import { B6HermesPatchPanel } from './b6-hermes-patch-panel'
import { B6LessonsPanel } from './b6-lessons-panel'
import type {
  AHEManifest,
  AHESummary,
  HermesAheTrackMode,
  HermesSummary,
  LessonItem,
  SkillPatch,
} from '../-types/hermes-ahe'

export function B6HermesAheCockpit() {
  const queryClient = useQueryClient()
  const [activeMode, setActiveMode] = React.useState<HermesAheTrackMode>('hermes_patch')
  const [searchQuery, setSearchQuery] = React.useState('')

  // 1. Hermes 全局统计
  const {
    data: hermesSummary,
    isLoading: hermesLoading,
    refetch: refetchHermes,
  } = useQuery<HermesSummary>({
    queryKey: ['hermes-summary'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/hermes/summary')
      return (res as { data: HermesSummary }).data
    },
    refetchInterval: 30_000,
  })

  // 2. Hermes 微补丁列表
  const {
    data: patches = [],
    isLoading: patchesLoading,
    refetch: refetchPatches,
  } = useQuery<SkillPatch[]>({
    queryKey: ['hermes-patches'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/hermes/patches')
      return (res as { data: SkillPatch[] }).data
    },
    refetchInterval: 30_000,
  })

  // 3. AHE 全局统计
  const {
    data: aheSummary,
    isLoading: aheLoading,
    refetch: refetchAhe,
  } = useQuery<AHESummary>({
    queryKey: ['ahe-summary'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/ahe/summary')
      return (res as { data: AHESummary }).data
    },
    refetchInterval: 30_000,
  })

  // 4. AHE Manifests 列表
  const {
    data: manifests = [],
    isLoading: manifestsLoading,
    refetch: refetchManifests,
  } = useQuery<AHEManifest[]>({
    queryKey: ['ahe-manifests'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/ahe/manifest')
      return (res as { data: AHEManifest[] }).data
    },
    refetchInterval: 30_000,
  })

  // 5. 全量事故与演进教训档案
  const {
    data: lessons = [],
    isLoading: lessonsLoading,
    refetch: refetchLessons,
  } = useQuery<LessonItem[]>({
    queryKey: ['evolution-harness-lessons'],
    queryFn: async () => {
      try {
        const res = await ovClient.instance.get<{
          lessons_count?: number
          lessons_detail?: LessonItem[]
        }>('/api/v1/system/harness_metrics')
        return res.data?.lessons_detail ?? []
      } catch (err) {
        console.warn('Failed to fetch evolution lessons:', err)
        return []
      }
    },
    staleTime: 15_000,
  })

  // 6. 应用 Hermes 微补丁
  const applyPatchMutation = useMutation({
    mutationFn: async (patchId: string) => {
      const res = await ovClient.instance.post(`/api/v1/hermes/patch/apply?patch_id=${patchId}`)
      return (res as { data: any }).data
    },
    onSuccess: () => {
      toast.success('微手术补丁已成功热应用并沉淀快照')
      queryClient.invalidateQueries({ queryKey: ['hermes-patches'] })
      queryClient.invalidateQueries({ queryKey: ['hermes-summary'] })
    },
    onError: (err: any) => {
      toast.error(`补丁应用失败: ${err?.message || '未知错误'}`)
    },
  })

  // 6. 回滚 Hermes 微补丁
  const revertPatchMutation = useMutation({
    mutationFn: async (patchId: string) => {
      const res = await ovClient.instance.post(`/api/v1/hermes/patch/revert?patch_id=${patchId}`)
      return (res as { data: any }).data
    },
    onSuccess: () => {
      toast.success('微手术补丁已秒级无损回退')
      queryClient.invalidateQueries({ queryKey: ['hermes-patches'] })
      queryClient.invalidateQueries({ queryKey: ['hermes-summary'] })
    },
    onError: (err: any) => {
      toast.error(`回退失败: ${err?.message || '未知错误'}`)
    },
  })

  // 7. 一键核验 AHE 契约假设
  const verifyAheMutation = useMutation({
    mutationFn: async () => {
      const res = await ovClient.instance.post('/api/v1/ahe/verify')
      return (res as { data: any }).data
    },
    onSuccess: () => {
      toast.success('AHE 契约漂移对抗核验完成')
      queryClient.invalidateQueries({ queryKey: ['ahe-manifests'] })
      queryClient.invalidateQueries({ queryKey: ['ahe-summary'] })
    },
    onError: (err: any) => {
      toast.error(`核验失败: ${err?.message || '未知错误'}`)
    },
  })

  const filteredPatches = React.useMemo(() => {
    if (!searchQuery.trim()) return patches
    const q = searchQuery.toLowerCase()
    return patches.filter(
      (p) =>
        p.skill_name?.toLowerCase().includes(q) ||
        p.reason?.toLowerCase().includes(q) ||
        p.patch_id?.toLowerCase().includes(q)
    )
  }, [patches, searchQuery])

  const filteredManifests = React.useMemo(() => {
    if (!searchQuery.trim()) return manifests
    const q = searchQuery.toLowerCase()
    return manifests.filter(
      (m) =>
        m.skill_name?.toLowerCase().includes(q) ||
        m.status?.toLowerCase().includes(q) ||
        m.manifest_id?.toLowerCase().includes(q)
    )
  }, [manifests, searchQuery])

  const totalExperienceMessages = hermesSummary?.experience?.total_messages ?? 0
  const totalPatches = hermesSummary?.patches?.total_patches ?? patches.length
  const proposedPatches = hermesSummary?.patches?.proposed ?? 0
  const activeManifests = aheSummary?.manifests?.active ?? 0
  const totalManifests = aheSummary?.manifests?.total ?? manifests.length
  const violatedCount = aheSummary?.manifests?.violated ?? 0

  return (
    <div className="rounded-md border border-border/80 bg-card p-3.5 shadow-2xs space-y-3">
      {/* 1. 顶栏双视角切换与动作栏 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-border/60 pb-3">
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setActiveMode('hermes_patch')}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-mono font-medium transition-all cursor-pointer ${
              activeMode === 'hermes_patch'
                ? 'bg-cyan-100 text-cyan-900 border border-cyan-300 dark:bg-cyan-950/60 dark:text-cyan-200 dark:border-cyan-800 font-semibold'
                : 'text-muted-foreground hover:bg-muted/40 border border-transparent'
            }`}
          >
            <DatabaseIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
            <span>🧬 第 11 阶: Hermes 经历微手术补丁审查 ({filteredPatches.length})</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveMode('ahe_guard')}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-mono font-medium transition-all cursor-pointer ${
              activeMode === 'ahe_guard'
                ? 'bg-cyan-100 text-cyan-900 border border-cyan-300 dark:bg-cyan-950/60 dark:text-cyan-200 dark:border-cyan-800 font-semibold'
                : 'text-muted-foreground hover:bg-muted/40 border border-transparent'
            }`}
          >
            <ShieldCheckIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
            <span>🛡️ 第 10 阶: AHE 契约假设与漂移对抗 ({filteredManifests.length})</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveMode('lessons')}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-mono font-medium transition-all cursor-pointer ${
              activeMode === 'lessons'
                ? 'bg-cyan-100 text-cyan-900 border border-cyan-300 dark:bg-cyan-950/60 dark:text-cyan-200 dark:border-cyan-800 font-semibold'
                : 'text-muted-foreground hover:bg-muted/40 border border-transparent'
            }`}
          >
            <LayersIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
            <span>📋 第 12 阶: 演进与反思教训档案 ({lessons.length})</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative w-40 sm:w-52">
            <SearchIcon className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索技能/教训/原因/ID..."
              className="text-xs font-mono h-7 pl-7 pr-2 border-border/80"
            />
          </div>
          {activeMode === 'hermes_patch' && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                refetchHermes()
                refetchPatches()
              }}
              disabled={hermesLoading || patchesLoading}
              className="text-xs h-7 font-mono px-2 border-border/80 cursor-pointer"
            >
              <RefreshCwIcon className={`size-3 mr-1 ${hermesLoading || patchesLoading ? 'animate-spin' : ''}`} />
              刷新
            </Button>
          )}
          {activeMode === 'ahe_guard' && (
            <div className="flex items-center gap-1.5">
              <Button
                size="sm"
                onClick={() => verifyAheMutation.mutate()}
                disabled={verifyAheMutation.isPending}
                className="text-xs h-7 font-mono px-2.5 bg-cyan-600 hover:bg-cyan-700 text-white font-semibold cursor-pointer shadow-xs"
              >
                <ShieldCheckIcon className="size-3 mr-1" />
                {verifyAheMutation.isPending ? '核验中...' : '⚡ 全量核验'}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  refetchAhe()
                  refetchManifests()
                }}
                disabled={aheLoading || manifestsLoading}
                className="text-xs h-7 font-mono px-2 border-border/80 cursor-pointer"
              >
                <RefreshCwIcon className={`size-3 mr-1 ${aheLoading || manifestsLoading ? 'animate-spin' : ''}`} />
                刷新
              </Button>
            </div>
          )}
          {activeMode === 'lessons' && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => refetchLessons()}
              disabled={lessonsLoading}
              className="text-xs h-7 font-mono px-2 border-border/80 cursor-pointer"
            >
              <RefreshCwIcon className={`size-3 mr-1 ${lessonsLoading ? 'animate-spin' : ''}`} />
              刷新
            </Button>
          )}
        </div>
      </div>

      {/* 2. 4 维核心 KPI 瓦片 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="rounded-md border border-border/70 bg-card p-2.5 shadow-2xs">
          <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
            <span>经历库历史对话总数</span>
            <DatabaseIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="text-lg font-bold font-mono text-foreground mt-1">
            {totalExperienceMessages}
          </div>
          <div className="text-xs font-mono text-muted-foreground mt-0.5 truncate">
            FTS5 复盘索引: 经历只增不删
          </div>
        </div>

        <div className="rounded-md border border-border/70 bg-card p-2.5 shadow-2xs">
          <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
            <span>微手术补丁总数</span>
            <CodeIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="text-lg font-bold font-mono text-cyan-800 dark:text-cyan-300 mt-1">
            {totalPatches}
          </div>
          <div className="text-xs font-mono text-muted-foreground mt-0.5 truncate">
            待审提议: {proposedPatches} · ≤30行硬限制
          </div>
        </div>

        <div className="rounded-md border border-border/70 bg-card p-2.5 shadow-2xs">
          <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
            <span>存活 AHE 契约假设</span>
            <LayersIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="text-lg font-bold font-mono text-foreground mt-1">
            {activeManifests} / {totalManifests}
          </div>
          <div className="text-xs font-mono text-muted-foreground mt-0.5 truncate">
            冻结面保护: 防契约漂移
          </div>
        </div>

        <div className="rounded-md border border-border/70 bg-card p-2.5 shadow-2xs">
          <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
            <span>演进教训归档总数</span>
            <LayersIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="text-lg font-bold font-mono text-cyan-800 dark:text-cyan-300 mt-1">
            {lessons.length}
          </div>
          <div className="text-xs font-mono text-muted-foreground mt-0.5 truncate">
            Master Memory: 99 项实机沉淀
          </div>
        </div>
      </div>

      {/* 3. 三轨解耦互动沙盘展示区 */}
      {activeMode === 'hermes_patch' && (
        <B6HermesPatchPanel
          patches={filteredPatches}
          isLoading={patchesLoading}
          onApplyPatch={(patchId) => applyPatchMutation.mutate(patchId)}
          onRevertPatch={(patchId) => revertPatchMutation.mutate(patchId)}
          isApplying={applyPatchMutation.isPending}
          isReverting={revertPatchMutation.isPending}
        />
      )}
      {activeMode === 'ahe_guard' && (
        <B6AheManifestPanel
          manifests={filteredManifests}
          isLoading={manifestsLoading}
        />
      )}
      {activeMode === 'lessons' && (
        <B6LessonsPanel
          lessons={lessons}
          searchQuery={searchQuery}
          isLoading={lessonsLoading}
        />
      )}
    </div>
  )
}
