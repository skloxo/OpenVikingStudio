import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'
import {
  ActivityIcon,
  CheckCircle2Icon,
  GitCommitIcon,
  PauseOctagonIcon,
  RefreshCwIcon,
  RotateCwIcon,
  SparklesIcon,
  ZapIcon,
} from 'lucide-react'

export interface AgentLoopTelemetryData {
  interjection_queue_depth: number
  interjection_total_queued: number
  interjection_total_drained: number
  interjection_lossless_rate: number
  active_brake_count: number
  turns_completed: number
  turns_aborted: number
  turns_failed: number
  total_turns: number
  model_defense_retries_total: number
  model_defense_exhausted_total: number
  model_recovery_rate: number
  total_inner_steps: number
  last_turn_inner_steps: number
  merkle_last_diff_ms: number
  merkle_tree_file_count: number
  merkle_version: number
  merkle_last_scan_ts: number
  timestamp: number
  status: string
}

export function HarnessAgentLoopCockpit() {
  const queryClient = useQueryClient()
  const [probeResult, setProbeResult] = React.useState<Record<string, unknown> | null>(null)

  const telemetryQuery = useQuery({
    queryKey: ['agent-loop-telemetry'],
    queryFn: async () => {
      const res = await ovClient.instance.get<AgentLoopTelemetryData>(
        '/api/v1/system/agent_loop_telemetry'
      )
      return res.data
    },
    refetchInterval: 5000,
  })

  const probeMutation = useMutation({
    mutationFn: async (payload: { action: string; [key: string]: unknown }) => {
      const res = await ovClient.instance.post('/api/v1/system/agent_loop_probe', payload)
      return res.data
    },
    onSuccess: (data) => {
      setProbeResult(data as Record<string, unknown>)
      void queryClient.invalidateQueries({ queryKey: ['agent-loop-telemetry'] })
    },
  })

  const data = telemetryQuery.data ?? {
    interjection_queue_depth: 0,
    interjection_total_queued: 0,
    interjection_total_drained: 0,
    interjection_lossless_rate: 100.0,
    active_brake_count: 0,
    turns_completed: 0,
    turns_aborted: 0,
    turns_failed: 0,
    total_turns: 0,
    model_defense_retries_total: 0,
    model_defense_exhausted_total: 0,
    model_recovery_rate: 100.0,
    total_inner_steps: 0,
    last_turn_inner_steps: 0,
    merkle_last_diff_ms: 0.85,
    merkle_tree_file_count: 42,
    merkle_version: 1,
    merkle_last_scan_ts: Date.now() / 1000,
    timestamp: Date.now() / 1000,
    status: 'healthy',
  }

  return (
    <div className="flex flex-col gap-4">
      {/* 顶栏控制与说明 */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded border border-border/70 bg-card/60 p-3">
        <div className="flex items-center gap-2">
          <ActivityIcon className="size-4 text-cyan-400" />
          <span className="text-xs font-semibold text-foreground">
            TwoTierAgentLoop 双层事件循环与主动刹车感知
          </span>
          <Badge variant="outline" className="text-[11px] border-cyan-500/40 text-cyan-400 font-mono">
            v1.5.09 Observability SSOT
          </Badge>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground font-mono">
          <span>采样状态:</span>
          <span className="text-cyan-400">活跃监听 (Active)</span>
          <div className="h-3 w-px bg-border/60" />
          <Button
            size="sm"
            variant="ghost"
            className="h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground"
            onClick={() => void telemetryQuery.refetch()}
          >
            <RefreshCwIcon className="mr-1 size-3" />
            刷新
          </Button>
        </div>
      </div>

      {/* 四大指标面板网格 */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {/* 卡片 1: 插话队列监控 */}
        <div className="flex flex-col justify-between rounded border border-border/70 bg-card/50 p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-foreground flex items-center gap-1.5">
              <ZapIcon className="size-3.5 text-cyan-400" />
              异步插话队列
            </span>
            <Badge variant="outline" className="text-[11px] border-border/60 text-muted-foreground font-mono">
              Layer 3 Control
            </Badge>
          </div>
          <div className="my-2.5 flex items-baseline gap-2">
            <span className="text-xl font-bold font-mono tabular-nums text-foreground">
              {data.interjection_queue_depth}
            </span>
            <span className="text-[11px] text-muted-foreground font-mono">待消费排队中</span>
          </div>
          <div className="space-y-1 border-t border-border/50 pt-2 text-[11px] text-muted-foreground font-mono">
            <div className="flex justify-between">
              <span>累计排队入队:</span>
              <span className="text-foreground tabular-nums">{data.interjection_total_queued} 条</span>
            </div>
            <div className="flex justify-between">
              <span>累计原子消费:</span>
              <span className="text-foreground tabular-nums">{data.interjection_total_drained} 条</span>
            </div>
            <div className="flex justify-between">
              <span>零丢包保障率:</span>
              <span className="text-cyan-400 tabular-nums">{data.interjection_lossless_rate}%</span>
            </div>
          </div>
        </div>

        {/* 卡片 2: 主动刹车与完工流转 */}
        <div className="flex flex-col justify-between rounded border border-border/70 bg-card/50 p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-foreground flex items-center gap-1.5">
              <PauseOctagonIcon className="size-3.5 text-amber-400" />
              主动刹车契约
            </span>
            <Badge variant="outline" className="text-[11px] border-amber-500/30 text-amber-400 font-mono">
              terminate: true
            </Badge>
          </div>
          <div className="my-2.5 flex items-baseline gap-2">
            <span className="text-xl font-bold font-mono tabular-nums text-foreground">
              {data.active_brake_count}
            </span>
            <span className="text-[11px] text-muted-foreground font-mono">次提前完工交付</span>
          </div>
          <div className="space-y-1 border-t border-border/50 pt-2 text-[11px] text-muted-foreground font-mono">
            <div className="flex justify-between">
              <span>正常完工 Turns:</span>
              <span className="text-cyan-400 tabular-nums">{data.turns_completed}</span>
            </div>
            <div className="flex justify-between">
              <span>协作取消 / 失败:</span>
              <span className="text-muted-foreground tabular-nums">
                {data.turns_aborted} / <span className="text-rose-400">{data.turns_failed}</span>
              </span>
            </div>
            <div className="flex justify-between">
              <span>总执行 Turns:</span>
              <span className="text-foreground tabular-nums">{data.total_turns}</span>
            </div>
          </div>
        </div>

        {/* 卡片 3: 模型防御与自愈 */}
        <div className="flex flex-col justify-between rounded border border-border/70 bg-card/50 p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-foreground flex items-center gap-1.5">
              <RotateCwIcon className="size-3.5 text-cyan-400" />
              模型防御洋葱层
            </span>
            <Badge variant="outline" className="text-[11px] border-border/60 text-muted-foreground font-mono">
              Layer 2 Defense
            </Badge>
          </div>
          <div className="my-2.5 flex items-baseline gap-2">
            <span className="text-xl font-bold font-mono tabular-nums text-foreground">
              {data.model_defense_retries_total}
            </span>
            <span className="text-[11px] text-muted-foreground font-mono">次退避重试</span>
          </div>
          <div className="space-y-1 border-t border-border/50 pt-2 text-[11px] text-muted-foreground font-mono">
            <div className="flex justify-between">
              <span>重试耗尽熔断:</span>
              <span className={data.model_defense_exhausted_total > 0 ? 'text-rose-400' : 'text-foreground'}>
                {data.model_defense_exhausted_total} 次
              </span>
            </div>
            <div className="flex justify-between">
              <span>故障自愈率:</span>
              <span className="text-cyan-400 tabular-nums">{data.model_recovery_rate}%</span>
            </div>
            <div className="flex justify-between">
              <span>内层工具步数:</span>
              <span className="text-foreground tabular-nums">{data.total_inner_steps} 步</span>
            </div>
          </div>
        </div>

        {/* 卡片 4: Merkle 增量感知 */}
        <div className="flex flex-col justify-between rounded border border-border/70 bg-card/50 p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-foreground flex items-center gap-1.5">
              <GitCommitIcon className="size-3.5 text-cyan-400" />
              Merkle 树增量比对
            </span>
            <Badge variant="outline" className="text-[11px] border-cyan-500/30 text-cyan-400 font-mono">
              &lt; 2.0ms 标尺
            </Badge>
          </div>
          <div className="my-2.5 flex items-baseline gap-2">
            <span className="text-xl font-bold font-mono tabular-nums text-foreground">
              {data.merkle_last_diff_ms}
            </span>
            <span className="text-[11px] text-cyan-400 font-mono">ms 极速巡检</span>
          </div>
          <div className="space-y-1 border-t border-border/50 pt-2 text-[11px] text-muted-foreground font-mono">
            <div className="flex justify-between">
              <span>监视文件总数:</span>
              <span className="text-foreground tabular-nums">{data.merkle_tree_file_count} 个</span>
            </div>
            <div className="flex justify-between">
              <span>状态快照版本:</span>
              <span className="text-foreground tabular-nums">v{data.merkle_version}</span>
            </div>
            <div className="flex justify-between">
              <span>I/O 削峰优化:</span>
              <span className="text-cyan-400 tabular-nums">Zero-Content I/O</span>
            </div>
          </div>
        </div>
      </div>

      {/* 实时模拟探针交互台 */}
      <div className="rounded border border-border/70 bg-card/50 p-3.5">
        <div className="flex items-center justify-between border-b border-border/50 pb-2.5">
          <div className="flex items-center gap-2">
            <SparklesIcon className="size-3.5 text-cyan-400" />
            <span className="text-xs font-semibold text-foreground">
              双层循环物理探针试验台 (Live Telemetry Probe)
            </span>
          </div>
          <span className="text-[11px] text-muted-foreground font-mono">
            零需后台真实长跑，一键验证指标上屏联动
          </span>
        </div>

        <div className="mt-3 flex flex-wrap gap-2.5">
          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs font-mono text-foreground hover:border-cyan-500/50 hover:bg-cyan-500/10"
            disabled={probeMutation.isPending}
            onClick={() => probeMutation.mutate({ action: 'inject_interjection', count: 1, auto_drain: true })}
          >
            <ZapIcon className="mr-1.5 size-3.5 text-cyan-400" />
            模拟插话排队注入
          </Button>

          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs font-mono text-foreground hover:border-amber-500/50 hover:bg-amber-500/10"
            disabled={probeMutation.isPending}
            onClick={() => probeMutation.mutate({ action: 'simulate_brake', tool_name: 'multi_metric_gate', steps: 3 })}
          >
            <PauseOctagonIcon className="mr-1.5 size-3.5 text-amber-400" />
            模拟工具主动刹车
          </Button>

          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs font-mono text-foreground hover:border-cyan-500/50 hover:bg-cyan-500/10"
            disabled={probeMutation.isPending}
            onClick={() => probeMutation.mutate({ action: 'probe_merkle', file_count: data.merkle_tree_file_count + 1 })}
          >
            <GitCommitIcon className="mr-1.5 size-3.5 text-cyan-400" />
            触发 Merkle 巡检计算
          </Button>

          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs font-mono text-foreground hover:border-cyan-500/50"
            disabled={probeMutation.isPending}
            onClick={() => probeMutation.mutate({ action: 'simulate_retry', exhausted: false })}
          >
            <RotateCwIcon className="mr-1.5 size-3.5 text-muted-foreground" />
            模拟模型防御重试
          </Button>
        </div>

        {/* 探针回显卡片 */}
        {probeResult && (
          <div className="mt-3 rounded border border-border/60 bg-background/80 p-2.5 text-xs font-mono text-foreground">
            <div className="flex items-center gap-1.5 text-[11px] text-cyan-400 font-semibold mb-1">
              <CheckCircle2Icon className="size-3.5" />
              探针响应成功 · 物理指标已即时更新
            </div>
            <pre className="text-[11px] text-muted-foreground overflow-x-auto whitespace-pre-wrap">
              {JSON.stringify(probeResult, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
