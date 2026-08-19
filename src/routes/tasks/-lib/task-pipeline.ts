import type { TaskRecord } from './task-record'
import type { ParsedQueueRow } from '#/routes/monitoring/-components/queue-status-card'

export type StepState = 'completed' | 'running' | 'pending' | 'failed'

export type PipelineStep = {
  name: string
  state: StepState
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

function inferState(
  qKey: string | null,
  fallback: StepState,
  status: string | undefined,
  qStatus: Record<string, { error_count?: number; processed?: number }> | undefined,
): StepState {
  if (status === 'pending') return 'pending'
  if (qKey && qStatus?.[qKey]) {
    const s = qStatus[qKey]
    if ((s.error_count ?? 0) > 0) return 'failed'
    if ((s.processed ?? 0) > 0) return 'completed'
    return status === 'running' ? 'running' : fallback
  }
  return fallback
}

/**
 * Single Source of Truth (SSOT) for task pipeline steps list.
 * Used by Task Detail Sheet Drawer for all 12 task types.
 */
export function getTaskPipelineSteps(
  task: TaskRecord,
  language: string = 'zh',
): PipelineStep[] {
  const isZh = language.startsWith('zh')
  const type = task.task_type
  const status = task.status
  const resObj = (task.result || {}) as Record<string, any>
  const metaObj = (task.meta || {}) as Record<string, any>
  const qStatus = resObj.queue_status as Record<string, { error_count?: number; processed?: number }> | undefined

  if (type === 'session_commit') {
    return [
      {
        name: isZh ? '对话轮次归档' : 'Dialogue Archival',
        state: status === 'pending' ? 'pending' : 'completed',
        count: metaObj.turns_count ?? metaObj.messages_count,
        unit: isZh ? '轮' : 'turns',
      },
      {
        name: isZh ? '经验 Lesson 萃取' : 'Lesson Extraction',
        state: status === 'pending' ? 'pending' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'completed',
        count: resObj.lessons_extracted ?? metaObj.lessons_count,
        unit: isZh ? '条经验' : 'lessons',
      },
      {
        name: isZh ? '快照持久化提交' : 'Snapshot Persistence',
        state: status === 'completed' ? 'completed' : (status as StepState),
      },
    ]
  }

  if (type === 'add_skill') {
    return [
      {
        name: isZh ? '目录递归扫描' : 'Directory Discovery',
        state: status === 'pending' ? 'pending' : 'completed',
      },
      {
        name: isZh ? 'Frontmatter 规范校验' : 'Frontmatter Validation',
        state: status === 'pending' ? 'pending' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'completed',
        count: resObj.valid_skills ?? metaObj.valid_skills,
        unit: isZh ? '技能' : 'skills',
      },
      {
        name: isZh ? '技能向量化建库' : 'Skill Embedding Indexing',
        state: inferState('Embedding', status === 'completed' ? 'completed' : (status as StepState), status, qStatus),
      },
    ]
  }

  if (type === 'user_delete' || type === 'user_deletion') {
    return [
      {
        name: isZh ? '命名空间解绑' : 'Namespace Unbinding',
        state: status === 'pending' ? 'pending' : 'completed',
      },
      {
        name: isZh ? 'VikingDB 向量注销' : 'Vector Deletion',
        state: status === 'pending' ? 'pending' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'completed',
        count: resObj.deleted_vectors ?? metaObj.deleted_vectors,
        unit: isZh ? '向量' : 'vectors',
      },
      {
        name: isZh ? 'AGFS 磁盘物理擦除' : 'AGFS Disk Cleanup',
        state: status === 'completed' ? 'completed' : (status as StepState),
        count: resObj.deleted_files ?? metaObj.deleted_files,
        unit: isZh ? '项' : 'items',
      },
    ]
  }

  if (type === 'admin_reindex') {
    return [
      {
        name: isZh ? '全盘资源扫描' : 'Resource Scanning',
        state: status === 'pending' ? 'pending' : 'completed',
        count: resObj.scanned_records ?? metaObj.scanned_records,
        unit: isZh ? '条目' : 'items',
      },
      {
        name: isZh ? '孤儿向量修剪' : 'Orphan Pruning',
        state: status === 'pending' ? 'pending' : 'completed',
        count: resObj.deleted_records ?? metaObj.deleted_records,
        unit: isZh ? '孤儿块' : 'orphans',
      },
      {
        name: isZh ? '批量切片重构' : 'Batch Chunk Embedding',
        state: inferState('Embedding', status === 'completed' ? 'completed' : (status as StepState), status, qStatus),
        count: resObj.rebuilt_records ?? resObj.reindexed_items ?? metaObj.rebuilt_records,
        unit: isZh ? '切片' : 'chunks',
      },
    ]
  }

  if (type === 'snapshot_restore_reindex') {
    return [
      {
        name: isZh ? '快照状态回滚' : 'Snapshot Rollback',
        state: status === 'pending' ? 'pending' : 'completed',
      },
      {
        name: isZh ? 'AGFS 节点树还原' : 'Inode Tree Restoration',
        state: status === 'pending' ? 'pending' : 'completed',
        count: resObj.restored_inodes ?? metaObj.restored_inodes,
        unit: isZh ? '节点' : 'inodes',
      },
      {
        name: isZh ? '增量向量重算' : 'Incremental Embedding',
        state: inferState('Embedding', status === 'completed' ? 'completed' : (status as StepState), status, qStatus),
        count: resObj.reindexed_items ?? metaObj.reindexed_items,
        unit: isZh ? '切片' : 'chunks',
      },
    ]
  }

  if (type === 'connector_import') {
    const preState: StepState = status === 'pending' ? 'pending' : 'completed'
    return [
      { name: isZh ? '连接器鉴权' : 'Connector Auth', state: preState },
      { name: isZh ? '远程资源拉取' : 'Resource Fetching', state: preState, count: resObj.downloaded_files ?? metaObj.downloaded_files, unit: isZh ? '篇文档' : 'docs' },
      { name: isZh ? '外部多格式解析' : 'Document Parsing', state: inferState('Semantic', status === 'completed' ? 'completed' : (status as StepState), status, qStatus) },
      { name: isZh ? '语义处理' : 'Semantic Extraction', state: inferState('Semantic', status === 'completed' ? 'completed' : (status as StepState), status, qStatus), count: qStatus?.Semantic?.processed, unit: isZh ? '节点' : 'nodes' },
      { name: isZh ? '嵌入向量' : 'Vector Embedding', state: inferState('Embedding', status === 'completed' ? 'completed' : (status as StepState), status, qStatus), count: qStatus?.Embedding?.processed, unit: isZh ? '切片' : 'chunks' },
    ]
  }

  if (type === 'legacy_migration') {
    return [
      {
        name: isZh ? '历史数据读取' : 'Legacy Data Reading',
        state: status === 'pending' ? 'pending' : 'completed',
      },
      {
        name: isZh ? 'Schema 格式转换' : 'Schema Conversion',
        state: status === 'pending' ? 'pending' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'completed',
        count: resObj.migrated_count ?? metaObj.migrated_count,
        unit: isZh ? '条记录' : 'records',
      },
      {
        name: isZh ? 'AGFS 新结构写入' : 'AGFS Target Ingestion',
        state: status === 'completed' ? 'completed' : (status as StepState),
      },
    ]
  }

  if (type === 'legacy_cleanup') {
    return [
      {
        name: isZh ? '引用图谱遍历' : 'Graph Traversal',
        state: status === 'pending' ? 'pending' : 'completed',
      },
      {
        name: isZh ? '孤儿数据回收' : 'Orphan Garbage Collection',
        state: status === 'pending' ? 'pending' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'completed',
        count: resObj.cleaned_items ?? metaObj.cleaned_items,
        unit: isZh ? '孤儿块' : 'items',
      },
      {
        name: isZh ? '存储空间释放' : 'Storage Reclamation',
        state: status === 'completed' ? 'completed' : (status as StepState),
      },
    ]
  }

  if (type === 'watch_sync') {
    return [
      {
        name: isZh ? '文件变更事件监听' : 'File Event Listening',
        state: status === 'pending' ? 'pending' : 'completed',
        count: metaObj.events_count,
        unit: isZh ? '事件' : 'events',
      },
      {
        name: isZh ? '防抖增量解析' : 'Debounced Parsing',
        state: status === 'pending' ? 'pending' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'completed',
        count: resObj.synced_files ?? metaObj.synced_files,
        unit: isZh ? '文件' : 'files',
      },
      {
        name: isZh ? '增量向量同步' : 'Incremental Sync',
        state: inferState('Embedding', status === 'completed' ? 'completed' : (status as StepState), status, qStatus),
      },
    ]
  }

  // Default resource ingestion pipeline: 文件扫描 -> 外部解析 -> (语义处理 + 嵌入向量)
  return [
    {
      name: isZh ? '资源扫描与入库' : 'Resource Ingestion',
      state: status === 'pending' ? 'pending' : 'completed',
      count: metaObj.file_count,
      unit: isZh ? '文件' : 'files',
    },
    {
      name: isZh ? '外部多格式解析' : 'Document Parsing',
      state: inferState('ExternalParse', status === 'completed' ? 'completed' : (status as StepState), status, qStatus),
      count: qStatus?.ExternalParse?.processed ?? metaObj.parsed_pages,
      unit: isZh ? '页' : 'pages',
    },
    {
      name: isZh ? '语义处理' : 'Semantic Extraction',
      state: inferState('Semantic', status === 'completed' ? 'completed' : (status as StepState), status, qStatus),
      count: qStatus?.Semantic?.processed ?? metaObj.semantic_nodes,
      unit: isZh ? '节点' : 'nodes',
    },
    {
      name: isZh ? '嵌入向量' : 'Vector Embedding',
      state: inferState('Embedding', status === 'completed' ? 'completed' : (status as StepState), status, qStatus),
      count: qStatus?.Embedding?.processed ?? metaObj.processed_chunks,
      unit: isZh ? '切片' : 'chunks',
    },
  ]
}

/**
 * Single Source of Truth (SSOT) for task pipeline diagram groups.
 * Used by Task Table Row column "工序队列流转".
 */
export function getTaskPipelineGroups(
  task: TaskRecord,
  language: string = 'zh',
): PipelineGroup[] {
  const isZh = language.startsWith('zh')
  const type = task.task_type
  const status = task.status
  const resObj = (task.result || {}) as Record<string, any>
  const qStatus = resObj.queue_status as Record<string, { error_count?: number; processed?: number }> | undefined

  if (type === 'session_commit') {
    return [
      {
        type: 'serial',
        step: {
          name: isZh ? '对话归档' : 'Archival',
          state: status === 'pending' ? 'pending' : 'completed',
        },
      },
      {
        type: 'serial',
        step: {
          name: isZh ? '经验萃取' : 'Lessons',
          state: status === 'pending' ? 'pending' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'completed',
        },
      },
      {
        type: 'serial',
        step: {
          name: isZh ? '快照提交' : 'Snapshot',
          state: status === 'completed' ? 'completed' : (status as StepState),
        },
      },
    ]
  }

  if (type === 'add_skill') {
    return [
      {
        type: 'serial',
        step: { name: isZh ? '目录扫描' : 'Discovery', state: status === 'pending' ? 'pending' : 'completed' },
      },
      {
        type: 'serial',
        step: { name: isZh ? '规范校验' : 'Spec', state: status === 'pending' ? 'pending' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'completed' },
      },
      {
        type: 'serial',
        step: { name: isZh ? '向量建库' : 'Embedding', state: inferState('Embedding', status === 'completed' ? 'completed' : (status as StepState), status, qStatus) },
      },
    ]
  }

  if (type === 'user_delete' || type === 'user_deletion') {
    return [
      {
        type: 'serial',
        step: { name: isZh ? '空间解绑' : 'Unbind', state: status === 'pending' ? 'pending' : 'completed' },
      },
      {
        type: 'serial',
        step: { name: isZh ? '向量注销' : 'Vector Purge', state: status === 'pending' ? 'pending' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'completed' },
      },
      {
        type: 'serial',
        step: { name: isZh ? '磁盘擦除' : 'Disk Wipe', state: status === 'completed' ? 'completed' : (status as StepState) },
      },
    ]
  }

  if (type === 'admin_reindex') {
    const purgeState: StepState = status === 'pending' ? 'pending' : 'completed'
    const rebuildState = inferState('Embedding', status === 'completed' ? 'completed' : (status as StepState), status, qStatus)
    return [
      { type: 'serial', step: { name: isZh ? '资源扫描' : 'Scan', state: purgeState } },
      { type: 'serial', step: { name: isZh ? '孤儿修剪' : 'Prune', state: purgeState } },
      { type: 'serial', step: { name: isZh ? '切片重构' : 'Embedding', state: rebuildState } },
    ]
  }

  if (type === 'snapshot_restore_reindex') {
    return [
      { type: 'serial', step: { name: isZh ? '快照回滚' : 'Restore', state: status === 'pending' ? 'pending' : 'completed' } },
      { type: 'serial', step: { name: isZh ? '节点还原' : 'Inodes', state: status === 'pending' ? 'pending' : 'completed' } },
      { type: 'serial', step: { name: isZh ? '增量向量' : 'Embedding', state: inferState('Embedding', status === 'completed' ? 'completed' : (status as StepState), status, qStatus) } },
    ]
  }

  if (type === 'connector_import') {
    const preState: StepState = status === 'pending' ? 'pending' : 'completed'
    const semState = inferState('Semantic', status === 'completed' ? 'completed' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'pending', status, qStatus)
    const embState = inferState('Embedding', status === 'completed' ? 'completed' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'pending', status, qStatus)
    return [
      { type: 'serial', step: { name: isZh ? '连接鉴权' : 'Auth', state: preState } },
      { type: 'serial', step: { name: isZh ? '资源拉取' : 'Fetch', state: preState } },
      { type: 'serial', step: { name: isZh ? '外部解析' : 'Parse', state: preState } },
      {
        type: 'parallel',
        steps: [
          { name: isZh ? '语义处理' : 'Semantic', state: semState },
          { name: isZh ? '嵌入向量' : 'Embedding', state: embState },
        ],
      },
    ]
  }

  if (type === 'legacy_migration') {
    return [
      { type: 'serial', step: { name: isZh ? '数据读取' : 'Read', state: status === 'pending' ? 'pending' : 'completed' } },
      { type: 'serial', step: { name: isZh ? 'Schema 转换' : 'Transform', state: status === 'pending' ? 'pending' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'completed' } },
      { type: 'serial', step: { name: isZh ? 'AGFS 写入' : 'Write', state: status === 'completed' ? 'completed' : (status as StepState) } },
    ]
  }

  if (type === 'legacy_cleanup') {
    return [
      { type: 'serial', step: { name: isZh ? '图谱遍历' : 'Traverse', state: status === 'pending' ? 'pending' : 'completed' } },
      { type: 'serial', step: { name: isZh ? '孤儿回收' : 'GC', state: status === 'pending' ? 'pending' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'completed' } },
      { type: 'serial', step: { name: isZh ? '空间释放' : 'Free', state: status === 'completed' ? 'completed' : (status as StepState) } },
    ]
  }

  if (type === 'watch_sync') {
    return [
      { type: 'serial', step: { name: isZh ? '事件监听' : 'Events', state: status === 'pending' ? 'pending' : 'completed' } },
      { type: 'serial', step: { name: isZh ? '增量解析' : 'Parse', state: status === 'pending' ? 'pending' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'completed' } },
      { type: 'serial', step: { name: isZh ? '向量同步' : 'Sync', state: inferState('Embedding', status === 'completed' ? 'completed' : (status as StepState), status, qStatus) } },
    ]
  }

  // Default resource ingestion pipeline: 外部解析 -> (语义处理 + 嵌入向量)
  const parseState: StepState = status === 'pending' ? 'pending' : 'completed'
  const semState = inferState('Semantic', status === 'completed' ? 'completed' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'pending', status, qStatus)
  const embState = inferState('Embedding', status === 'completed' ? 'completed' : status === 'running' ? 'running' : status === 'failed' ? 'failed' : 'pending', status, qStatus)
  return [
    { type: 'serial', step: { name: isZh ? '外部解析' : 'Parse', state: parseState } },
    {
      type: 'parallel',
      steps: [
        { name: isZh ? '语义处理' : 'Semantic', state: semState },
        { name: isZh ? '嵌入向量' : 'Embedding', state: embState },
      ],
    },
  ]
}

/**
 * Extract rich quantified physical workload for a task.
 * Returns quantified metrics like "1,192 / 14,689 切片", "48 / 320 节点", "16 / 54 页", etc.
 */
export function getTaskQuantifiedWorkload(
  task: TaskRecord,
  queueRows: ParsedQueueRow[] = [],
  language: string = 'zh',
): QuantifiedWorkload | null {
  const isZh = language.startsWith('zh')
  const type = task.task_type
  const meta = (task.meta && typeof task.meta === 'object') ? (task.meta as Record<string, any>) : {}
  const resObj = (task.result && typeof task.result === 'object') ? (task.result as Record<string, any>) : {}

  // 1. Direct Explicit Meta Workload (Highest precision)
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

  // 2. Type-specific result/meta synthesis
  if (type === 'session_commit') {
    const turns = meta.turns_count ?? resObj.turns_processed ?? meta.messages_count
    const lessons = resObj.lessons_extracted ?? meta.lessons_count
    if (turns !== undefined || lessons !== undefined) {
      const parts: string[] = []
      if (turns !== undefined) parts.push(isZh ? `${turns} 轮对话` : `${turns} turns`)
      if (lessons !== undefined) parts.push(isZh ? `${lessons} 条新经验` : `${lessons} lessons`)
      return {
        icon: '💾',
        label: parts.join(isZh ? ' ｜ ' : ' | '),
        unit: isZh ? '轮对话' : 'turns',
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

  // 3. Match Live QueueFS Rows
  const embeddingRow = queueRows.find((r) => r.name.toLowerCase().includes('embedding'))
  const semanticRow = queueRows.find((r) => r.name.toLowerCase().includes('semantic'))
  const parseRow = queueRows.find((r) => r.name.toLowerCase().includes('parse'))
  const resourceRow = queueRows.find((r) => r.name.toLowerCase().includes('resource'))

  if (embeddingRow && embeddingRow.total > 0) {
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

  if (resourceRow && resourceRow.total > 0) {
    const pct = Math.round((resourceRow.completed / resourceRow.total) * 100)
    return {
      icon: '📦',
      label: isZh
        ? `${resourceRow.completed.toLocaleString()} / ${resourceRow.total.toLocaleString()} 文件 (${pct}%)`
        : `${resourceRow.completed.toLocaleString()} / ${resourceRow.total.toLocaleString()} files (${pct}%)`,
      processed: resourceRow.completed,
      total: resourceRow.total,
      unit: isZh ? '文件' : 'files',
      pct,
    }
  }

  return null
}
