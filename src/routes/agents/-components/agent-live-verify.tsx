/**
 * agent-live-verify.tsx
 * 智能体通道桥连通性与真实工具调用验证 (Live Verification Sandbox) 组件。
 *
 * 遵循 Cockpit UI 视觉规范：
 * 1. 严格禁止使用绿色 🚫 (NO GREEN EVER)；
 * 2. 成功/正向使用冰青 (cyan-500/cyan-400)，异常使用玫瑰红 (rose-500)；
 * 3. 字号物理硬下限 >= 12px (text-xs)；
 * 4. 真实调用后端 /verify 端点，验证握手状态并回显 MCP 工具试跑结果。
 */

import * as React from 'react'
import {
  CheckCircle2Icon,
  LoaderCircleIcon,
  PlayIcon,
  RadioIcon,
  XCircleIcon,
  ZapIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'

export type VerificationResult = {
  status: string
  verified: boolean
  latency_ms: number
  agent_id: string
  agent_name?: string
  user_id: string
  authenticated: boolean
  active_plugins: string[]
  authorized_tool_count: number | string
  hooks_attached?: string[]
  tested_tool: string
  tool_call_result: {
    tool: string
    plugin_id?: string
    status: string
    result: Record<string, unknown>
  }
  bridge_handshake?: {
    protocol: string
    bridge_package: string
    handshake_verified: boolean
  }
  message: string
}

export type AgentLiveVerifyProps = {
  agentId: string
  userId: string
}

export function AgentLiveVerify({ agentId, userId }: AgentLiveVerifyProps) {
  const [isVerifying, setIsVerifying] = React.useState(false)
  const [verifyResult, setVerifyResult] = React.useState<VerificationResult | null>(null)
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null)

  // 发起通道桥真实握手与工具调用验证
  const handleVerifyConnection = async () => {
    setIsVerifying(true)
    setErrorMsg(null)
    try {
      const resp = await fetch(`/api/v1/users/${encodeURIComponent(userId)}/agents/${encodeURIComponent(agentId)}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_key: 'vk-live-probe-token',
        }),
      })

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => null)
        const errMsg = errJson?.detail || `HTTP ${resp.status}: 握手校验未通过`
        setErrorMsg(errMsg)
        toast.error(`连通性验证失败: ${errMsg}`)
        return
      }

      const data: VerificationResult = await resp.json()
      setVerifyResult(data)
      toast.success('连通性握手与工具试跑成功')
    } catch (err) {
      const msg = err instanceof Error ? err.message : '网络通信异常或端点不可达'
      setErrorMsg(msg)
      toast.error(`连通性验证失败: ${msg}`)
    } finally {
      setIsVerifying(false)
    }
  }

  return (
    <div className="rounded-md border border-cyan-500/40 bg-card p-3 space-y-2.5">
      {/* 头部标题与操作按钮 */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/50 pb-2">
        <div className="flex items-center gap-2">
          <CheckCircle2Icon className="size-4 text-cyan-500" />
          <span className="font-semibold text-foreground text-xs">
            通道桥连通性与真实工具调用验证 (Live Verification)
          </span>
        </div>
        <Button
          type="button"
          size="sm"
          onClick={handleVerifyConnection}
          disabled={isVerifying}
          className="h-7 gap-1 font-mono text-xs border border-cyan-500/40 bg-cyan-500/10 text-cyan-700 hover:bg-cyan-500/20 active:bg-cyan-500/30 dark:border-cyan-500/50 dark:bg-cyan-950/40 dark:text-cyan-300 dark:hover:bg-cyan-900/50"
        >
          {isVerifying ? (
            <LoaderCircleIcon className="size-3 animate-spin" />
          ) : (
            <PlayIcon className="size-3" />
          )}
          验证连通与工具调用
        </Button>
      </div>

      {/* 错误提示 */}
      {errorMsg && (
        <div className="flex items-start gap-2 rounded border border-rose-500/40 bg-rose-500/10 p-2.5 font-mono text-xs text-rose-700 dark:text-rose-400">
          <XCircleIcon className="size-4 shrink-0 text-rose-500" />
          <div>
            <div className="font-semibold">握手失败: {errorMsg}</div>
            <div className="text-muted-foreground mt-0.5">请检查所属用户的 API Key 格式或服务端 1933 端口状态。</div>
          </div>
        </div>
      )}

      {/* 成功握手与工具试跑回显 */}
      {verifyResult && (
        <div className="space-y-2 rounded border border-border/60 bg-muted/20 p-2.5 font-mono text-xs">
          <div className="flex flex-wrap items-center justify-between gap-1 border-b border-border/40 pb-1.5">
            <span className="text-cyan-600 dark:text-cyan-400 font-semibold">
              ● {verifyResult.message}
            </span>
            <Badge variant="outline" className="text-xs text-muted-foreground border-border/60">
              延迟 {verifyResult.latency_ms}ms
            </Badge>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-muted-foreground">
            <div>
              <span className="text-foreground font-medium">握手插件: </span>
              {verifyResult.active_plugins.join(', ')}
            </div>
            <div>
              <span className="text-foreground font-medium">可用工具数: </span>
              {verifyResult.authorized_tool_count} 项
            </div>
            <div>
              <span className="text-foreground font-medium">已测试工具: </span>
              <span className="text-cyan-600 dark:text-cyan-400">{verifyResult.tested_tool}</span>
            </div>
          </div>

          {verifyResult.hooks_attached && verifyResult.hooks_attached.length > 0 && (
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <ZapIcon className="size-3 text-amber-400 shrink-0" />
              <span>已挂载 Hook: </span>
              <span className="text-foreground">{verifyResult.hooks_attached.join(' · ')}</span>
            </div>
          )}

          <div className="rounded bg-background p-2 text-foreground/90 border border-border/40 overflow-x-auto">
            <div className="text-muted-foreground mb-1 flex items-center justify-between">
              <span>真实 MCP 工具调用证明:</span>
              <span className="text-xs">{verifyResult.bridge_handshake?.protocol || 'HTTP/SSE RPC'}</span>
            </div>
            <pre className="text-xs text-cyan-700 dark:text-cyan-300">
              {JSON.stringify(verifyResult.tool_call_result, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
