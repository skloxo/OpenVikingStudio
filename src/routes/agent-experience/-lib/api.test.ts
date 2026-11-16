import { afterEach, describe, expect, it, vi } from 'vitest'

import { OvClientError, ovClient } from '#/lib/ov-client'

import {
  fetchContent,
  fetchExperiences,
  fetchOutcomeDistribution,
  fetchSourceTrajectories,
  fetchTrajectories,
  searchExperiences,
} from './api'

const okResp = (result: unknown) => ({
  status: 200,
  headers: {},
  data: { status: 'ok', result },
})

describe('agent-experience route api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetchExperiences prefers merged /api/v1/agent-evolution/experiences', async () => {
    const getSpy = vi.spyOn(ovClient.client, 'get').mockResolvedValueOnce(
      okResp({
        items: [
          {
            uri: 'viking://resources/master_memory/evolution_lessons/l1.md',
            name: 'l1.md',
            trajectory_count: 3,
            updated_at: '2026-11-16T12:00:00Z',
            size: 256,
            source: 'evolution_lesson',
          },
        ],
        total: 1,
        limit: 10,
        offset: 0,
        has_more: false,
      }) as never,
    )

    const page = await fetchExperiences({
      experiencesUri: 'viking://user/default/memories/experiences',
      page: 1,
      pageSize: 10,
    })

    expect(getSpy).toHaveBeenCalledWith(
      expect.objectContaining({ url: '/api/v1/agent-evolution/experiences' }),
    )
    expect(page.items).toHaveLength(1)
    expect(page.items[0]?.source).toBe('evolution_lesson')
    expect(page.items[0]?.trajectoryCount).toBe(3)
  })

  it('fetchExperiences falls back to /api/v1/fs/ls when merged endpoint returns 404', async () => {
    const err404 = new OvClientError({
      code: 'NOT_FOUND',
      message: 'missing',
      statusCode: 404,
    })
    const getSpy = vi
      .spyOn(ovClient.client, 'get')
      .mockRejectedValueOnce(err404)
      .mockResolvedValueOnce(
        okResp([
          {
            name: 'exp.md',
            uri: 'viking://user/default/memories/experiences/exp.md',
            modTime: '2026-11-16T09:00:00Z',
            size: 128,
          },
        ]) as never,
      )

    const page = await fetchExperiences({
      experiencesUri: 'viking://user/default/memories/experiences',
      page: 1,
      pageSize: 10,
    })

    expect(getSpy).toHaveBeenLastCalledWith(
      expect.objectContaining({ url: '/api/v1/fs/ls' }),
    )
    expect(page.items[0]?.name).toBe('exp.md')
    expect(page.hasMore).toBe(false)
  })

  it('searchExperiences merges user experiences and master_memory lessons', async () => {
    vi.spyOn(ovClient.client, 'post')
      .mockResolvedValueOnce(
        okResp({
          memories: [
            { uri: 'viking://user/default/memories/experiences/shared.md' },
          ],
        }) as never,
      )
      .mockResolvedValueOnce(
        okResp({
          resources: [
            {
              uri: 'viking://resources/master_memory/evolution_lessons/shared.md',
            },
            {
              uri: 'viking://resources/master_memory/evolution_lessons/pitfall.md',
            },
          ],
        }) as never,
      )

    const res = await searchExperiences({
      experiencesUri: 'viking://user/default/memories/experiences',
      keyword: 'pitfall',
    })

    expect(res.items.map((item) => item.name)).toEqual([
      'shared.md',
      'pitfall.md',
    ])
  })

  it('fetchContent, fetchTrajectories, fetchOutcomeDistribution and fetchSourceTrajectories parse responses', async () => {
    const getSpy = vi
      .spyOn(ovClient.client, 'get')
      .mockResolvedValueOnce(okResp('# Lesson body') as never)
      .mockResolvedValueOnce(
        okResp({
          experience_uri: 'viking://user/default/memories/experiences/a.md',
          items: [
            {
              uri: 'viking://user/default/memories/trajectories/t1.md',
              name: 't1.md',
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
          has_more: false,
        }) as never,
      )
      .mockResolvedValueOnce(
        okResp({
          experience_uri: 'viking://user/default/memories/experiences/a.md',
          outcome_distribution: [{ outcome: 'success', count: 2 }],
        }) as never,
      )
      .mockResolvedValueOnce(
        okResp({
          attrs: {
            memory: {
              links: [
                {
                  link_type: 'derived_from',
                  to_uri: 'viking://user/default/memories/trajectories/src.md',
                },
              ],
            },
          },
        }) as never,
      )

    const expUri = 'viking://user/default/memories/experiences/a.md'
    expect(await fetchContent(expUri)).toBe('# Lesson body')
    const traj = await fetchTrajectories({ experienceUri: expUri })
    expect(traj.items).toHaveLength(1)
    const dist = await fetchOutcomeDistribution({ experienceUri: expUri })
    expect(dist.distribution[0]).toEqual({ outcome: 'success', count: 2 })
    const src = await fetchSourceTrajectories(expUri)
    expect(src).toEqual([
      { uri: 'viking://user/default/memories/trajectories/src.md', reason: undefined },
    ])
    expect(getSpy).toHaveBeenCalledTimes(4)
  })
})
