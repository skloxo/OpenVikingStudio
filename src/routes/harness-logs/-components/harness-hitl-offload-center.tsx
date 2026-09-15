import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'
import {
  CheckCircle2Icon,
  FileCodeIcon,
  HistoryIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
  XCircleIcon,
  ZapIcon,
} from 'lucide-react'

export interface FileRefHandleItem {
  ref_id: string
  target_path: string
  total_lines: number
  total_bytes: number
  estimated_raw_tokens: number
  estimated_offloaded_tokens: number
  tokens_saved: number
  content_hash: string
  created_at: number
}

export interface HITLActionItem {
  action_id: string
  tool_name: string
  args_summary: string
  danger_reason: string
  phase: string
  status: 'pending' | 'approved' | 'rejected'
  approval_token: string
  created_at: number
  resolved_at?: number
  resolved_by?: string
  comment?: string
}

export interface HITLOffloadData {
  summary: {
    total_tokens_saved: number
    reduction_ratio_pct: number
    active_refs_count: number
    pending_hitl_count: number
    total_interceptions: number
    approved_count: number
    rejected_count: number
    danger_interception_rate_pct: number
  }
  read_offload: {
    total_files_offloaded: number
    total_raw_tokens: number
    total_offloaded_tokens: number
    active_handles: FileRefHandleItem[]
  }
  hitl_queue: {
    pending: HITLActionItem[]
    history: HITLActionItem[]
  }
}

