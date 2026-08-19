import type { TaskRecord } from './task-record'
import type { ParsedQueueRow } from '#/routes/monitoring/-components/queue-status-card'

export type StepState = 'completed' | 'running' | 'pending' | 'failed'

export type PipelineStep = {
  name: string
  state: StepState
  processed?: number
  total?: number
  count?: number
  unit?: string
  detail?: string
}

export type PipelineGroup =
  | { type: 'serial'; step: PipelineStep }
  | { type: 'parallel'; steps: PipelineStep[] }

export interface QuantifiedWorkload {
  icon: string
  label: string
  processed?: number
  total?: number
  unit: string
  pct?: number
}

function inferStepState(
  qKey: string | null,
  stepOrder: number, // 1-based index
  totalSteps: number,
  taskStatus: string | null | undefined,
  taskStage: string | null | undefined,
  qStatus: Record<string, { error_count?: number; processed?: number }> | undefined,
): StepState {
  const normStatus = taskStatus?.toLowerCase()
  if (normStatus === 'completed') return 'completed'
  if (normStatus === 'failed') {
    // If we have explicit queue error
    if (qKey && qStatus?.[qKey] && (qStatus[qKey].error_count ?? 0) > 0) return 'failed'
    return stepOrder === totalSteps ? 'failed' : 'completed'
  }
  if (normStatus === 'pending') return 'pending'

  // If task is running
  if (normStatus === 'running') {
    const stage = taskStage?.toLowerCase() || ''
    if (qKey === 'Embedding' && (stage.includes('embedding') || stage.includes('reindex'))) return 'running'
    if (qKey === 'Semantic' && (stage.includes('semantic') || stage.includes('extract'))) return 'running'
    if (qKey === 'ExternalParse' && (stage.includes('parse') || stage.includes('scan'))) return 'running'

    // If queue has explicit processed count, mark previous steps as completed
    if (qKey && qStatus?.[qKey]) {
      const s = qStatus[qKey]
      if ((s.error_count ?? 0) > 0) return 'failed'
      if ((s.processed ?? 0) > 0) return 'completed'
    }

    if (stepOrder === 1) return 'completed'
    if (stepOrder === 2) return 'running'
    return 'pending'
  }

  return 'pending'
}

/**
 * Single Source of Truth (SSOT) for task pipeline steps list.
 * 100% physically aligned with getTaskPipelineGroups.
 */
