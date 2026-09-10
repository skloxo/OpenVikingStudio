/**
 * Task Pipeline Schema (SSOT)
 *
 * 核心哲学：实事求是 —— A就是A，B就是B，不要虚构C。
 * 1. 纯动作型工序 (Action-Only)：成功即展示“已完成”，严禁虚构造假数字 (如 1/1 次、1/1 空间、1/1 快照)；
 * 2. 量化计数型工序 (Metric-Counted)：严格绑定后端物理汇报字段，无数据则展示状态，绝不编造假数字；
 * 3. 按需触发型工序 (On-Demand)：仅当物理产出 > 0 或正在运行时按需呈现，产出为 0 坚决剔除伪工序。
 * 4. 算子可扩展 (Extensible)：未来增加新算子或新引擎，只需在此声明配置，通用引擎自动动态适配。
 */

import { CORE_STEP_SPECS } from './task-pipeline-specs-core'
import { ENTROPY_STEP_SPECS } from './task-pipeline-specs-entropy'

export interface AtomicStepSpec {
  id: string
  nameZh: string
  nameEn: string
  unitZh?: string
  unitEn?: string
  /** 运行时 stage 关键词匹配 */
  stageKeywords: string[]
  /** 从 result / meta 中提取真实计数候选键 (按优先级降序) */
  metricKeys?: string[]
  /** 从 result / meta 中提取预估总量候选键 (按优先级降序) */
  totalKeys?: string[]
  /** 是否为按需旁路工序：已完成时若指标 <= 0 则彻底剔除伪工序 */
  isOnDemand?: boolean
  /** 是否为纯动作工序：成功时无需造假数字，直接展示状态徽章 */
  isActionOnly?: boolean
  /** 承接该工序的底层引擎 Key */
  engineKey?: string
}

export const ATOMIC_STEP_SPECS: Record<string, AtomicStepSpec> = {
  ...CORE_STEP_SPECS,
  ...ENTROPY_STEP_SPECS,
}

/**
 * 任务类型 -> 候选标准工序流映射 (Task Flow Registry)
 * 每种任务声明其物理流动的工序 ID 序列。
 */
export const TASK_FLOW_REGISTRY: Record<string, string[]> = {
  add_resource: [
    'step_valet_decision',
    'step_parsing',
    'step_semantic',
    'step_embedding',
    'step_quality_gate',
    'step_memory_linking',
  ],
  resource_build: [
    'step_parsing',
    'step_semantic',
    'step_embedding',
  ],
  knowledge_pack: [
    'step_parsing',
    'step_semantic',
    'step_embedding',
  ],
  add_skill: [
    'step_skill_scan',
    'step_spec_audit',
    'step_skill_embedding',
  ],
  session_commit: [
    'step_valet_decision',
    'step_session_archive',
    'step_lesson_extraction',
    'step_quality_gate',
    'step_snapshot_commit',
  ],
  admin_reindex: [
    'step_semantic',
    'step_embedding',
    'step_pruning',
  ],
  snapshot_restore_reindex: [
    'step_snapshot_rollback',
    'step_inode_restore',
    'step_embedding',
  ],
  connector_import: [
    'step_auth_handshake',
    'step_external_fetch',
    'step_parsing',
    'step_semantic',
    'step_embedding',
  ],
  legacy_migration: [
    'step_legacy_read',
    'step_schema_transform',
    'step_viking_write',
  ],
  legacy_cleanup: [
    'step_graph_traverse',
    'step_orphan_gc',
    'step_space_release',
  ],
  user_delete: [
    'step_soft_mark',
    'step_vector_purge',
    'step_disk_wipe',
  ],
  user_deletion: [
    'step_soft_mark',
    'step_vector_purge',
    'step_disk_wipe',
  ],
  valet_parking: [
    'step_valet_handover',
    'step_valet_probe',
    'step_valet_decision',
    'step_valet_parking',
  ],
}
