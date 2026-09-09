import { describe, expect, it } from 'vitest'
import {
  getTaskExecutionDynamic,
  getTaskFinalOutcome,
  getTaskPipelineSteps,
  getTaskQuantifiedWorkload,
} from './task-pipeline'
import type { TaskRecord } from './task-record'

describe('task-pipeline 抗熵增与轻量入库治理测试', () => {
  it('抗熵增任务流水线测试: 5大新增任务模型工序流推导与交付物契约', () => {
    // 1. memory_dream
    const dreamTask: TaskRecord = {
      task_id: 'dream-test-01',
      task_type: 'memory_dream',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      meta: {
        theme: 'reflection_test',
        raw_observations_count: 48,
        distilled_insights_count: 3,
      },
      result: {
        insights_extracted: 3,
        theme: 'reflection_test',
      },
    }
    const dreamSteps = getTaskPipelineSteps(dreamTask, [], 'zh')
    expect(dreamSteps).toHaveLength(4)
    expect(dreamSteps.map((s) => s.name)).toEqual([
      '观察扫描',
      '模式聚类',
      '反思提炼',
      '主记忆固化',
    ])
    const dreamOutcome = getTaskFinalOutcome(dreamTask, 'zh')
    expect(dreamOutcome.deliverableText).toContain('扫描 48 条观察碎片')
    expect(dreamOutcome.deliverableText).toContain('提炼 3 条认知洞察')
    const dreamWorkload = getTaskQuantifiedWorkload(dreamTask, [], 'zh')
    expect(dreamWorkload?.label).toBe('3 条洞察提炼')
    expect(dreamWorkload?.icon).toBe('🌙')

    // 2. memory_compaction
    const compactTask: TaskRecord = {
      task_id: 'compact-test-01',
      task_type: 'memory_compaction',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      meta: {
        scanned_records: 120,
        pruned_duplicates: 4,
      },
      result: {
        pruned_duplicates: 4,
        hot_tier_ratio: 0.3,
      },
    }
    const compactSteps = getTaskPipelineSteps(compactTask, [], 'zh')
    expect(compactSteps).toHaveLength(4)
    expect(compactSteps.map((s) => s.name)).toEqual([
      '分层体检',
      '余弦去重',
      '剪枝归档',
      '索引重平衡',
    ])
    expect(compactSteps[3].isActionOnly).toBe(true)
    const compactWorkload = getTaskQuantifiedWorkload(compactTask, [], 'zh')
    expect(compactWorkload?.label).toBe('去重剪枝 4 条')
    expect(compactWorkload?.icon).toBe('🗜️')

    // 3. fact_mutation
    const factTask: TaskRecord = {
      task_id: 'fact-test-01',
      task_type: 'fact_mutation',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      meta: {
        extracted_facts: 16,
      },
      result: {
        net_new_facts: 9,
        conflicts_resolved: 3,
      },
    }
    const factSteps = getTaskPipelineSteps(factTask, [], 'zh')
    expect(factSteps).toHaveLength(4)
    expect(factSteps.map((s) => s.name)).toEqual([
      '原子事实抽取',
      '冲突检测',
      '四态流转执行',
      '图谱原子提交',
    ])
    const factOutcome = getTaskFinalOutcome(factTask, 'zh')
    expect(factOutcome.deliverableText).toContain('抽取 16 条原子事实')
    expect(factOutcome.deliverableText).toContain('净新增 9 条')

    // 4. entity_summarization
    const entityTask: TaskRecord = {
      task_id: 'entity-test-01',
      task_type: 'entity_summarization',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      meta: {
        target_entity: 'TaskTracker',
        timeline_events_count: 24,
      },
      result: {
        entity: 'TaskTracker',
        resolved_contradictions: 2,
      },
    }
    const entitySteps = getTaskPipelineSteps(entityTask, [], 'zh')
    expect(entitySteps).toHaveLength(4)
    expect(entitySteps.map((s) => s.name)).toEqual([
      '实体三元组抽取',
      '时序版本链排序',
      '时序矛盾消解',
      '实体SSOT浓缩更新',
    ])
    expect(entitySteps[3].isActionOnly).toBe(true)

    // 5. four_tier_governance
    const tier4Task: TaskRecord = {
      task_id: 'tier4-test-01',
      task_type: 'four_tier_governance',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      meta: {
        topic: 'vector_entropy',
        merged_notes_count: 8,
        token_compression_pct: 58.4,
      },
      result: {
        topic: 'vector_entropy',
        token_compression_pct: 58.4,
      },
    }
    const tier4Steps = getTaskPipelineSteps(tier4Task, [], 'zh')
    expect(tier4Steps).toHaveLength(4)
    expect(tier4Steps.map((s) => s.name)).toEqual([
      '四层全息诊断',
      '同主题聚类',
      '同主题深度归纳',
      '纲要写回与清理',
    ])
    expect(tier4Steps[3].isActionOnly).toBe(true)
    const tier4Outcome = getTaskFinalOutcome(tier4Task, 'zh')
    expect(tier4Outcome.deliverableText).toContain('合并 8 篇碎片')
    expect(tier4Outcome.deliverableText).toContain('58.4%')
  })

  it('轻量增量入库任务流水线与量化交付物测试', () => {
    const valetTask: TaskRecord = {
      task_id: 'ticket_valet_test_01',
      task_type: 'valet_parking',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      meta: { human_title: '轻量增量入库：测试节点' },
      result: {
        status: 'ok',
        action: 'add',
        similarity: 0.0,
        progress: { completed: 1, total: 1, unit: '个节点' },
      },
    }
    const steps = getTaskPipelineSteps(valetTask, [], 'zh')
    expect(steps).toHaveLength(4)
    expect(steps.map((s) => s.name)).toEqual(['快速接管', '向量探针', '准入判定', '存储落盘'])
    expect(steps[0]).toMatchObject({ processed: 1, total: 1, detail: '接管暂存' })
    expect(steps[1]).toMatchObject({ processed: 1, total: 1, detail: '相似度 0.0000' })
    expect(steps[2]).toMatchObject({ processed: 1, total: 1, detail: '判定: 独立新增' })
    expect(steps[3]).toMatchObject({ processed: 1, total: 1, detail: '存储落盘' })

    const outcome = getTaskFinalOutcome(valetTask, 'zh')
    expect(outcome.deliverableText).toContain('准入判定: 独立新增 (ADD)')
    expect(outcome.deliverableText).toContain('1 个知识节点已存储落盘')
  })
})
