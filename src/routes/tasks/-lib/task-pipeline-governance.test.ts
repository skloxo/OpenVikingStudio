import { describe, expect, it } from 'vitest'
import {
  getTaskFinalOutcome,
  getTaskPipelineSteps,
} from './task-pipeline'
import type { TaskRecord } from './task-record'

describe('task-pipeline 10大真实车间流水线与交付物契约测试', () => {
  it('经典基建车间流水线测试: 资源处理、会话提交、技能导入、连接器导入、空间注销', () => {
    // 1. add_resource
    const resourceTask: TaskRecord = {
      task_id: 'res-test-01',
      task_type: 'add_resource',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      meta: { file_count: 3 },
      result: { file_count: 3, processed_chunks: 24, total_links: 12 },
    }
    const resSteps = getTaskPipelineSteps(resourceTask, [], 'zh')
    expect(resSteps.length).toBeGreaterThan(0)
    const resStepNames = resSteps.map((s) => s.name)
    expect(resStepNames).toContain('资源准入')
    expect(resStepNames).toContain('熵增防御')
    expect(resSteps.find((s) => s.name === '资源准入')?.detail).toBe('准入通过')
    expect(resSteps.find((s) => s.name === '熵增防御')?.detail).toBe('防御通过')

    const resOutcome = getTaskFinalOutcome(resourceTask, 'zh')
    expect(resOutcome.title).toBe('资源入库')
    expect(resOutcome.deliverableText).toContain('3 个文件已落盘索引')
    expect(resOutcome.deliverableText).toContain('24 个向量切片')

    // 2. session_commit
    const sessionTask: TaskRecord = {
      task_id: 'session-test-01',
      task_type: 'session_commit',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      meta: { turns_count: 8 },
      result: { turns_processed: 8, lessons_extracted: 2 },
    }
    const sessionSteps = getTaskPipelineSteps(sessionTask, [], 'zh')
    expect(sessionSteps.length).toBeGreaterThan(0)
    const sessionStepNames = sessionSteps.map((s) => s.name)
    expect(sessionStepNames).toContain('会话准入')
    expect(sessionStepNames).toContain('熵增防御')
    expect(sessionSteps.find((s) => s.name === '会话准入')?.detail).toBe('准入通过')
    expect(sessionSteps.find((s) => s.name === '熵增防御')?.detail).toBe('防御通过')

    const sessionOutcome = getTaskFinalOutcome(sessionTask, 'zh')
    expect(sessionOutcome.title).toBe('会话归档')
    expect(sessionOutcome.deliverableText).toContain('8 轮对话已归档')
    expect(sessionOutcome.deliverableText).toContain('2 条经验已沉淀')

    // 3. add_skill
    const skillTask: TaskRecord = {
      task_id: 'skill-test-01',
      task_type: 'add_skill',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      meta: { skill_name: 'test-skill' },
      result: { skills_indexed: 1 },
    }
    const skillSteps = getTaskPipelineSteps(skillTask, [], 'zh')
    expect(skillSteps.length).toBeGreaterThan(0)

    // 4. connector_import
    const connTask: TaskRecord = {
      task_id: 'conn-test-01',
      task_type: 'connector_import',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      meta: { connector_id: 'feishu-wiki' },
      result: { fetched_docs: 10, processed_chunks: 50 },
    }
    const connSteps = getTaskPipelineSteps(connTask, [], 'zh')
    expect(connSteps.length).toBeGreaterThan(0)

    // 5. user_delete
    const userDeleteTask: TaskRecord = {
      task_id: 'del-test-01',
      task_type: 'user_delete',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      meta: { user_id: 'user_123' },
      result: { vectors_dropped: 120, files_unlinked: 15 },
    }
    const delSteps = getTaskPipelineSteps(userDeleteTask, [], 'zh')
    expect(delSteps.length).toBeGreaterThan(0)
  })

  it('原子入库任务流水线与量化交付物测试 (ADD / NOOP / UPDATE)', () => {
    // 1. ADD 新增
    const valetAdd: TaskRecord = {
      task_id: 'ticket_valet_test_01',
      task_type: 'valet_parking',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      meta: { human_title: '原子入库：测试节点' },
      result: {
        status: 'ok',
        action: 'add',
        similarity: 0.1234,
        progress: { completed: 1, total: 1, unit: '个节点' },
      },
    }
    const steps = getTaskPipelineSteps(valetAdd, [], 'zh')
    expect(steps).toHaveLength(4)
    expect(steps.map((s) => s.name)).toEqual(['轻量准入', '向量探针', '熵增防御', '存储落盘'])
    expect(steps[0]).toMatchObject({ processed: 1, total: 1, detail: '轻量准入' })
    expect(steps[1]).toMatchObject({ processed: 1, total: 1, detail: '相似度 0.1234' })
    expect(steps[2]).toMatchObject({ processed: 1, total: 1, detail: '裁决: 独立新增' })
    expect(steps[3]).toMatchObject({ processed: 1, total: 1, detail: '存储落盘' })

    const addOutcome = getTaskFinalOutcome(valetAdd, 'zh')
    expect(addOutcome.deliverableText).toContain('准入判定: 独立新增 (ADD)')
    expect(addOutcome.deliverableText).toContain('1 个知识节点已存储落盘')

    // 2. NOOP 去重
    const valetNoop: TaskRecord = {
      task_id: 'ticket_valet_test_02',
      task_type: 'valet_parking',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      result: {
        status: 'ok',
        action: 'noop',
        similarity: 0.985,
        saved_bytes: 4096,
      },
    }
    const noopOutcome = getTaskFinalOutcome(valetNoop, 'zh')
    expect(noopOutcome.deliverableText).toContain('准入判定: 同义合并 (NOOP)')
    expect(noopOutcome.deliverableText).toContain('节约物理存储 4.0 KB')

    // 3. UPDATE 演化
    const valetUpdate: TaskRecord = {
      task_id: 'ticket_valet_test_03',
      task_type: 'valet_parking',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
      result: {
        status: 'ok',
        action: 'update',
        similarity: 0.912,
      },
    }
    const updateOutcome = getTaskFinalOutcome(valetUpdate, 'zh')
    expect(updateOutcome.deliverableText).toContain('准入判定: 增量演进 (UPDATE)')
    expect(updateOutcome.deliverableText).toContain('既有知识节点已版本升级')
  })

  it('未知/历史任务类型的安全通用兜底测试', () => {
    const unknownTask: TaskRecord = {
      task_id: 'legacy-unknown-01',
      task_type: 'some_old_type',
      status: 'completed',
      stage: 'completed',
      created_at: 1772800000,
    }
    const outcome = getTaskFinalOutcome(unknownTask, 'zh')
    expect(outcome.title).toBe('任务交付成果')
    expect(outcome.deliverableText).toBe('物理工序已全部执行完毕并校验入库')
  })
})
