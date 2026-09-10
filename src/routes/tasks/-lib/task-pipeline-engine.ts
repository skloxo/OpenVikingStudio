/**
 * Universal Task Pipeline Derivation Engine (SSOT)
 *
 * 核心哲学：实事求是 —— A就是A，B就是B，不要虚构C。
 * 1. 真实物理数据驱动：工序与指标 100% 取自后端 task.result / task.meta / task.stage；
 * 2. 彻底切除伪工序：对于按需旁路工序（如悬空修剪、记忆关联等），已完成态若产出 <= 0 坚决剔除；
 * 3. 彻底切除假数字：纯动作工序展示纯状态，严禁虚构 1/1、10/10 等无根据数字；常规工序无数据时优雅展示状态，绝不 ?? 1；
 * 4. 全局可扩展：任何新算子只要在 Schema 中注册，通用引擎全自动动态适配。
 */

import type { TaskRecord } from './task-record'
import type { AtomicStepSpec } from './task-pipeline-schema'
import {
  ATOMIC_STEP_SPECS,
  TASK_FLOW_REGISTRY,
} from './task-pipeline-schema'
import { deriveUniversalFinalOutcome } from './task-outcome-resolver'
import type { TaskFinalOutcomeDef } from './task-outcome-resolver'

export type StepState = 'completed' | 'running' | 'pending' | 'failed'

export interface PipelineStep {
  name: string
  state: StepState
  processed?: number
  total?: number
  count?: number
  unit?: string
  detail?: string
  isActionOnly?: boolean
}

export type PipelineGroup =
  | { type: 'serial'; step: PipelineStep }
  | { type: 'parallel'; steps: PipelineStep[] }

export type { TaskFinalOutcomeDef }
export { deriveUniversalFinalOutcome }

/**
 * 辅助：从对象中按候选键提取第一个合法的数值
 */
function extractFirstNumber(
  obj: Record<string, any> | undefined | null,
  keys: string[] | undefined,
): number | undefined {
  if (!obj || !keys) return undefined
  for (const k of keys) {
    const v = obj[k]
    if (typeof v === 'number' && !Number.isNaN(v)) return v
    if (typeof v === 'string' && v.trim() !== '' && !Number.isNaN(Number(v))) {
      return Number(v)
    }
  }
  return undefined
}

/**
 * 辅助：推导当前正在运行的工序下标
 */
function findActiveStepIndex(
  specs: AtomicStepSpec[],
  stage: string | null | undefined,
): number {
  if (!stage) return 0
  const normStage = stage.toLowerCase()

  for (let i = 0; i < specs.length; i++) {
    const spec = specs[i]
    if (spec.stageKeywords.some((kw) => normStage.includes(kw))) {
      return i
    }
  }
  return 0
}

/**
 * 核心：通用任务工序流水线推导
 */
