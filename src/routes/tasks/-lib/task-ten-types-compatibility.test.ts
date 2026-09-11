import { describe, expect, it } from 'vitest'
import enTasks from '#/i18n/locales/en/tasks'
import zhTasks from '#/i18n/locales/zh-CN/tasks'
import { TASK_FLOWS } from './pipeline-definitions'
import {
  computeTaskKpiData,
  TASK_TYPE_OPTIONS,
} from './task-api'
import {
  getTaskFinalOutcome,
  getTaskPipelineSteps,
} from './task-pipeline'
import type { TaskRecord } from './task-record'

describe('10 大任务类型全景兼容性与适配性矩阵测试', () => {
  const TEN_TASK_TYPES = [
    'valet_parking',
    'add_resource',
    'session_commit',
    'add_skill',
    'connector_import',
    'admin_reindex',
    'snapshot_restore_reindex',
    'legacy_migration',
    'legacy_cleanup',
    'user_delete',
  ] as const

  it('契约 1: TASK_TYPE_OPTIONS 必须精确涵盖全部 10 大核心任务类型', () => {
    expect(TASK_TYPE_OPTIONS).toHaveLength(10)
    for (const typeKey of TEN_TASK_TYPES) {
      expect(TASK_TYPE_OPTIONS).toContain(typeKey)
    }
  })

  it('契约 2: TASK_FLOWS 必须注册全部 10 大车间工序流，且各工序流至少包含 2 道工序', () => {
    expect(TASK_FLOWS).toHaveLength(10)
    const registeredKeys = TASK_FLOWS.map((f) => f.typeKey)
    for (const typeKey of TEN_TASK_TYPES) {
      expect(registeredKeys).toContain(typeKey)
      const flow = TASK_FLOWS.find((f) => f.typeKey === typeKey)
      expect(flow?.stepIds.length).toBeGreaterThanOrEqual(2)
      expect(flow?.nameZh).toBeTruthy()
      expect(flow?.nameEn).toBeTruthy()
    }
    // 重点验证原子入库的官方信达雅命名
    const valetFlow = TASK_FLOWS.find((f) => f.typeKey === 'valet_parking')
    expect(valetFlow?.nameZh).toBe('原子入库')
    expect(valetFlow?.nameEn).toBe('Atomic Ingestion')
  })

  it('契约 3: 中英文双语 i18n 语言包中 10 大任务类型 100% 对等注册', () => {
    const zhTypes = zhTasks.tasksPage.types as Record<string, string>
    const enTypes = enTasks.tasksPage.types as Record<string, string>

    for (const typeKey of TEN_TASK_TYPES) {
      expect(zhTypes[typeKey], `Missing zh translation for ${typeKey}`).toBeTruthy()
      expect(enTypes[typeKey], `Missing en translation for ${typeKey}`).toBeTruthy()
    }

    expect(zhTypes.valet_parking).toBe('原子入库')
    expect(enTypes.valet_parking).toBe('Atomic Ingestion')
  })

  it('契约 4: 全部 10 大任务类型在完成态下均能正常推导出流水线工序 (Zero Crash)', () => {
    const mockTasks: Record<string, TaskRecord> = {
      valet_parking: {
        task_id: 't-valet',
        task_type: 'valet_parking',
        status: 'completed',
        meta: { human_title: '📥 原子入库：doc_test' },
        result: { action: 'add', similarity: 0.1234, saved_bytes: 0 },
      },
      add_resource: {
        task_id: 't-res',
        task_type: 'add_resource',
        status: 'completed',
        meta: { file_count: 5 },
        result: { processed_chunks: 10, total_links: 5 },
      },
      session_commit: {
        task_id: 't-session',
        task_type: 'session_commit',
        status: 'completed',
        meta: { turns_count: 6 },
        result: { turns_processed: 6, lessons_extracted: 1 },
      },
      add_skill: {
        task_id: 't-skill',
        task_type: 'add_skill',
        status: 'completed',
        result: { valid_skills: 2 },
      },
      connector_import: {
        task_id: 't-conn',
        task_type: 'connector_import',
        status: 'completed',
        result: { fetched_docs: 3, processed_chunks: 12 },
      },
      admin_reindex: {
        task_id: 't-reindex',
        task_type: 'admin_reindex',
        status: 'completed',
        result: { scanned_records: 100, rebuilt_records: 120 },
      },
      snapshot_restore_reindex: {
        task_id: 't-restore',
        task_type: 'snapshot_restore_reindex',
        status: 'completed',
        result: { restored_inodes: 10, reindexed_items: 10 },
      },
      legacy_migration: {
        task_id: 't-mig',
        task_type: 'legacy_migration',
        status: 'completed',
        result: { migrated_records: 50 },
      },
      legacy_cleanup: {
        task_id: 't-clean',
        task_type: 'legacy_cleanup',
        status: 'completed',
        result: { cleaned_items: 25 },
      },
      user_delete: {
        task_id: 't-del',
        task_type: 'user_delete',
        status: 'completed',
        result: { vectors_dropped: 60, files_unlinked: 5 },
      },
    }

    for (const typeKey of TEN_TASK_TYPES) {
      const task = mockTasks[typeKey]
      expect(task).toBeDefined()
      const steps = getTaskPipelineSteps(task, [], 'zh')
      expect(steps.length, `Steps for ${typeKey} should be > 0`).toBeGreaterThan(0)
      for (const step of steps) {
        expect(step.name).toBeTruthy()
        expect(step.state).toBe('completed')
      }
    }
  })

  it('契约 5: 全部 10 大任务类型均有确定的最终成果物摘要输出 (getTaskFinalOutcome)', () => {
    const mockTasks: TaskRecord[] = [
      { task_id: '1', task_type: 'valet_parking', status: 'completed', result: { action: 'noop', similarity: 0.99 } },
      { task_id: '2', task_type: 'add_resource', status: 'completed', result: { file_count: 2, processed_chunks: 10 } },
      { task_id: '3', task_type: 'session_commit', status: 'completed', result: { turns_processed: 4, lessons_extracted: 1 } },
      { task_id: '4', task_type: 'add_skill', status: 'completed', result: { skills_indexed: 1 } },
      { task_id: '5', task_type: 'connector_import', status: 'completed', result: { fetched_docs: 5, processed_chunks: 20 } },
      { task_id: '6', task_type: 'admin_reindex', status: 'completed', result: { scanned_records: 50, rebuilt_records: 60 } },
      { task_id: '7', task_type: 'snapshot_restore_reindex', status: 'completed', result: { restored_inodes: 8 } },
      { task_id: '8', task_type: 'legacy_migration', status: 'completed', result: { migrated_records: 12 } },
      { task_id: '9', task_type: 'legacy_cleanup', status: 'completed', result: { cleaned_items: 30 } },
      { task_id: '10', task_type: 'user_delete', status: 'completed', result: { vectors_dropped: 15, files_unlinked: 3 } },
    ]

    for (const task of mockTasks) {
      const outcomeZh = getTaskFinalOutcome(task, 'zh')
      expect(outcomeZh.title, `Outcome title missing for ${task.task_type}`).toBeTruthy()
      expect(outcomeZh.deliverableText, `Outcome deliverableText missing for ${task.task_type}`).toBeTruthy()

      const outcomeEn = getTaskFinalOutcome(task, 'en')
      expect(outcomeEn.title).toBeTruthy()
      expect(outcomeEn.deliverableText).toBeTruthy()
    }
  })

  it('契约 6: computeTaskKpiData 大盘聚合能够正确统计 10 大任务类型，typeRows 零丢失', () => {
    const mockAllTasks: TaskRecord[] = TEN_TASK_TYPES.map((typeKey, idx) => ({
      task_id: `mock-t-${idx}`,
      task_type: typeKey,
      status: 'completed',
      created_at: 1772800000 + idx * 10,
      updated_at: 1772800000 + idx * 10 + 2,
    }))

    const t = (key: string, options?: any) => {
      const typeKey = key.replace('types.', '')
      return (zhTasks.tasksPage.types as Record<string, string>)[typeKey] || options?.defaultValue || key
    }

    const kpi = computeTaskKpiData(mockAllTasks, t)
    expect(kpi.total).toBe(10)
    expect(kpi.completed).toBe(10)
    expect(kpi.successRate).toBe(100)

    // typeRows 包含 10 个基本类型 + 1 个 TOTAL 汇总行
    expect(kpi.typeRows).toHaveLength(11)
    const typeKeysInRows = kpi.typeRows
      .filter((r) => r.typeKey)
      .map((r) => r.typeKey)

    for (const typeKey of TEN_TASK_TYPES) {
      expect(typeKeysInRows).toContain(typeKey)
    }

    // 验证每种类型的计数都精确为 1
    for (const typeKey of TEN_TASK_TYPES) {
      const row = kpi.typeRows.find((r) => r.typeKey === typeKey)
      expect(row?.total).toBe(1)
      expect(row?.completed).toBe(1)
    }
  })
})
