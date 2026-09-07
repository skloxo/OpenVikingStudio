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
  qStatus:
    | Record<string, { error_count?: number; processed?: number } | undefined>
    | undefined,
): StepState {
  const normStatus = taskStatus?.toLowerCase()
  if (normStatus === 'completed') return 'completed'
  if (normStatus === 'failed') {
    // If we have explicit queue error
    if (qKey && qStatus?.[qKey] && (qStatus[qKey].error_count ?? 0) > 0)
      return 'failed'
    return stepOrder === totalSteps ? 'failed' : 'completed'
  }
  if (normStatus === 'pending') return 'pending'

  // If task is running
  if (normStatus === 'running') {
    const stage = taskStage?.toLowerCase() || ''

    // Explicit stage matching
    if (stage) {
      if (stage.includes('semantic') || stage.includes('extract')) {
        if (stepOrder === 1) return 'running'
        return stepOrder < 1 ? 'completed' : 'pending'
      }
      if (
        stage.includes('embed') ||
        stage.includes('vector') ||
        stage.includes('reindex')
      ) {
        if (stepOrder === 2) return 'running'
        return stepOrder < 2 ? 'completed' : 'pending'
      }
      if (stage.includes('prune') || stage.includes('deletion')) {
        if (stepOrder === 3) return 'running'
        return stepOrder < 3 ? 'completed' : 'pending'
      }
    }

    if (
      qKey === 'Embedding' &&
      (stage.includes('embedding') || stage.includes('reindex'))
    )
      return 'running'
    if (
      qKey === 'Semantic' &&
      (stage.includes('semantic') || stage.includes('extract'))
    )
      return 'running'
    if (
      qKey === 'ExternalParse' &&
      (stage.includes('parse') || stage.includes('scan'))
    )
      return 'running'

    // If queue has explicit processed count, mark previous steps as completed
    if (qKey && qStatus?.[qKey]) {
      const s = qStatus[qKey]
      if ((s.error_count ?? 0) > 0) return 'failed'
      if ((s.processed ?? 0) > 0) return 'completed'
    }

    if (stepOrder === 1) return 'running'
    return 'pending'
  }

  return 'pending'
}

/**
 * Single Source of Truth (SSOT) for task pipeline steps list.
 * 100% physically aligned with getTaskPipelineGroups.
 */
/**
 * Single Source of Truth (SSOT) for task pipeline steps list.
 * 100% physically aligned with getTaskPipelineGroups.
 */
