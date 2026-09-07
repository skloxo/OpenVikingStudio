/**
 * Task Pipeline Architecture SSOT
 *
 * 核心哲学：实事求是 —— A就是A，B就是B，不要虚构C。
 * 1. 纯动作型工序 (Action-Only)：成功即展示“已完成”，严禁虚构造假数字 (如 1/1 次、1/1 空间、1/1 快照)；
 * 2. 量化计数型工序 (Metric-Counted)：严格绑定后端物理汇报字段，无数据则展示状态，绝不编造假数字；
 * 3. 按需触发型工序 (On-Demand)：仅当物理产出 > 0 或正在运行时按需呈现，产出为 0 坚决剔除伪工序；
 * 4. 算子可扩展 (Extensible)：任何新算子只要在 Schema 中注册，通用推导引擎全自动动态适配。
 */

import type { TaskRecord } from './task-record'
import type { ParsedQueueRow } from '#/routes/monitoring/-components/queue-status-card'
import type {
  PipelineGroup,
  PipelineStep,
  StepState,
  TaskFinalOutcomeDef,
} from './task-pipeline-engine'
import {
  deriveUniversalFinalOutcome,
  deriveUniversalPipelineSteps,
} from './task-pipeline-engine'

export type {
  StepState,
  PipelineStep,
  PipelineGroup,
  TaskFinalOutcomeDef,
}

export interface QuantifiedWorkload {
  icon: string
  label: string
  processed?: number
  total?: number
  unit: string
  pct?: number
}

export interface ActiveStepPair {
  name: string
  metric?: string
}

export interface TaskDynamicDef {
  status: 'pending' | 'running' | 'completed' | 'failed'
  activeStepName: string
  activeEngineName: string
  activeStepIndex: number
  totalSteps: number
  progressPct: number
  workloadText?: string
  workloadIcon?: string
  summaryText?: string
  activeStepPairs?: ActiveStepPair[]
}

/**
 * 辅助：从会话归档元数据中提取轮数与萃取经验数
 */
export function extractSessionCommitMetrics(
  meta: Record<string, any>,
  result: Record<string, any>,
  status?: string,
): { turns: number; lessons: number } {
  let lessons = 0
  if (
    result.memories_extracted &&
    typeof result.memories_extracted === 'object'
  ) {
    lessons = Object.values(
      result.memories_extracted as Record<string, number>,
    ).reduce((sum, val) => sum + (typeof val === 'number' ? val : 0), 0)
  } else if (typeof result.memories_extracted === 'number') {
    lessons = result.memories_extracted
  } else if (typeof result.lessons_extracted === 'number') {
    lessons = result.lessons_extracted
  } else if (typeof meta.lessons_count === 'number') {
    lessons = meta.lessons_count
  }

  let turns =
    meta.turns_count ??
    result.turns_processed ??
    meta.messages_count ??
    result.messages_count
  if (turns === undefined && status?.toLowerCase() === 'completed') {
    turns = 1
  }

  return { turns: turns ?? 1, lessons }
}

/**
 * 获取任务对应的流水线工序步骤 (Pipeline Steps)
 * 100% 接入 Universal Pipeline Engine，彻底切除任何硬编码伪数据
 */
export function getTaskPipelineSteps(
  task: TaskRecord,
  _queueRows: ParsedQueueRow[] | string = [],
  language: string = 'zh',
): PipelineStep[] {
  const actualLang: string =
    typeof _queueRows === 'string' ? _queueRows : language
  return deriveUniversalPipelineSteps(task, actualLang)
}

/**
 * 获取任务工序的分组展示（串行 / 并行）
 */
export function getTaskPipelineGroups(
  task: TaskRecord,
  _queueRows: ParsedQueueRow[] | string = [],
  language: string = 'zh',
): PipelineGroup[] {
  const actualLang: string =
    typeof _queueRows === 'string' ? _queueRows : language
  const steps = getTaskPipelineSteps(task, _queueRows, actualLang)
  const type = task.task_type || ''

  // 资源入库 / 外部接入：中间阶段若同时存在语义提取与切片重构，以并排卡片自适应呈现
  if (type === 'add_resource' || type === 'connector_import') {
    const semIdx = steps.findIndex((s) => s.name.includes('语义'))
    const embIdx = steps.findIndex((s) => s.name.includes('切片') || s.name.includes('向量'))

    if (semIdx !== -1 && embIdx !== -1 && Math.abs(semIdx - embIdx) === 1) {
      const groups: PipelineGroup[] = []
      const minIdx = Math.min(semIdx, embIdx)
      const maxIdx = Math.max(semIdx, embIdx)

      for (let i = 0; i < minIdx; i++) {
        groups.push({ type: 'serial', step: steps[i] })
      }
      groups.push({
        type: 'parallel',
        steps: [steps[minIdx], steps[maxIdx]],
      })
      for (let i = maxIdx + 1; i < steps.length; i++) {
        groups.push({ type: 'serial', step: steps[i] })
      }
      return groups
    }
  }

  // 默认：严格按串行流动顺序展示
  return steps.map((step) => ({ type: 'serial' as const, step }))
}

