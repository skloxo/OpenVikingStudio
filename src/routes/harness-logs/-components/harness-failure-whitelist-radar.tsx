import { useQuery } from '@tanstack/react-query'
import { Badge } from '#/components/ui/badge'
import { ovClient } from '#/lib/ov-client'
import {
  FileCheckIcon,
  FlameIcon,
  RepeatIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
  ZapIcon,
} from 'lucide-react'
import { HarnessFailureSandboxProbe } from './harness-failure-sandbox-probe'

export interface FailureTaxonomyData {
  transient_count: number
  deterministic_count: number
  fatal_count: number
  total_failures: number
  blocked_fingerprints_count: number
  transient_retries_used: number
  max_transient_retries: number
  anti_loop_interceptions: number
  whitelist_items_count: number
  whitelist_by_type: Record<string, number>
  whitelist_preservation_rate: number
  estimated_tokens_saved: number
  recent_events: Array<{
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
  timestamp: number
  status: string
}

export function HarnessFailureWhitelistRadar() {
  const telemetryQuery = useQuery({
    queryKey: ['failure-taxonomy-telemetry'],
    queryFn: async () => {
      const res = await ovClient.instance.get<FailureTaxonomyData>(
        '/api/v1/system/failure_taxonomy_metrics'
      )
      return res.data
    },
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
    staleTime: 10_000,
  })

  const data = telemetryQuery.data

  return (
    <div className="flex flex-col gap-4">
      {/* 4 Primary High-Density Metric Tiles */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {/* Metric 1: Transient Retry Budget */}
        <div className="rounded-md border border-border/60 bg-card p-3.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>瞬态重试预算 (Retry Budget)</span>
            <RepeatIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="mt-1 font-mono text-xl font-bold tabular-nums text-foreground">
            {data?.transient_retries_used ?? 0}
            <span className="text-xs font-normal text-muted-foreground ml-1">
              / {data?.max_transient_retries ?? 3} 次消耗
            </span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground font-mono">
            指数退避 (0.1s ➔ 0.4s) 动态抗抖动
          </div>
        </div>

        {/* Metric 2: Anti-Loop Blocked Fingerprints */}
        <div className="rounded-md border border-border/60 bg-card p-3.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Anti-Loop 物理阻断指纹</span>
            <ShieldAlertIcon className="size-3.5 text-amber-600 dark:text-amber-400" />
          </div>
          <div className="mt-1 font-mono text-xl font-bold tabular-nums text-foreground">
            {data?.anti_loop_interceptions ?? 0}
            <span className="text-xs font-normal text-muted-foreground ml-1">次拦截</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground font-mono">
            已阻断 {data?.blocked_fingerprints_count ?? 0} 个重复死循环参数指纹
          </div>
        </div>

        {/* Metric 3: Fatal Halts */}
        <div className="rounded-md border border-border/60 bg-card p-3.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>致命异常即刻刹车 (Fatal Halts)</span>
            <FlameIcon className="size-3.5 text-rose-600 dark:text-rose-400" />
          </div>
          <div className="mt-1 font-mono text-xl font-bold tabular-nums text-foreground">
            {data?.fatal_count ?? 0}
            <span className="text-xs font-normal text-muted-foreground ml-1">次熔断</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground font-mono">
            越权、沙箱逃逸与 OOM 立即停止
          </div>
        </div>

        {/* Metric 4: Compression Whitelist Preservation */}
        <div className="rounded-md border border-border/60 bg-card p-3.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>免压缩白名单保真度</span>
            <FileCheckIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="mt-1 font-mono text-xl font-bold tabular-nums text-cyan-700 dark:text-cyan-400">
            {data?.whitelist_preservation_rate != null ? `${data.whitelist_preservation_rate}%` : '--'}
            <span className="text-xs font-normal text-muted-foreground ml-1">
              ({data?.whitelist_items_count != null ? `${data.whitelist_items_count} 项` : '--'})
            </span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground font-mono">
            {data?.estimated_tokens_saved != null
              ? `估算累计免损保护 ${data.estimated_tokens_saved} Tokens`
              : '估算累计免损保护 --'}
          </div>
        </div>
      </div>

      {/* Main Two Panels: Failure Taxonomy Profile & Whitelist Radar */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Left: Failure Taxonomy Profile */}
        <div className="flex flex-col gap-3 rounded-md border border-border/60 bg-card p-4">
          <div className="flex items-center justify-between border-b border-border/60 pb-2.5">
            <div>
              <h2 className="text-xs font-bold text-foreground flex items-center gap-1.5">
                <ShieldCheckIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                工具失败分类画像 (Failure Taxonomy Profile)
              </h2>
              <p className="text-xs text-muted-foreground">
                瞬态、确定性与致命三层故障分类及物理抗死循环防线
              </p>
            </div>
            <Badge variant="outline" className="text-xs font-mono border-cyan-200 bg-cyan-50 text-cyan-800 dark:border-cyan-500/30 dark:bg-cyan-950/20 dark:text-cyan-400">
              AgentScope 2.0 Invariant
            </Badge>
          </div>

          <div className="space-y-2.5">
            {/* Transient Bar */}
            <div className="rounded-md border border-border/60 bg-muted/20 p-3">
              <div className="flex items-center justify-between text-xs font-medium text-foreground">
                <span className="flex items-center gap-1.5">
                  <span className="size-2 rounded-full bg-cyan-500 dark:bg-cyan-400" />
                  瞬态错误 (Transient)
                </span>
                <span className="font-mono text-cyan-700 dark:text-cyan-400 tabular-nums">
                  {data?.transient_count ?? 0} 次 / 允许退避重试
                </span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                网络超时、HTTP 429、503 抖动。采用指数退避重试（上限 {data?.max_transient_retries ?? 3} 次），防范无效高频重试压垮上游。
              </p>
            </div>

            {/* Deterministic Bar */}
            <div className="rounded-md border border-border/60 bg-muted/20 p-3">
              <div className="flex items-center justify-between text-xs font-medium text-foreground">
                <span className="flex items-center gap-1.5">
                  <span className="size-2 rounded-full bg-amber-500 dark:bg-amber-400" />
                  确定性错误 (Deterministic)
                </span>
                <span className="font-mono text-amber-700 dark:text-amber-400 tabular-nums">
                  {data?.deterministic_count ?? 0} 次 / Anti-Loop 物理门锁
                </span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                HTTP 400、参数缺失、类型不匹配。<strong>Anti-Loop Barrier</strong> 立即阻断相同入参重复调用，并生成反思 Prompt 引导 Agent 纠偏。
              </p>
            </div>

            {/* Fatal Bar */}
            <div className="rounded-md border border-border/60 bg-muted/20 p-3">
              <div className="flex items-center justify-between text-xs font-medium text-foreground">
                <span className="flex items-center gap-1.5">
                  <span className="size-2 rounded-full bg-rose-500 dark:bg-rose-400" />
                  致命错误 (Fatal)
                </span>
                <span className="font-mono text-rose-700 dark:text-rose-400 tabular-nums">
                  {data?.fatal_count ?? 0} 次 / 物理即刻刹车
                </span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                沙箱越权逃逸、鉴权吊销、内存耗尽。零等待立即阻断所有下游工具派发，防止损坏宿主系统。
              </p>
            </div>
          </div>
        </div>

        {/* Right: Abstract Workspace Whitelist Sensor */}
        <div className="flex flex-col gap-3 rounded-md border border-border/60 bg-card p-4">
          <div className="flex items-center justify-between border-b border-border/60 pb-2.5">
            <div>
              <h2 className="text-xs font-bold text-foreground flex items-center gap-1.5">
                <FileCheckIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                AFS 免压缩白名单保真雷达 (Compression Whitelist)
              </h2>
              <p className="text-xs text-muted-foreground">
                核心规划与租户授权状态物理豁免有损 Compaction 压缩
              </p>
            </div>
            <Badge variant="outline" className="text-xs font-mono border-cyan-200 bg-cyan-50 text-cyan-800 dark:border-cyan-500/30 dark:bg-cyan-950/20 dark:text-cyan-400">
              DeepSeek-Harness SSOT
            </Badge>
          </div>

          <div className="space-y-2.5">
            {/* TaskPlan Invariant */}
            <div className="rounded-md border border-border/60 bg-muted/20 p-3">
              <div className="flex items-center justify-between text-xs font-medium text-foreground">
                <span className="font-mono text-foreground flex items-center gap-1.5">
                  <ZapIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                  TaskPlan (任务蓝图与长程工单)
                </span>
                <Badge variant="outline" className="text-xs font-mono border-cyan-200 bg-cyan-50 text-cyan-800 dark:border-cyan-500/30 dark:bg-cyan-950/20 dark:text-cyan-400">
                  {data?.whitelist_by_type.TaskPlan ?? 0} 项受保
                </Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                多阶段长程规划与依赖拓扑。物理锁定不可压缩，杜绝多次 Summarize 导致的步骤遗忘与目标漂移。
              </p>
            </div>

            {/* SubAgentTracker Invariant */}
            <div className="rounded-md border border-border/60 bg-muted/20 p-3">
              <div className="flex items-center justify-between text-xs font-medium text-foreground">
                <span className="font-mono text-foreground flex items-center gap-1.5">
                  <RepeatIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                  SubAgentTracker (子代理血缘追踪)
                </span>
                <Badge variant="outline" className="text-xs font-mono border-cyan-200 bg-cyan-50 text-cyan-800 dark:border-cyan-500/30 dark:bg-cyan-950/20 dark:text-cyan-400">
                  {data?.whitelist_by_type.SubAgentTracker ?? 0} 项受保
                </Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                卫星舰队与多角色协作上下文。追踪 Client@Node 身份与派工责任链，禁止在截断中丢失通信句柄。
              </p>
            </div>

            {/* AuthGrants Invariant */}
            <div className="rounded-md border border-border/60 bg-muted/20 p-3">
              <div className="flex items-center justify-between text-xs font-medium text-foreground">
                <span className="font-mono text-foreground flex items-center gap-1.5">
                  <ShieldCheckIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                  AuthGrants (多租户企业授权与权限)
                </span>
                <Badge variant="outline" className="text-xs font-mono border-cyan-200 bg-cyan-50 text-cyan-800 dark:border-cyan-500/30 dark:bg-cyan-950/20 dark:text-cyan-400">
                  {data?.whitelist_by_type.AuthGrants ?? 0} 项受保
                </Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                企业级租户 ID、角色清单与最小特权令牌。绝对禁止进入上下文压缩流水线，防止权限漂移。
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Sandbox Probe & Audit Log */}
      <HarnessFailureSandboxProbe recentEvents={data?.recent_events} />
    </div>
  )
}
