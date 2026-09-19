import { useState, useEffect, useCallback } from 'react'
import {
  GaugeIcon,
  ActivityIcon,
  SlidersIcon,
  UserCheckIcon,
  SparklesIcon,
} from 'lucide-react'

interface SensorSummaryData {
  sample_count: number
  avg_token_snr: number
  avg_p5_precision: number
  human_intervention_rate: number
  snr_status: string
  p5_status: string
  intervention_status: string
  recent_timeline: Array<{
    session_id: string
    token_snr: number
    p5_precision: number
    interventions: number
    timestamp: number
  }>
}

export function AgentSensorsCard() {
  const [data, setData] = useState<SensorSummaryData | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchMetrics = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/metrics/agent-sensors')
      if (res.ok) {
        const json = await res.json()
        setData(json.data)
      }
    } catch {
      // Keep existing state on error
    }
  }, [])

  useEffect(() => {
    fetchMetrics()
    const interval = setInterval(fetchMetrics, 30_000)
    return () => clearInterval(interval)
  }, [fetchMetrics])

  const handleInjectSample = async () => {
    setLoading(true)
    try {
      const randomId = `sess_${Math.random().toString(36).substring(2, 8)}`
      await fetch('/api/v1/metrics/agent-sensors/sample', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: randomId,
          effective_tokens: 720,
          total_tokens: 1000,
          top5_hits: 4,
          interventions_count: 0,
        }),
      })
      await fetchMetrics()
    } finally {
      setLoading(false)
    }
  }

  const hasData = data && data.sample_count > 0

  return (
    <div className="rounded-lg border border-border/60 bg-card/40 p-4 space-y-4 font-sans text-xs text-muted-foreground">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded bg-cyan-500/10 text-cyan-500">
            <GaugeIcon className="size-4" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-foreground tracking-tight">
              智能体三维效能物理探针 (Agent 3D Performance Sensors)
            </h3>
            <p className="text-[12px] text-muted-foreground">
              基于 CPA 导师第一性原理物理标尺：Token SNR 有效载荷率、P@5 召回采纳率与人工介入率
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-muted-foreground">
            样本数: <span className="text-foreground font-semibold">{data?.sample_count ?? 0}</span>
          </span>
          <button
            type="button"
            onClick={handleInjectSample}
            disabled={loading}
            className="px-2.5 py-1 rounded bg-secondary hover:bg-secondary/80 text-foreground text-xs font-mono transition-colors flex items-center gap-1 cursor-pointer"
          >
            <SparklesIcon className="size-3 text-cyan-500" />
            + 注入会话采样
          </button>
        </div>
      </div>

      {/* 3 Main Physical Gauges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* Gauge 1: Token SNR */}
        <div className="rounded-md border border-border/40 bg-background/50 p-3.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-foreground flex items-center gap-1.5">
              <ActivityIcon className="size-3.5 text-cyan-500" />
              Token SNR 有效载荷率
            </span>
            <span
              className={`text-[12px] font-mono px-1.5 py-0.5 rounded ${
                hasData && data.snr_status === 'optimal'
                  ? 'bg-cyan-500/10 text-cyan-500'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              {hasData ? (data.snr_status === 'optimal' ? 'SNR OPTIMAL' : 'DEGRADED') : '--'}
            </span>
          </div>

          <div className="flex items-baseline gap-2">
            <span className="text-lg font-bold font-mono text-foreground">
              {hasData ? `${(data.avg_token_snr * 100).toFixed(1)}%` : '--'}
            </span>
            <span className="text-xs text-muted-foreground font-mono">基线目标: ≥65.0%</span>
          </div>

          <div className="text-[12px] text-muted-foreground leading-relaxed">
            有效指令与代码 Token 占会话全上下文的比重，杜绝冗余水话与无意义 prompt 堆叠。
          </div>
        </div>

        {/* Gauge 2: P@5 Precision */}
        <div className="rounded-md border border-border/40 bg-background/50 p-3.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-foreground flex items-center gap-1.5">
              <SlidersIcon className="size-3.5 text-cyan-500" />
              P@5 召回采纳精度
            </span>
            <span
              className={`text-[12px] font-mono px-1.5 py-0.5 rounded ${
                hasData && data.p5_status === 'optimal'
                  ? 'bg-cyan-500/10 text-cyan-500'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              {hasData ? (data.p5_status === 'optimal' ? 'TARGET REACHED' : 'SUBOPTIMAL') : '--'}
            </span>
          </div>

          <div className="flex items-baseline gap-2">
            <span className="text-lg font-bold font-mono text-foreground">
              {hasData ? `${(data.avg_p5_precision * 100).toFixed(1)}%` : '--'}
            </span>
            <span className="text-xs text-muted-foreground font-mono">基线目标: ≥80.0%</span>
          </div>

          <div className="text-[12px] text-muted-foreground leading-relaxed">
            Top-5 检索结果中被 Agent 在后续生成与规划中实际引用的比例，衡量检索真实有效性。
          </div>
        </div>

        {/* Gauge 3: Human Intervention Rate */}
        <div className="rounded-md border border-border/40 bg-background/50 p-3.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-foreground flex items-center gap-1.5">
              <UserCheckIcon className="size-3.5 text-cyan-500" />
              人工介入纠偏率
            </span>
            <span
              className={`text-[12px] font-mono px-1.5 py-0.5 rounded ${
                hasData && data.intervention_status === 'elevated'
                  ? 'bg-rose-500/10 text-rose-500'
                  : 'bg-cyan-500/10 text-cyan-500'
              }`}
            >
              {hasData ? (data.intervention_status === 'optimal' ? 'STEERING LOW' : 'ELEVATED') : '--'}
            </span>
          </div>

          <div className="flex items-baseline gap-2">
            <span className="text-lg font-bold font-mono text-foreground">
              {hasData ? `${(data.human_intervention_rate * 100).toFixed(1)}%` : '--'}
            </span>
            <span className="text-xs text-muted-foreground font-mono">上限红线: ≤15.0%</span>
          </div>

          <div className="text-[12px] text-muted-foreground leading-relaxed">
            人类被迫输入打断、指正或反问的会话比重，度量智能体自主闭环交付的真实可信度。
          </div>
        </div>
      </div>

      {/* Timeline Trend Stream */}
      {data?.recent_timeline && data.recent_timeline.length > 0 && (
        <div className="rounded-md border border-border/30 bg-muted/20 p-3 space-y-2">
          <div className="flex items-center justify-between text-[12px] text-muted-foreground">
            <span>近期会话时序探针采样流 (Recent 20 Sessions)</span>
            <span className="font-mono">~/.openviking/data/agent_metrics.jsonl</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-1.5 pt-1 font-mono text-[12px]">
            {data.recent_timeline.map((pt, idx) => (
              <div
                key={idx}
                className="p-1.5 rounded border border-border/30 bg-background/60 flex items-center justify-between"
                title={`Session: ${pt.session_id} | Interventions: ${pt.interventions}`}
              >
                <span className="truncate max-w-[70px] text-muted-foreground">{pt.session_id}</span>
                <span className="text-cyan-500 font-semibold">{Math.round(pt.token_snr * 100)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
