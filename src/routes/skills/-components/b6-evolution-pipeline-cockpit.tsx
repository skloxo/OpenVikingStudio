// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ActivityIcon,
  ArrowRightIcon,
  CheckCircle2Icon,
  CpuIcon,
  LayersIcon,
  PlayIcon,
  RefreshCwIcon,
  ShieldCheckIcon,
  SparklesIcon,
  WorkflowIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { ovClient } from '#/lib/ov-client'
import { cn } from '#/lib/utils'
import { B6_PIPELINE_STAGES, type B6PipelineStage } from '../-constants/b6-pipeline-stages'
import { useSkillEventBus } from '../-hooks/use-skill-event-bus'

export function B6EvolutionPipelineCockpit() {
  const queryClient = useQueryClient()
  const { isConnected: isEventBusConnected } = useSkillEventBus()
  const [selectedStageId, setSelectedStageId] = React.useState<string>('seam_decision')

  // 读取准入队列实时深度
  const { data: queueData, isFetching: isQueueFetching, refetch: refetchQueue } = useQuery({
    queryKey: ['skills-ingestion-queue-depth-cockpit'],
    queryFn: async () => {
      const res = await ovClient.instance.get<{
        status: string
        queue_depth: {
          total: number
          pending: number
          validating: number
          staged: number
          committed: number
          rejected: number
          error: number
        }
      }>('/api/v1/skills/ingestion/queue?limit=1')
      return res.data
    },
    refetchInterval: 10_000,
  })

  // 手动推进一个周期的流水线批处理
  const processBatchMutation = useMutation({
    mutationFn: async () => {
      return (await ovClient.instance.post('/api/v1/skills/ingestion/process-batch?batch_size=5', {})).data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills-ingestion-queue'] })
      queryClient.invalidateQueries({ queryKey: ['skills-provenance-events'] })
      queryClient.invalidateQueries({ queryKey: ['skills-ingestion-queue-depth-cockpit'] })
    },
  })

  const depth = queueData?.queue_depth ?? { total: 0, pending: 0, validating: 0, staged: 0, committed: 0, rejected: 0, error: 0 }
  const selectedStage = B6_PIPELINE_STAGES.find((s) => s.id === selectedStageId) ?? B6_PIPELINE_STAGES[4]

  return (
    <div className="flex flex-col gap-4">
      {/* 1. 顶部全息态势带 */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-cyan-200 bg-cyan-50/70 dark:border-cyan-500/30 dark:bg-cyan-950/20 px-3.5 py-2.5 text-xs font-mono shadow-2xs">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center justify-center size-6 rounded bg-cyan-100/90 dark:bg-cyan-900/40 text-cyan-700 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-800">
            <WorkflowIcon className="size-3.5" />
          </div>
          <div>
            <div className="font-semibold text-cyan-900 dark:text-cyan-200 flex items-center gap-2">
              <span>⚡ B6 自主结晶演进流水线与全息运行中枢</span>
              <Badge variant="outline" className="border-cyan-300 bg-cyan-100/70 text-cyan-800 dark:border-cyan-700 dark:bg-cyan-950/50 dark:text-cyan-200 text-xs px-1.5 py-0">
                12-Stage Cycle Active
              </Badge>
            </div>
            <div className="text-muted-foreground text-xs">
              贯穿准入嗅探、AST 自愈、质量门禁、接缝裁决、视网膜验收、零退化保护与 Hermes 微手术反哺全闭环
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-background/80 border border-border/70 text-xs">
            <span className="text-muted-foreground">队列:</span>
            <span className="text-amber-700 dark:text-amber-400 font-semibold">{depth.pending} 待审</span>
            <span className="text-muted-foreground/60">/</span>
            <span className="text-cyan-600 dark:text-cyan-400 font-semibold">{depth.committed} 落盘</span>
          </div>

          <Badge variant="outline" className="border-border bg-background/80 text-foreground text-xs flex items-center gap-1.5">
            <span className={`size-1.5 rounded-full ${isEventBusConnected ? 'bg-cyan-500 animate-pulse' : 'bg-muted-foreground'}`} />
            <span>{isEventBusConnected ? '实时双工已连通' : '轮询保障中'}</span>
          </Badge>

          <Button
            size="sm"
            variant="outline"
            disabled={processBatchMutation.isPending || isQueueFetching}
            onClick={() => processBatchMutation.mutate()}
            className="h-7 text-xs font-mono border-cyan-300 text-cyan-700 hover:bg-cyan-100/60 dark:border-cyan-700 dark:text-cyan-300 dark:hover:bg-cyan-950/40"
          >
            <PlayIcon className={processBatchMutation.isPending ? 'size-3 animate-spin mr-1' : 'size-3 mr-1'} />
            推进批处理
          </Button>

          <Button
            size="sm"
            variant="ghost"
            onClick={() => void refetchQueue()}
            className="h-7 px-1.5 text-muted-foreground hover:text-foreground"
          >
            <RefreshCwIcon className={isQueueFetching ? 'size-3.5 animate-spin' : 'size-3.5'} />
          </Button>
        </div>
      </div>

      {/* 2. 12 阶自主工序全景态势沙盘 */}
      <Card className="p-3.5 border-border/80 shadow-2xs">
        <div className="flex items-center justify-between border-b border-border/60 pb-2 mb-3">
          <div className="flex items-center gap-2">
            <LayersIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
            <h3 className="text-xs font-semibold font-mono text-foreground">
              12 阶自适应生命周期态势图 (12-Stage Ingestion & Closed-Loop Lifecycle)
            </h3>
          </div>
          <span className="text-xs font-mono text-muted-foreground">
            点击任意工序查看物理贯彻契约与底层承载引擎
          </span>
        </div>

        {/* 12 阶工序网格：前 6 阶准入熔炼 + 后 6 阶闭环验真 */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
          {B6_PIPELINE_STAGES.map((st) => {
            const isSelected = st.id === selectedStageId
            const isIngestion = st.phase === 'ingestion'

            return (
              <button
                key={st.id}
                type="button"
                onClick={() => setSelectedStageId(st.id)}
                className={cn(
                  'flex flex-col text-left p-2.5 rounded-md border transition-all cursor-pointer relative group',
                  isSelected
                    ? 'border-cyan-500 bg-cyan-50/80 dark:bg-cyan-950/40 shadow-xs'
                    : 'border-border/60 bg-card hover:border-cyan-300 dark:hover:border-cyan-800 hover:bg-muted/30'
                )}
              >
                <div className="flex items-center justify-between w-full mb-1">
                  <span
                    className={cn(
                      'size-4 rounded flex items-center justify-center text-xs font-mono font-bold',
                      isSelected
                        ? 'bg-cyan-600 text-white dark:bg-cyan-500 dark:text-neutral-950'
                        : 'bg-muted text-muted-foreground group-hover:text-foreground'
                    )}
                  >
                    {st.number}
                  </span>
                  <span
                    className={cn(
                      'text-xs font-mono px-1.5 py-0.5 rounded border',
                      isIngestion
                        ? 'border-cyan-300/70 bg-cyan-100/50 text-cyan-800 dark:border-cyan-800/50 dark:bg-cyan-950/30 dark:text-cyan-300'
                        : 'border-blue-300/70 bg-blue-100/50 text-blue-800 dark:border-blue-800/50 dark:bg-blue-950/30 dark:text-blue-300'
                    )}
                  >
                    {st.badge}
                  </span>
                </div>

                <div className="text-xs font-semibold font-mono text-foreground truncate mt-0.5">
                  {st.name}
                </div>

                <div className="text-xs font-mono text-muted-foreground truncate mt-1">
                  {st.engine.split(' ')[0]}
                </div>
              </button>
            )
          })}
        </div>

        {/* 3. 选中工序的深度穿透与契约解析视窗 */}
        {selectedStage && (
          <div className="mt-3.5 pt-3.5 border-t border-border/60 bg-muted/20 rounded-md p-3">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <span className="flex items-center justify-center size-5 rounded-full bg-cyan-600 text-white dark:bg-cyan-400 dark:text-neutral-950 text-xs font-mono font-bold">
                  {selectedStage.number}
                </span>
                <span className="text-xs font-bold font-mono text-foreground">
                  {selectedStage.name}
                </span>
                <Badge variant="outline" className="border-cyan-300 text-cyan-800 dark:border-cyan-800 dark:text-cyan-300 text-xs font-mono">
                  {selectedStage.badge}
                </Badge>
                <span className="text-xs text-muted-foreground font-mono">
                  (执行角色: {selectedStage.role})
                </span>
              </div>

              <div className="text-xs font-mono text-muted-foreground">
                承载引擎: <span className="text-foreground font-semibold">{selectedStage.engine}</span>
              </div>
            </div>

            <p className="text-xs text-muted-foreground mb-2.5 leading-relaxed">
              {selectedStage.desc}
            </p>

            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              <span className="text-xs font-mono font-semibold text-foreground">物理贯彻契约 (Enforced Invariants):</span>
              {selectedStage.invariants.map((rule, idx) => (
                <span
                  key={idx}
                  className="text-xs font-mono px-1.5 py-0.5 rounded border border-border/80 bg-background/80 text-foreground"
                >
                  {rule}
                </span>
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
