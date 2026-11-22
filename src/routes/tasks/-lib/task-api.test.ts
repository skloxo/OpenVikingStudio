import { beforeEach, describe, expect, it, vi } from 'vitest'

const { mockPost } = vi.hoisted(() => ({
  mockPost: vi.fn(),
}))

vi.mock('#/lib/ov-client', () => ({
  getOvResult: vi.fn(),
  getTasks: vi.fn(),
  ovClient: {
    instance: {
      post: mockPost,
    },
  },
}))

vi.mock('#/gen/ov-client', () => ({
  postResources: vi.fn(),
}))

vi.mock('#/lib/sessions/api', () => ({
  commitSession: vi.fn(),
}))

import { executeTaskRetry } from './task-api'

describe('Card-277 executeTaskRetry quality_gate & zero-mock closure', () => {
  beforeEach(() => {
    mockPost.mockReset()
  })

  it('posts quality_gate retry to /api/v1/tasks/trigger-quality-gate and returns newTaskId', async () => {
    mockPost.mockResolvedValueOnce({
      data: {
        status: 'ok',
        result: {
          task_id: 'manual-qg-991',
          quality_gate_task_id: 'manual-qg-991',
        },
      },
    })

    const res = await executeTaskRetry(
      {
        task_id: 'qg-old-1',
        task_type: 'quality_gate',
        status: 'failed',
        meta: { mode: 'smoke', threshold: 0.75 },
      },
      true,
    )

    expect(mockPost).toHaveBeenCalledWith('/api/v1/tasks/trigger-quality-gate', {
      mode: 'smoke',
      resource_id: undefined,
      threshold: 0.75,
      queries: undefined,
      reason: 'ui_task_retry',
    })
    expect(res.newTaskId).toBe('manual-qg-991')
  })

  it('does not short-circuit mock_task_ prefix and propagates backend 404/500 failure', async () => {
    mockPost.mockRejectedValueOnce(new Error('Request failed with status code 500'))

    await expect(
      executeTaskRetry(
        {
          task_id: 'mock_task_123',
          task_type: 'benchmark_eval',
          status: 'failed',
        },
        false,
      ),
    ).rejects.toThrow('500')
    expect(mockPost).toHaveBeenCalledTimes(1)
  })
})
