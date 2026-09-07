import { describe, expect, it } from 'vitest'
import type { ParsedQueueRow } from '#/routes/monitoring/-components/queue-status-card'
import {
  getTaskExecutionDynamic,
  getTaskFinalOutcome,
  getTaskPipelineGroups,
  getTaskPipelineSteps,
  getTaskQuantifiedWorkload,
} from './task-pipeline'
import type { TaskRecord } from './task-record'

describe('task-pipeline RFC 治理与真实数据契约测试', () => {
  const completedReindexTask: TaskRecord = {
    task_id: 'fa3912d9-34ed-4bc5-9bce-acb0fc67f588',
    task_type: 'admin_reindex',
    status: 'completed',
    stage: 'completed',
    created_at: 1772800000,
    meta: {
      mode: 'semantic_and_vectors',
      resource_id: 'viking://user/default/memories',
    },
    result: {
      mode: 'semantic_and_vectors',
      scanned_records: 1010,
      semantic_records: 1010,
      rebuilt_records: 1112,
      deleted_records: 0,
      reindexed_items: 1112,
      elapsed_seconds: 12595,
    },
  }

  const runningVectorStageTask: TaskRecord = {
    task_id: 'fa3912d9-running-vector',
    task_type: 'admin_reindex',
    status: 'running',
    stage: 'vector',
    created_at: 1772800000,
    meta: {
      mode: 'semantic_and_vectors',
      resource_id: 'viking://user/default/memories',
      processed_chunks: 1050,
      total_chunks: 1112,
    },
  }

  const mockGlobalQueueRows: ParsedQueueRow[] = [
    {
      name: 'Embedding',
      pending: 45,
      processing: 2,
      completed: 32444,
      total: 32737,
      errors: 0,
    },
    {
      name: 'Semantic',
      pending: 26,
      processing: 1,
      completed: 100,
      total: 127,
      errors: 0,
    },
  ]

  it('缺陷 1: 保证工序单向单调推进律 (Monotonicity)，进入向量阶段绝不倒流回语义阶段', () => {
    // 即使全局队列中 Semantic.pending 为 26，当前进入 vector 阶段的任务第一步必须依然是 completed
    const steps = getTaskPipelineSteps(runningVectorStageTask, mockGlobalQueueRows, 'zh')
    expect(steps.length).toBe(2)
    expect(steps[0].name).toBe('语义提炼')
    expect(steps[0].state).toBe('completed')
    expect(steps[1].name).toBe('切片重构')
    expect(steps[1].state).toBe('running')
    expect(steps[1].processed).toBe(1050)
    expect(steps[1].total).toBe(1112)
  })

  it('缺陷 2: 切断全局 observer 假分母劫持，完成态 100% 使用自身真实数据而非 32,737', () => {
    const steps = getTaskPipelineSteps(completedReindexTask, mockGlobalQueueRows, 'zh')
    expect(steps.length).toBe(2)
    const embeddingStep = steps[1]
    expect(embeddingStep.name).toBe('切片重构')
    expect(embeddingStep.state).toBe('completed')
    expect(embeddingStep.processed).toBe(1112)
    expect(embeddingStep.total).toBe(1112)
    expect(embeddingStep.unit).toBe('切片')
    // 绝对不采用全局大盘累积 32,737
    expect(embeddingStep.total).not.toBe(32737)
  })

  it('缺陷 3: 动态自适应工序，semantic_and_vectors 模式彻底剔除未执行的“悬空修剪”伪工序', () => {
    const steps = getTaskPipelineSteps(completedReindexTask, mockGlobalQueueRows, 'zh')
    expect(steps.map((s) => s.name)).toEqual(['语义提炼', '切片重构'])
    expect(steps.some((s) => s.name.includes('修剪'))).toBe(false)

    const groups = getTaskPipelineGroups(completedReindexTask, mockGlobalQueueRows, 'zh')
    expect(groups.length).toBe(2)
    expect(groups.every((g) => g.type === 'serial')).toBe(true)
  })

  it('缺陷 3 补充: 当 mode 为 prune_orphans 或有真实删除碎片时，自适应保留“悬空修剪”工序', () => {
    const taskWithPrune: TaskRecord = {
      ...completedReindexTask,
      meta: { mode: 'prune_orphans' },
      result: {
        scanned_records: 1010,
        rebuilt_records: 1112,
        deleted_records: 42,
      },
    }
    const steps = getTaskPipelineSteps(taskWithPrune, mockGlobalQueueRows, 'zh')
    expect(steps.length).toBe(3)
    expect(steps[2].name).toBe('悬空修剪')
    expect(steps[2].count).toBe(42)

    const groups = getTaskPipelineGroups(taskWithPrune, mockGlobalQueueRows, 'zh')
    expect(groups.length).toBe(3)
  })

  it('按需展示原则: 当 mode 为 prune_orphans 但实际修剪 0 个碎片时，已完成任务坚决剔除“悬空修剪”伪工序', () => {
    const taskZeroPrune: TaskRecord = {
      ...completedReindexTask,
      meta: { mode: 'prune_orphans' },
      result: {
        scanned_records: 1010,
        rebuilt_records: 1112,
        deleted_records: 0,
      },
    }
    const steps = getTaskPipelineSteps(taskZeroPrune, mockGlobalQueueRows, 'zh')
    // 删除了 0 个碎片，属于无修剪产出，已完成视图下坚决不显示伪工序
    expect(steps.length).toBe(2)
    expect(steps.some((s) => s.name.includes('修剪'))).toBe(false)
    const groups = getTaskPipelineGroups(taskZeroPrune, mockGlobalQueueRows, 'zh')
    expect(groups.length).toBe(2)
  })

  it('缺陷 4: 语义提炼阶段透出真实的量化成果指标 (1,010 篇)', () => {
    const steps = getTaskPipelineSteps(completedReindexTask, mockGlobalQueueRows, 'zh')
    const semanticStep = steps[0]
    expect(semanticStep.name).toBe('语义提炼')
    expect(semanticStep.state).toBe('completed')
    expect(semanticStep.processed).toBe(1010)
    expect(semanticStep.total).toBe(1010)
    expect(semanticStep.unit).toBe('篇')
  })

  it('缺陷 5: 最终输出交付卡片由真实后端数据动态拼装，拒绝空洞写死文案', () => {
    const outcome = getTaskFinalOutcome(completedReindexTask, 'zh')
    expect(outcome.title).toBe('全量索引重建')
    expect(outcome.deliverableText).toBe('已完成 1,010 篇记忆扫描 · 重构 1,112 个向量切片 · 成功率 100%')
    expect(outcome.expectedText).toBe('全量记忆节点扫描与向量切片重构')

    // 英文环境验证
    const outcomeEn = getTaskFinalOutcome(completedReindexTask, 'en')
    expect(outcomeEn.deliverableText).toBe('Scanned 1,010 memories · Rebuilt 1,112 vector chunks · 100% Success')
  })

  it('列表动态摘要与量化负载：正确透出扫描篇数与重构切片数', () => {
    const dynamic = getTaskExecutionDynamic(completedReindexTask, mockGlobalQueueRows, 'zh')
    expect(dynamic.summaryText).toContain('1,010')
    expect(dynamic.summaryText).toContain('1,112')

    const workload = getTaskQuantifiedWorkload(completedReindexTask, mockGlobalQueueRows, 'zh')
    expect(workload).not.toBeNull()
    expect(workload?.label).toBe('1,010 篇扫描 ｜ 1,112 切片重构')
  })

  it('全量任务假数据切除: add_skill 正在运行时绝不借用 32,444 全局切片，单位必须为技能', () => {
    const runningSkillTask: TaskRecord = {
      task_id: 'skill-task-1',
      task_type: 'add_skill',
      status: 'running',
      stage: 'embed',
      created_at: 1772800000,
      meta: { valid_skills: 5 },
    }
    const steps = getTaskPipelineSteps(runningSkillTask, mockGlobalQueueRows, 'zh')
    const step3 = steps.find((s) => s.name === '向量建库')
    expect(step3).toBeDefined()
    expect(step3?.unit).toBe('技能')
    expect(step3?.total).toBe(5)
    // 严禁盗用全局 32,444
    expect(step3?.processed).not.toBe(32444)

    const workload = getTaskQuantifiedWorkload(runningSkillTask, mockGlobalQueueRows, 'zh')
    if (workload) {
      expect(workload.label).not.toContain('32,444')
      expect(workload.label).not.toContain('32,737')
    }
  })

  it('全量任务假数据切除: resource_build / add_resource 正在运行时绝不借用全局 observer 进度', () => {
    const runningResourceTask: TaskRecord = {
      task_id: 'res-task-1',
      task_type: 'add_resource',
      status: 'running',
      stage: 'embedding',
      created_at: 1772800000,
      meta: { file_count: 3 },
    }
    const steps = getTaskPipelineSteps(runningResourceTask, mockGlobalQueueRows, 'zh')
    expect(steps.some((s) => s.processed === 32444)).toBe(false)
    expect(steps.some((s) => s.total === 32737)).toBe(false)

    const workload = getTaskQuantifiedWorkload(runningResourceTask, mockGlobalQueueRows, 'zh')
    if (workload) {
      expect(workload.processed).not.toBe(32444)
      expect(workload.total).not.toBe(32737)
    }
  })

  it('全量任务假数据切除: connector_import 正在运行时绝不借用全局 32,444 切片或外部解析页数', () => {
    const runningConnectorTask: TaskRecord = {
      task_id: 'conn-task-1',
      task_type: 'connector_import',
      status: 'running',
      stage: 'embedding',
      created_at: 1772800000,
      meta: { downloaded_files: 8 },
    }
    const steps = getTaskPipelineSteps(runningConnectorTask, mockGlobalQueueRows, 'zh')
    expect(steps.some((s) => s.processed === 32444)).toBe(false)

    const workload = getTaskQuantifiedWorkload(runningConnectorTask, mockGlobalQueueRows, 'zh')
    if (workload) {
      expect(workload.processed).not.toBe(32444)
      expect(workload.total).not.toBe(32737)
    }
  })

  it('全量任务假数据切除: snapshot_restore_reindex 正在运行时绝不借用全局 32,444 切片', () => {
    const runningRestoreTask: TaskRecord = {
      task_id: 'restore-task-1',
      task_type: 'snapshot_restore_reindex',
      status: 'running',
      stage: 'embedding',
      created_at: 1772800000,
      meta: { reindexed_items: 20 },
    }
    const steps = getTaskPipelineSteps(runningRestoreTask, mockGlobalQueueRows, 'zh')
    expect(steps.some((s) => s.processed === 32444)).toBe(false)

    const workload = getTaskQuantifiedWorkload(runningRestoreTask, mockGlobalQueueRows, 'zh')
    if (workload) {
      expect(workload.processed).not.toBe(32444)
      expect(workload.total).not.toBe(32737)
    }
  })

  it('实事求是铁律: add_skill 完成态绝不再捏造“10 / 10 源目录”硬编码假数据', () => {
    const completedSkillTask: TaskRecord = {
      task_id: 'skill-task-done',
      task_type: 'add_skill',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      result: {
        valid_skills: 3,
        scanned_skills: 3,
      },
    }
    const steps = getTaskPipelineSteps(completedSkillTask, mockGlobalQueueRows, 'zh')
    // 技能扫描工序绝不捏造 processed: 10, total: 10
    const scanStep = steps.find((s) => s.name === '技能扫描')
    if (scanStep) {
      expect(scanStep.processed).not.toBe(10)
      expect(scanStep.total).not.toBe(10)
    }
    // 规范审计与向量建库均真实透出 3 技能
    const auditStep = steps.find((s) => s.name === '规范审计')
    expect(auditStep?.count).toBe(3)
    const embedStep = steps.find((s) => s.name === '向量建库')
    expect(embedStep?.count).toBe(3)
  })

  it('实事求是铁律: snapshot_restore_reindex 纯动作工序绝不再捏造“1 / 1 快照”', () => {
    const completedRestoreTask: TaskRecord = {
      task_id: 'restore-task-done',
      task_type: 'snapshot_restore_reindex',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      result: {
        restored_inodes: 45,
        reindexed_items: 45,
      },
    }
    const steps = getTaskPipelineSteps(completedRestoreTask, mockGlobalQueueRows, 'zh')
    const rollbackStep = steps.find((s) => s.name === '快照回滚')
    expect(rollbackStep).toBeDefined()
    expect(rollbackStep?.isActionOnly).toBe(true)
    // 纯动作工序绝不捏造 processed: 1, total: 1
    expect(rollbackStep?.processed).toBeUndefined()
    expect(rollbackStep?.total).toBeUndefined()
    // 节点还原真实透出 45 节点
    const inodeStep = steps.find((s) => s.name === '节点还原')
    expect(inodeStep?.count).toBe(45)
  })

  it('实事求是铁律: legacy_cleanup 纯动作工序绝不再捏造“1 / 1 空间”', () => {
    const completedCleanupTask: TaskRecord = {
      task_id: 'cleanup-task-done',
      task_type: 'legacy_cleanup',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      result: {
        cleaned_items: 88,
      },
    }
    const steps = getTaskPipelineSteps(completedCleanupTask, mockGlobalQueueRows, 'zh')
    const releaseStep = steps.find((s) => s.name === '空间释放')
    expect(releaseStep).toBeDefined()
    expect(releaseStep?.isActionOnly).toBe(true)
    expect(releaseStep?.processed).toBeUndefined()
    expect(releaseStep?.total).toBeUndefined()
  })
})