export function getTaskPipelineSteps(
  task: TaskRecord,
  language: string = 'zh',
): PipelineStep[] {
  const isZh = language.startsWith('zh')
  const type = task.task_type
  const status = task.status
  const stage = task.stage
  const resObj = (task.result && typeof task.result === 'object') ? (task.result as Record<string, any>) : {}
  const metaObj = (task.meta && typeof task.meta === 'object') ? (task.meta as Record<string, any>) : {}
  const qStatus = resObj.queue_status as Record<string, { error_count?: number; processed?: number }> | undefined

  if (type === 'session_commit') {
    const turns = metaObj.turns_count ?? resObj.turns_processed ?? metaObj.messages_count
    const lessons = resObj.lessons_extracted ?? metaObj.lessons_count
    return [
      {
        name: isZh ? '对话归档' : 'Archival',
        state: status === 'pending' ? 'pending' : 'completed',
        count: turns,
        unit: isZh ? '轮' : 'turns',
      },
      {
        name: isZh ? '经验萃取' : 'Lessons',
        state: inferStepState(null, 2, 3, status, stage, qStatus),
        count: lessons,
        unit: isZh ? '条经验' : 'lessons',
      },
      {
        name: isZh ? '快照提交' : 'Snapshot',
        state: status === 'completed' ? 'completed' : 'pending',
      },
    ]
  }

  if (type === 'add_skill') {
    const skills = resObj.valid_skills ?? metaObj.valid_skills ?? resObj.scanned_skills
    return [
      {
        name: isZh ? '目录扫描' : 'Discovery',
        state: status === 'pending' ? 'pending' : 'completed',
      },
      {
        name: isZh ? '规范校验' : 'Spec Validation',
        state: inferStepState(null, 2, 3, status, stage, qStatus),
        count: skills,
        unit: isZh ? '技能' : 'skills',
      },
      {
        name: isZh ? '向量建库' : 'Vector Embedding',
        state: inferStepState('Embedding', 3, 3, status, stage, qStatus),
      },
    ]
  }

  if (type === 'user_delete' || type === 'user_deletion') {
    return [
      {
        name: isZh ? '空间解绑' : 'Namespace Unbind',
        state: status === 'pending' ? 'pending' : 'completed',
      },
      {
        name: isZh ? '向量注销' : 'Vector Purge',
        state: inferStepState('UserDeletion', 2, 3, status, stage, qStatus),
        count: resObj.deleted_vectors ?? metaObj.deleted_vectors,
        unit: isZh ? '向量' : 'vectors',
      },
      {
        name: isZh ? '磁盘擦除' : 'Disk Wipe',
        state: status === 'completed' ? 'completed' : 'pending',
        count: resObj.deleted_files ?? metaObj.deleted_files,
        unit: isZh ? '项' : 'items',
      },
    ]
  }

  if (type === 'admin_reindex') {
    return [
      {
        name: isZh ? '资源扫描' : 'Scanning',
        state: status === 'pending' ? 'pending' : 'completed',
        count: resObj.scanned_records ?? metaObj.scanned_records,
        unit: isZh ? '项' : 'items',
      },
      {
        name: isZh ? '孤儿修剪' : 'Pruning',
        state: inferStepState(null, 2, 3, status, stage, qStatus),
        count: resObj.deleted_records ?? metaObj.deleted_records,
        unit: isZh ? '孤儿块' : 'orphans',
      },
      {
        name: isZh ? '切片重构' : 'Embedding',
        state: inferStepState('Embedding', 3, 3, status, stage, qStatus),
        count: resObj.rebuilt_records ?? resObj.reindexed_items ?? metaObj.rebuilt_records,
        unit: isZh ? '切片' : 'chunks',
      },
    ]
  }

  if (type === 'snapshot_restore_reindex') {
    return [
      {
        name: isZh ? '快照回滚' : 'Rollback',
        state: status === 'pending' ? 'pending' : 'completed',
      },
      {
        name: isZh ? '节点还原' : 'Inodes',
        state: inferStepState(null, 2, 3, status, stage, qStatus),
        count: resObj.restored_inodes ?? metaObj.restored_inodes,
        unit: isZh ? '节点' : 'inodes',
      },
      {
        name: isZh ? '增量向量' : 'Embedding',
        state: inferStepState('Embedding', 3, 3, status, stage, qStatus),
        count: resObj.reindexed_items ?? metaObj.reindexed_items,
        unit: isZh ? '切片' : 'chunks',
      },
    ]
  }

  if (type === 'connector_import') {
    return [
      { name: isZh ? '连接鉴权' : 'Auth', state: status === 'pending' ? 'pending' : 'completed' },
      { name: isZh ? '资源拉取' : 'Fetch', state: inferStepState(null, 2, 5, status, stage, qStatus), count: resObj.downloaded_files ?? metaObj.downloaded_files, unit: isZh ? '篇' : 'docs' },
      { name: isZh ? '文档解析' : 'Parse', state: inferStepState('ExternalParse', 3, 5, status, stage, qStatus), count: metaObj.parsed_pages, unit: isZh ? '页' : 'pages' },
      { name: isZh ? '语义提取' : 'Semantic', state: inferStepState('Semantic', 4, 5, status, stage, qStatus), count: metaObj.semantic_nodes, unit: isZh ? '节点' : 'nodes' },
      { name: isZh ? '向量建库' : 'Embedding', state: inferStepState('Embedding', 5, 5, status, stage, qStatus), count: metaObj.processed_chunks, unit: isZh ? '切片' : 'chunks' },
    ]
  }

  if (type === 'legacy_migration') {
    return [
      { name: isZh ? '数据读取' : 'Read', state: status === 'pending' ? 'pending' : 'completed' },
      { name: isZh ? 'Schema 转换' : 'Transform', state: inferStepState(null, 2, 3, status, stage, qStatus), count: resObj.migrated_count ?? metaObj.migrated_count, unit: isZh ? '条' : 'records' },
      { name: isZh ? 'AGFS 写入' : 'Write', state: status === 'completed' ? 'completed' : 'pending' },
    ]
  }

  if (type === 'legacy_cleanup') {
    return [
      { name: isZh ? '图谱遍历' : 'Traverse', state: status === 'pending' ? 'pending' : 'completed' },
      { name: isZh ? '孤儿回收' : 'GC', state: inferStepState(null, 2, 3, status, stage, qStatus), count: resObj.cleaned_items ?? metaObj.cleaned_items, unit: isZh ? '项' : 'items' },
      { name: isZh ? '空间释放' : 'Free', state: status === 'completed' ? 'completed' : 'pending' },
    ]
  }

  if (type === 'watch_sync') {
    return [
      { name: isZh ? '事件监听' : 'Events', state: status === 'pending' ? 'pending' : 'completed', count: metaObj.events_count, unit: isZh ? '事件' : 'events' },
      { name: isZh ? '增量解析' : 'Parse', state: inferStepState('ExternalParse', 2, 3, status, stage, qStatus), count: resObj.synced_files ?? metaObj.synced_files, unit: isZh ? '文件' : 'files' },
      { name: isZh ? '向量同步' : 'Sync', state: inferStepState('Embedding', 3, 3, status, stage, qStatus) },
    ]
  }

  // Default resource ingestion pipeline (add_resource): 资源入库 -> 文档解析 -> (语义提取 + 向量建库)
  const isEmbedStage = stage?.toLowerCase().includes('embedding')
  const isSemStage = stage?.toLowerCase().includes('semantic') || stage?.toLowerCase().includes('extract')
  const isParseStage = stage?.toLowerCase().includes('parse') || stage?.toLowerCase().includes('scan')

  const s1: StepState = status === 'pending' ? 'pending' : 'completed'
  const s2: StepState = status === 'completed' ? 'completed' : isParseStage ? 'running' : status === 'running' ? 'completed' : 'pending'
  const s3: StepState = status === 'completed' ? 'completed' : isSemStage ? 'running' : status === 'running' ? (isEmbedStage ? 'completed' : 'running') : 'pending'
  const s4: StepState = status === 'completed' ? 'completed' : isEmbedStage ? 'running' : status === 'running' ? 'running' : 'pending'

  const extParseProcessed = qStatus?.ExternalParse?.processed ?? metaObj.processed_pages
  const extParseTotal = qStatus?.ExternalParse?.total ?? metaObj.total_pages ?? metaObj.parsed_pages

  const semProcessed = qStatus?.Semantic?.processed ?? metaObj.processed_nodes
  const semTotal = qStatus?.Semantic?.total ?? metaObj.total_nodes ?? metaObj.semantic_nodes

  const embProcessed = qStatus?.Embedding?.processed ?? metaObj.processed_chunks
  const embTotal = qStatus?.Embedding?.total ?? metaObj.total_chunks ?? metaObj.processed_chunks

  return [
    {
      name: isZh ? '资源入库' : 'Ingestion',
      state: s1,
      processed: metaObj.file_count ? metaObj.file_count : 1,
      total: metaObj.file_count ? metaObj.file_count : 1,
      count: metaObj.file_count ?? 1,
      unit: isZh ? '文件' : 'files',
    },
    {
      name: isZh ? '文档解析' : 'Parsing',
      state: s2,
      processed: extParseProcessed,
      total: extParseTotal,
      count: metaObj.parsed_pages,
      unit: isZh ? '页' : 'pages',
    },
    {
      name: isZh ? '语义提取' : 'Semantic',
      state: s3,
      processed: semProcessed,
      total: semTotal,
      count: metaObj.semantic_nodes,
      unit: isZh ? '节点' : 'nodes',
    },
    {
      name: isZh ? '向量建库' : 'Embedding',
      state: s4,
      processed: embProcessed,
      total: embTotal,
      count: metaObj.processed_chunks,
      unit: isZh ? '切片' : 'chunks',
    },
  ]
}