export function HarnessHITLOffloadCenter() {
  const queryClient = useQueryClient()
  const [probeNotice, setProbeNotice] = React.useState<string | null>(null)

  const metricsQuery = useQuery({
    queryKey: ['hitl-offload-metrics'],
    queryFn: async () => {
      const res = await ovClient.instance.get<HITLOffloadData>('/api/v1/system/hitl_offload_metrics')
      return res.data
    },
    refetchInterval: 10_000,
    staleTime: 5_000,
  })

  const resolveMutation = useMutation({
    mutationFn: async ({ actionId, decision }: { actionId: string; decision: 'approve' | 'reject' }) => {
      const res = await ovClient.instance.post<{ status: string; action: HITLActionItem }>('/api/v1/hitl/resolve', {
        action_id: actionId,
        decision,
        resolved_by: 'operator@console',
        comment: decision === 'approve' ? '座舱控制台人工批准授权' : '座舱控制台人工驳回高危操作',
      })
      return res.data
    },
    onSuccess: (data) => {
      setProbeNotice(
        data.action.status === 'approved'
          ? `已批准高危操作 ${data.action.tool_name}，授权令牌已生效！`
          : `已驳回高危操作 ${data.action.tool_name}！`
      )
      void queryClient.invalidateQueries({ queryKey: ['hitl-offload-metrics'] })
    },
  })

  const probeMutation = useMutation({
    mutationFn: async (payload: { probe_type: string; target_path?: string; tool_name?: string; command?: string }) => {
      const res = await ovClient.instance.post<{ status: string; message: string }>('/api/v1/hitl/probe', payload)
      return res.data
    },
    onSuccess: (data) => {
      setProbeNotice(data.message)
      void queryClient.invalidateQueries({ queryKey: ['hitl-offload-metrics'] })
    },
  })

  const data = metricsQuery.data

  return (
    <div className="space-y-4">
      {/* Top Banner Notice */}
      {probeNotice && (
        <div className="flex items-center justify-between rounded-md border border-cyan-500/30 bg-cyan-500/10 px-3.5 py-2 text-xs text-cyan-300">
          <div className="flex items-center gap-2">
            <ZapIcon className="size-3.5 shrink-0 text-cyan-400" />
            <span>{probeNotice}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setProbeNotice(null)}
            className="h-5 px-1.5 text-[11px] text-cyan-400 hover:bg-cyan-500/20"
          >
            关闭
          </Button>
        </div>
      )}

      {/* 4 High-Density Metric Tiles */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {/* Metric 1: Tokens Saved */}
        <div className="flex flex-col justify-between rounded-md border border-border/60 bg-muted/20 p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>读 Offload 累计节约</span>
            <Badge variant="outline" className="h-4 border-cyan-500/30 bg-cyan-500/10 px-1 text-[11px] text-cyan-400">
              减负 {data?.summary?.reduction_ratio_pct ?? '--'}%
            </Badge>
          </div>
          <div className="my-1 font-mono text-lg font-semibold tabular-nums text-cyan-400">
            {data?.summary?.total_tokens_saved?.toLocaleString() ?? '--'}{' '}
            <span className="text-xs font-normal text-muted-foreground">Tok</span>
          </div>
          <div className="text-[11px] text-muted-foreground">
            原文 {data?.read_offload?.total_raw_tokens?.toLocaleString() ?? '--'} ➔ Offload{' '}
            {data?.read_offload?.total_offloaded_tokens?.toLocaleString() ?? '--'}
          </div>
        </div>

        {/* Metric 2: Active FileRef Handles */}
        <div className="flex flex-col justify-between rounded-md border border-border/60 bg-muted/20 p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>活跃 FileRef 句柄</span>
            <FileCodeIcon className="size-3.5 text-muted-foreground" />
          </div>
          <div className="my-1 font-mono text-lg font-semibold tabular-nums text-foreground">
            {data?.summary?.active_refs_count ?? '--'}{' '}
            <span className="text-xs font-normal text-muted-foreground">个句柄</span>
          </div>
          <div className="text-[11px] text-muted-foreground">
            累计 Offload {data?.read_offload?.total_files_offloaded ?? '--'} 个超大文件
          </div>
        </div>

        {/* Metric 3: HITL Pending Actions */}
        <div className="flex flex-col justify-between rounded-md border border-border/60 bg-muted/20 p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>HITL 待审高危操作</span>
            {(data?.summary?.pending_hitl_count ?? 0) > 0 ? (
              <Badge variant="outline" className="h-4 border-amber-500/30 bg-amber-500/10 px-1 text-[11px] text-amber-400 animate-pulse">
                需确认
              </Badge>
            ) : (
              <Badge variant="outline" className="h-4 border-muted-foreground/30 bg-muted px-1 text-[11px] text-muted-foreground">
                全就绪
              </Badge>
            )}
          </div>
          <div className="my-1 font-mono text-lg font-semibold tabular-nums text-amber-400">
            {data?.summary?.pending_hitl_count ?? '--'}{' '}
            <span className="text-xs font-normal text-muted-foreground">项待审</span>
          </div>
          <div className="text-[11px] text-muted-foreground">
            已批准 {data?.summary?.approved_count ?? 0} ｜ 已驳回 {data?.summary?.rejected_count ?? 0}
          </div>
        </div>

        {/* Metric 4: Interception Rate */}
        <div className="flex flex-col justify-between rounded-md border border-border/60 bg-muted/20 p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>高危操作拦截率</span>
            <ShieldCheckIcon className="size-3.5 text-cyan-400" />
          </div>
          <div className="my-1 font-mono text-lg font-semibold tabular-nums text-cyan-400">
            {data?.summary?.danger_interception_rate_pct ?? '--'}%
          </div>
          <div className="text-[11px] text-muted-foreground">
            拦截 {data?.summary?.total_interceptions ?? 0} 次，0 越权通过
          </div>
        </div>
      </div>

      {/* Dual 50/50 Cockpit Layout */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Left Card: Read Offload FileRef Radar */}
        <div className="flex flex-col rounded-md border border-border/60 bg-muted/10 p-3.5">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileCodeIcon className="size-4 text-cyan-400" />
              <span className="text-xs font-semibold text-foreground">读侧 FileRef 句柄流转与 Token 节约</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              disabled={probeMutation.isPending}
              onClick={() =>
                probeMutation.mutate({
                  probe_type: 'simulate_read_offload',
                  target_path: `openviking/service/large_dataset_${Date.now().toString().slice(-4)}.py`,
                })
              }
              className="h-6 gap-1 px-2 text-[11px] text-cyan-400 hover:bg-cyan-500/10 hover:text-cyan-300"
            >
              <ZapIcon className="size-3" />
              模拟超大文件 Offload
            </Button>
          </div>

          <div className="text-[11px] text-muted-foreground mb-2">
            腾讯 DECO 读护栏：针对 &gt;300行 或 &gt;12KB 文件，自动离线缓存并返回轻量 FileRefHandle，防止全文撑爆模型工作记忆。
          </div>

          <div className="flex-1 space-y-2 overflow-y-auto max-h-80 pr-1">
            {data?.read_offload?.active_handles?.length ? (
              data.read_offload.active_handles.map((item: FileRefHandleItem) => (
                <div
                  key={item.ref_id}
                  className="rounded border border-border/50 bg-background/50 p-2.5 text-xs transition-colors hover:border-cyan-500/30"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 font-mono text-cyan-400 text-[11px]">
                      <span>{item.ref_id}</span>
                      <span className="text-muted-foreground">·</span>
                      <span className="text-muted-foreground font-sans truncate max-w-50" title={item.target_path}>
                        {item.target_path}
                      </span>
                    </div>
                    <Badge variant="outline" className="h-4 border-cyan-500/30 bg-cyan-500/10 px-1 text-[11px] text-cyan-400 font-mono">
                      +省 {item.tokens_saved.toLocaleString()} Tok
                    </Badge>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-[11px] text-muted-foreground">
                    <span>
                      {item.total_lines} 行 ｜ {(item.total_bytes / 1024).toFixed(1)} KB
                    </span>
                    <span className="font-mono text-[11px]">
                      SHA: {item.content_hash.slice(0, 10)}...
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-xs text-muted-foreground">暂无活跃 FileRef 句柄</div>
            )}
          </div>
        </div>

        {/* Right Card: HITL Danger Approval Center */}
        <div className="flex flex-col rounded-md border border-border/60 bg-muted/10 p-3.5">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlertIcon className="size-4 text-amber-400" />
              <span className="text-xs font-semibold text-foreground">HITL 危险操作待审与授权控制台</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              disabled={probeMutation.isPending}
              onClick={() =>
                probeMutation.mutate({
                  probe_type: 'simulate_hitl_intercept',
                  tool_name: 'run_command',
                  command: 'rm -rf /tmp/production_dump/*',
                })
              }
              className="h-6 gap-1 px-2 text-[11px] text-amber-400 hover:bg-amber-500/10 hover:text-amber-300"
            >
              <ZapIcon className="size-3" />
              模拟高危操作拦截
            </Button>
          </div>

          <div className="text-[11px] text-muted-foreground mb-2">
            腾讯 DECO 生产护栏：物理拦截 destructive/deploy 危险操作，必须由人工在座舱授予有效 approval_token 方可放行。
          </div>

          {/* Pending Action Items */}
          <div className="flex-1 space-y-2 overflow-y-auto max-h-40 pr-1 mb-3">
            <div className="text-[11px] font-semibold text-muted-foreground">待审任务队列 ({data?.hitl_queue?.pending?.length ?? 0})</div>
            {data?.hitl_queue?.pending?.length ? (
              data.hitl_queue.pending.map((action: HITLActionItem) => (
                <div
                  key={action.action_id}
                  className="rounded border border-amber-500/30 bg-amber-500/5 p-2.5 text-xs transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] font-bold text-amber-400">
                      {action.tool_name} <span className="font-normal text-muted-foreground">({action.action_id})</span>
                    </span>
                    <Badge variant="outline" className="h-4 border-amber-500/30 bg-amber-500/20 px-1 text-[11px] text-amber-400">
                      阶段: {action.phase}
                    </Badge>
                  </div>
                  <div className="mt-1 text-[11px] text-muted-foreground line-clamp-1" title={action.args_summary}>
                    参数: {action.args_summary}
                  </div>
                  <div className="mt-0.5 text-[11px] text-rose-400/90 line-clamp-1">
                    {action.danger_reason}
                  </div>
                  <div className="mt-2 flex items-center justify-end gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={resolveMutation.isPending}
                      onClick={() => resolveMutation.mutate({ actionId: action.action_id, decision: 'reject' })}
                      className="h-5 px-2 text-[11px] text-rose-400 hover:bg-rose-500/10 border-rose-500/30"
                    >
                      <XCircleIcon className="mr-1 size-3" />
                      驳回
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={resolveMutation.isPending}
                      onClick={() => resolveMutation.mutate({ actionId: action.action_id, decision: 'approve' })}
                      className="h-5 px-2 text-[11px] text-cyan-400 hover:bg-cyan-500/10 border-cyan-500/30"
                    >
                      <CheckCircle2Icon className="mr-1 size-3" />
                      批准执行
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-4 text-center text-xs text-muted-foreground">暂无待审危险操作，所有执行均已放行</div>
            )}
          </div>

          {/* Audit History */}
          <div className="border-t border-border/40 pt-2">
            <div className="flex items-center justify-between text-[11px] font-semibold text-muted-foreground mb-1.5">
              <span>已审/拦截审计流水</span>
              <HistoryIcon className="size-3 text-muted-foreground" />
            </div>
            <div className="space-y-1.5 overflow-y-auto max-h-30 pr-1">
              {data?.hitl_queue?.history?.length ? (
                data.hitl_queue.history.slice(0, 5).map((item: HITLActionItem) => (
                  <div
                    key={item.action_id}
                    className="flex items-center justify-between rounded border border-border/40 bg-background/40 px-2 py-1 text-[11px]"
                  >
                    <div className="flex items-center gap-1.5 font-mono">
                      {item.status === 'approved' ? (
                        <CheckCircle2Icon className="size-3 text-cyan-400 shrink-0" />
                      ) : (
                        <XCircleIcon className="size-3 text-rose-400 shrink-0" />
                      )}
                      <span className={item.status === 'approved' ? 'text-cyan-400' : 'text-rose-400'}>
                        {item.tool_name}
                      </span>
                      <span className="text-muted-foreground truncate max-w-35 font-sans">
                        {item.comment || item.args_summary}
                      </span>
                    </div>
                    <span className="text-muted-foreground font-mono shrink-0">
                      {item.resolved_by || 'system'}
                    </span>
                  </div>
                ))
              ) : (
                <div className="py-2 text-center text-[11px] text-muted-foreground">暂无历史审计记录</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
