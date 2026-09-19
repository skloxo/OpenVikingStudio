import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Card } from '#/components/ui/card'
import { Badge } from '#/components/ui/badge'
import { RefreshCwIcon, ShieldCheckIcon, AlertTriangleIcon } from 'lucide-react'
import { ovClient } from '#/lib/ov-client'

interface HygieneResponse {
  status: string
  result: {
    health_score: number
    total_inspected: number
    dormant_count: number
    disputed_count: number
    orphaned_count: number
    stale_percentage: number
    inspection_ts: number
    latency_ms: number
    issues: Array<{
      uri: string
      issue_type: string
      severity: string
      detail: string
      recommendation: string
    }>
    recommendations: string[]
  }
}

export function KnowledgeHealthRadarCard() {
  const { t } = useTranslation('retrieval')

  const { data, isLoading, refetch, isFetching } = useQuery<HygieneResponse>({
    queryKey: ['knowledge-hygiene-health-report'],
    queryFn: async () => {
      const res = await ovClient.instance.get<HygieneResponse>('/api/v1/retrieval/hygiene/report')
      return res.data
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    staleTime: 15_000,
  })

  const report = data?.result
  const score = report?.health_score ?? 100
  const inspected = report?.total_inspected ?? 0
  const dormant = report?.dormant_count ?? 0
  const disputed = report?.disputed_count ?? 0

  // 5 Radar Dimensions (Normalized 0.0 to 1.0)
  const radarMetrics = useMemo(() => {
    if (!report || inspected === 0) {
      return [
        { label: '保真度', val: 0.95 },
        { label: '活跃度', val: 0.85 },
        { label: '连通度', val: 0.90 },
        { label: '新鲜度', val: 0.88 },
        { label: '防线', val: 0.98 },
      ]
    }
    const fidelity = Math.max(0.2, 1.0 - (disputed / Math.max(1, inspected)))
    const activity = Math.max(0.2, 1.0 - (dormant / Math.max(1, inspected)))
    const connectivity = Math.max(0.2, 1.0 - (report.orphaned_count / Math.max(1, inspected)))
    const freshness = Math.max(0.2, 1.0 - (report.stale_percentage / 100.0))
    const defense = 0.95

    return [
      { label: '保真度', val: fidelity },
      { label: '活跃度', val: activity },
      { label: '连通度', val: connectivity },
      { label: '新鲜度', val: freshness },
      { label: '防线', val: defense },
    ]
  }, [report, inspected, dormant, disputed])

  // SVG Radar Geometry: Center (100, 70), R=45
  const cx = 100
  const cy = 70
  const radius = 45

  const polygonPoints = useMemo(() => {
    const total = radarMetrics.length
    return radarMetrics
      .map((m, idx) => {
        const angle = (Math.PI * 2 * idx) / total - Math.PI / 2
        const r = radius * Math.min(1.0, Math.max(0.1, m.val))
        const x = cx + r * Math.cos(angle)
        const y = cy + r * Math.sin(angle)
        return `${x.toFixed(1)},${y.toFixed(1)}`
      })
      .join(' ')
  }, [radarMetrics])

  const gridLevels = [0.5, 1.0]

  return (
    <Card className="flex flex-col gap-3 p-3.5 shadow-none border-border/60 bg-card">
      <div className="flex items-center justify-between border-b border-border/40 pb-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <ShieldCheckIcon className="size-3.5 text-cyan-600 dark:text-cyan-400 shrink-0" />
          <h4 className="text-xs font-semibold text-foreground tracking-tight truncate">
            {t('retrieval.operationalTelemetry.healthRadar', '知识库健康度多维雷达')}
          </h4>
        </div>
        <div className="flex items-center gap-1.5">
          <Badge
            variant="outline"
            className={`text-xs font-mono tabular-nums ${
              score >= 80
                ? 'border-cyan-500/30 text-cyan-600 dark:text-cyan-400'
                : 'border-amber-500/30 text-amber-600 dark:text-amber-400'
            }`}
          >
            Score {isLoading ? '--' : score}
          </Badge>
          <button
            type="button"
            onClick={() => void refetch()}
            disabled={isFetching}
            title={t('retrieval.operationalTelemetry.runInspection', '立即巡检')}
            className="p-1 rounded hover:bg-muted/60 text-muted-foreground hover:text-foreground transition-colors cursor-pointer disabled:opacity-50"
          >
            <RefreshCwIcon className={`size-3 text-cyan-500 ${isFetching ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 items-center">
        {/* Left: SVG Radar Chart */}
        <div className="flex justify-center items-center py-1">
          <svg viewBox="0 0 200 145" className="w-40 h-28 overflow-visible select-none">
            {/* Concentric Grid Polygons */}
            {gridLevels.map((lvl) => {
              const pts = [0, 1, 2, 3, 4]
                .map((idx) => {
                  const angle = (Math.PI * 2 * idx) / 5 - Math.PI / 2
                  const r = radius * lvl
                  return `${(cx + r * Math.cos(angle)).toFixed(1)},${(cy + r * Math.sin(angle)).toFixed(1)}`
                })
                .join(' ')
              return (
                <polygon
                  key={lvl}
                  points={pts}
                  fill="none"
                  stroke="currentColor"
                  className="text-border/60"
                  strokeWidth="0.75"
                />
              )
            })}

            {/* Axis Radial Lines */}
            {[0, 1, 2, 3, 4].map((idx) => {
              const angle = (Math.PI * 2 * idx) / 5 - Math.PI / 2
              const x2 = cx + radius * Math.cos(angle)
              const y2 = cy + radius * Math.sin(angle)
              return (
                <line
                  key={idx}
                  x1={cx}
                  y1={cy}
                  x2={x2}
                  y2={y2}
                  stroke="currentColor"
                  className="text-border/40"
                  strokeWidth="0.75"
                />
              )
            })}

            {/* Active Radar Value Polygon */}
            <polygon
              points={polygonPoints}
              fill="rgba(6, 182, 212, 0.25)"
              stroke="#06b6d4"
              strokeWidth="1.5"
              className="transition-all duration-300"
            />

            {/* Labels at outer perimeter */}
            {radarMetrics.map((m, idx) => {
              const angle = (Math.PI * 2 * idx) / 5 - Math.PI / 2
              const r = radius + 15
              const lx = cx + r * Math.cos(angle)
              const ly = cy + r * Math.sin(angle) + 4
              return (
                <text
                  key={m.label}
                  x={lx}
                  y={ly}
                  textAnchor="middle"
                  className="fill-muted-foreground text-xs font-mono"
                  style={{ fontSize: '12px' }}
                >
                  {m.label}
                </text>
              )
            })}
          </svg>
        </div>

        {/* Right: Dimension Metrics */}
        <div className="flex flex-col gap-2">
          <div className="p-2 rounded bg-muted/20 border border-border/40 flex items-center justify-between">
            <span className="text-xs text-muted-foreground">在籍巡检样本</span>
            <span className="font-mono text-xs font-bold tabular-nums text-foreground">
              {isLoading ? '--' : `${inspected} 篇`}
            </span>
          </div>
          <div className="p-2 rounded bg-muted/20 border border-border/40 flex items-center justify-between">
            <span className="text-xs text-muted-foreground">休眠/死重条目</span>
            <span className="font-mono text-xs font-bold tabular-nums text-amber-600 dark:text-amber-400">
              {isLoading ? '--' : `${dormant} 项`}
            </span>
          </div>
          <div className="p-2 rounded bg-muted/20 border border-border/40 flex items-center justify-between">
            <span className="text-xs text-muted-foreground">存疑冲突条目</span>
            <span className="font-mono text-xs font-bold tabular-nums text-foreground">
              {isLoading ? '--' : `${disputed} 项`}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-auto pt-1 text-xs text-muted-foreground border-t border-border/30 flex items-center justify-between">
        <span className="flex items-center gap-1 truncate">
          <AlertTriangleIcon className="size-3 text-cyan-500" />
          {report?.recommendations[0] ?? '知识卫生状态健康，无严重漂移'}
        </span>
      </div>
    </Card>
  )
}
