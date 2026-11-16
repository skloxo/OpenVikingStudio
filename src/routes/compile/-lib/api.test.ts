import { beforeEach, describe, expect, it, vi } from 'vitest'

const { mockGet, mockPost } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
}))

vi.mock('#/lib/ov-client', async () => {
  const actual = await vi.importActual<typeof import('#/lib/ov-client/errors')>(
    '#/lib/ov-client/errors',
  )
  return {
    ...actual,
    ovClient: {
      client: {
        get: mockGet,
        post: mockPost,
      },
    },
  }
})

import {
  active,
  createCompile,
  fetchCapabilities,
  fetchCompileConfigs,
  fetchCompileTasks,
  taskTitle,
} from './api'

describe('compile api adapter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches compile tasks and normalizes null request.from', async () => {
    mockGet.mockResolvedValueOnce({
      status: 200,
      headers: {},
      data: {
        status: 'ok',
        result: {
          items: [
            {
              task_id: 'cmp_1',
              task_type: 'compile',
              status: 'completed',
              meta: {
                request: {
                  from: null,
                  to: 'viking://resources/out',
                  skill: 'viking://system/compile/example-skills/llm-wiki',
                },
              },
            },
          ],
          next_cursor: null,
          has_more: false,
        },
      },
    })

    const page = await fetchCompileTasks('completed', 'wiki')
    expect(mockGet).toHaveBeenCalledWith(
      expect.objectContaining({
        url: '/api/v1/tasks',
        query: expect.objectContaining({
          task_type: 'compile',
          pagination: 'cursor',
          status: 'completed',
          q: 'wiki',
        }),
      }),
    )
    expect(page.items[0].meta?.request?.from).toEqual([])
    expect(taskTitle(page.items[0])).toBe('llm-wiki → out')
  })

  it('creates compile job with Idempotency-Key header', async () => {
    mockPost.mockResolvedValueOnce({
      status: 202,
      headers: {},
      data: {
        status: 'ok',
        result: { task_id: 'cmp_99', status: 'pending' },
      },
    })

    const result = await createCompile(
      {
        from: ['viking://resources/notes'],
        to: 'viking://resources/wiki',
        skill: 'viking://system/compile/example-skills/llm-wiki',
      },
      '1234567890:abcdef',
    )
    expect(mockPost).toHaveBeenCalledWith({
      url: '/api/v1/compile',
      body: {
        from: ['viking://resources/notes'],
        to: 'viking://resources/wiki',
        skill: 'viking://system/compile/example-skills/llm-wiki',
      },
      headers: { 'Idempotency-Key': '1234567890:abcdef' },
    })
    expect('task_id' in result && result.task_id).toBe('cmp_99')
  })

  it('fetches capabilities and scheduled compile configs', async () => {
    mockGet.mockResolvedValueOnce({
      status: 200,
      headers: {},
      data: { status: 'ok', result: { configured: true, can_create: true } },
    })
    const cap = await fetchCapabilities()
    expect(cap.can_create).toBe(true)

    mockGet.mockResolvedValueOnce({
      status: 200,
      headers: {},
      data: { status: 'ok', result: { targets: [], next_cursor: null } },
    })
    const configs = await fetchCompileConfigs()
    expect(configs.targets).toEqual([])
    expect(active('running')).toBe(true)
    expect(active('completed')).toBe(false)
  })
})