function extractSessionCommitMetrics(
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

export function getTaskPipelineSteps(
  task: TaskRecord,
  _queueRows: ParsedQueueRow[] | string = [],
  language: string = 'zh',
): PipelineStep[] {
  const actualLang: string =
    typeof _queueRows === 'string' ? _queueRows : language
  const isZh = actualLang.startsWith('zh')
  const type = task.task_type
  const status = task.status
  const normStatus = status?.toLowerCase()
  const stage = task.stage
  const resObj: Record<string, any> =
    task.result && typeof task.result === 'object'
      ? (task.result as Record<string, any>)
      : {}
  const metaObj = task.meta && typeof task.meta === 'object' ? task.meta : {}
  const qStatus = resObj.queue_status as
    | Record<
        string,
        { error_count?: number; processed?: number; total?: number } | undefined
      >
    | undefined



  if (type === 'session_commit') {
    const { turns, lessons } = extractSessionCommitMetrics(
      metaObj,
      resObj,
      status,
    )
    const isCompleted = normStatus === 'completed'
    const isRunning = normStatus === 'running'
    const isLessonStage =
      stage?.toLowerCase().includes('lesson') ||
      stage?.toLowerCase().includes('extract') ||
      stage?.toLowerCase().includes('memory')
    const isSnapshotStage =
      stage?.toLowerCase().includes('snapshot') ||
      stage?.toLowerCase().includes('commit')

    const step1State: StepState =
      isCompleted || isLessonStage || isSnapshotStage
        ? 'completed'
        : isRunning
          ? 'running'
          : 'pending'
    const step2State: StepState =
      isCompleted || isSnapshotStage
        ? 'completed'
        : isLessonStage
          ? 'running'
          : 'pending'
    const step3State: StepState = isCompleted
      ? 'completed'
      : isSnapshotStage
        ? 'running'
        : 'pending'

    return [
      {
        name: isZh ? '对话归档' : 'Archival',
        state: step1State,
        processed:
          step1State === 'completed'
            ? turns
            : isRunning
              ? (resObj.turns_processed ?? 0)
              : 0,
        total: turns,
        count: turns,
        unit: isZh ? '轮' : 'turns',
      },
      {
        name: isZh ? '经验萃取' : 'Lessons',
        state: step2State,
        processed:
          step2State === 'completed'
            ? lessons
            : step2State === 'running'
              ? lessons
              : 0,
        total: lessons,
        count: lessons,
        unit: isZh ? '条经验' : 'lessons',
      },
      {
        name: isZh ? '快照提交' : 'Snapshot',
        state: step3State,
        processed: step3State === 'completed' ? 1 : 0,
        total: 1,
        count: 1,
        unit: isZh ? '次' : 'commits',
      },
    ]
  }

  if (type === 'add_skill') {
    const skills =
      resObj.valid_skills ?? metaObj.valid_skills ?? resObj.scanned_skills
    const isCompleted = normStatus === 'completed'
    const isRunning = normStatus === 'running'
    const isEmbedStage =
      stage?.toLowerCase().includes('embed') ||
      stage?.toLowerCase().includes('vector')
    const isValidating =
      stage?.toLowerCase().includes('valid') ||
      stage?.toLowerCase().includes('spec')

    const step1State: StepState =
      isCompleted || isRunning ? 'completed' : 'pending'
    const step2State: StepState =
      isCompleted || isEmbedStage
        ? 'completed'
        : isValidating
          ? 'running'
          : 'pending'
    const step3State: StepState = isCompleted
      ? 'completed'
      : isEmbedStage
        ? 'running'
        : 'pending'

    return [
      {
        name: isZh ? '目录扫描' : 'Discovery',
        state: step1State,
        processed: step1State === 'completed' ? 10 : 0,
        total: 10,
        count: 10,
        unit: isZh ? '源目录' : 'sources',
      },
      {
        name: isZh ? '规范校验' : 'Spec Validation',
        state: step2State,
        processed:
          step2State === 'completed'
            ? skills
            : step2State === 'running'
              ? (resObj.valid_skills ?? 0)
              : 0,
        total: skills,
        count: skills,
        unit: isZh ? '技能' : 'skills',
      },
      {
        name: isZh ? '向量建库' : 'Vector Embedding',
        state: step3State,
        processed:
          step3State === 'completed'
            ? skills
            : step3State === 'running'
              ? (resObj.embedded_skills ?? metaObj.embedded_skills ?? (resObj.slices_count ?? 0))
              : 0,
        total: skills,
        count: skills,
        unit: isZh ? '技能' : 'skills',
      },
    ]
  }

  if (type === 'user_delete' || type === 'user_deletion') {
    const deletedVectors = resObj.deleted_vectors ?? metaObj.deleted_vectors
    const deletedFiles = resObj.deleted_files ?? metaObj.deleted_files
    const isCompleted = normStatus === 'completed'
    const isRunning = normStatus === 'running'
    const isPurgeStage =
      stage?.toLowerCase().includes('vector') ||
      stage?.toLowerCase().includes('purge')
    const isWipeStage =
      stage?.toLowerCase().includes('wipe') ||
      stage?.toLowerCase().includes('disk')

    const step1State: StepState =
      isCompleted || isRunning ? 'completed' : 'pending'
    const step2State: StepState =
      isCompleted || isWipeStage
        ? 'completed'
        : isPurgeStage
          ? 'running'
          : 'pending'
    const step3State: StepState = isCompleted
      ? 'completed'
      : isWipeStage
        ? 'running'
        : 'pending'

    return [
      {
        name: isZh ? '软标记清理' : 'Soft Mark',
        state: step1State,
        processed: 1,
        total: 1,
        count: 1,
        unit: isZh ? '次' : 'ops',
      },
      {
        name: isZh ? '向量注销' : 'Vector Purge',
        state: step2State,
        processed: step2State === 'completed' ? deletedVectors : 0,
        total: deletedVectors,
        count: deletedVectors,
        unit: isZh ? '条' : 'vectors',
      },
      {
        name: isZh ? '磁盘擦除' : 'Disk Wipe',
        state: step3State,
        processed: step3State === 'completed' ? deletedFiles : 0,
        total: deletedFiles,
        count: deletedFiles,
        unit: isZh ? '项' : 'items',
      },
    ]
  }

  if (type === 'resource_build' || type === 'knowledge_pack') {
    const totalFiles = metaObj.total_files ?? resObj.processed_files ?? 1
    const isCompleted = normStatus === 'completed'
    const parseCount = isCompleted
      ? (qStatus?.ExternalParse?.processed ?? resObj.parsed_files ?? totalFiles)
      : (resObj.parsed_files ?? metaObj.parsed_files ?? qStatus?.ExternalParse?.processed ?? 0)
    const semanticCount = isCompleted
      ? (qStatus?.Semantic?.processed ?? resObj.semantic_files ?? totalFiles)
      : (resObj.semantic_files ?? metaObj.semantic_files ?? qStatus?.Semantic?.processed ?? 0)
    const embeddingCount = isCompleted
      ? (qStatus?.Embedding?.processed ?? resObj.embedded_files ?? totalFiles)
      : (resObj.embedded_files ?? metaObj.embedded_files ?? qStatus?.Embedding?.processed ?? 0)
    return [
      {
        name: isZh ? '文档解析' : 'Parsing',
        state: inferStepState('ExternalParse', 1, 3, status, stage, qStatus),
        processed: parseCount,
        total: totalFiles,
        count: parseCount,
        unit: isZh ? '篇' : 'docs',
      },
      {
        name: isZh ? '语义提炼' : 'Semantic',
        state: inferStepState('Semantic', 2, 3, status, stage, qStatus),
        processed: semanticCount,
        total: totalFiles,
        count: semanticCount,
        unit: isZh ? '篇' : 'docs',
      },
      {
        name: isZh ? '切片重构' : 'Embedding',
        state: inferStepState('Embedding', 3, 3, status, stage, qStatus),
        processed: embeddingCount,
        total: totalFiles,
        count: embeddingCount,
        unit: isZh ? '切片' : 'chunks',
      },
    ]
  }

  if (type === 'admin_reindex') {
    const mode = String(resObj.mode || metaObj.mode || '').toLowerCase()
    const deletedCount = Number(
      resObj.deleted_records ??
        resObj.deleted_chunks ??
        metaObj.deleted_records ??
        metaObj.deleted_chunks ??
        0,
    )
    const isCompleted = normStatus === 'completed'
    const isRunning = normStatus === 'running'
    const isPruneStage = Boolean(stage?.toLowerCase().includes('prune'))
    const isVectorStage = Boolean(
      stage?.toLowerCase().includes('vector') ||
      stage?.toLowerCase().includes('embed'),
    )
    const isSemanticStage = isRunning && !isVectorStage && !isPruneStage

    // 是否需要展示修剪工序：仅当模式显式要求修剪或实际删除了碎片时
    const hasPruning =
      mode === 'prune_orphans' ||
      mode === 'full' ||
      deletedCount > 0 ||
      isPruneStage

    // 工序单向单调推进律 (Monotonicity)：进入 vector/prune/completed 后绝对禁止倒流回 semantic
    const step1State: StepState =
      isCompleted || isVectorStage || isPruneStage
        ? 'completed'
        : isSemanticStage
          ? 'running'
          : 'pending'
    const step2State: StepState =
      isCompleted || isPruneStage
        ? 'completed'
        : isVectorStage
          ? 'running'
          : 'pending'
    const step3State: StepState = isCompleted
      ? 'completed'
      : isPruneStage
        ? 'running'
        : 'pending'

    // 100% 真实数据契约：语义提炼数量
    const semanticTotal =
      resObj.semantic_records ??
      resObj.scanned_records ??
      metaObj.semantic_records ??
      metaObj.scanned_records ??
      resObj.semantic_nodes ??
      metaObj.semantic_nodes ??
      metaObj.total_nodes
    const semanticProcessed = isCompleted
      ? semanticTotal
      : step1State === 'running'
        ? (metaObj.processed_nodes ?? undefined)
        : step1State === 'completed'
          ? semanticTotal
          : undefined

    // 100% 真实数据契约：切片重构数量（严禁使用全局 observer 的累计历史吞吐冒充）
    const rebuiltTotal =
      resObj.rebuilt_records ??
      resObj.reindexed_items ??
      metaObj.rebuilt_records ??
      metaObj.reindexed_items ??
      metaObj.total_chunks
    const chunksProcessed = isCompleted
      ? rebuiltTotal
      : step2State === 'running'
        ? (metaObj.processed_chunks ?? undefined)
        : step2State === 'completed'
          ? rebuiltTotal
          : undefined

    const steps: PipelineStep[] = [
      {
        name: isZh ? '语义提炼' : 'Semantic',
        state: step1State,
        processed: step1State === 'pending' ? undefined : semanticProcessed,
        total:
          step1State === 'pending'
            ? undefined
            : semanticTotal && semanticTotal > 0
              ? semanticTotal
              : undefined,
        count: semanticProcessed,
        unit: isZh ? '篇' : 'docs',
      },
      {
        name: isZh ? '切片重构' : 'Embedding',
        state: step2State,
        processed: step2State === 'pending' ? undefined : chunksProcessed,
        total:
          step2State === 'pending'
            ? undefined
            : rebuiltTotal && rebuiltTotal > 0
              ? rebuiltTotal
              : undefined,
        count: chunksProcessed,
        unit: isZh ? '切片' : 'chunks',
      },
    ]

    // 动态自适应：仅当任务确实包含修剪工序时追加，彻底剔除未执行的伪工序
    if (hasPruning) {
      steps.push({
        name: isZh ? '悬空修剪' : 'Pruning',
        state: step3State,
        processed: step3State === 'completed' ? deletedCount : undefined,
        total: step3State === 'completed' ? deletedCount : undefined,
        count: step3State === 'completed' ? deletedCount : undefined,
        unit: isZh ? '切片' : 'chunks',
      })
    }

    return steps
  }

  if (type === 'snapshot_restore_reindex') {
    const inodes = resObj.restored_inodes ?? metaObj.restored_inodes ?? 1
    const items =
      qStatus?.Embedding?.processed ??
      resObj.reindexed_items ??
      metaObj.reindexed_items ??
      1
    const isCompleted = normStatus === 'completed'
    const isRunning = normStatus === 'running'
    const isEmbedStage =
      stage?.toLowerCase().includes('embed') ||
      stage?.toLowerCase().includes('vector')

    const step1State: StepState =
      isCompleted || isRunning ? 'completed' : 'pending'
    const step2State: StepState =
      isCompleted || isEmbedStage
        ? 'completed'
        : isRunning
          ? 'running'
          : 'pending'
    const step3State: StepState = isCompleted
      ? 'completed'
      : isEmbedStage
        ? 'running'
        : 'pending'

    return [
      {
        name: isZh ? '快照回滚' : 'Rollback',
        state: step1State,
        processed: step1State === 'completed' ? 1 : 0,
        total: 1,
        count: 1,
        unit: isZh ? '快照' : 'commits',
      },
      {
        name: isZh ? '节点还原' : 'Inodes',
        state: step2State,
        processed:
          step2State === 'completed' ? inodes : (resObj.restored_inodes ?? 0),
        total: inodes,
        count: inodes,
        unit: isZh ? '节点' : 'inodes',
      },
      {
        name: isZh ? '增量向量' : 'Embedding',
        state: step3State,
        processed:
          step3State === 'completed'
            ? items
            : (resObj.reindexed_items ?? metaObj.reindexed_items ?? 0),
        total: items,
        count: items,
        unit: isZh ? '切片' : 'chunks',
      },
    ]
  }

  if (type === 'connector_import') {
    const docs = resObj.downloaded_files ?? metaObj.downloaded_files ?? 1
    const pages =
      qStatus?.ExternalParse?.processed ?? metaObj.parsed_pages ?? docs
    const nodes = qStatus?.Semantic?.processed ?? metaObj.semantic_nodes ?? docs
    const chunks =
      qStatus?.Embedding?.processed ?? metaObj.processed_chunks ?? docs
    const isCompleted = normStatus === 'completed'
    return [
      {
        name: isZh ? '连接鉴权' : 'Auth',
        state: status === 'pending' ? 'pending' : 'completed',
        processed: isCompleted ? 1 : status === 'pending' ? 0 : 1,
        total: 1,
        unit: isZh ? '连接' : 'auth',
      },
      {
        name: isZh ? '资源拉取' : 'Fetch',
        state: inferStepState(null, 2, 5, status, stage, qStatus),
        processed: isCompleted ? docs : (resObj.downloaded_files ?? 0),
        total: docs,
        count: docs,
        unit: isZh ? '篇' : 'docs',
      },
      {
        name: isZh ? '文档解析' : 'Parse',
        state: inferStepState('ExternalParse', 3, 5, status, stage, qStatus),
        processed: isCompleted
          ? pages
          : (resObj.parsed_pages ?? metaObj.parsed_pages ?? qStatus?.ExternalParse?.processed ?? 0),
        total: pages,
        count: pages,
        unit: isZh ? '页' : 'pages',
      },
      {
        name: isZh ? '语义提取' : 'Semantic',
        state: inferStepState('Semantic', 4, 5, status, stage, qStatus),
        processed: isCompleted
          ? nodes
          : (resObj.semantic_nodes ?? metaObj.semantic_nodes ?? qStatus?.Semantic?.processed ?? 0),
        total: nodes,
        count: nodes,
        unit: isZh ? '节点' : 'nodes',
      },
      {
        name: isZh ? '向量建库' : 'Embedding',
        state: inferStepState('Embedding', 5, 5, status, stage, qStatus),
        processed: isCompleted
          ? chunks
          : (resObj.processed_chunks ?? metaObj.processed_chunks ?? qStatus?.Embedding?.processed ?? 0),
        total: chunks,
        count: chunks,
        unit: isZh ? '切片' : 'chunks',
      },
    ]
  }

  if (type === 'legacy_migration') {
    const migrated = resObj.migrated_count ?? metaObj.migrated_count ?? 1
    const isCompleted = normStatus === 'completed'
    return [
      {
        name: isZh ? '数据读取' : 'Read',
        state: status === 'pending' ? 'pending' : 'completed',
        processed: isCompleted ? migrated : 0,
        total: migrated,
        count: migrated,
        unit: isZh ? '条' : 'records',
      },
      {
        name: isZh ? '格式转换' : 'Transform',
        state: inferStepState(null, 2, 3, status, stage, qStatus),
        processed: isCompleted ? migrated : 0,
        total: migrated,
        count: migrated,
        unit: isZh ? '条' : 'records',
      },
      {
        name: isZh ? '存储落盘' : 'Write',
        state: status === 'completed' ? 'completed' : 'pending',
        processed: isCompleted ? migrated : 0,
        total: migrated,
        count: migrated,
        unit: isZh ? '节点' : 'nodes',
      },
    ]
  }

  if (type === 'legacy_cleanup') {
    const cleaned = resObj.cleaned_items ?? metaObj.cleaned_items ?? 1
    const isCompleted = normStatus === 'completed'
    return [
      {
        name: isZh ? '图谱遍历' : 'Traverse',
        state: status === 'pending' ? 'pending' : 'completed',
        processed: isCompleted ? cleaned : 0,
        total: cleaned,
        count: cleaned,
        unit: isZh ? '实体' : 'entities',
      },
      {
        name: isZh ? '碎片回收' : 'GC',
        state: inferStepState(null, 2, 3, status, stage, qStatus),
        processed: isCompleted ? cleaned : 0,
        total: cleaned,
        count: cleaned,
        unit: isZh ? '项' : 'items',
      },
      {
        name: isZh ? '空间释放' : 'Free',
        state: status === 'completed' ? 'completed' : 'pending',
        processed: isCompleted ? 1 : 0,
        total: 1,
        count: 1,
        unit: isZh ? '空间' : 'namespaces',
      },
    ]
  }

  if (type === 'watch_sync') {
    const events = metaObj.events_count ?? 1
    const synced = resObj.synced_files ?? metaObj.synced_files ?? 1
    const chunks =
      qStatus?.Embedding?.processed ?? metaObj.processed_chunks ?? synced
    const isCompleted = normStatus === 'completed'
    return [
      {
        name: isZh ? '事件监听' : 'Events',
        state: status === 'pending' ? 'pending' : 'completed',
        processed: isCompleted ? events : 0,
        total: events,
        count: events,
        unit: isZh ? '事件' : 'events',
      },
      {
        name: isZh ? '增量解析' : 'Parse',
        state: inferStepState('ExternalParse', 2, 3, status, stage, qStatus),
        processed: isCompleted
          ? synced
          : (resObj.synced_files ?? metaObj.synced_files ?? qStatus?.ExternalParse?.processed ?? 0),
        total: synced,
        count: synced,
        unit: isZh ? '文件' : 'files',
      },
      {
        name: isZh ? '向量同步' : 'Sync',
        state: inferStepState('Embedding', 3, 3, status, stage, qStatus),
        processed: isCompleted
          ? chunks
          : (resObj.processed_chunks ?? metaObj.processed_chunks ?? qStatus?.Embedding?.processed ?? 0),
        total: chunks,
        unit: isZh ? '切片' : 'chunks',
      },
    ]
  }

  // Default resource ingestion pipeline (add_resource): 资源入库 -> 文档解析 -> 语义提取 -> 向量建库 -> 记忆关联
  const isEmbedStage =
    stage?.toLowerCase().includes('embedding') ||
    stage?.toLowerCase().includes('vector')
  const isSemStage =
    stage?.toLowerCase().includes('semantic') ||
    stage?.toLowerCase().includes('extract')
  const isParseStage =
    stage?.toLowerCase().includes('parse') ||
    stage?.toLowerCase().includes('scan')
  const isLinkingStage =
    stage?.toLowerCase().includes('link') ||
    stage?.toLowerCase().includes('relation') ||
    stage?.toLowerCase().includes('memory')
  const isCompleted = normStatus === 'completed'
  const isRunning = normStatus === 'running'

  const s1: StepState = status === 'pending' ? 'pending' : 'completed'
  const s2: StepState =
    isCompleted || isSemStage || isEmbedStage || isLinkingStage
      ? 'completed'
      : isParseStage
        ? 'running'
        : isRunning
          ? 'completed'
          : 'pending'
  const s3: StepState =
    isCompleted || isEmbedStage || isLinkingStage
      ? 'completed'
      : isSemStage
        ? 'running'
        : 'pending'
  const s4: StepState =
    isCompleted || isLinkingStage
      ? 'completed'
      : isEmbedStage
        ? 'running'
        : 'pending'
  const s5: StepState = isCompleted
    ? 'completed'
    : isLinkingStage
      ? 'running'
      : 'pending'

  const fileCount = metaObj.file_count ?? 1

  // 1. ExternalParse
  const extParseTotal = Math.max(
    1,
    metaObj.total_pages ??
      metaObj.parsed_pages ??
      resObj.parsed_pages ??
      (s2 === 'completed' ? fileCount : 1),
  )
  const rawExtParseProcessed =
    s2 === 'completed' ? extParseTotal : (metaObj.parsed_pages ?? 0)
  const extParseProcessed = Math.min(
    extParseTotal,
    Math.max(0, rawExtParseProcessed),
  )

  // 2. Semantic
  const semTotal = Math.max(
    1,
    metaObj.total_nodes ??
      metaObj.semantic_nodes ??
      resObj.semantic_nodes ??
      (s3 === 'completed' ? fileCount : 1),
  )
  const rawSemProcessed =
    s3 === 'completed' ? semTotal : (metaObj.semantic_nodes ?? 0)
  const semProcessed = Math.min(semTotal, Math.max(0, rawSemProcessed))

  // 3. Embedding
  const embTotal = Math.max(
    1,
    metaObj.total_chunks ??
      metaObj.processed_chunks ??
      resObj.processed_chunks ??
      resObj.total_chunks ??
      (s4 === 'completed' ? fileCount : 1),
  )
  const rawEmbProcessed =
    s4 === 'completed' ? embTotal : (metaObj.processed_chunks ?? 0)
  const embProcessed = Math.min(embTotal, Math.max(0, rawEmbProcessed))

  // 4. Memory Linking
  const linkTotal = Math.max(
    1,
    metaObj.total_links ??
      resObj.total_links ??
      (s5 === 'completed' ? fileCount : 1),
  )
  const rawLinkProcessed =
    s5 === 'completed'
      ? linkTotal
      : (resObj.linked_memories ?? metaObj.linked_memories ?? 0)
  const linkProcessed = Math.min(linkTotal, Math.max(0, rawLinkProcessed))

  return [
    {
      name: isZh ? '资源入库' : 'Resource Ingestion',
      state: s1,
      processed: s1 === 'completed' ? fileCount : 0,
      total: fileCount,
      count: fileCount,
      unit: isZh ? '文件' : 'files',
    },
    {
      name: isZh ? '文档解析' : 'Document Parsing',
      state: s2,
      processed: extParseProcessed,
      total: extParseTotal,
      count: extParseProcessed,
      unit: isZh ? '页' : 'pages',
    },
    {
      name: isZh ? '语义提取' : 'Semantic Extraction',
      state: s3,
      processed: semProcessed,
      total: semTotal,
      count: semProcessed,
      unit: isZh ? '节点' : 'nodes',
    },
    {
      name: isZh ? '向量建库' : 'Vector Embedding',
      state: s4,
      processed: embProcessed,
      total: embTotal,
      count: embProcessed,
      unit: isZh ? '切片' : 'chunks',
    },
    {
      name: isZh ? '记忆关联' : 'Memory Linking',
      state: s5,
      processed: linkProcessed,
      total: linkTotal,
      count: linkProcessed,
      unit: isZh ? '关联' : 'links',
    },
  ]
}

/**
 * Single Source of Truth (SSOT) for task pipeline diagram groups.
 * 100% physically aligned with getTaskPipelineSteps.
 */
export function getTaskPipelineGroups(
  task: TaskRecord,
  queueRows: ParsedQueueRow[] | string = [],
  language: string = 'zh',
): PipelineGroup[] {
  const steps = getTaskPipelineSteps(task, queueRows, language)
  const type = task.task_type

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
    return steps.map((step) => ({ type: 'serial' as const, step }))
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

  // Default resource ingestion pipeline: 资源入库 -> 文档解析 -> [ 语义提取 ∥ 向量建库 ] -> 记忆关联
  if (steps[4]) {
    return [
      { type: 'serial', step: steps[0] },
      { type: 'serial', step: steps[1] },
      {
        type: 'parallel',
        steps: [steps[2], steps[3]],
      },
      { type: 'serial', step: steps[4] },
    ]
  }

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
  _queueRows: ParsedQueueRow[] = [],
  language: string = 'zh',
): QuantifiedWorkload | null {
  const isZh = language.startsWith('zh')
  const type = task.task_type
  const status = task.status?.toLowerCase()
  const meta = task.meta && typeof task.meta === 'object' ? task.meta : {}
  const resObj: Record<string, any> =
    task.result && typeof task.result === 'object'
      ? (task.result as Record<string, any>)
      : {}

  // 1. Task's OWN Explicit Numerical Quantities (Highest precision)
  if (
    typeof meta.processed_chunks === 'number' &&
    typeof meta.total_chunks === 'number' &&
    meta.total_chunks > 0
  ) {
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

  if (
    typeof meta.processed_nodes === 'number' &&
    typeof meta.total_nodes === 'number' &&
    meta.total_nodes > 0
  ) {
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

  if (
    typeof meta.processed_pages === 'number' &&
    typeof meta.total_pages === 'number' &&
    meta.total_pages > 0
  ) {
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
    const { turns, lessons } = extractSessionCommitMetrics(meta, resObj, status)
    const parts: string[] = []
    parts.push(isZh ? `${turns} 轮对话` : `${turns} turns`)
    if (lessons > 0) {
      parts.push(isZh ? `${lessons} 条经验` : `${lessons} lessons`)
    }
    return {
      icon: '💾',
      label: parts.join(isZh ? ' ｜ ' : ' | '),
      processed: turns,
      total: turns,
      unit: isZh ? '轮' : 'turns',
      pct: 100,
    }
  }

  if (type === 'add_skill') {
    const skills =
      resObj.valid_skills ?? resObj.scanned_skills ?? meta.valid_skills
    if (skills !== undefined) {
      return {
        icon: '🤹',
        label: isZh ? `${skills} 项技能` : `${skills} skills`,
        unit: isZh ? '项技能' : 'skills',
      }
    }
  }

  if (type === 'admin_reindex') {
    const items =
      resObj.rebuilt_records ?? resObj.reindexed_items ?? meta.rebuilt_records
    const scanned =
      resObj.semantic_records ??
      resObj.scanned_records ??
      meta.semantic_records ??
      meta.scanned_records
    if (items !== undefined || scanned !== undefined) {
      const parts: string[] = []
      if (scanned !== undefined)
        parts.push(
          isZh
            ? `${Number(scanned).toLocaleString()} 篇扫描`
            : `${Number(scanned).toLocaleString()} scanned`,
        )
      if (items !== undefined)
        parts.push(
          isZh
            ? `${Number(items).toLocaleString()} 切片重构`
            : `${Number(items).toLocaleString()} chunks`,
        )
      return {
        icon: '⚡',
        label: parts.join(isZh ? ' ｜ ' : ' | '),
        unit: isZh ? '切片' : 'chunks',
      }
    }
  }

  if (type === 'user_delete' || type === 'user_deletion') {
    const items = resObj.deleted_files ?? meta.deleted_files
    const vectors = resObj.deleted_vectors ?? meta.deleted_vectors
    if (items !== undefined || vectors !== undefined) {
      const parts: string[] = []
      if (items !== undefined)
        parts.push(isZh ? `${items} 项资源` : `${items} items`)
      if (vectors !== undefined)
        parts.push(isZh ? `${vectors} 向量` : `${vectors} vectors`)
      return {
        icon: '🧹',
        label: parts.join(' ｜ '),
        unit: isZh ? '项' : 'items',
      }
    }
  }

  if (type === 'add_resource' || type === 'resource_build') {
    const qStatus = resObj.queue_status as
      Record<string, { processed?: number } | undefined> | undefined
    const embProcessed =
      qStatus?.Embedding?.processed ??
      resObj.processed_chunks ??
      meta.processed_chunks
    const semProcessed =
      qStatus?.Semantic?.processed ??
      resObj.processed_nodes ??
      meta.processed_nodes
    if (embProcessed !== undefined || semProcessed !== undefined) {
      const parts: string[] = []
      if (semProcessed !== undefined)
        parts.push(isZh ? `${semProcessed} 节点` : `${semProcessed} nodes`)
      if (embProcessed !== undefined)
        parts.push(isZh ? `${embProcessed} 切片` : `${embProcessed} chunks`)
      return {
        icon: '⚡',
        label: parts.join(isZh ? ' ｜ ' : ' | '),
        processed: embProcessed ?? semProcessed,
        total: embProcessed ?? semProcessed,
        unit: isZh ? '切片' : 'chunks',
        pct: 100,
      }
    }
    const files = resObj.processed_files ?? meta.file_count ?? meta.total_files
    if (files !== undefined) {
      return {
        icon: '📦',
        label: isZh ? `${files} 个文件` : `${files} files`,
        unit: isZh ? '个文件' : 'files',
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
      if (inodes !== undefined)
        parts.push(isZh ? `${inodes} 还原节点` : `${inodes} inodes`)
      if (items !== undefined)
        parts.push(isZh ? `${items} 切片` : `${items} chunks`)
      return {
        icon: '🔄',
        label: parts.join(' ｜ '),
        unit: isZh ? '节点' : 'inodes',
      }
    }
  }

  if (type === 'legacy_migration') {
    const count = resObj.migrated_count ?? meta.migrated_count
    if (count !== undefined) {
      return {
        icon: '📦',
        label: isZh ? `${count} 条迁移记录` : `${count} records migrated`,
        unit: isZh ? '条' : 'records',
      }
    }
  }

  if (type === 'legacy_cleanup') {
    const cleaned = resObj.cleaned_records ?? meta.cleaned_records
    if (cleaned !== undefined) {
      return {
        icon: '🧹',
        label: isZh ? `${cleaned} 条清理碎片` : `${cleaned} records cleaned`,
        unit: isZh ? '条' : 'records',
      }
    }
  }

  if (type === 'watch_sync') {
    const synced = resObj.synced_files ?? meta.synced_files
    if (synced !== undefined) {
      return {
        icon: '👀',
        label: isZh ? `${synced} 个监听文件同步` : `${synced} files synced`,
        unit: isZh ? '文件' : 'files',
      }
    }
  }

  // 严格遵守第一性原理与绝对数据真实性：
  // 任何 running 或 pending 状态的任务，若自身 meta/result 尚无明确物理数字，
  // 坚决返回 null（由工序状态直接中性展示“进行中”），100% 杜绝冒充借用全局 QueueFS 的假切片假节点！
  return null
}

export interface ActiveStepPair {
  name: string
  metric?: string
}

export interface TaskExecutionDynamic {
  status: 'completed' | 'running' | 'pending' | 'failed'
  activeStepName: string
  activeEngineName: string
  activeStepIndex: number
  totalSteps: number
  progressPct: number
  activeStepPairs?: ActiveStepPair[]
  workloadText?: string
  workloadIcon?: string
  summaryText: string
}

export function getTaskExecutionDynamic(
  task: TaskRecord,
  queueRows: ParsedQueueRow[] = [],
  language: string = 'zh',
  calcProgressPct?: (t: TaskRecord) => number,
): TaskExecutionDynamic {
  const isZh = language.startsWith('zh')
  const status = (task.status?.toLowerCase() || 'pending') as
    'completed' | 'running' | 'pending' | 'failed'
  const type = task.task_type || ''
  const meta = task.meta && typeof task.meta === 'object' ? task.meta : {}
  const result: Record<string, any> =
    task.result && typeof task.result === 'object'
      ? (task.result as Record<string, any>)
      : {}
  const steps = getTaskPipelineSteps(task, queueRows, language)
  const totalSteps = Math.max(1, steps.length)
  const workload = getTaskQuantifiedWorkload(task, queueRows, language)
  const progressPct = calcProgressPct
    ? calcProgressPct(task)
    : status === 'completed'
      ? 100
      : 50

  // 1. Completed
  if (status === 'completed') {
    let summary = isZh ? '全工序已完成' : 'All steps completed'
    if (type === 'session_commit') {
      const { turns, lessons } = extractSessionCommitMetrics(
        meta,
        result,
        status,
      )
      summary =
        (isZh ? `${turns} 轮对话已归档` : `${turns} turns archived`) +
        (lessons > 0
          ? isZh
            ? ` · ${lessons} 条经验沉淀`
            : ` · ${lessons} lessons`
          : '')
    } else if (type === 'add_resource') {
      const files = meta.file_count ?? 1
      summary = isZh
        ? `${files} 个文件已落盘索引`
        : `${files} files persisted & indexed`
    } else if (type === 'add_skill') {
      const skills =
        result.valid_skills ?? meta.valid_skills ?? result.scanned_skills
      summary = skills
        ? isZh
          ? `${skills} 项技能已校验入库`
          : `${skills} skills validated`
        : isZh
          ? '技能已完成入库'
          : 'Skills loaded'
    } else if (type === 'admin_reindex') {
      const scanned =
        result.semantic_records ??
        result.scanned_records ??
        meta.semantic_records ??
        meta.scanned_records
      const rebuilt = result.rebuilt_records ?? meta.rebuilt_records
      summary =
        scanned && rebuilt
          ? isZh
            ? `已扫描 ${Number(scanned).toLocaleString()} 篇 · 重构 ${Number(rebuilt).toLocaleString()} 个切片`
            : `${scanned} docs scanned, ${rebuilt} chunks rebuilt`
          : isZh
            ? '全量索引重构完成'
            : 'Global reindex completed'
    } else if (type === 'snapshot_restore_reindex') {
      summary = isZh ? '快照状态已成功还原' : 'Snapshot restored'
    } else if (type === 'connector_import') {
      const docs = result.downloaded_files ?? meta.downloaded_files
      summary = docs
        ? isZh
          ? `${docs} 篇外部文档已导入`
          : `${docs} docs imported`
        : isZh
          ? '外部数据已导入'
          : 'Data imported'
    } else if (type === 'legacy_migration') {
      summary = isZh ? '旧数据已完成格式迁移' : 'Legacy data migrated'
    } else if (type === 'legacy_cleanup') {
      summary = isZh ? '历史无用碎片已清理释放' : 'Storage space cleaned'
    }

    return {
      status: 'completed',
      activeStepName: steps[steps.length - 1]?.name || (isZh ? '完成' : 'Done'),
      activeEngineName: isZh ? '就绪' : 'Ready',
      activeStepIndex: totalSteps,
      totalSteps,
      progressPct: 100,
      workloadText: workload?.label,
      workloadIcon: workload?.icon,
      summaryText: summary,
    }
  }

  // 2. Running
  if (status === 'running') {
    let runningSteps = steps.filter((s) => s.state === 'running')
    if (runningSteps.length === 0) {
      const pendingStep = steps.find((s) => s.state === 'pending') ?? steps[0]
      runningSteps = [pendingStep]
    }

    // Pair each active step with its own quantified metric
    const activeStepPairs: ActiveStepPair[] = runningSteps.map((s) => {
      let metric = ''
      if (s.processed !== undefined && s.total !== undefined && s.total > 0) {
        metric =
          `${s.processed.toLocaleString()}/${s.total.toLocaleString()} ${s.unit ?? ''}`.trim()
      } else if (s.count !== undefined) {
        metric = `${s.count.toLocaleString()} ${s.unit ?? ''}`.trim()
      } else if (s.processed !== undefined) {
        metric = `${s.processed.toLocaleString()} ${s.unit ?? ''}`.trim()
      }
      return {
        name: s.name,
        metric: metric || undefined,
      }
    })

    // Step names joined directly without "工序 X/Y:" prefix
    const stepName =
      runningSteps.map((s) => s.name).join(isZh ? ' & ' : ' & ') ||
      (isZh ? '正在处理' : 'Processing')

    // Map active engine name
    const engines = runningSteps.map((s) => {
      const sName = s.name
      if (sName.includes('向量') || sName.includes('切片'))
        return isZh ? '向量计算' : 'Embedding'
      if (sName.includes('语义')) return isZh ? '语义提取' : 'Semantic'
      if (sName.includes('解析') || sName.includes('扫描'))
        return isZh ? '文档解析' : 'ExternalParse'
      if (
        sName.includes('入库') ||
        sName.includes('写入') ||
        sName.includes('落盘') ||
        sName.includes('拉取')
      )
        return isZh ? '资源入库' : 'AddResource'
      if (
        sName.includes('归档') ||
        sName.includes('萃取') ||
        sName.includes('快照')
      )
        return isZh ? '会话归档' : 'SessionCommit'
      if (
        sName.includes('修剪') ||
        sName.includes('回收') ||
        sName.includes('释放') ||
        sName.includes('注销')
      )
        return isZh ? '空间注销' : 'UserDeletion'
      if (sName.includes('图谱') || sName.includes('遍历'))
        return isZh ? '语义拓扑' : 'Semantic Topology'
      return isZh ? '计算中' : 'Running'
    })
    const engineName = Array.from(new Set(engines)).join(' + ')

    // Joined combined workload text (for fallback)
    const stepMetrics = activeStepPairs.map((p) =>
      p.metric ? `${p.name} · ${p.metric}` : p.name,
    )
    const joinedMetric =
      stepMetrics.length > 0 ? stepMetrics.join(' & ') : workload?.label

    return {
      status: 'running',
      activeStepName: stepName,
      activeEngineName: engineName,
      activeStepIndex: 0,
      totalSteps,
      progressPct,
      activeStepPairs,
      workloadText: joinedMetric,
      workloadIcon: workload?.icon ?? '⚡',
      summaryText: isZh
        ? `执行中 (${progressPct}%)`
        : `Running (${progressPct}%)`,
    }
  }

  // 3. Pending
  if (status === 'pending') {
    return {
      status: 'pending',
      activeStepName: isZh ? '等待调度' : 'Pending',
      activeEngineName: isZh ? '排队中' : 'Queued',
      activeStepIndex: 0,
      totalSteps,
      progressPct: 0,
      summaryText: isZh
        ? '排队等待执行引擎调度分配'
        : 'Queued, awaiting execution engine',
    }
  }

  // 4. Failed
  const failedStep =
    steps.find((s) => s.state === 'failed') ?? steps[steps.length - 1]
  const failedName = failedStep.name
  return {
    status: 'failed',
    activeStepName: failedStep.name,
    activeEngineName: isZh ? '执行中断' : 'Interrupted',
    activeStepIndex: steps.indexOf(failedStep) + 1,
    totalSteps,
    progressPct: 0,
    summaryText: isZh
      ? `[${failedName}] 执行中断`
      : `Aborted at [${failedName}]`,
  }
}

export interface TaskFinalOutcomeDef {
  title: string
  deliverableText: string
  expectedText: string
}

export function getTaskFinalOutcome(
  task: TaskRecord,
  language: string = 'zh',
): TaskFinalOutcomeDef {
  const isZh = language.startsWith('zh')
  const type = task.task_type || ''
  const meta = task.meta && typeof task.meta === 'object' ? task.meta : {}
  const result: Record<string, any> =
    task.result && typeof task.result === 'object'
      ? (task.result as Record<string, any>)
      : {}

  if (type === 'add_resource') {
    const files = meta.file_count ?? 1
    return {
      title: isZh ? '资源入库' : 'Resource Ingestion',
      deliverableText: isZh
        ? `${files} 个文件已落盘索引并建立向量`
        : `${files} files persisted & vector indexed`,
      expectedText: isZh
        ? '物理文件落盘与语义向量建库'
        : 'File persistence and vector index creation',
    }
  }

  if (type === 'add_skill') {
    const skills =
      result.valid_skills ?? meta.valid_skills ?? result.scanned_skills
    return {
      title: isZh ? '技能入库' : 'Skill Ingestion',
      deliverableText: skills
        ? isZh
          ? `${skills} 项技能已完成校验并注册入库`
          : `${skills} skills validated & registered`
        : isZh
          ? '技能已完成校验并注册入库'
          : 'Skills validated & registered',
      expectedText: isZh
        ? '技能合规校验与向量注册入库'
        : 'Skill spec validation & embedding registration',
    }
  }

  if (type === 'session_commit') {
    const { turns, lessons } = extractSessionCommitMetrics(
      meta,
      result,
      task.status,
    )
    return {
      title: isZh ? '会话归档' : 'Session Commit',
      deliverableText: isZh
        ? `${turns} 轮对话已归档` +
          (lessons > 0 ? ` · ${lessons} 条经验已沉淀` : '')
        : `${turns} turns archived` +
          (lessons > 0 ? ` · ${lessons} lessons extracted` : ''),
      expectedText: isZh
        ? '对话上下文序列化与经验记忆萃取'
        : 'Dialogue context serialization & lesson extraction',
    }
  }

  if (type === 'admin_reindex') {
    const scanned =
      result.semantic_records ??
      result.scanned_records ??
      meta.semantic_records ??
      meta.scanned_records
    const rebuilt = result.rebuilt_records ?? meta.rebuilt_records
    const deleted = Number(result.deleted_records ?? meta.deleted_records ?? 0)

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

  if (type === 'snapshot_restore_reindex') {
    const inodes = result.restored_inodes ?? meta.restored_inodes
    return {
      title: isZh ? '快照还原' : 'Snapshot Restore',
      deliverableText: inodes
        ? isZh
          ? `${inodes} 个节点已还原 · 增量向量已同步`
          : `${inodes} inodes restored & vectors synced`
        : isZh
          ? '快照状态已成功还原'
          : 'Snapshot restored',
      expectedText: isZh
        ? 'AGFS 树节点回滚与增量向量数据同步'
        : 'AGFS tree rollback & vector synchronization',
    }
  }

  if (type === 'connector_import') {
    const docs = result.downloaded_files ?? meta.downloaded_files
    return {
      title: isZh ? '外部资源接入' : 'Connector Import',
      deliverableText: docs
        ? isZh
          ? `${docs} 篇外部文档已导入入库`
          : `${docs} documents imported & indexed`
        : isZh
          ? '外部数据已完成导入'
          : 'Data imported',
      expectedText: isZh
        ? '外部文档解析抓取与图谱建立'
        : 'External doc parsing & graph index creation',
    }
  }

  if (type === 'legacy_migration') {
    const count = result.migrated_count ?? meta.migrated_count
    return {
      title: isZh ? '旧数据迁移' : 'Legacy Migration',
      deliverableText: count
        ? isZh
          ? `${count} 条历史数据已完成格式迁移落盘`
          : `${count} records migrated to AGFS`
        : isZh
          ? '历史数据已完成迁移落盘'
          : 'Data migrated to AGFS',
      expectedText: isZh
        ? '历史数据格式转换与 AGFS 存储规范落盘'
        : 'Format transformation & AGFS persistence',
    }
  }

  if (type === 'legacy_cleanup') {
    const cleaned = result.cleaned_items ?? meta.cleaned_items
    return {
      title: isZh ? '旧数据清理' : 'Legacy Cleanup',
      deliverableText: cleaned
        ? isZh
          ? `${cleaned} 项孤儿碎片已清理 · 存储空间已释放`
          : `${cleaned} orphan fragments pruned & storage released`
        : isZh
          ? '历史无用碎片已清理释放'
          : 'Storage space released',
      expectedText: isZh
        ? '孤儿碎片回收与磁盘物理空间释放'
        : 'Garbage collection & physical storage release',
    }
  }

  if (type === 'user_delete' || type === 'user_deletion') {
    return {
      title: isZh ? '资源注销' : 'Resource Deletion',
      deliverableText: isZh
        ? '物理资源及关联向量已安全销毁'
        : 'Physical resources & vectors safely purged',
      expectedText: isZh
        ? '空间解除绑定与向量索引彻底擦除'
        : 'Namespace unbinding & vector deletion',
    }
  }

  return {
    title: isZh ? '任务交付产出' : 'Final Outcome',
    deliverableText: isZh
      ? '任务工序已执行完毕并完成交付'
      : 'Task pipeline executed & delivered',
    expectedText: isZh
      ? '工序编排调度与最终业务数据落盘'
      : 'Process orchestration & business data persistence',
  }
}