/**
 * Single Source of Truth (SSOT) for task pipeline diagram groups.
 * 100% physically aligned with getTaskPipelineSteps.
 */
export function getTaskPipelineGroups(
  task: TaskRecord,
  language: string = 'zh',
): PipelineGroup[] {
  const isZh = language.startsWith('zh')
  const type = task.task_type
  const steps = getTaskPipelineSteps(task, language)

  if (type === 'session_commit') {
    return [
      { type: 'serial', step: steps[0] },
      { type: 'serial', step: steps[1] },
      { type: 'serial', step: steps[2] },
    ]
  }

  if (type === 'add_skill') {
    return [
      { type: 'serial', step: steps[0] },
      { type: 'serial', step: steps[1] },
      { type: 'serial', step: steps[2] },
    ]
  }

  if (type === 'user_delete' || type === 'user_deletion') {
    return [
      { type: 'serial', step: steps[0] },
      { type: 'serial', step: steps[1] },
      { type: 'serial', step: steps[2] },
    ]
  }

  if (type === 'admin_reindex') {
    return [
      { type: 'serial', step: steps[0] },
      { type: 'serial', step: steps[1] },
      { type: 'serial', step: steps[2] },
    ]
  }

  if (type === 'snapshot_restore_reindex') {
    return [
      { type: 'serial', step: steps[0] },
      { type: 'serial', step: steps[1] },
      { type: 'serial', step: steps[2] },
    ]
  }

  if (type === 'connector_import') {
    return [
      { type: 'serial', step: steps[0] },
      { type: 'serial', step: steps[1] },
      { type: 'serial', step: steps[2] },
      {
        type: 'parallel',
        steps: [steps[3], steps[4]],
      },
    ]
  }

  if (type === 'legacy_migration') {
    return [
      { type: 'serial', step: steps[0] },
      { type: 'serial', step: steps[1] },
      { type: 'serial', step: steps[2] },
    ]
  }

  if (type === 'legacy_cleanup') {
    return [
      { type: 'serial', step: steps[0] },
      { type: 'serial', step: steps[1] },
      { type: 'serial', step: steps[2] },
    ]
  }

  if (type === 'watch_sync') {
    return [
      { type: 'serial', step: steps[0] },
      { type: 'serial', step: steps[1] },
      { type: 'serial', step: steps[2] },
    ]
  }

  // Default resource ingestion pipeline: 资源入库 -> 文档解析 -> [ 语义提取 ∥ 向量建库 ]
  return [
    { type: 'serial', step: steps[0] },
    { type: 'serial', step: steps[1] },
    {
      type: 'parallel',
      steps: [steps[2], steps[3]],
    },
  ]
}

