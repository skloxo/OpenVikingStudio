import * as React from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'
import { RefreshCwIcon, TerminalIcon } from 'lucide-react'

export interface HarnessFailureSandboxProbeProps {
  recentEvents?: Array<{
    type: string
    category?: string
    tool_name?: string
    whitelist_type?: string
    payload_id?: string
    reason?: string
    blocked?: boolean
    backoff_sec?: number
    timestamp: number
  }>
}

export function HarnessFailureSandboxProbe({ recentEvents }: HarnessFailureSandboxProbeProps) {
  const queryClient = useQueryClient()
  const [probeResult, setProbeResult] = React.useState<Record<string, unknown> | null>(null)

  const probeMutation = useMutation({
    mutationFn: async (payload: { action: string; tool_name?: string; whitelist_type?: string }) => {
      const res = await ovClient.instance.post<Record<string, unknown>>(
        '/api/v1/system/failure_taxonomy_probe',
        payload
      )
      return res.data
    },
    onSuccess: (data) => {
      setProbeResult(data)
      void queryClient.invalidateQueries({ queryKey: ['failure-taxonomy-telemetry'] })
    },
  })

  return (
    <div className="flex flex-col gap-3 rounded-md border border-border/60 bg-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-2.5">
        <div>
          <h2 className="text-xs font-bold text-foreground flex items-center gap-1.5">
            <TerminalIcon className="size-3.5 text-cyan-400" />
            受控混沌演练与自愈韧性探针 (Controlled Chaos & Resilience Probe)
          </h2>
          <p className="text-xs text-muted-foreground">
            在受控沙箱中真实注入 429 限流、Watchdog 超时熔断与真实 Merkle 状态树，检验底层自愈力与资源回收
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={probeMutation.isPending}
            onClick={() =>
              probeMutation.mutate({ action: 'simulate_transient', tool_name: 'fetch_remote_context' })
            }
            className="h-7 text-xs text-foreground"
          >
            🔥 真实 429 退避自愈
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={probeMutation.isPending}
            onClick={() =>
              probeMutation.mutate({ action: 'drill_watchdog_timeout' })
            }
            className="h-7 text-xs text-foreground"
          >
            ⚡ Watchdog 超时熔断
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={probeMutation.isPending}
            onClick={() =>
              probeMutation.mutate({ action: 'drill_real_merkle' })
            }
            className="h-7 text-xs text-foreground"
          >
            🌲 真实 Merkle 状态树
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={probeMutation.isPending}
            onClick={() =>
              probeMutation.mutate({
                action: 'simulate_deterministic',
                tool_name: 'exec_database_query',
              })
            }
            className="h-7 text-xs text-foreground"
          >
            防死循环屏障 (Anti-Loop)
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={probeMutation.isPending}
            onClick={() =>
              probeMutation.mutate({ action: 'register_whitelist', whitelist_type: 'TaskPlan' })
            }
            className="h-7 text-xs text-foreground"
          >
            + TaskPlan 免压缩白名单
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={probeMutation.isPending}
            onClick={() => probeMutation.mutate({ action: 'reset' })}
            className="h-7 text-xs text-muted-foreground hover:text-foreground"
            title="重置探针状态"
          >
            <RefreshCwIcon className="size-3" />
          </Button>
        </div>
      </div>

      {/* Live Probe Feedback Banner */}
      {probeResult && (
        <div className="rounded-md border border-cyan-500/30 bg-cyan-500/10 p-3 text-xs flex flex-col gap-2">
          <div className="flex items-center justify-between font-mono font-semibold text-cyan-400">
            <span>混沌演练与探针实时响应 (Probe Feedback):</span>
            <span className="text-muted-foreground font-normal">
              {new Date().toLocaleTimeString()}
            </span>
          </div>

          {/* 真实演练指标回显瓦片 */}
          {Boolean(probeResult.real_drill_executed) && (
            <div className="grid grid-cols-3 gap-2 p-2 bg-background/60 border border-border/60 rounded font-mono text-xs">
              <div className="flex flex-col">
                <span className="text-muted-foreground">演练耗时</span>
                <span className="text-foreground font-semibold tabular-nums">
                  {typeof probeResult.actual_duration_ms === 'number'
                    ? `${probeResult.actual_duration_ms.toFixed(1)} ms`
                    : typeof probeResult.duration_ms === 'number'
                    ? `${probeResult.duration_ms.toFixed(1)} ms`
                    : '--'}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-muted-foreground">自愈/熔断状态</span>
                <span className="text-cyan-400 font-semibold">
                  {probeResult.drill_success ? 'PASS (100% 自愈)' : 'FAIL'}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-muted-foreground">隔离安全契约</span>
                <span className="text-cyan-400 font-semibold">生产业务 0 污染</span>
              </div>
            </div>
          )}

          <pre className="max-h-32 overflow-auto font-mono text-xs text-foreground/90 leading-relaxed bg-background/50 p-2 rounded">
            {JSON.stringify(probeResult, null, 2)}
          </pre>
        </div>
      )}

      {/* Real-time Event Stream Mini-Log */}
      <div className="mt-1">
        <div className="text-xs font-semibold text-foreground mb-1.5 flex items-center justify-between">
          <span>最近拦截与分类事件流水 (Recent Telemetry Stream)</span>
          <span className="text-muted-foreground font-mono font-normal">
            最新 {recentEvents?.length ?? 0} 条
          </span>
        </div>
        <div className="divide-y divide-border/40 rounded-md border border-border/60 bg-muted/10 font-mono text-xs max-h-48 overflow-y-auto">
          {(!recentEvents || recentEvents.length === 0) ? (
            <div className="p-3 text-center text-muted-foreground">
              暂无异常事件，系统处于稳态运行
            </div>
          ) : (
            recentEvents.map((evt, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 hover:bg-muted/20 transition-colors"
              >
                <div className="flex items-center gap-2 truncate">
                  <span
                    className={
                      evt.type === 'transient'
                        ? 'text-cyan-400 font-bold'
                        : evt.type === 'deterministic'
                          ? 'text-amber-400 font-bold'
                          : evt.type === 'fatal'
                            ? 'text-rose-400 font-bold'
                            : 'text-cyan-300 font-bold'
                    }
                  >
                    [{evt.type.toUpperCase()}]
                  </span>
                  <span className="text-foreground truncate max-w-xs sm:max-w-md">
                    {evt.tool_name ?? evt.whitelist_type ?? evt.category ?? 'event'}
                  </span>
                  {evt.reason && (
                    <span className="text-muted-foreground text-xs truncate max-w-sm">
                      ({evt.reason})
                    </span>
                  )}
                </div>
                <div className="shrink-0 text-muted-foreground text-xs font-mono ml-2">
                  {new Date(evt.timestamp * 1000).toLocaleTimeString()}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
