import { afterEach, describe, expect, it, vi } from 'vitest'

import { ovClient } from '#/lib/ov-client'

import {
  deleteSharedResource,
  isSharedResourceUri,
  isValidTransferTarget,
  transferSharedResource,
} from './resource-actions'

const okResp = (result: unknown) => ({
  status: 200,
  headers: {},
  data: { status: 'ok', result },
})

describe('shared resource transfer & delete actions', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('validates shared resource URI boundaries cleanly', () => {
    expect(isSharedResourceUri('viking://resources/docs/a.md')).toBe(true)
    expect(isSharedResourceUri('viking://resources/')).toBe(false)
    expect(isSharedResourceUri('viking://user/default/a.md')).toBe(false)

    expect(
      isValidTransferTarget(
        'viking://resources/docs/a.md',
        'viking://resources/docs/b.md',
      ),
    ).toBe(true)
    expect(
      isValidTransferTarget(
        'viking://resources/docs/a.md',
        'viking://resources/docs/a.md',
      ),
    ).toBe(false)
    expect(
      isValidTransferTarget(
        'viking://resources/docs/a.md',
        'viking://resources/../secret.md',
      ),
    ).toBe(false)
  })

  it('calls /api/v1/resources/cp and /api/v1/resources/mv and DELETE /api/v1/resources', async () => {
    const postSpy = vi
      .spyOn(ovClient.instance, 'post')
      .mockResolvedValueOnce(
        okResp({
          from_uri: 'viking://resources/a.md',
          to_uri: 'viking://resources/b.md',
        }) as never,
      )
      .mockResolvedValueOnce(
        okResp({
          from_uri: 'viking://resources/a.md',
          to_uri: 'viking://resources/c.md',
        }) as never,
      )
    const delSpy = vi
      .spyOn(ovClient.instance, 'delete')
      .mockResolvedValueOnce(
        okResp({
          uri: 'viking://resources/a.md',
          semantic_status: 'queued',
        }) as never,
      )

    await transferSharedResource(
      'copy',
      'viking://resources/a.md',
      'viking://resources/b.md',
      false,
    )
    expect(postSpy).toHaveBeenCalledWith('/api/v1/resources/cp', {
      from_uri: 'viking://resources/a.md',
      to_uri: 'viking://resources/b.md',
    })

    await transferSharedResource(
      'move',
      'viking://resources/a.md',
      'viking://resources/c.md',
      false,
    )
    expect(postSpy).toHaveBeenCalledWith('/api/v1/resources/mv', {
      from_uri: 'viking://resources/a.md',
      to_uri: 'viking://resources/c.md',
    })

    const delRes = await deleteSharedResource('viking://resources/a.md', true)
    expect(delSpy).toHaveBeenCalledWith('/api/v1/resources', {
      params: { uri: 'viking://resources/a.md', recursive: true },
    })
    expect(delRes.semanticStatus).toBe('queued')
  })
})
