/**
 * network-search-dashboard.tsx
 * 26-Key 微缩健康矩阵胶囊与45天滚动归档大盘组件 (Cockpit UI 规范)。
 * NO GREEN EVER 🚫，字号 >= 12px，font-mono 代码与标签，6px 微圆角。
 */

import * as React from 'react'
import {
  ActivityIcon,
  ArchiveIcon,
  DatabaseIcon,
  RefreshCwIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'

export type KeyItem = {
  key_id: string
  engine: string
  alias: string
  fingerprint: string
  status: 'ready' | 'active' | 'rate_limited' | 'exhausted'
  total_calls: number
  total_credits: number
  monthly_quota: number
  rate_limit_calls: number
  last_call_at: string
}

export type WatermarkInfo = {
  used_calls?: number
  used_credits?: number
  total_quota: number
  unit: string
}

export type SearchUsageSummary = {
  status: string
  month: string
  total_keys: number
  keys: KeyItem[]
  watermarks: {
    keenable: WatermarkInfo
    exa: WatermarkInfo
    tavily: WatermarkInfo
  }
  db_stats: {
    db_size_bytes: number
    detail_records: number
    archived_summary_records: number
    db_path: string
  }
  updated_at: number
}

export function NetworkSearchDashboard() {
  const [data, setData] = React.useState<SearchUsageSummary | null>(null)
  const [isLoading, setIsLoading] = React.useState(true)
  const [isPruning, setIsPruning] = React.useState(false)

  const fetchSummary = React.useCallback(async () => {
    try {
      setIsLoading(true)
      const res = await fetch('/api/v1/plugins/network-search/usage/summary')
      if (res.ok) {
        const json = await res.json()
        setData(json)
      }
    } catch {
      // 降级静音处理
    } finally {
      setIsLoading(false)
    }
  }, [])

  React.useEffect(() => {
    fetchSummary()
  }, [fetchSummary])

  const handlePrune = async () => {
    try {
      setIsPruning(true)
      const res = await fetch('/api/v1/plugins/network-search/usage/prune?retention_days=45', {
        method: 'POST',
      })
      if (res.ok) {
        await fetchSummary()
      }
    } finally {
      setIsPruning(false)
    }
  }

  if (isLoading && !data) {
    return (
      <div className="rounded-md border border-border/60 bg-muted/10 p-4 text-center text-xs font-mono text-muted-foreground animate-pulse">
        加载 26-Key 实时流水与配额大盘...
      </div>
    )
  }

  if (!data) return null

  const getStatusBadgeClass = (status: KeyItem['status']) => {
    switch (status) {
      case 'active':
        return 'border-cyan-500/30 bg-cyan-500/10 text-cyan-700 dark:text-cyan-400'
      case 'rate_limited':
        return 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400'
      case 'exhausted':
        return 'border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-400'
      case 'ready':
      default:
        return 'border-border/60 bg-muted/30 text-muted-foreground'
    }
  }

  const getStatusText = (status: KeyItem['status']) => {
    switch (status) {
      case 'active':
        return '活跃'
      case 'rate_limited':
        return '冷却'
      case 'exhausted':
        return '耗尽'
      case 'ready':
      default:
        return '就绪'
    }
  }

  const keysByEngine = {
    keenable: data.keys.filter((k) => k.engine === 'keenable'),
    exa: data.keys.filter((k) => k.engine === 'exa'),
    tavily: data.keys.filter((k) => k.engine === 'tavily'),
  }

  return (
    <div className="space-y-4 rounded-md border border-border/70 bg-card/40 p-3.5">
      {/* 头部标题与刷新 */}
      <div className="flex items-center justify-between border-b border-border/50 pb-2.5">
        <div className="flex items-center gap-2">
          <ActivityIcon className="size-4 text-cyan-400" />
          <h4 className="text-xs font-semibold text-foreground tracking-tight">
            26-Key 微缩健康矩阵与月度配额大盘
          </h4>
          <Badge variant="outline" className="text-xs font-mono border-border/60 px-1.5 py-0">
            {data.month}
          </Badge>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-xs font-mono text-muted-foreground hover:text-foreground"
          onClick={fetchSummary}
        >
          <RefreshCwIcon className="mr-1 size-3" />
          刷新
        </Button>
      </div>

      {/* 1. 三大引擎月度配额水位条 */}
      <div className="grid grid-cols-3 gap-2">
        {/* Keenable 水位 */}
        <div className="rounded border border-border/50 bg-muted/20 p-2 text-xs">
          <div className="flex justify-between text-muted-foreground font-mono">
            <span>Keenable (80万次)</span>
            <span className="text-foreground font-medium">
              {(data.watermarks.keenable.used_calls || 0).toLocaleString()} / 800,000
            </span>
          </div>
          <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted/50">
            <div
              className="h-full bg-cyan-500 transition-all"
              style={{
                width: `${Math.min(
                  100,
                  ((data.watermarks.keenable.used_calls || 0) / 800000) * 100
                )}%`,
              }}
            />
          </div>
        </div>

        {/* Exa 水位 */}
        <div className="rounded border border-border/50 bg-muted/20 p-2 text-xs">
          <div className="flex justify-between text-muted-foreground font-mono">
            <span>Exa ($90 额度)</span>
            <span className="text-foreground font-medium">
              ${(data.watermarks.exa.used_credits || 0).toFixed(2)} / $90.00
            </span>
          </div>
          <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted/50">
            <div
              className="h-full bg-cyan-500 transition-all"
              style={{
                width: `${Math.min(
                  100,
                  ((data.watermarks.exa.used_credits || 0) / 90.0) * 100
                )}%`,
              }}
            />
          </div>
        </div>

        {/* Tavily 水位 */}
        <div className="rounded border border-border/50 bg-muted/20 p-2 text-xs">
          <div className="flex justify-between text-muted-foreground font-mono">
            <span>Tavily (9000分)</span>
            <span className="text-foreground font-medium">
              {(data.watermarks.tavily.used_credits || 0).toFixed(0)} / 9,000
            </span>
          </div>
          <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted/50">
            <div
              className="h-full bg-cyan-500 transition-all"
              style={{
                width: `${Math.min(
                  100,
                  ((data.watermarks.tavily.used_credits || 0) / 9000) * 100
                )}%`,
              }}
            />
          </div>
        </div>
      </div>

      {/* 2. 26 Key 微缩健康矩阵胶囊 */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="font-mono">Key 指纹脱敏微缩网格 (8 Keenable + 9 Exa + 9 Tavily)</span>
          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="flex items-center gap-1 text-muted-foreground">
              <span className="size-1.5 rounded-full bg-muted-foreground" /> 就绪
            </span>
            <span className="flex items-center gap-1 text-cyan-400">
              <span className="size-1.5 rounded-full bg-cyan-400" /> 活跃
            </span>
            <span className="flex items-center gap-1 text-amber-400">
              <span className="size-1.5 rounded-full bg-amber-400" /> 429冷却
            </span>
            <span className="flex items-center gap-1 text-rose-400">
              <span className="size-1.5 rounded-full bg-rose-400" /> 耗尽
            </span>
          </div>
        </div>

        {/* 各引擎胶囊行 */}
        <div className="space-y-2">
          {/* Keenable 矩阵 */}
          <div className="rounded border border-border/40 bg-card/30 p-2">
            <div className="mb-1 text-xs font-mono font-medium text-muted-foreground">
              Keenable (8 Keys · 80万次池)
            </div>
            <div className="grid grid-cols-4 gap-1.5">
              {keysByEngine.keenable.map((k) => (
                <div
                  key={k.key_id}
                  className={`flex flex-col rounded border p-1.5 text-xs font-mono transition-colors ${getStatusBadgeClass(
                    k.status
                  )}`}
                  title={`账号: ${k.alias}\n调用: ${k.total_calls}次\n429限流: ${k.rate_limit_calls}次\n最后使用: ${k.last_call_at}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{k.fingerprint}</span>
                    <span className="text-xs opacity-80">{getStatusText(k.status)}</span>
                  </div>
                  <div className="mt-0.5 text-xs opacity-75">
                    {k.total_calls} 次 / {k.total_credits.toFixed(0)} pts
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Exa 矩阵 */}
          <div className="rounded border border-border/40 bg-card/30 p-2">
            <div className="mb-1 text-xs font-mono font-medium text-muted-foreground">
              Exa (9 Keys · $90额度池)
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {keysByEngine.exa.map((k) => (
                <div
                  key={k.key_id}
                  className={`flex flex-col rounded border p-1.5 text-xs font-mono transition-colors ${getStatusBadgeClass(
                    k.status
                  )}`}
                  title={`账号: ${k.alias}\n调用: ${k.total_calls}次\n费用: $${k.total_credits.toFixed(
                    3
                  )}\n429限流: ${k.rate_limit_calls}次\n最后使用: ${k.last_call_at}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{k.fingerprint}</span>
                    <span className="text-xs opacity-80">{getStatusText(k.status)}</span>
                  </div>
                  <div className="mt-0.5 text-xs opacity-75">
                    {k.total_calls} 次 / ${k.total_credits.toFixed(3)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Tavily 矩阵 */}
          <div className="rounded border border-border/40 bg-card/30 p-2">
            <div className="mb-1 text-xs font-mono font-medium text-muted-foreground">
              Tavily (9 Keys · 9,000积分池)
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {keysByEngine.tavily.map((k) => (
                <div
                  key={k.key_id}
                  className={`flex flex-col rounded border p-1.5 text-xs font-mono transition-colors ${getStatusBadgeClass(
                    k.status
                  )}`}
                  title={`账号: ${k.alias}\n调用: ${k.total_calls}次\n消耗积分: ${k.total_credits.toFixed(
                    1
                  )}\n429限流: ${k.rate_limit_calls}次\n最后使用: ${k.last_call_at}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{k.fingerprint}</span>
                    <span className="text-xs opacity-80">{getStatusText(k.status)}</span>
                  </div>
                  <div className="mt-0.5 text-xs opacity-75">
                    {k.total_calls} 次 / {k.total_credits.toFixed(1)} pts
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 3. 45天自动滚动归档与物理防爆指示器 */}
      <div className="flex items-center justify-between rounded border border-border/50 bg-muted/20 p-2.5 text-xs">
        <div className="flex items-center gap-2 font-mono">
          <DatabaseIcon className="size-3.5 text-cyan-400" />
          <span className="text-muted-foreground">45天滚动防爆存储:</span>
          <span className="text-foreground">
            {data.db_stats.detail_records} 条实时流水 / {data.db_stats.archived_summary_records} 条日归档
          </span>
          <span className="text-muted-foreground">
            ({(data.db_stats.db_size_bytes / 1024).toFixed(1)} KB)
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="h-6 px-2 text-xs font-mono"
          onClick={handlePrune}
          disabled={isPruning}
        >
          <ArchiveIcon className="mr-1 size-3 text-cyan-400" />
          {isPruning ? '归档清理中...' : '立即滚动归档'}
        </Button>
      </div>
    </div>
  )
}
