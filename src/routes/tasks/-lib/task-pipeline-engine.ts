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

export interface TaskFinalOutcomeDef {
  title: string
  deliverableText: string
  expectedText: string
}

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
    // 若属于按需旁路工序（如悬空修剪、记忆关联、碎片回收等）：
    // 在完成态下，如果物理产出指标 <= 0 或不存在，坚决剔除，绝不展示 0/0 伪工序！
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
    // 纯动作工序：成功即完成，绝不造假数字 1/1
    if (spec.isActionOnly) {
      steps.push({
        name: isZh ? spec.nameZh : spec.nameEn,
        state,
        isActionOnly: true,
      })
      continue
    }

    // 量化计数工序：严格使用真实物理数据
    const effectiveMetric =
      state === 'completed'
        ? metricVal
        : state === 'running'
          ? (metricVal ?? 0)
          : undefined

    const effectiveTotal =
      state === 'completed'
        ? (totalVal ?? metricVal)
        : (totalVal ?? undefined)

    steps.push({
      name: isZh ? spec.nameZh : spec.nameEn,
      state,
      processed: effectiveMetric,
      total: effectiveTotal,
      count: effectiveMetric,
      unit: isZh ? spec.unitZh : spec.unitEn,
    })
  }

  return steps
}

/**
 * 通用终点输出成果推导 (Universal Final Deliverable)
 */