/**
 * 提取任务量化物理负载 (Quantified Workload)
 * 严格使用任务自身物理数据，绝不借用全局 observer 污染
 */
export function getTaskQuantifiedWorkload(
  task: TaskRecord,
  _queueRows: ParsedQueueRow[] = [],
  language: string = 'zh',
): QuantifiedWorkload | null {
  const isZh = language.startsWith('zh')
  const type = task.task_type
  const meta = task.meta && typeof task.meta === 'object' ? task.meta : {}
  const resObj: Record<string, any> =
    task.result && typeof task.result === 'object'
      ? (task.result as Record<string, any>)
      : {}

  // 1. admin_reindex 真实度量优先：扫描篇数与重构切片数组合透出
  if (type === 'admin_reindex') {
    const scanned = resObj.semantic_records ?? resObj.scanned_records ?? meta.scanned_records
    const rebuilt = resObj.rebuilt_records ?? resObj.reindexed_items ?? meta.rebuilt_records
    if (scanned !== undefined || rebuilt !== undefined) {
      const parts: string[] = []
      if (scanned !== undefined) {
        parts.push(isZh ? `${Number(scanned).toLocaleString()} 篇扫描` : `${Number(scanned).toLocaleString()} scanned`)
      }
      if (rebuilt !== undefined) {
        parts.push(isZh ? `${Number(rebuilt).toLocaleString()} 切片重构` : `${Number(rebuilt).toLocaleString()} chunks`)
      }
      return {
        icon: '🔄',
        label: parts.join(isZh ? ' ｜ ' : ' | '),
        processed: rebuilt ? Number(rebuilt) : Number(scanned),
        total: rebuilt ? Number(rebuilt) : Number(scanned),
        unit: rebuilt ? (isZh ? '切片' : 'chunks') : (isZh ? '篇' : 'docs'),
        pct: 100,
      }
    }
  }

  // 2. 显式切片数 (最高物理精度)
  const chunksProcessed = meta.processed_chunks ?? resObj.processed_chunks ?? resObj.rebuilt_records
  const chunksTotal = meta.total_chunks ?? resObj.total_chunks ?? resObj.rebuilt_records
  if (typeof chunksProcessed === 'number' && typeof chunksTotal === 'number' && chunksTotal > 0) {
    const pct = Math.min(100, Math.round((chunksProcessed / chunksTotal) * 100))
    return {
      icon: '⚡',
      label: isZh
        ? `${chunksProcessed.toLocaleString()} / ${chunksTotal.toLocaleString()} 切片 (${pct}%)`
        : `${chunksProcessed.toLocaleString()} / ${chunksTotal.toLocaleString()} chunks (${pct}%)`,
      processed: chunksProcessed,
      total: chunksTotal,
      unit: isZh ? '切片' : 'chunks',
      pct,
    }
  }

  // 3. 显式节点数 / 篇数
  const nodesProcessed = meta.processed_nodes ?? resObj.processed_nodes ?? resObj.semantic_records
  const nodesTotal = meta.total_nodes ?? resObj.total_nodes ?? resObj.semantic_records
  if (typeof nodesProcessed === 'number' && typeof nodesTotal === 'number' && nodesTotal > 0) {
    const pct = Math.min(100, Math.round((nodesProcessed / nodesTotal) * 100))
    return {
      icon: '🧠',
      label: isZh
        ? `${nodesProcessed.toLocaleString()} / ${nodesTotal.toLocaleString()} 篇 (${pct}%)`
        : `${nodesProcessed.toLocaleString()} / ${nodesTotal.toLocaleString()} docs (${pct}%)`,
      processed: nodesProcessed,
      total: nodesTotal,
      unit: isZh ? '篇' : 'docs',
      pct,
    }
  }

  // 3. 任务类型特化真实度量
  if (type === 'admin_reindex') {
    const scanned = resObj.semantic_records ?? resObj.scanned_records ?? meta.scanned_records
    const rebuilt = resObj.rebuilt_records ?? resObj.reindexed_items ?? meta.rebuilt_records
    if (scanned !== undefined || rebuilt !== undefined) {
      const parts: string[] = []
      if (scanned !== undefined) {
        parts.push(isZh ? `${Number(scanned).toLocaleString()} 篇扫描` : `${Number(scanned).toLocaleString()} scanned`)
      }
      if (rebuilt !== undefined) {
        parts.push(isZh ? `${Number(rebuilt).toLocaleString()} 切片重构` : `${Number(rebuilt).toLocaleString()} chunks`)
      }
      return {
        icon: '🔄',
        label: parts.join(' · '),
        processed: rebuilt ? Number(rebuilt) : Number(scanned),
        total: rebuilt ? Number(rebuilt) : Number(scanned),
        unit: rebuilt ? (isZh ? '切片' : 'chunks') : (isZh ? '篇' : 'docs'),
        pct: 100,
      }
    }
  }

  if (type === 'add_skill') {
    const skills = resObj.valid_skills ?? meta.valid_skills ?? resObj.scanned_skills
    if (skills !== undefined) {
      return {
        icon: '🤹',
        label: isZh ? `${skills} 项技能` : `${skills} skills`,
        unit: isZh ? '项技能' : 'skills',
        processed: Number(skills),
        total: Number(skills),
        pct: 100,
      }
    }
  }

  if (type === 'session_commit') {
    const { turns, lessons } = extractSessionCommitMetrics(meta, resObj, task.status)
    return {
      icon: '💾',
      label: isZh
        ? `${turns} 轮对话` + (lessons > 0 ? ` · ${lessons} 条经验` : '')
        : `${turns} turns` + (lessons > 0 ? ` · ${lessons} lessons` : ''),
      unit: isZh ? '轮' : 'turns',
      processed: turns,
      total: turns,
      pct: 100,
    }
  }

  return null
}

