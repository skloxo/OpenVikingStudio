import { describe, expect, it } from 'vitest'

import type { TaskRecord } from './task-record'

describe('Dual-Track Task Models & Humanized Presentation', () => {
  it('correctly identifies business job fields from task record', () => {
    const record: TaskRecord = {
      task_id: 'biz_01928374abcd',
      task_type: 'valet_parking',
      status: 'completed',
      created_at: 1789053849,
      updated_at: 1789053850,
      resource_id: 'viking://resources/staging/antigravity_sessions/test_doc.md',
      meta: {
        is_business: true,
        human_title: '📥 原子入库：test_doc',
        initiator: 'Agent (Gemini Flash)',
        deliverable: {
          uri: 'viking://resources/staging/antigravity_sessions/test_doc.md',
          label: '成果物直达',
        },
        progress: {
          completed: 1,
          total: 1,
          unit: '个节点',
        },
      },
      result: {
        deliverable: {
          uri: 'viking://resources/staging/antigravity_sessions/test_doc.md',
          label: '成果物直达',
        },
      },
    }

    expect(record.task_id).toBe('biz_01928374abcd')
    expect(record.meta?.human_title).toBe('📥 原子入库：test_doc')
    expect(record.meta?.initiator).toBe('Agent (Gemini Flash)')
    expect(record.meta?.deliverable?.uri).toBe(
      'viking://resources/staging/antigravity_sessions/test_doc.md',
    )
    expect(record.meta?.progress?.completed).toBe(1)
    expect(record.meta?.progress?.total).toBe(1)
  })

  it('preserves system operation definitions for machine level tracking', () => {
    const record: TaskRecord = {
      task_id: 'admin_reindex_123',
      task_type: 'admin_reindex',
      status: 'running',
      created_at: 1789053849,
      updated_at: 1789053850,
      stage: 'vector_rebuild',
      meta: {},
    }

    expect(record.task_type).toBe('admin_reindex')
    expect(record.stage).toBe('vector_rebuild')
    expect(record.meta?.is_business).toBeFalsy()
  })
})
