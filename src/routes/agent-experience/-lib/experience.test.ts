// @vitest-environment jsdom
import { describe, expect, it, beforeEach } from 'vitest'

import {
  buildCustomTimeRange,
  buildExperiencesUri,
  getExperienceDisplayName,
  isExperienceUpdatedSinceLastSeen,
  markExperiencesSeen,
  normalizeExperienceFiles,
  normalizeOutcomeDistribution,
  normalizeSourceTrajectoryLinks,
  normalizeTrajectoryPage,
  OUTCOME_COLORS,
  resolveTimeRange,
  TRAJECTORY_OUTCOMES,
} from './experience'

describe('agent-experience pure helpers', () => {
  beforeEach(() => {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.clear()
    }
  })

  it('uses NO-GREEN cyan palette for success outcome', () => {
    expect(OUTCOME_COLORS.success).toBe('bg-cyan-500')
    for (const cls of Object.values(OUTCOME_COLORS)) {
      expect(cls).not.toMatch(/emerald|green/i)
    }
  })

  it('builds user experiences URI and strips .md in display name', () => {
    expect(buildExperiencesUri(' alice smith ')).toBe(
      'viking://user/alice%20smith/memories/experiences',
    )
    expect(buildExperiencesUri('')).toBe(
      'viking://user/default/memories/experiences',
    )
    expect(
      getExperienceDisplayName(
        'viking://user/default/memories/experiences/exchange.md',
      ),
    ).toBe('exchange')
  })

  it('normalizes both user experiences and evolution lessons with stats', () => {
    const items = normalizeExperienceFiles([
      { name: 'dir', uri: 'viking://x/dir', isDir: true },
      {
        name: 'exp.md',
        uri: 'viking://user/default/memories/experiences/exp.md',
        modTime: '2026-11-16T08:00:00Z',
        size: 120,
        trajectory_count: 5,
      },
      {
        name: 'lesson.md',
        uri: 'viking://resources/master_memory/evolution_lessons/lesson.md',
        updated_at: '2026-11-16T10:00:00Z',
        size: 340,
        trajectory_count: 2,
      },
    ])
    expect(items).toEqual([
      {
        name: 'exp.md',
        uri: 'viking://user/default/memories/experiences/exp.md',
        modTime: '2026-11-16T08:00:00Z',
        size: 120,
        trajectoryCount: 5,
        source: 'experience',
      },
      {
        name: 'lesson.md',
        uri: 'viking://resources/master_memory/evolution_lessons/lesson.md',
        modTime: '2026-11-16T10:00:00Z',
        size: 340,
        trajectoryCount: 2,
        source: 'evolution_lesson',
      },
    ])
  })

  it('normalizes trajectory page and fixed outcome distribution order', () => {
    const page = normalizeTrajectoryPage(
      {
        experience_uri: 'viking://user/default/memories/experiences/exp.md',
        items: [{ uri: 'viking://t/1.md', name: '1.md', description: 'desc' }],
        total: 3,
        limit: 1,
        offset: 0,
      },
      'viking://fallback',
    )
    expect(page?.hasMore).toBe(true)
    expect(page?.items).toHaveLength(1)

    const dist = normalizeOutcomeDistribution(
      { outcome_distribution: [{ outcome: 'success', count: 4 }] },
      'viking://exp',
    )
    expect(dist.distribution.map((d) => d.outcome)).toEqual(
      TRAJECTORY_OUTCOMES,
    )
    expect(dist.distribution[0]).toEqual({ outcome: 'success', count: 4 })
    expect(dist.distribution[1]).toEqual({ outcome: 'failure', count: 0 })
  })

  it('resolves UTC quick presets and validates custom ranges', () => {
    const now = new Date('2026-11-16T12:00:00Z')
    expect(resolveTimeRange('7d', now)).toEqual({
      preset: '7d',
      startDate: '2026-11-10',
      endDate: '2026-11-16',
    })
    expect(buildCustomTimeRange('2026-11-20', '2026-11-10')).toEqual({
      error: 'order',
    })
    expect(buildCustomTimeRange('bad', '2026-11-10')).toEqual({
      error: 'invalid',
    })
    expect(buildCustomTimeRange('2026-11-01', '2026-11-16')).toEqual({
      range: {
        preset: 'all',
        startDate: '2026-11-01',
        endDate: '2026-11-16',
      },
    })
  })

  it('filters derived_from trajectory links and tracks seen timestamps', () => {
    const links = normalizeSourceTrajectoryLinks({
      attrs: {
        memory: {
          links: [
            {
              link_type: 'derived_from',
              to_uri: 'viking://user/a/memories/trajectories/t1.md',
              description: 'distilled from commit',
            },
            {
              link_type: 'derived_from',
              to_uri: 'viking://user/a/memories/trajectories/t1.md',
            },
            {
              link_type: 'related',
              to_uri: 'viking://user/a/memories/trajectories/ignored.md',
            },
          ],
        },
      },
    })
    expect(links).toEqual([
      {
        uri: 'viking://user/a/memories/trajectories/t1.md',
        reason: 'distilled from commit',
      },
    ])

    const uri = 'viking://user/a/memories/experiences/exp.md'
    expect(isExperienceUpdatedSinceLastSeen(uri, '2026-11-16T08:00:00Z')).toBe(
      true,
    )
    markExperiencesSeen([{ uri }])
    expect(isExperienceUpdatedSinceLastSeen(uri, '2026-11-16T08:00:00Z')).toBe(
      false,
    )
  })
})
