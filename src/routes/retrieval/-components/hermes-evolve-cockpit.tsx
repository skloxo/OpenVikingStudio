// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ClockIcon,
  CodeIcon,
  DatabaseIcon,
  PlayIcon,
  RefreshCwIcon,
  RotateCcwIcon,
  SearchIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { ovClient } from '#/lib/ov-client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FTS5SearchResult {
  msg_id: string
  session_id: string
  role: string
  snippet: string
  created_at: number
  rank: number
}

interface SkillPatch {
  patch_id: string
  skill_name: string
  file_path: string
  target_content: string
  replacement_content: string
  reason: string
  status: 'proposed' | 'applied' | 'reverted'
  created_at: number
  applied_at?: number
  target_line_count: number
  replacement_line_count: number
}

interface HermesSummary {
  experience: {
    total_messages: number
    total_sessions: number
    db_path: string
  }
  nudge: {
    queue_depth: number
    completed_reviews: number
    is_running: boolean
  }
  patches: {
    total_patches: number
    proposed: number
    applied: number
    reverted: number
    max_allowed_lines: number
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
// Main Component
// ---------------------------------------------------------------------------

export function HermesEvolveCockpit() {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = React.useState('FastAPI')
  const [appliedQuery, setAppliedQuery] = React.useState('FastAPI')

  // 1. 全局统计
  const summaryQuery = useQuery<HermesSummary>({
    queryKey: ['hermes', 'summary'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/hermes/summary')
      return (res as { data: HermesSummary }).data
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  })

  // 2. FTS5 真实检索
  const searchResultsQuery = useQuery<{ matches: FTS5SearchResult[] }>({
    queryKey: ['hermes', 'search', appliedQuery],
    queryFn: async () => {
      if (!appliedQuery.trim()) return { matches: [] }
      const res = await ovClient.instance.get(`/api/v1/hermes/experience/search?q=${encodeURIComponent(appliedQuery)}`)
      return (res as { data: { matches: FTS5SearchResult[] } }).data
    },
    enabled: appliedQuery.trim().length > 0,
    staleTime: 5_000,
  })

  // 3. 微补丁列表
  const patchesQuery = useQuery<SkillPatch[]>({
    queryKey: ['hermes', 'patches'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/hermes/patches')
      return (res as { data: SkillPatch[] }).data
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  })

  // 4. 应用 / 回滚 Mutations
  const applyMutation = useMutation({
    mutationFn: async (patchId: string) => {
      const res = await ovClient.instance.post(`/api/v1/hermes/patch/${patchId}/apply`)
      return (res as { data: SkillPatch }).data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hermes'] })
    },
  })

  const revertMutation = useMutation({
    mutationFn: async (patchId: string) => {
      const res = await ovClient.instance.post(`/api/v1/hermes/patch/${patchId}/revert`)
      return (res as { data: SkillPatch }).data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hermes'] })
    },
  })

  const summary = summaryQuery.data
  const searchResults = searchResultsQuery.data?.matches ?? []
  const patches = patchesQuery.data ?? []

  return (
    <div className="flex flex-col gap-4">
      {/* 顶栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <DatabaseIcon className="size-4 text-cyan-500" />
            Hermes 经历能力解耦与微手术补丁座舱
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            经历只增不删 · FTS5 真实倒排索引 · 异步副进程复盘 · 补丁 ≤30 行硬门禁
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => queryClient.invalidateQueries({ queryKey: ['hermes'] })}
          className="text-xs h-7 gap-1"
        >
          <RefreshCwIcon className="size-3" />
          刷新数据
        </Button>
      </div>

      {/* KPI 瓦片 */}
      <div className="grid grid-cols-4 gap-3">
        <KpiTile
          icon={DatabaseIcon}
          label="经历消息总数"
          value={summary?.experience.total_messages ?? '--'}
          sub={`涉及会话: ${summary?.experience.total_sessions ?? '--'}`}
          accent
        />
        <KpiTile
          icon={SearchIcon}
          label="FTS5 检索就绪"
          value="毫秒级"
          sub="SQLite 原生倒排 · 拒绝虚假摘要"
          accent
        />
        <KpiTile
          icon={ClockIcon}
          label="异步复盘完成数"
          value={summary?.nudge.completed_reviews ?? '--'}
          sub={`待处理队列: ${summary?.nudge.queue_depth ?? '--'}`}
        />
        <KpiTile
          icon={CodeIcon}
          label="微手术补丁 (≤30行)"
          value={`${summary?.patches.applied ?? '--'} / ${summary?.patches.total_patches ?? '--'}`}
          sub="拒绝全量重写 · 保留90%既有逻辑"
          accent
        />
      </div>

      {/* 主体两栏布局 */}
      <div className="grid grid-cols-2 gap-3">
        {/* 左栏: FTS5 真实消息检索 */}
        <div className="rounded-md border border-border/70 bg-card p-3 flex flex-col gap-2 shadow-xs">
          <div className="flex items-center justify-between pb-1 border-b border-border/60">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <SearchIcon className="size-3.5 text-cyan-500" />
              跨会话 FTS5 真实倒排检索
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') setAppliedQuery(searchQuery)
              }}
              placeholder="输入关键词进行全文倒排检索..."
              className="h-7 text-xs"
            />
            <Button
              size="sm"
              variant="outline"
              onClick={() => setAppliedQuery(searchQuery)}
              className="h-7 px-2.5 text-xs shrink-0"
            >
              检索
            </Button>
          </div>

          <div className="flex flex-col gap-2 max-h-72 overflow-y-auto pr-1">
            {searchResults.length === 0 ? (
              <div className="p-4 text-center text-xs text-muted-foreground">
                {appliedQuery ? '未检索到匹配的经历消息' : '请输入关键词开始检索'}
              </div>
            ) : (
              searchResults.map((m) => (
                <div
                  key={m.msg_id}
                  className="rounded border border-border/60 bg-muted/20 p-2.5 flex flex-col gap-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-cyan-600 dark:text-cyan-400 font-semibold">{m.session_id}</span>
                    <span className="text-xs font-mono text-muted-foreground">[{m.role}]</span>
                  </div>
                  <div
                    className="text-xs text-foreground bg-muted/40 p-1.5 rounded font-mono break-all"
                    dangerouslySetInnerHTML={{ __html: m.snippet }}
                  />
                  <div className="text-xs text-muted-foreground font-mono">
                    Rank: {m.rank.toFixed(2)} · ID: {m.msg_id}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 右栏: 微手术补丁中心 */}
        <div className="rounded-md border border-border/70 bg-card p-3 flex flex-col gap-2 shadow-xs">
          <div className="flex items-center justify-between pb-1 border-b border-border/60">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <CodeIcon className="size-3.5 text-cyan-500" />
              技能微手术补丁中心 ({patches.length})
            </span>
          </div>

          <div className="flex flex-col gap-2 max-h-72 overflow-y-auto pr-1">
            {patches.length === 0 ? (
              <div className="p-4 text-center text-xs text-muted-foreground">暂无待应用的微手术补丁</div>
            ) : (
              patches.map((p) => (
                <div
                  key={p.patch_id}
                  className="rounded border border-border/60 bg-muted/20 p-2.5 flex flex-col gap-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-foreground font-semibold">{p.patch_id}</span>
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded font-mono ${
                        p.status === 'applied'
                          ? 'bg-cyan-50 dark:bg-cyan-950/40 text-cyan-800 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800/40'
                          : p.status === 'reverted'
                            ? 'bg-muted text-muted-foreground border border-border'
                            : 'bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800/40'
                      }`}
                    >
                      {p.status.toUpperCase()}
                    </span>
                  </div>

                  <div className="text-xs text-muted-foreground">
                    技能: <span className="font-mono text-cyan-600 dark:text-cyan-400">{p.skill_name}</span> · 变更行数:{' '}
                    <span className="font-mono text-foreground">
                      -{p.target_line_count} / +{p.replacement_line_count}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground truncate">{p.reason}</div>

                  <div className="flex items-center justify-end gap-2 pt-1 border-t border-border/40">
                    {p.status === 'proposed' && (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={applyMutation.isPending}
                        onClick={() => applyMutation.mutate(p.patch_id)}
                        className="h-6 px-2 text-xs text-cyan-600 dark:text-cyan-400 hover:text-cyan-700 dark:hover:text-cyan-300 hover:bg-cyan-50 dark:hover:bg-cyan-950/40"
                      >
                        <PlayIcon className="size-2.5 mr-1" />
                        应用微补丁
                      </Button>
                    )}
                    {p.status === 'applied' && (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={revertMutation.isPending}
                        onClick={() => revertMutation.mutate(p.patch_id)}
                        className="h-6 px-2 text-xs text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-950/40"
                      >
                        <RotateCcwIcon className="size-2.5 mr-1" />
                        一键回滚
                      </Button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
