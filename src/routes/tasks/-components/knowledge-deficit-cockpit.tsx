// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BotIcon,
  CheckCircle2Icon,
  CompassIcon,
  EyeOffIcon,
  FlameIcon,
  RefreshCwIcon,
  SparklesIcon,
  UserCheckIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { Textarea } from '#/components/ui/textarea'
import {
  castDeficitScaffold,
  dismissDeficitCard,
  fetchDeficitsList,
  fetchDeficitSummary,
  fulfillDeficitCard,
} from '#/routes/tasks/-lib/knowledge-deficit-api'
import type { DeficitStatus, KnowledgeDeficitItem } from '#/routes/tasks/-lib/knowledge-deficit-api'

type FilterTab = DeficitStatus | 'all'

export function KnowledgeDeficitCockpit() {
  const queryClient = useQueryClient()
  const [tab, setTab] = React.useState<FilterTab>('pending_fulfillment')
  const [selectedId, setSelectedId] = React.useState<string | null>(null)
  const [draftContent, setDraftContent] = React.useState('')

  const summaryQuery = useQuery({
    queryKey: ['knowledge-deficits-summary'],
    queryFn: fetchDeficitSummary,
    refetchInterval: 30_000,
  })

  const listQuery = useQuery({
    queryKey: ['knowledge-deficits-list', tab],
    queryFn: () => fetchDeficitsList(tab),
    refetchInterval: 30_000,
  })

  const invalidateAll = React.useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['knowledge-deficits-summary'] })
    void queryClient.invalidateQueries({ queryKey: ['knowledge-deficits-list'] })
  }, [queryClient])

  const scaffoldMut = useMutation({
    mutationFn: (id: string) => castDeficitScaffold(id),
    onSuccess: (updated) => {
      setSelectedId(updated.deficit_id)
      invalidateAll()
    },
  })

  const fulfillMut = useMutation({
    mutationFn: (args: { id: string; content: string; track: string }) =>
      fulfillDeficitCard(args.id, { content: args.content, track: args.track }),
    onSuccess: () => {
      setDraftContent('')
      setSelectedId(null)
      invalidateAll()
    },
  })

  const dismissMut = useMutation({
    mutationFn: (id: string) => dismissDeficitCard(id, 'manual_dismiss'),
    onSuccess: () => {
      setSelectedId(null)
      invalidateAll()
    },
  })

  const stats = summaryQuery.data
  const items: KnowledgeDeficitItem[] = listQuery.data || []
  const selectedItem = items.find((it) => it.deficit_id === selectedId) || null

  const selectRow = (item: KnowledgeDeficitItem) => {
    if (selectedId === item.deficit_id) {
      setSelectedId(null)
      return
    }
    setSelectedId(item.deficit_id)
    setDraftContent(item.fulfillment_content || item.scaffold_markdown || '')
  }

  return (
    <Card className="flex flex-col gap-3 p-3.5 bg-card/70 border-border/80 rounded-md">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-muted/60 text-cyan-400">
            <CompassIcon className="size-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold tracking-tight text-foreground">
                知识盲区频次漏斗与双轨补全引擎
              </h2>
              <Badge variant="outline" className="border-cyan-500/30 bg-cyan-500/10 text-cyan-400 font-mono text-xs">
                Card-207
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              偶发未命中静默观察（0 Token），累计 ≥{stats?.miss_threshold ?? 3} 次自动铸造反思骨架并按公私属性双轨分流补齐
            </p>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={summaryQuery.isFetching || listQuery.isFetching}
          onClick={invalidateAll}
          className="h-7 text-xs gap-1"
        >
          <RefreshCwIcon className={`size-3 ${summaryQuery.isFetching ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        <div className="flex flex-col gap-1 rounded-md bg-muted/20 p-2.5 border border-border/40">
          <div className="flex items-center justify-between text-muted-foreground text-xs">
            <span>热点待补齐</span>
            <FlameIcon className="size-3.5 text-rose-400" />
          </div>
          <span className={`font-mono text-xl font-bold tabular-nums ${stats && stats.pending_fulfillment_count > 0 ? 'text-rose-400' : 'text-foreground'}`}>
            {stats ? stats.pending_fulfillment_count : '--'}
          </span>
          <span className="text-xs text-muted-foreground">
            人工 {stats?.human_assistance_pending ?? 0} • 工兵 {stats?.autonomous_researcher_pending ?? 0}
          </span>
        </div>

        <div className="flex flex-col gap-1 rounded-md bg-muted/20 p-2.5 border border-border/40">
          <div className="flex items-center justify-between text-muted-foreground text-xs">
            <span>漏斗抗风暴率</span>
            <SparklesIcon className="size-3.5 text-cyan-400" />
          </div>
          <span className="font-mono text-xl font-bold tabular-nums text-foreground">
            {stats ? `${stats.storm_suppression_pct.toFixed(1)}%` : '--'}
          </span>
          <span className="text-xs text-muted-foreground">累计捕获 {stats ? stats.total_misses : '--'} 次未命中</span>
        </div>

        <div className="flex flex-col gap-1 rounded-md bg-muted/20 p-2.5 border border-border/40">
          <div className="flex items-center justify-between text-muted-foreground text-xs">
            <span>低频观察池</span>
            <UserCheckIcon className="size-3.5 text-slate-400" />
          </div>
          <span className="font-mono text-xl font-bold tabular-nums text-foreground">
            {stats ? stats.observing_count : '--'}
          </span>
          <span className="text-xs text-muted-foreground">未达阈值静默沉淀</span>
        </div>

        <div className="flex flex-col gap-1 rounded-md bg-muted/20 p-2.5 border border-border/40">
          <div className="flex items-center justify-between text-muted-foreground text-xs">
            <span>已双轨补全</span>
            <CheckCircle2Icon className="size-3.5 text-cyan-400" />
          </div>
          <span className="font-mono text-xl font-bold tabular-nums text-cyan-400">
            {stats ? stats.fulfilled_count : '--'}
          </span>
          <span className="text-xs text-muted-foreground">已忽略 {stats ? stats.dismissed_count : 0} 项</span>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 border-b border-border/40 pb-1.5">
        {(
          [
            ['pending_fulfillment', `待补全热点 (${stats?.pending_fulfillment_count ?? 0})`],
            ['observing', `低频观察池 (${stats?.observing_count ?? 0})`],
            ['fulfilled', `已双轨补全 (${stats?.fulfilled_count ?? 0})`],
            ['all', `全部 (${stats?.total_tracked ?? 0})`],
          ] as [FilterTab, string][]
        ).map(([key, label]) => (
          <Button
            key={key}
            type="button"
            variant={tab === key ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setTab(key)}
            className={`h-7 px-2.5 text-xs ${tab === key ? 'font-semibold text-foreground' : 'text-muted-foreground'}`}
          >
            {label}
          </Button>
        ))}
      </div>

      {items.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-5 text-center text-xs text-muted-foreground border border-dashed border-border/60 rounded-md">
          <CheckCircle2Icon className="size-5 text-cyan-400/80 mb-1" />
          <span>当前视图暂无知识盲区记录</span>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border border-border/60">
          <table className="w-full text-left text-xs">
            <thead className="bg-muted/30 text-muted-foreground border-b border-border/40">
              <tr>
                <th className="py-2 px-3 font-medium">状态</th>
                <th className="py-2 px-3 font-medium">盲区实体 / Query</th>
                <th className="py-2 px-3 font-medium">分流轨道</th>
                <th className="py-2 px-3 font-medium text-center">未命中次数</th>
                <th className="py-2 px-3 font-medium text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/30">
              {items.map((item) => (
                <tr
                  key={item.deficit_id}
                  onClick={() => selectRow(item)}
                  className="hover:bg-muted/20 cursor-pointer transition-colors"
                >
                  <td className="py-2 px-3">
                    <Badge
                      variant="outline"
                      className={
                        item.status === 'pending_fulfillment'
                          ? 'border-rose-500/40 bg-rose-500/10 text-rose-400 text-xs'
                          : item.status === 'fulfilled'
                          ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-400 text-xs'
                          : 'border-border/60 bg-muted/30 text-muted-foreground text-xs'
                      }
                    >
                      {item.status}
                    </Badge>
                  </td>
                  <td className="py-2 px-3">
                    <div className="flex flex-col">
                      <span className="font-medium text-foreground">{item.entity_name}</span>
                      <span className="text-xs text-muted-foreground font-mono truncate max-w-md">
                        {item.canonical_query}
                      </span>
                    </div>
                  </td>
                  <td className="py-2 px-3">
                    <Badge variant="outline" className="text-xs gap-1 border-border/60 text-foreground">
                      {item.suggested_route === 'autonomous_researcher' ? (
                        <BotIcon className="size-3 text-amber-400" />
                      ) : (
                        <UserCheckIcon className="size-3 text-cyan-400" />
                      )}
                      {item.suggested_route === 'autonomous_researcher' ? '工兵自主调研' : '人类协助填空'}
                    </Badge>
                  </td>
                  <td className="py-2 px-3 text-center font-mono">{item.miss_count}</td>
                  <td className="py-2 px-3 text-right">
                    {item.status === 'observing' && (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="h-6 px-2 text-xs"
                        disabled={scaffoldMut.isPending}
                        onClick={(e) => {
                          e.stopPropagation()
                          scaffoldMut.mutate(item.deficit_id)
                        }}
                      >
                        铸造骨架
                      </Button>
                    )}
                    {item.status === 'pending_fulfillment' && (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="h-6 px-2 text-xs border-cyan-500/40 text-cyan-400"
                        onClick={(e) => {
                          e.stopPropagation()
                          selectRow(item)
                        }}
                      >
                        双轨补齐
                      </Button>
                    )}
                    {item.status === 'fulfilled' && (
                      <span className="font-mono text-xs text-cyan-400">{item.deliverable_uri}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedItem && (
        <div className="flex flex-col gap-2.5 rounded-md border border-cyan-500/30 bg-muted/20 p-3 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-semibold text-foreground">
              骨架详情 · {selectedItem.entity_name} ({selectedItem.deficit_id})
            </span>
            <span className="font-mono text-muted-foreground">
              同义聚合词: {selectedItem.aliases.join(' | ')}
            </span>
          </div>
          {selectedItem.scaffold_markdown && (
            <pre className="max-h-44 overflow-auto rounded bg-background/80 p-2.5 font-mono text-xs text-muted-foreground border border-border/40">
              {selectedItem.scaffold_markdown}
            </pre>
          )}
          {selectedItem.status !== 'fulfilled' && (
            <div className="flex flex-col gap-2">
              <Textarea
                value={draftContent}
                onChange={(e) => setDraftContent(e.target.value)}
                rows={4}
                placeholder="在此补齐实证知识正文（或由工兵调研结果填入）..."
                className="text-xs font-mono"
              />
              <div className="flex items-center justify-end gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="h-7 text-xs text-rose-400 gap-1"
                  disabled={dismissMut.isPending}
                  onClick={() => dismissMut.mutate(selectedItem.deficit_id)}
                >
                  <EyeOffIcon className="size-3" />
                  忽略噪点
                </Button>
                <Button
                  type="button"
                  size="sm"
                  className="h-7 text-xs bg-cyan-600 hover:bg-cyan-500 text-white"
                  disabled={fulfillMut.isPending || !draftContent.trim()}
                  onClick={() =>
                    fulfillMut.mutate({
                      id: selectedItem.deficit_id,
                      content: draftContent,
                      track: selectedItem.suggested_route,
                    })
                  }
                >
                  写回知识库并闭环
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
