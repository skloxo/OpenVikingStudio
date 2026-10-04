// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangleIcon,
  ArchiveIcon,
  CheckCircleIcon,
  LayersIcon,
  RefreshCwIcon,
  ShieldCheckIcon,
  UsersIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { ovClient } from '#/lib/ov-client'
import { TaskCardDetailDrawer } from './task-card-detail-drawer'
import type { TaskCardRecord } from './task-card-detail-drawer'


interface TaskCardSummary {
  pending_count: number
  resolved_count: number
  p0_count: number
  p1_count: number
  p2_count: number
  p3_count: number
  total_occurrences: number
  storm_suppression_pct: number
  affected_agents_count: number
  affected_agents: string[]
}

interface CardsListResponse {
  status: string
  result: {
    total: number
    cards: TaskCardRecord[]
  }
}

interface SummaryResponse {
  status: string
  result: TaskCardSummary
}

export function IssueTaskCardsCockpit() {
  const [tab, setTab] = React.useState<'pending' | 'resolved'>('pending')
  const [selectedCard, setSelectedCard] = React.useState<TaskCardRecord | null>(null)
  const [drawerOpen, setDrawerOpen] = React.useState(false)

  // 1. Fetch summary metrics
  const summaryQuery = useQuery<SummaryResponse>({
    queryKey: ['task-cards-summary'],
    queryFn: async () => (await ovClient.instance.get('/api/v1/task-cards/summary')).data,
    refetchInterval: 30_000,
  })

  // 2. Fetch list of cards according to active tab
  const listQuery = useQuery<CardsListResponse>({
    queryKey: ['task-cards-list', tab],
    queryFn: async () =>
      (await ovClient.instance.get(`/api/v1/task-cards/${tab === 'pending' ? 'pending' : 'resolved'}`)).data,
    refetchInterval: 30_000,
  })

  const stats = summaryQuery.data?.result
  const cards = listQuery.data?.result?.cards || []

  const handleOpenDetail = (card: TaskCardRecord) => {
    setSelectedCard(card)
    setDrawerOpen(true)
  }

  const handleRefetch = () => {
    void summaryQuery.refetch()
    void listQuery.refetch()
  }

  return (
    <Card className="flex flex-col gap-3 p-3.5 bg-card/70 border-border/80 rounded-md">
      {/* 头部标题与控制区 */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-muted/60 text-cyan-400">
            <LayersIcon className="size-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold tracking-tight text-foreground">
                集群智能体自主建卡与异常上报座舱 (AIFP)
              </h2>
              <Badge variant="outline" className="border-cyan-500/30 bg-cyan-500/10 text-cyan-400 font-mono text-[12px]">
                v1.7.3
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              告别口头汇报与人肉传话：全集群子代理发现异常自动立卡，防爆聚合去重，由 Master Agent 排期闭环
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={summaryQuery.isFetching || listQuery.isFetching}
            onClick={handleRefetch}
            className="h-7 text-xs gap-1"
          >
            <RefreshCwIcon className={`size-3 ${summaryQuery.isFetching ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      {/* 高密指标瓦片 (4 Tiles) */}
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        <div className="flex flex-col gap-1 rounded-md bg-muted/20 p-2.5 border border-border/40">
          <div className="flex items-center justify-between text-muted-foreground text-xs">
            <span>待分诊工单</span>
            <AlertTriangleIcon className="size-3.5 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className={`font-mono text-xl font-bold tabular-nums ${stats && stats.pending_count > 0 ? 'text-amber-400' : 'text-foreground'}`}>
              {stats ? stats.pending_count : '--'}
            </span>
            <span className="text-xs text-muted-foreground">张待办</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground pt-0.5">
            <span className={stats && stats.p0_count > 0 ? 'text-rose-400 font-semibold' : ''}>
              P0: {stats ? stats.p0_count : '--'}
            </span>
            <span>•</span>
            <span className={stats && stats.p1_count > 0 ? 'text-amber-400 font-medium' : ''}>
              P1: {stats ? stats.p1_count : '--'}
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-1 rounded-md bg-muted/20 p-2.5 border border-border/40">
          <div className="flex items-center justify-between text-muted-foreground text-xs">
            <span>防爆卡聚合率</span>
            <ShieldCheckIcon className="size-3.5 text-cyan-400" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="font-mono text-xl font-bold tabular-nums text-foreground">
              {stats ? `${stats.storm_suppression_pct.toFixed(1)}%` : '--'}
            </span>
            <span className="text-xs text-muted-foreground">抗风暴</span>
          </div>
          <p className="text-xs text-muted-foreground truncate">
            累计吞吐 {stats ? stats.total_occurrences : '--'} 次异常事件
          </p>
        </div>

        <div className="flex flex-col gap-1 rounded-md bg-muted/20 p-2.5 border border-border/40">
          <div className="flex items-center justify-between text-muted-foreground text-xs">
            <span>受波及智能体</span>
            <UsersIcon className="size-3.5 text-cyan-400" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="font-mono text-xl font-bold tabular-nums text-foreground">
              {stats ? stats.affected_agents_count : '--'}
            </span>
            <span className="text-xs text-muted-foreground">个实例</span>
          </div>
          <p className="text-xs text-muted-foreground truncate font-mono">
            {stats && stats.affected_agents.length > 0 ? stats.affected_agents.slice(0, 2).join(', ') : '暂无'}
          </p>
        </div>

        <div className="flex flex-col gap-1 rounded-md bg-muted/20 p-2.5 border border-border/40">
          <div className="flex items-center justify-between text-muted-foreground text-xs">
            <span>历史已闭环归档</span>
            <ArchiveIcon className="size-3.5 text-cyan-400" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="font-mono text-xl font-bold tabular-nums text-foreground">
              {stats ? stats.resolved_count : '--'}
            </span>
            <span className="text-xs text-muted-foreground">张卡片</span>
          </div>
          <p className="text-xs text-muted-foreground">
            包含 Commit Hash 与 Release Tag 留痕
          </p>
        </div>
      </div>

      {/* Tab 导航与切换 */}
      <div className="flex items-center justify-between gap-2 border-b border-border/40 pt-1 pb-1.5">
        <div className="flex items-center gap-1.5">
          <Button
            type="button"
            variant={tab === 'pending' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setTab('pending')}
            className={`h-7 px-2.5 text-xs ${tab === 'pending' ? 'font-semibold text-foreground' : 'text-muted-foreground'}`}
          >
            待处理收件箱 ({stats ? stats.pending_count : 0})
          </Button>
          <Button
            type="button"
            variant={tab === 'resolved' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setTab('resolved')}
            className={`h-7 px-2.5 text-xs ${tab === 'resolved' ? 'font-semibold text-foreground' : 'text-muted-foreground'}`}
          >
            已归档总账 ({stats ? stats.resolved_count : 0})
          </Button>
        </div>
      </div>

      {/* 工单数据列表 */}
      {cards.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-6 text-center text-xs text-muted-foreground border border-dashed border-border/60 rounded-md">
          <CheckCircleIcon className="size-6 text-cyan-400/80 mb-1" />
          <span>{tab === 'pending' ? '收件箱暂无待处理工单，集群运行健康稳定' : '暂无已归档工单'}</span>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border border-border/60">
          <table className="w-full text-left text-xs">
            <thead className="bg-muted/30 text-muted-foreground border-b border-border/40">
              <tr>
                <th className="py-2 px-3 font-medium">优先级</th>
                <th className="py-2 px-3 font-medium">工单 ID / 标题</th>
                <th className="py-2 px-3 font-medium">受影响模块</th>
                <th className="py-2 px-3 font-medium text-center">聚合频次</th>
                <th className="py-2 px-3 font-medium">上报智能体</th>
                <th className="py-2 px-3 font-medium text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/30">
              {cards.map((c) => (
                <tr
                  key={c.card_id}
                  onClick={() => handleOpenDetail(c)}
                  className="hover:bg-muted/20 cursor-pointer transition-colors"
                >
                  <td className="py-2 px-3">
                    <Badge
                      variant="outline"
                      className={
                        c.priority === 'P0'
                          ? 'border-rose-500/40 bg-rose-500/10 text-rose-400 font-semibold'
                          : c.priority === 'P1'
                          ? 'border-amber-400/40 bg-amber-400/10 text-amber-400 font-semibold'
                          : 'border-border/60 bg-muted/30 text-muted-foreground'
                      }
                    >
                      {c.priority}
                    </Badge>
                  </td>
                  <td className="py-2 px-3">
                    <div className="flex flex-col">
                      <span className="font-medium text-foreground truncate max-w-sm sm:max-w-md">
                        {c.title}
                      </span>
                      <span className="font-mono text-muted-foreground text-[12px] truncate">
                        {c.card_id}
                      </span>
                    </div>
                  </td>
                  <td className="py-2 px-3">
                    <code className="rounded bg-muted/40 px-1.5 py-0.5 font-mono text-[12px] text-foreground">
                      {c.module}
                    </code>
                  </td>
                  <td className="py-2 px-3 text-center font-mono tabular-nums text-foreground">
                    <Badge variant="secondary" className="font-mono text-[12px] px-1.5 py-0">
                      ×{c.occurrence_count}
                    </Badge>
                  </td>
                  <td className="py-2 px-3">
                    <span className="font-mono text-muted-foreground text-[12px] truncate">
                      {c.initiator}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-right">
                    <Button variant="ghost" size="xs" className="h-6 text-xs text-cyan-400">
                      查看详情
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 详情抽屉 */}
      <TaskCardDetailDrawer
        card={selectedCard}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        onResolvedSuccess={handleRefetch}
      />
    </Card>
  )
}
