import { useState, useEffect, useCallback } from 'react'
import {
  ShieldAlertIcon,
  RefreshCwIcon,
  MoonIcon,
  LayersIcon,
  AlertTriangleIcon,
  ActivityIcon,
  SlidersIcon,
  SparklesIcon,
} from 'lucide-react'

interface PackageItem {
  package_id: string
  target_skill: string
  line_count: number
  current_stage: string
  canary_traffic_pct: number
  passed_safety_gate: boolean
  rolled_back: boolean
}

interface GovernanceState {
  autonomous_level: string
  emergency_kill_switch_tripped: boolean
  auto_downgrade_count: number
  second_order_metrics: {
    output_length_ratio: number
    refusal_rate: number
    retry_rate: number
    drift_detected: boolean
  }
}

interface DreamingStatus {
  status: string
  total_traces_scanned: number
  defects_mined: number
  crystals_fused: number
  defects: Array<{
    defect_id: string
    cluster_topic: string
    severity: string
    failing_traces_count: number
    candidate_patch: string
  }>
}

const STAGES = [
  'signal_aggregation',
  'candidate_generation',
  'isolated_evaluation',
  'safety_gate',
  'canary_rollout',
  'monitoring_rollback',
  'experience_crystallization',
]

export function EvolutionCICDCockpit() {
  const [governance, setGovernance] = useState<GovernanceState | null>(null)
  const [packages, setPackages] = useState<PackageItem[]>([])
  const [dreaming, setDreaming] = useState<DreamingStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [targetSkill, setTargetSkill] = useState('agent-friendly-code-org')
  const [samplePatch, setSamplePatch] = useState('+- DO NOT exceed 300 lines\n+- INSTEAD extract seam early')

  const fetchData = useCallback(async () => {
    try {
      const [govRes, pkgRes, dreamRes] = await Promise.all([
        fetch('/api/v1/evolution/governance'),
        fetch('/api/v1/evolution/pipeline/packages'),
        fetch('/api/v1/evolution/dreaming/status'),
      ])
      if (govRes.ok) setGovernance(await govRes.json())
      if (pkgRes.ok) {
        const d = await pkgRes.json()
        setPackages(d.packages || [])
      }
      if (dreamRes.ok) setDreaming(await dreamRes.json())
    } catch {
      // Keep state intact on fetch failure
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleCreatePackage = async () => {
    setLoading(true)
    try {
      await fetch('/api/v1/evolution/pipeline/package', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_skill: targetSkill, diff_patch: samplePatch }),
      })
      await fetchData()
    } finally {
      setLoading(false)
    }
  }

  const handleAdvance = async (pkgId: string) => {
    setLoading(true)
    try {
      await fetch('/api/v1/evolution/pipeline/advance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ package_id: pkgId }),
      })
      await fetchData()
    } finally {
      setLoading(false)
    }
  }

  const handleTriggerDreaming = async () => {
    setLoading(true)
    try {
      await fetch('/api/v1/evolution/dreaming/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ traces: [{ success: false, category: 'InstructionDrift' }] }),
      })
      await fetchData()
    } finally {
      setLoading(false)
    }
  }

  const handleEmergencyRollback = async () => {
    setLoading(true)
    try {
      await fetch('/api/v1/evolution/governance/rollback', { method: 'POST' })
      await fetchData()
    } finally {
      setLoading(false)
    }
  }

  const handleSetLevel = async (level: string) => {
    setLoading(true)
    try {
      await fetch('/api/v1/evolution/governance/level', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ level }),
      })
      await fetchData()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4 text-xs font-sans text-muted-foreground">
      {/* 4 KPI Tiles */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="rounded-md border border-border/40 bg-card/40 p-3.5 space-y-1">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs">自治等级阶梯</span>
            <SlidersIcon className="size-3.5 text-cyan-500" />
          </div>
          <div className="text-sm font-semibold font-mono text-foreground">
            {governance?.autonomous_level ? governance.autonomous_level.toUpperCase() : '--'}
          </div>
          <div className="text-xs text-muted-foreground">
            自动降级次数: <span className="font-mono text-foreground">{governance?.auto_downgrade_count ?? 0}</span>
          </div>
        </div>

        <div className="rounded-md border border-border/40 bg-card/40 p-3.5 space-y-1">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs">流水线变更包</span>
            <LayersIcon className="size-3.5 text-cyan-500" />
          </div>
          <div className="text-sm font-semibold font-mono text-foreground">{packages.length} 活跃</div>
          <div className="text-xs text-muted-foreground">严格保持 ≤300 行甜点区</div>
        </div>

        <div className="rounded-md border border-border/40 bg-card/40 p-3.5 space-y-1">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs">二阶漂移风险</span>
            <ActivityIcon className="size-3.5 text-cyan-500" />
          </div>
          <div className="text-sm font-semibold font-mono text-foreground">
            {governance?.second_order_metrics?.drift_detected ? (
              <span className="text-rose-500">DRIFT ALERT</span>
            ) : (
              <span className="text-cyan-500">NORMAL (0 漂移)</span>
            )}
          </div>
          <div className="text-xs text-muted-foreground">
            拒答率: {(governance?.second_order_metrics?.refusal_rate ?? 0) * 100}% | 重试率:{' '}
            {(governance?.second_order_metrics?.retry_rate ?? 0) * 100}%
          </div>
        </div>

        <div className="rounded-md border border-border/40 bg-card/40 p-3.5 space-y-1">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs">Dreaming 聚类缺陷</span>
            <MoonIcon className="size-3.5 text-cyan-500" />
          </div>
          <div className="text-sm font-semibold font-mono text-foreground">
            {dreaming?.defects_mined ?? 0} 缺陷 | {dreaming?.crystals_fused ?? 0} 结晶
          </div>
          <div className="text-xs text-muted-foreground">夜间统一周期熔铸</div>
        </div>
      </div>

      {/* Seven-Stage Pipeline Stream & Human Inviolable Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* Left 2 Cols: Pipeline Stream */}
        <div className="lg:col-span-2 rounded-md border border-border/40 bg-card/40 p-3.5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <RefreshCwIcon className="size-3.5 text-cyan-500" />
              <span className="text-xs font-medium text-foreground">七阶段变更流水线泳道</span>
            </div>
            <button
              onClick={handleCreatePackage}
              disabled={loading}
              className="px-2.5 py-1 rounded bg-secondary hover:bg-secondary/80 text-foreground text-xs font-mono transition-colors"
            >
              + 注入演化候选 Patch
            </button>
          </div>

          <div className="space-y-2">
            {packages.length === 0 ? (
              <div className="py-6 text-center text-xs text-muted-foreground border border-dashed border-border/40 rounded">
                暂无活跃流水线包，点击右上角注入候选 Patch
              </div>
            ) : (
              packages.map((pkg) => (
                <div key={pkg.package_id} className="p-2.5 rounded border border-border/30 bg-background/50 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-foreground font-semibold">
                      {pkg.package_id} ({pkg.target_skill})
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                        {pkg.line_count} 行
                      </span>
                      {pkg.rolled_back && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-500 font-mono">
                          ROLLED BACK
                        </span>
                      )}
                      <button
                        onClick={() => handleAdvance(pkg.package_id)}
                        disabled={loading || pkg.rolled_back}
                        className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-500 hover:bg-cyan-500/30 text-xs font-mono"
                      >
                        推进下一阶段 ➔
                      </button>
                    </div>
                  </div>

                  {/* Visual 7-Stage Track */}
                  <div className="grid grid-cols-7 gap-1 pt-1">
                    {STAGES.map((st, idx) => {
                      const isCurrent = pkg.current_stage === st
                      const isPast = STAGES.indexOf(pkg.current_stage) > idx
                      return (
                        <div
                          key={st}
                          className={`p-1 rounded text-center text-[12px] truncate font-mono border ${
                            isCurrent
                              ? 'border-cyan-500/80 bg-cyan-500/10 text-cyan-500 font-semibold'
                              : isPast
                              ? 'border-border/60 bg-muted/30 text-foreground'
                              : 'border-border/20 text-muted-foreground/50'
                          }`}
                          title={st}
                        >
                          {idx + 1}. {st.split('_')[0]}
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Col: Governance & Inviolable Decisions */}
        <div className="rounded-md border border-border/40 bg-card/40 p-3.5 space-y-3">
          <div className="flex items-center gap-2">
            <ShieldAlertIcon className="size-3.5 text-cyan-500" />
            <span className="text-xs font-medium text-foreground">人类五大不可剥夺决策权</span>
          </div>

          <div className="space-y-2">
            <div className="text-xs text-muted-foreground">自治梯阶调控（人类具有绝对支配权）:</div>
            <div className="grid grid-cols-2 gap-1.5 font-mono text-xs">
              {['level_0_observe', 'level_1_human_gate', 'level_2_bounded_auto', 'level_3_full_evolve'].map((lvl) => (
                <button
                  key={lvl}
                  onClick={() => handleSetLevel(lvl)}
                  className={`px-2 py-1 rounded text-left truncate border ${
                    governance?.autonomous_level === lvl
                      ? 'border-cyan-500 bg-cyan-500/10 text-cyan-500 font-semibold'
                      : 'border-border/40 hover:bg-secondary/40 text-muted-foreground'
                  }`}
                >
                  {lvl.replace('level_', 'L')}
                </button>
              ))}
            </div>

            <div className="pt-2 border-t border-border/30 space-y-2">
              <div className="text-xs text-muted-foreground">离线异步 Dreaming 缺陷聚类:</div>
              <button
                onClick={handleTriggerDreaming}
                disabled={loading}
                className="w-full py-1.5 px-3 rounded bg-secondary hover:bg-secondary/80 text-foreground text-xs flex items-center justify-center gap-1.5 font-mono"
              >
                <SparklesIcon className="size-3 text-cyan-500" />
                手动触发低峰 Dreaming 挖掘
              </button>
            </div>

            <div className="pt-2 border-t border-border/30 space-y-2">
              <div className="text-xs text-rose-500 flex items-center gap-1">
                <AlertTriangleIcon className="size-3 text-rose-500" />
                紧急一键熔断与全量回滚:
              </div>
              <button
                onClick={handleEmergencyRollback}
                disabled={loading}
                className="w-full py-1.5 px-3 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 border border-rose-500/30 text-xs font-mono font-semibold"
              >
                🚨 触发 EMERGENCY KILL-SWITCH
              </button>
              <div className="text-[12px] text-muted-foreground">
                立即降级至 L0 观察模式，撤回所有 10%/50% 灰度流量。
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