/**
 * Extract rich quantified physical workload ONLY from task's OWN data or active running stage.
 * NEVER falsely leaks global QueueFS observer totals to unrelated tasks.
 */
export function getTaskQuantifiedWorkload(
  task: TaskRecord,
  queueRows: ParsedQueueRow[] = [],
  language: string = 'zh',
): QuantifiedWorkload | null {
  const isZh = language.startsWith('zh')
  const type = task.task_type
  const status = task.status?.toLowerCase()
  const meta = (task.meta && typeof task.meta === 'object') ? (task.meta as Record<string, any>) : {}
  const resObj = (task.result && typeof task.result === 'object') ? (task.result as Record<string, any>) : {}

  // 1. Task's OWN Explicit Numerical Quantities (Highest precision)
  if (typeof meta.processed_chunks === 'number' && typeof meta.total_chunks === 'number' && meta.total_chunks > 0) {
    const pct = Math.round((meta.processed_chunks / meta.total_chunks) * 100)
    return {
      icon: '⚡',
      label: isZh
        ? `${meta.processed_chunks.toLocaleString()} / ${meta.total_chunks.toLocaleString()} 切片 (${pct}%)`
        : `${meta.processed_chunks.toLocaleString()} / ${meta.total_chunks.toLocaleString()} chunks (${pct}%)`,
      processed: meta.processed_chunks,
      total: meta.total_chunks,
      unit: isZh ? '切片' : 'chunks',
      pct,
    }
  }

  if (typeof meta.processed_nodes === 'number' && typeof meta.total_nodes === 'number' && meta.total_nodes > 0) {
    const pct = Math.round((meta.processed_nodes / meta.total_nodes) * 100)
    return {
      icon: '🧠',
      label: isZh
        ? `${meta.processed_nodes.toLocaleString()} / ${meta.total_nodes.toLocaleString()} 节点 (${pct}%)`
        : `${meta.processed_nodes.toLocaleString()} / ${meta.total_nodes.toLocaleString()} nodes (${pct}%)`,
      processed: meta.processed_nodes,
      total: meta.total_nodes,
      unit: isZh ? '节点' : 'nodes',
      pct,
    }
  }

  if (typeof meta.processed_pages === 'number' && typeof meta.total_pages === 'number' && meta.total_pages > 0) {
    const pct = Math.round((meta.processed_pages / meta.total_pages) * 100)
    return {
      icon: '📑',
      label: isZh
        ? `${meta.processed_pages.toLocaleString()} / ${meta.total_pages.toLocaleString()} 页 (${pct}%)`
        : `${meta.processed_pages.toLocaleString()} / ${meta.total_pages.toLocaleString()} pages (${pct}%)`,
      processed: meta.processed_pages,
      total: meta.total_pages,
      unit: isZh ? '页' : 'pages',
      pct,
    }
  }

  // 2. Type-specific result/meta for this task
  if (type === 'session_commit') {
    const turns = meta.turns_count ?? resObj.turns_processed ?? meta.messages_count
    const lessons = resObj.lessons_extracted ?? meta.lessons_count
    if (turns !== undefined || lessons !== undefined) {
      const parts: string[] = []
      if (turns !== undefined) parts.push(isZh ? `${turns} 轮对话` : `${turns} turns`)
      if (lessons !== undefined) parts.push(isZh ? `${lessons} 条经验` : `${lessons} lessons`)
      return {
        icon: '💾',
        label: parts.join(isZh ? ' ｜ ' : ' | '),
        unit: isZh ? '轮对话' : 'turns',
      }
    }
    if (status === 'completed') {
      return {
        icon: '💾',
        label: isZh ? '会话已归档' : 'Committed',
        unit: isZh ? '会话' : 'session',
      }
    }
  }

  if (type === 'add_skill') {
    const skills = resObj.valid_skills ?? resObj.scanned_skills ?? meta.valid_skills
    if (skills !== undefined) {
      return {
        icon: '🤹',
        label: isZh ? `${skills} 项技能` : `${skills} skills`,
        unit: isZh ? '项技能' : 'skills',
      }
    }
  }

  if (type === 'admin_reindex') {
    const items = resObj.rebuilt_records ?? resObj.reindexed_items
    if (items !== undefined) {
      return {
        icon: '⚡',
        label: isZh ? `${items.toLocaleString()} 重构切片` : `${items.toLocaleString()} chunks`,
        unit: isZh ? '切片' : 'chunks',
      }
    }
  }

  if (type === 'user_delete' || type === 'user_deletion') {
    const items = resObj.deleted_files ?? meta.deleted_files
    const vectors = resObj.deleted_vectors ?? meta.deleted_vectors
    if (items !== undefined || vectors !== undefined) {
      const parts: string[] = []
      if (items !== undefined) parts.push(isZh ? `${items} 项资源` : `${items} items`)
      if (vectors !== undefined) parts.push(isZh ? `${vectors} 向量` : `${vectors} vectors`)
      return {
        icon: '🧹',
        label: parts.join(' ｜ '),
        unit: isZh ? '项' : 'items',
      }
    }
  }

  if (type === 'connector_import') {
    const docs = resObj.downloaded_files ?? meta.downloaded_files
    const mb = meta.downloaded_mb ?? resObj.downloaded_mb
    if (docs !== undefined) {
      return {
        icon: '🔌',
        label: mb ? `${docs} 篇 (${mb} MB)` : `${docs} 篇文档`,
        unit: isZh ? '篇文档' : 'docs',
      }
    }
  }

  if (type === 'snapshot_restore_reindex') {
    const inodes = resObj.restored_inodes ?? meta.restored_inodes
    const items = resObj.reindexed_items ?? meta.reindexed_items
    if (inodes !== undefined || items !== undefined) {
      const parts: string[] = []
      if (inodes !== undefined) parts.push(isZh ? `${inodes} 还原节点` : `${inodes} inodes`)
      if (items !== undefined) parts.push(isZh ? `${items} 切片` : `${items} chunks`)
      return {
        icon: '🔄',
        label: parts.join(' ｜ '),
        unit: isZh ? '节点' : 'inodes',
      }
    }
  }

  // 3. ONLY for currently RUNNING tasks, match active QueueFS throughput
  if (status === 'running') {
    const stage = task.stage?.toLowerCase() || ''
    const embeddingRow = queueRows.find((r) => r.name.toLowerCase().includes('embedding'))
    const semanticRow = queueRows.find((r) => r.name.toLowerCase().includes('semantic'))
    const parseRow = queueRows.find((r) => r.name.toLowerCase().includes('parse'))

    if (stage.includes('extract') || stage.includes('semantic')) {
      if (semanticRow && semanticRow.total > 0) {
        const pct = Math.round((semanticRow.completed / semanticRow.total) * 100)
        return {
          icon: '🧠',
          label: isZh
            ? `${semanticRow.completed.toLocaleString()} / ${semanticRow.total.toLocaleString()} 节点 (${pct}%)`
            : `${semanticRow.completed.toLocaleString()} / ${semanticRow.total.toLocaleString()} nodes (${pct}%)`,
          processed: semanticRow.completed,
          total: semanticRow.total,
          unit: isZh ? '节点' : 'nodes',
          pct,
        }
      }
    }

    if (stage.includes('parse') || stage.includes('scan')) {
      if (parseRow && parseRow.total > 0) {
        const pct = Math.round((parseRow.completed / parseRow.total) * 100)
        return {
          icon: '📑',
          label: isZh
            ? `${parseRow.completed.toLocaleString()} / ${parseRow.total.toLocaleString()} 页 (${pct}%)`
            : `${parseRow.completed.toLocaleString()} / ${parseRow.total.toLocaleString()} pages (${pct}%)`,
          processed: parseRow.completed,
          total: parseRow.total,
          unit: isZh ? '页' : 'pages',
          pct,
        }
      }
    }

    if (stage.includes('embed') || stage.includes('reindex') || type === 'add_resource' || type === 'connector_import') {
      if (embeddingRow && embeddingRow.total > 0 && embeddingRow.processing > 0) {
        const pct = Math.round((embeddingRow.completed / embeddingRow.total) * 100)
        return {
          icon: '⚡',
          label: isZh
            ? `${embeddingRow.completed.toLocaleString()} / ${embeddingRow.total.toLocaleString()} 切片 (${pct}%)`
            : `${embeddingRow.completed.toLocaleString()} / ${embeddingRow.total.toLocaleString()} chunks (${pct}%)`,
          processed: embeddingRow.completed,
          total: embeddingRow.total,
          unit: isZh ? '切片' : 'chunks',
          pct,
        }
      }
    }
  }

  return null
}
