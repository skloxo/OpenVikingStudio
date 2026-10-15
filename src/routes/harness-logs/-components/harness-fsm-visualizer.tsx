import * as React from 'react'
import { Badge } from '#/components/ui/badge'
import {
  ActivityIcon,
  AlertTriangleIcon,
  CheckCircle2Icon,
  ChevronRightIcon,
  LayersIcon,
  RefreshCwIcon,
  ShieldAlertIcon,
  WorkflowIcon,
} from 'lucide-react'

export interface FsmPipelineStage {
  id: string
  label: string
  desc: string
  role?: string
}

export interface FsmExceptionState {
  id: string
  label: string
  desc: string
  type: string
}

export interface FsmMeta {
  states: string[]
  current_state: string
  active_state: string
  transition_rules_count?: number
  pipeline: FsmPipelineStage[]
  exceptions: FsmExceptionState[]
}

interface HarnessFsmVisualizerProps {
  fsm?: FsmMeta
}

export function HarnessFsmVisualizer({ fsm }: HarnessFsmVisualizerProps) {
  const [selectedState, setSelectedState] = React.useState<string>('VERIFY')

  const pipeline = fsm?.pipeline ?? [
    { id: 'SPEC_INGEST', label: '规格摄取', desc: '任务规格冻结与输入三元组校验 (Spec P Ingestion)', role: 'Orchestrator' },
    { id: 'DECOMPOSE', label: '工单拆解', desc: 'Tracer-Bullet 工单拆解与 DAG 依赖编排', role: 'Orchestrator' },
    { id: 'DISPATCH', label: '专业分发', desc: '角色隔离沙箱分配 (Orchestrator != Specialist)', role: 'Orchestrator' },
    { id: 'RUNNING', label: '执行生成', desc: '沙箱代码生成与工具调用拦截', role: 'Specialist' },
    { id: 'VERIFY', label: '物理验真', desc: '真实物理 Diff + 测试视网膜执行门禁', role: 'MultiMetricGate' },
    { id: 'EVALUATE', label: '独立评审', desc: '生成者与评估者物理防串通 (Generator != Evaluator)', role: 'Independent Evaluator' },
    { id: 'CHECKPOINT', label: '状态快照', desc: '不可变 SHA-256 检查点落盘', role: 'Harness Trace' },
    { id: 'COMPLETED', label: '交付归档', desc: '版本回溯与 Git Tag 物理留痕', role: 'Release SOP' },
  ]

  const exceptions = fsm?.exceptions ?? [
    { id: 'BLOCKED', label: '护栏拦截', desc: '防偷懒省略 / 超大读取物理阻断', type: 'guard' },
    { id: 'RECOVERING', label: '自愈重试', desc: '三元故障恢复与预算自愈', type: 'retry' },
    { id: 'FAILED', label: '熔断终止', desc: '不可逆错误熔断阻断', type: 'terminal' },
  ]

  const activeStage = pipeline.find((p) => p.id === selectedState)
    || exceptions.find((e) => e.id === selectedState)

  return (
    <div className="space-y-4">
      {/* Topology Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          <WorkflowIcon className="size-4 text-cyan-400" />
          <h3 className="text-sm font-semibold tracking-wide">
            12-态确定性有限状态机流水线 (Deterministic Harness FSM)
          </h3>
          <Badge variant="outline" className="border-cyan-500/30 bg-cyan-500/10 text-xs text-cyan-300 font-mono">
            {fsm?.transition_rules_count ?? 26} 条有向转移规则
          </Badge>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="inline-block size-2 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.6)] animate-pulse" />
            主链路 (Mainline DAG)
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block size-2 rounded-full bg-rose-500" />
            阻断/异常 (Guards)
          </span>
        </div>
      </div>

      {/* Mainline Pipeline Steps */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
        {pipeline.map((stage, idx) => {
          const isSelected = selectedState === stage.id
          return (
            <button
              key={stage.id}
              type="button"
              onClick={() => setSelectedState(stage.id)}
              className={`group relative flex flex-col justify-between rounded-md border p-2.5 text-left transition-all ${
                isSelected
                  ? 'border-cyan-500/60 bg-cyan-500/10 shadow-sm shadow-cyan-950/20'
                  : 'border-border/60 bg-card/60 hover:border-border hover:bg-card'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-muted-foreground">
                  0{idx + 1}
                </span>
                {isSelected ? (
                  <CheckCircle2Icon className="size-3.5 text-cyan-400" />
                ) : (
                  <ChevronRightIcon className="size-3 text-muted-foreground/40 group-hover:text-muted-foreground" />
                )}
              </div>
              <div className="my-2">
                <div className="text-xs font-medium text-foreground truncate">{stage.label}</div>
                <div className="font-mono text-xs text-cyan-400/90 truncate">{stage.id}</div>
              </div>
              <div className="border-t border-border/40 pt-1 text-xs text-muted-foreground truncate">
                {stage.role ?? 'Harness'}
              </div>
            </button>
          )
        })}
      </div>

      {/* Exception & Recovery Branches */}
      <div className="rounded-md border border-border/70 bg-card/40 p-3">
        <div className="mb-2 flex items-center gap-2 text-xs font-medium text-muted-foreground">
          <LayersIcon className="size-3.5 text-rose-400" />
          <span>异常拦截与自愈分支 (Guards & Recovery States)</span>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {exceptions.map((ex) => {
            const isSelected = selectedState === ex.id
            const isBlocked = ex.id === 'BLOCKED'
            const isRetry = ex.id === 'RECOVERING'
            return (
              <button
                key={ex.id}
                type="button"
                onClick={() => setSelectedState(ex.id)}
                className={`flex items-start gap-2.5 rounded-md border p-2.5 text-left transition-all ${
                  isSelected
                    ? isBlocked
                      ? 'border-rose-500/60 bg-rose-500/10'
                      : isRetry
                      ? 'border-amber-500/60 bg-amber-500/10'
                      : 'border-rose-500/60 bg-rose-500/10'
                    : 'border-border/60 bg-background/50 hover:bg-background'
                }`}
              >
                {isBlocked && <ShieldAlertIcon className="mt-0.5 size-4 text-rose-400 shrink-0" />}
                {isRetry && <RefreshCwIcon className="mt-0.5 size-4 text-amber-400 shrink-0" />}
                {!isBlocked && !isRetry && <AlertTriangleIcon className="mt-0.5 size-4 text-rose-400 shrink-0" />}
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-semibold">{ex.label}</span>
                    <span className="font-mono text-xs text-muted-foreground">[{ex.id}]</span>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground line-clamp-1">{ex.desc}</p>
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Active State Detail Panel */}
      {activeStage && (
        <div className="rounded-md border border-cyan-500/30 bg-cyan-950/10 p-3.5 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-cyan-500/20 pb-2">
            <div className="flex items-center gap-2">
              <ActivityIcon className="size-3.5 text-cyan-400" />
              <span className="font-semibold text-cyan-200">当前聚焦状态: {activeStage.label}</span>
              <span className="font-mono text-xs text-cyan-400">({activeStage.id})</span>
            </div>
            {'role' in activeStage && activeStage.role && (
              <Badge variant="outline" className="border-cyan-500/40 text-xs text-cyan-300">
                主控职责: {activeStage.role}
              </Badge>
            )}
          </div>
          <p className="mt-2 text-muted-foreground leading-relaxed">
            {activeStage.desc}
          </p>
        </div>
      )}
    </div>
  )
}