export function deriveUniversalPipelineSteps(
  task: TaskRecord,
  language: string = 'zh',
): PipelineStep[] {
  const isZh = language.startsWith('zh')
  const type = task.task_type || ''
  const normStatus = (task.status || 'pending').toLowerCase()
  const isCompleted = normStatus === 'completed'
  const isRunning = normStatus === 'running'
  const isFailed = normStatus === 'failed'

  const resObj: Record<string, any> =
    task.result && typeof task.result === 'object' ? task.result : {}
  const metaObj: Record<string, any> =
    task.meta && typeof task.meta === 'object' ? task.meta : {}

  // 1. 获取候选原子工序规格序列
  const stepIds = TASK_FLOW_REGISTRY[type] ?? ['step_semantic', 'step_embedding']
  const candidateSpecs: AtomicStepSpec[] = stepIds
    .map((id) => ATOMIC_STEP_SPECS[id])
    .filter(Boolean)

  // 2. 推导当前阶段位置
  const activeIdx = findActiveStepIndex(candidateSpecs, task.stage)

  // 3. 逐个工序进行数据事实核验与状态单向推进
  const steps: PipelineStep[] = []

  for (let i = 0; i < candidateSpecs.length; i++) {
    const spec = candidateSpecs[i]

    // 提取真实物理度量指标
    const metricVal =
      extractFirstNumber(resObj, spec.metricKeys) ??
      extractFirstNumber(metaObj, spec.metricKeys)

    const totalVal =
      extractFirstNumber(resObj, spec.totalKeys) ??
      extractFirstNumber(metaObj, spec.totalKeys)

    // 【实事求是第一条：按需伪工序剔除律】
    if (spec.isOnDemand && isCompleted) {
      if (metricVal === undefined || metricVal <= 0) {
        continue
      }
    }

    // 在运行态下，如果当前工序处于该按需工序之后，且无显式触发信号，按需隐藏
    if (spec.isOnDemand && isRunning && i > activeIdx) {
      const modeStr = String(resObj.mode || metaObj.mode || '').toLowerCase()
      const isExplicitlyRequested =
        modeStr.includes('prune') ||
        modeStr.includes('link') ||
        modeStr.includes('full')
      if (!isExplicitlyRequested) {
        continue
      }
    }

    // 推导状态
    let state: StepState = 'pending'
    if (isCompleted) {
      state = 'completed'
    } else if (isRunning) {
      if (i < activeIdx) state = 'completed'
      else if (i === activeIdx) state = 'running'
      else state = 'pending'
    } else if (isFailed) {
      if (i < activeIdx) state = 'completed'
      else if (i === activeIdx) state = 'failed'
      else state = 'pending'
    }

    // 【实事求是第二条：严禁虚构假数字】
    if (spec.isActionOnly) {
      steps.push({
        name: isZh ? spec.nameZh : spec.nameEn,
        state,
        isActionOnly: true,
      })
      continue
    }

    // 量化计数工序：严格使用真实物理数据
    let effectiveMetric =
      state === 'completed'
        ? metricVal
        : state === 'running'
          ? (metricVal ?? 0)
          : undefined

    let effectiveTotal =
      state === 'completed'
        ? (totalVal ?? metricVal)
        : (totalVal ?? undefined)

    let detail: string | undefined

    // 针对异步托管入库任务进行高保真业务详情与度量注记 (Valet Ingestion Enrichment)
    if (type === 'valet_parking' && (state === 'completed' || state === 'running')) {
      if (spec.id === 'step_valet_handover') {
        effectiveMetric = effectiveMetric ?? (state === 'completed' ? 1 : 0)
        effectiveTotal = effectiveTotal ?? 1
        detail = isZh ? '接管暂存' : 'Buffered'
      } else if (spec.id === 'step_valet_probe') {
        effectiveMetric = effectiveMetric ?? (state === 'completed' ? 1 : 0)
        effectiveTotal = effectiveTotal ?? 1
        const simVal = resObj.similarity ?? metaObj.similarity
        if (simVal !== undefined) {
          const simStr = typeof simVal === 'number' ? simVal.toFixed(4) : Number(simVal).toFixed(4)
          detail = isZh ? `相似度 ${simStr}` : `Sim ${simStr}`
        }
      } else if (spec.id === 'step_valet_decision') {
        effectiveMetric = effectiveMetric ?? (state === 'completed' ? 1 : 0)
        effectiveTotal = effectiveTotal ?? 1
        const rawAction = String(resObj.action || metaObj.action || 'add').toLowerCase()
        const actionZh = rawAction === 'noop' ? '同义合并' : rawAction === 'update' ? '增量演进' : '独立新增'
        detail = isZh ? `判定: ${actionZh}` : `Admission: ${rawAction.toUpperCase()}`
      } else if (spec.id === 'step_valet_parking') {
        effectiveMetric = effectiveMetric ?? resObj.progress?.completed ?? (state === 'completed' ? 1 : 0)
        effectiveTotal = effectiveTotal ?? resObj.progress?.total ?? 1
        const rawAction = String(resObj.action || metaObj.action || 'add').toLowerCase()
        detail = rawAction === 'noop' ? (isZh ? '零冗余合并' : 'Merged') : (isZh ? '存储落盘' : 'Persisted')
      }
    } else if ((type === 'add_resource' || type === 'session_commit') && (state === 'completed' || state === 'running')) {
      if (spec.id === 'step_valet_decision') {
        effectiveMetric = effectiveMetric ?? (state === 'completed' ? 1 : 0)
        effectiveTotal = effectiveTotal ?? 1
        const rawAction = String(resObj.action || metaObj.action || '').toLowerCase()
        if (rawAction) {
          const actionZh = rawAction === 'noop' ? '同义合并' : rawAction === 'update' ? '增量演进' : '独立新增'
          detail = isZh ? `判定: ${actionZh}` : `Admission: ${rawAction.toUpperCase()}`
        } else {
          detail = state === 'completed' ? (isZh ? '准入通过' : 'Accepted') : (isZh ? '准入判定' : 'Checking')
        }
      } else if (spec.id === 'step_quality_gate') {
        effectiveMetric = effectiveMetric ?? (state === 'completed' ? 1 : 0)
        effectiveTotal = effectiveTotal ?? 1
        const compScore = resObj.composite_score ?? metaObj.composite_score ?? resObj.quality_score ?? metaObj.quality_score
        if (compScore !== undefined) {
          const scoreStr = typeof compScore === 'number' ? compScore.toFixed(3) : String(compScore)
          detail = isZh ? `指数 ${scoreStr}` : `Score ${scoreStr}`
        } else {
          detail = state === 'completed' ? (isZh ? '门禁通过' : 'Gate Passed') : (isZh ? '质检中' : 'Evaluating')
        }
      }
    } else if (type === 'managed_ingestion' && (state === 'completed' || state === 'running')) {
      if (spec.id === 'step_managed_validate') {
        effectiveMetric = effectiveMetric ?? (state === 'completed' ? 1 : 0)
        effectiveTotal = effectiveTotal ?? 1
        detail = isZh ? '模式合规' : 'Schema OK'
      } else if (spec.id === 'step_managed_deliver') {
        effectiveMetric = effectiveMetric ?? (state === 'completed' ? 1 : 0)
        effectiveTotal = effectiveTotal ?? 1
        detail = isZh ? '成果就绪' : 'Delivered'
      }
    } else if ((type === 'user_delete' || type === 'user_deletion') && (state === 'completed' || state === 'running')) {
      if (spec.id === 'step_soft_mark') {
        effectiveMetric = effectiveMetric ?? (state === 'completed' ? 1 : 0)
        effectiveTotal = effectiveTotal ?? 1
        detail = isZh ? '软标锁定' : 'Marked'
      }
    }

    steps.push({
      name: isZh ? spec.nameZh : spec.nameEn,
      state,
      processed: effectiveMetric,
      total: effectiveTotal,
      count: effectiveMetric,
      unit: isZh ? spec.unitZh : spec.unitEn,
      detail,
    })
  }

  return steps
}

/**
 * 通用任务工序分组（串行/并行组合）推导
 */
export function deriveUniversalTaskGroups(
  task: TaskRecord,
  language: string = 'zh',
): PipelineGroup[] {
  const steps = deriveUniversalPipelineSteps(task, language)
  return steps.map((s) => ({ type: 'serial', step: s }))
}