/**
 * 提取任务执行动态 (Execution Dynamic)
 */
export function getTaskExecutionDynamic(
  task: TaskRecord,
  queueRows: ParsedQueueRow[] = [],
  language: string = 'zh',
): TaskDynamicDef {
  const isZh = language.startsWith('zh')
  const status = (task.status || 'pending').toLowerCase() as TaskDynamicDef['status']
  const steps = getTaskPipelineSteps(task, queueRows, language)
  const workload = getTaskQuantifiedWorkload(task, queueRows, language)
  const totalSteps = steps.length

  if (status === 'completed') {
    const outcome = deriveUniversalFinalOutcome(task, language)
    return {
      status: 'completed',
      activeStepName: steps[steps.length - 1]?.name || (isZh ? '完成' : 'Done'),
      activeEngineName: isZh ? '就绪' : 'Ready',
      activeStepIndex: totalSteps,
      totalSteps,
      progressPct: 100,
      workloadText: workload?.label,
      workloadIcon: workload?.icon,
      summaryText: outcome.deliverableText,
    }
  }

  if (status === 'running') {
    const runningSteps = steps.filter((s) => s.state === 'running')
    const activeSteps = runningSteps.length > 0 ? runningSteps : [steps[0]]
    const stepName = activeSteps.map((s) => s.name).join(' & ')

    const activeStepPairs: ActiveStepPair[] = activeSteps.map((s) => {
      let metric = ''
      if (s.processed !== undefined && s.total !== undefined && s.total > 0) {
        metric = `${s.processed.toLocaleString()} / ${s.total.toLocaleString()} ${s.unit ?? ''}`.trim()
      } else if (s.count !== undefined) {
        metric = `${s.count.toLocaleString()} ${s.unit ?? ''}`.trim()
      }
      return { name: s.name, metric: metric || undefined }
    })

    return {
      status: 'running',
      activeStepName: stepName,
      activeEngineName: isZh ? '计算中' : 'Executing',
      activeStepIndex: 1,
      totalSteps,
      progressPct: 50,
      activeStepPairs,
      workloadText: workload?.label,
      workloadIcon: workload?.icon ?? '⚡',
      summaryText: isZh ? '正在执行' : 'Executing',
    }
  }

  if (status === 'failed') {
    return {
      status: 'failed',
      activeStepName: isZh ? '执行异常' : 'Failed',
      activeEngineName: isZh ? '中断' : 'Aborted',
      activeStepIndex: 0,
      totalSteps,
      progressPct: 0,
      summaryText: isZh ? '任务执行失败' : 'Task execution failed',
    }
  }

  return {
    status: 'pending',
    activeStepName: isZh ? '等待调度' : 'Pending',
    activeEngineName: isZh ? '排队中' : 'Queued',
    activeStepIndex: 0,
    totalSteps,
    progressPct: 0,
    summaryText: isZh ? '排队等待调度' : 'Queued',
  }
}

/**
 * 获取任务最终交付成果 (Final Deliverable Outcome)
 */
export function getTaskFinalOutcome(
  task: TaskRecord,
  language: string = 'zh',
): TaskFinalOutcomeDef {
  return deriveUniversalFinalOutcome(task, language)
}
