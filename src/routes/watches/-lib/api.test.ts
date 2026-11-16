import { afterEach, describe, expect, it, vi } from 'vitest'

import { ovClient } from '#/lib/ov-client'

import {
  deleteWatch,
  fetchWatches,
  normalizeWatchList,
  triggerWatch,
  updateWatch,
} from './api'

const okResp = (result: unknown) => ({
  status: 200,
  headers: {},
  data: { status: 'ok', result },
})

describe('watches route api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('normalizes valid watch items and skips malformed ones', () => {
    const list = normalizeWatchList({
      tasks: [
        {
          task_id: 'w1',
          path: 'https://github.com/volcengine/OpenViking',
          to_uri: 'viking://resources/ov',
          watch_interval: 60,
          is_active: true,
        },
        { task_id: 'bad' },
      ],
    })
    expect(list).toHaveLength(1)
    expect(list[0]?.isActive).toBe(true)
    expect(list[0]?.watchInterval).toBe(60)
  })

  it('calls GET/PATCH/POST trigger/DELETE watch endpoints cleanly', async () => {
    vi.spyOn(ovClient.client, 'get').mockResolvedValueOnce(
      okResp({
        tasks: [
          {
            task_id: 'w1',
            path: 'https://example.com',
            to_uri: 'viking://resources/example',
            watch_interval: 30,
            is_active: false,
          },
        ],
      }) as never,
    )
    const patchSpy = vi
      .spyOn(ovClient.client, 'patch')
      .mockResolvedValueOnce(okResp({}) as never)
    const postSpy = vi
      .spyOn(ovClient.client, 'post')
      .mockResolvedValueOnce(okResp({}) as never)
    const delSpy = vi
      .spyOn(ovClient.client, 'delete')
      .mockResolvedValueOnce(okResp({}) as never)

    const items = await fetchWatches()
    expect(items).toHaveLength(1)

    await updateWatch('w1', { watchInterval: 120, isActive: true })
    expect(patchSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        url: '/api/v1/watches/w1',
        body: { watch_interval: 120, is_active: true },
      }),
    )

    await triggerWatch('w1')
    expect(postSpy).toHaveBeenCalledWith(
      expect.objectContaining({ url: '/api/v1/watches/w1/trigger' }),
    )

    await deleteWatch('w1')
    expect(delSpy).toHaveBeenCalledWith(
      expect.objectContaining({ url: '/api/v1/watches/w1' }),
    )
  })
})
