/**
 * 通用记忆增量审计快照轮子 — 领域模型与强类型 DTO (SSOT)
 * 剥离 SessionMeta 强绑定，构建跨模块（会话/任务/治理/结晶）通用的纯数据驱动契约。
 */

export type UniversalMemoryDiffKind = 'add' | 'update' | 'delete'

export interface UniversalMemoryDiffOperation {
  kind: UniversalMemoryDiffKind
  uri: string
  memoryType: string
  before?: string
  after?: string
  description?: string
  meta?: Record<string, unknown>
}

export interface UniversalMemoryDiffSummary {
  adds: number
  updates: number
  deletes: number
}

export interface UniversalMemoryDiff {
  archiveId: string
  extractedAt?: string
  summary: UniversalMemoryDiffSummary
  operations: UniversalMemoryDiffOperation[]
}

/**
 * 汇总计算原子操作集的三态增量
 */
export function summarizeOperations(
  operations: UniversalMemoryDiffOperation[],
): UniversalMemoryDiffSummary {
  return operations.reduce(
    (acc, op) => {
      if (op.kind === 'add') acc.adds += 1
      else if (op.kind === 'update') acc.updates += 1
      else acc.deletes += 1
      return acc
    },
    { adds: 0, updates: 0, deletes: 0 },
  )
}

/**
 * 汇总多个 Diff 的总计
 */
export function summarizeDiffs(
  diffs: UniversalMemoryDiff[],
): UniversalMemoryDiffSummary {
  return diffs.reduce(
    (acc, diff) => ({
      adds: acc.adds + diff.summary.adds,
      updates: acc.updates + diff.summary.updates,
      deletes: acc.deletes + diff.summary.deletes,
    }),
    { adds: 0, updates: 0, deletes: 0 },
  )
}

/**
 * 根据 URI 智能推导记忆类型
 */
export function deriveMemoryType(uri?: string): string {
  if (!uri) return 'resources'
  const lower = uri.toLowerCase()
  if (lower.includes('/memories/cases') || lower.includes('/cases/')) return 'cases'
  if (lower.includes('/memories/entities') || lower.includes('/entities/')) return 'entities'
  if (lower.includes('/memories/events') || lower.includes('/events/')) return 'events'
  if (lower.includes('/memories/experiences') || lower.includes('/experiences/')) return 'experiences'
  if (lower.includes('/memories/trajectories') || lower.includes('/trajectories/')) return 'trajectories'
  if (lower.includes('/memories/lessons') || lower.includes('/lessons/')) return 'lessons'
  if (lower.includes('/memories/profile') || lower.includes('/profile/')) return 'profile'
  if (lower.includes('/skills/') || lower.includes('skill')) return 'skills'
  if (lower.includes('/staging/')) return 'staging'
  if (lower.includes('/sessions/')) return 'sessions'
  return 'resources'
}
