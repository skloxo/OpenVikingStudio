import { describe, expect, it } from 'vitest'

import {
  getWatchRefetchInterval,
  hasCompletedTriggeredWatchSync,
  hasDiscoveredWatch,
  hasWatchExecutionAdvanced,
  normalizeWatchUri,
} from './watch-discovery'

describe('watch discovery helpers', () => {
  it('normalizes trailing slashes and discovers watch targets', () => {
    expect(normalizeWatchUri('viking://resources/docs/')).toBe(
      'viking://resources/docs',
    )
    expect(getWatchRefetchInterval(true)).toBe(1000)
    expect(getWatchRefetchInterval(false)).toBe(false)
    expect(
      hasDiscoveredWatch(
        [
          {
            createdAt: null,
            instruction: '',
            isActive: true,
            lastExecutionTime: null,
            nextExecutionTime: null,
            path: 'https://a.com',
            reason: '',
            taskId: '1',
            toUri: 'viking://resources/docs',
            watchInterval: 60,
          },
        ],
        'viking://resources/docs/',
      ),
    ).toBe(true)
  })

  it('detects triggered sync completion and timestamp advancement', () => {
    expect(
      hasCompletedTriggeredWatchSync(
        [
          { task_id: 'old', status: 'completed' },
          { task_id: 'new', status: 'completed' },
        ],
        ['old'],
      ),
    ).toBe(true)

    expect(
      hasWatchExecutionAdvanced(
        '2026-11-16T12:05:00Z',
        '2026-11-16T12:00:00Z',
      ),
    ).toBe(true)
    expect(
      hasWatchExecutionAdvanced(
        '2026-11-16T12:00:00Z',
        '2026-11-16T12:00:00Z',
      ),
    ).toBe(false)
  })
})