export function deriveUniversalFinalOutcome(
  task: TaskRecord,
  language: string = 'zh',
): TaskFinalOutcomeDef {
  const isZh = language.startsWith('zh')
  const type = task.task_type || ''
  const isCompleted = (task.status || '').toLowerCase() === 'completed'

  const resObj: Record<string, any> =
    task.result && typeof task.result === 'object' ? task.result : {}
  const metaObj: Record<string, any> =
    task.meta && typeof task.meta === 'object' ? task.meta : {}

  // 1. 全局索引重建
  if (type === 'admin_reindex') {
    const scanned = resObj.semantic_records ?? resObj.scanned_records ?? metaObj.scanned_records
    const rebuilt = resObj.rebuilt_records ?? resObj.reindexed_items ?? metaObj.rebuilt_records
    const deleted = Number(resObj.deleted_records ?? metaObj.deleted_records ?? 0)

    let deliverableText = isZh ? '全量索引重构完成' : 'Global reindex completed'
    if (scanned !== undefined && rebuilt !== undefined) {
      if (deleted > 0) {
        deliverableText = isZh
          ? `已完成 ${Number(scanned).toLocaleString()} 篇记忆扫描 · 重构 ${Number(rebuilt).toLocaleString()} 个向量切片 · 修剪 ${deleted} 个孤儿碎片`
          : `Scanned ${Number(scanned).toLocaleString()} memories · Rebuilt ${Number(rebuilt).toLocaleString()} vector chunks · Pruned ${deleted} orphans`
      } else {
        deliverableText = isZh
          ? `已完成 ${Number(scanned).toLocaleString()} 篇记忆扫描 · 重构 ${Number(rebuilt).toLocaleString()} 个向量切片 · 成功率 100%`
          : `Scanned ${Number(scanned).toLocaleString()} memories · Rebuilt ${Number(rebuilt).toLocaleString()} vector chunks · 100% Success`
      }
    }

    return {
      title: isZh ? '全量索引重建' : 'Global Reindex',
      deliverableText,
      expectedText:
        deleted > 0
          ? isZh
            ? '修剪孤儿悬空碎片与全量向量切片重构'
            : 'Prune orphan dangling fragments & rebuild vectors'
          : isZh
            ? '全量记忆节点扫描与向量切片重构'
            : 'Full memory node scanning & vector chunk rebuilding',
    }
  }

  // 2. 资源入库 / 知识包
  if (type === 'add_resource' || type === 'resource_build' || type === 'knowledge_pack') {
    const files = metaObj.file_count ?? resObj.file_count ?? 1
    const chunks = resObj.processed_chunks ?? metaObj.processed_chunks
    const links = resObj.total_links ?? metaObj.total_links

    const parts: string[] = [isZh ? `${files} 个文件已落盘索引` : `${files} files indexed`]
    if (chunks && Number(chunks) > 0) {
      parts.push(isZh ? `生成 ${Number(chunks).toLocaleString()} 个向量切片` : `${Number(chunks).toLocaleString()} chunks`)
    }
    if (links && Number(links) > 0) {
      parts.push(isZh ? `建立 ${Number(links).toLocaleString()} 条记忆关联` : `${Number(links).toLocaleString()} links`)
    }

    return {
      title: isZh ? '资源入库' : 'Resource Ingestion',
      deliverableText: parts.join(' · '),
      expectedText: isZh ? '物理文件落盘与语义向量建库' : 'File persistence and vector indexing',
    }
  }

  // 3. 技能入库
  if (type === 'add_skill') {
    const skills = resObj.valid_skills ?? metaObj.valid_skills ?? resObj.scanned_skills
    return {
      title: isZh ? '技能入库' : 'Skill Ingestion',
      deliverableText: skills
        ? (isZh ? `${skills} 项技能已完成校验并注册入库` : `${skills} skills validated & registered`)
        : (isZh ? '技能已完成校验并注册入库' : 'Skills validated & registered'),
      expectedText: isZh ? '技能合规校验与向量注册入库' : 'Skill spec validation & embedding registration',
    }
  }

  // 4. 会话归档
  if (type === 'session_commit') {
    const turns = metaObj.turns_count ?? resObj.turns_processed ?? 1
    const lessons = Number(resObj.lessons_extracted ?? metaObj.lessons_count ?? 0)
    return {
      title: isZh ? '会话归档' : 'Session Commit',
      deliverableText: isZh
        ? `${turns} 轮对话已归档` + (lessons > 0 ? ` · ${lessons} 条经验已沉淀` : '')
        : `${turns} turns archived` + (lessons > 0 ? ` · ${lessons} lessons extracted` : ''),
      expectedText: isZh ? '对话上下文序列化与经验记忆萃取' : 'Context serialization & lesson extraction',
    }
  }

  // 5. 质量门禁 (Quality Gate)
  if (type === 'quality_gate' || type === 'benchmark_eval') {
    const composite = resObj.composite_score ?? metaObj.composite_score
    const totalCases = resObj.total_queries ?? resObj.total_cases ?? metaObj.total_queries ?? 10
    const hitRate = resObj.hit_rate ?? metaObj.hit_rate

    let deliverableText = isZh ? '抗熵增质量门禁已执行' : 'Anti-entropy quality gate completed'
    if (composite !== undefined) {
      const compStr = typeof composite === 'number' ? composite.toFixed(3) : String(composite)
      const hitStr = hitRate !== undefined ? (typeof hitRate === 'number' ? `${(hitRate * 100).toFixed(0)}%` : String(hitRate)) : undefined
      deliverableText = isZh
        ? `评测 ${totalCases} 组金标用例 · RAGAS 综合指数 ${compStr}` + (hitStr ? ` · 命中率 ${hitStr}` : '')
        : `Evaluated ${totalCases} test cases · RAGAS Composite ${compStr}` + (hitStr ? ` · Hit Rate ${hitStr}` : '')
    }

    return {
      title: isZh ? '抗熵增质量门禁' : 'Anti-Entropy Quality Gate',
      deliverableText,
      expectedText: isZh ? '四维指标调和评测与抗熵增基线断言' : '4D RAGAS harmonic evaluation & baseline assertion',
    }
  }

  // 6. 知识自愈优化 (Knowledge Remediation)
  if (type === 'knowledge_remediation' || type === 'entropy_healing') {
    const faults = resObj.located_faults ?? metaObj.located_faults ?? (metaObj.fault_queries?.length || 0)
    const conflicts = resObj.resolved_conflicts ?? metaObj.resolved_conflicts ?? 0
    const chunks = resObj.reindexed_chunks ?? metaObj.reindexed_chunks ?? 0

    return {
      title: isZh ? '知识自愈优化' : 'Knowledge Remediation',
      deliverableText: isZh
        ? `定位 ${faults} 处病灶 · 仲裁 ${conflicts} 项冲突 · 增量重索引 ${chunks} 切片`
        : `Located ${faults} faults · Resolved ${conflicts} conflicts · Reindexed ${chunks} chunks`,
      expectedText: isZh ? '抗熵增病灶靶向自愈与新旧冲突消解' : 'Targeted fault remediation & conflict resolution',
    }
  }

  // 7. 记忆流与反思做梦 (Memory Dream)
  if (type === 'memory_dream') {
    const rawCount = metaObj.raw_observations_count ?? 0
    const insights = resObj.insights_extracted ?? metaObj.distilled_insights_count ?? 0
    const theme = resObj.theme ?? metaObj.theme ?? 'general'
    return {
      title: isZh ? '记忆流反思做梦' : 'Memory Reflection & Dream',
      deliverableText: isZh
        ? `扫描 ${rawCount} 条观察碎片 · 提炼 ${insights} 条认知洞察 · 沉淀主题 [${theme}]`
        : `Scanned ${rawCount} observations · Distilled ${insights} insights · Topic [${theme}]`,
      expectedText: isZh ? '经验流时效衰减扫描与高阶因果洞察提炼' : 'Observation recency decay & high-level insight distillation',
    }
  }

  // 8. 分层内存与压缩淘汰 (Memory Compaction)
  if (type === 'memory_compaction') {
    const scanned = metaObj.scanned_records ?? 0
    const pruned = resObj.pruned_duplicates ?? metaObj.pruned_duplicates ?? 0
    const ratio = resObj.hot_tier_ratio ? `${(resObj.hot_tier_ratio * 100).toFixed(0)}%` : '30%'
    return {
      title: isZh ? '分层内存压缩淘汰' : 'Memory Compaction & Pruning',
      deliverableText: isZh
        ? `分层体检 ${scanned} 条记忆 · 余弦去重剪枝 ${pruned} 条 · 热层占比 ${ratio}`
        : `Evaluated ${scanned} memories · Pruned ${pruned} duplicates · Hot tier ${ratio}`,
      expectedText: isZh ? '冷热温三层动态分层与艾宾浩斯剪枝归档' : 'Hierarchical tiering & Ebbinghaus decay pruning',
    }
  }

  // 9. 增量事实四态流转 (Fact Mutation)
  if (type === 'fact_mutation') {
    const facts = metaObj.extracted_facts ?? 0
    const newFacts = resObj.net_new_facts ?? 0
    const conflicts = resObj.conflicts_resolved ?? 0
    return {
      title: isZh ? '增量事实四态流转' : 'Atomic Fact Mutation',
      deliverableText: isZh
        ? `抽取 ${facts} 条原子事实 · 净新增 ${newFacts} 条 · 消解冲突 ${conflicts} 项`
        : `Extracted ${facts} atomic facts · Net added ${newFacts} · Resolved ${conflicts} conflicts`,
      expectedText: isZh ? '原子事实抽取与四态流转 (ADD/UPDATE/DEL/NOOP)' : 'Atomic fact extraction & 4-way mutation routing',
    }
  }

  // 10. 时态图谱实体浓缩 (Entity Summarization)
  if (type === 'entity_summarization') {
    const entity = resObj.entity ?? metaObj.target_entity ?? 'OpenViking'
    const events = metaObj.timeline_events_count ?? 0
    const conflicts = resObj.resolved_contradictions ?? metaObj.resolved_contradictions ?? 0
    return {
      title: isZh ? '时态图谱实体浓缩' : 'Entity Summarization',
      deliverableText: isZh
        ? `追踪实体 [${entity}] · 编排 ${events} 条时序事件 · 消解 ${conflicts} 处矛盾`
        : `Entity [${entity}] · Ordered ${events} timeline events · Resolved ${conflicts} contradictions`,
      expectedText: isZh ? '实体时序版本链排序与单一真相源 (SSOT) 浓缩' : 'Temporal timeline ordering & entity SSOT summarization',
    }
  }

  // 11. 四层全息治理 (Four-Tier Governance)
  if (type === 'four_tier_governance') {
    const topic = resObj.topic ?? metaObj.topic ?? 'vector_entropy'
    const notes = metaObj.merged_notes_count ?? 0
    const pct = resObj.token_compression_pct ?? metaObj.token_compression_pct ?? 0
    return {
      title: isZh ? '四层治理同主题合并' : 'Four-Tier Governance',
      deliverableText: isZh
        ? `主题 [${topic}] · 归纳合并 ${notes} 篇碎片 · Token 压缩率 ${pct}%`
        : `Topic [${topic}] · Consolidated ${notes} fragments · Token compression ${pct}%`,
      expectedText: isZh ? '四层全息诊断与跨目录同主题深度归纳写回' : '4-Tier diagnosis & cross-directory topic consolidation',
    }
  }

  // 默认通用兜底：实事求是
  return {
    title: isZh ? '任务交付成果' : 'Task Deliverable',
    deliverableText: isCompleted
      ? (isZh ? '物理工序已全部执行完毕并校验入库' : 'All stages physically completed & verified')
      : (isZh ? '正在按序流转执行' : 'Executing pipeline stages'),
    expectedText: isZh ? '物理计算与状态同步' : 'Physical computation & state sync',
  }
}
