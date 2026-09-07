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
    expect(groups.every((g) => g.type === 'serial' && g.step !== undefined)).toBe(true)
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
})
