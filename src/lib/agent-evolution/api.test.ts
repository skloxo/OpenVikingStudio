import { describe, expect, it, vi } from 'vitest'

import { ovClient } from '#/lib/ov-client'
import {
  fetchAgentEvolutionOverview,
  fetchUserExperiences,
  fetchExperienceTrajectories,
  fetchExperienceOutcomeDistribution,
} from './api'

describe('Agent Evolution API Client', () => {
  it('fetchAgentEvolutionOverview returns overview data', async () => {
    const mockOverview = {
      total_trajectories: 20,
      total_experiences: 5,
      outcomes_summary: {
        success: 18,
        failure: 2,
        partial: 0,
        unknown: 0,
        unfinished: 0,
      },
      success_rate: 90.0,
      recent_24h_active_count: 6,
    }

    vi.spyOn(ovClient.instance, 'get').mockResolvedValueOnce({
      data: { status: 'ok', result: mockOverview },
    })

    const result = await fetchAgentEvolutionOverview()
    expect(result).toEqual(mockOverview)
    expect(ovClient.instance.get).toHaveBeenCalledWith(
      '/api/v1/agent-evolution/overview',
    )
  })

  it('fetchUserExperiences passes pagination params', async () => {
    const mockExperiences = {
      items: [
        {
          uri: 'viking://user/default/memories/experiences/trading.md',
          name: 'trading.md',
          trajectory_count: 8,
          updated_at: '2026-08-24T12:00:00Z',
          size: 2048,
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
      has_more: false,
    }

    vi.spyOn(ovClient.instance, 'get').mockResolvedValueOnce({
      data: { status: 'ok', result: mockExperiences },
    })

    const result = await fetchUserExperiences({ limit: 20, offset: 0 })
    expect(result.items.length).toBe(1)
    expect(result.items[0].name).toBe('trading.md')
    expect(ovClient.instance.get).toHaveBeenCalledWith(
      '/api/v1/agent-evolution/experiences',
      { params: { limit: 20, offset: 0 } },
    )
  })

  it('fetchExperienceTrajectories passes optional parameters', async () => {
    const mockTrajectories = {
      experience_uri: 'viking://user/default/memories/experiences/trading.md',
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
      has_more: false,
    }

    vi.spyOn(ovClient.instance, 'get').mockResolvedValueOnce({
      data: { status: 'ok', result: mockTrajectories },
    })

    const result = await fetchExperienceTrajectories({
      experience_uri: 'viking://user/default/memories/experiences/trading.md',
      start_date: '2026-08-01',
    })
    expect(result.experience_uri).toBe(
      'viking://user/default/memories/experiences/trading.md',
    )
    expect(ovClient.instance.get).toHaveBeenCalledWith(
      '/api/v1/agent-evolution/experiences/trajectories',
      {
        params: {
          experience_uri: 'viking://user/default/memories/experiences/trading.md',
          start_date: '2026-08-01',
        },
      },
    )
  })

  it('fetchExperienceOutcomeDistribution calls endpoint correctly', async () => {
    const mockOutcomes = {
      experience_uri: null,
      outcome_distribution: [
        { outcome: 'success', count: 10 },
        { outcome: 'failure', count: 1 },
      ],
    }

    vi.spyOn(ovClient.instance, 'get').mockResolvedValueOnce({
      data: { status: 'ok', result: mockOutcomes },
    })

    const result = await fetchExperienceOutcomeDistribution()
    expect(result.outcome_distribution.length).toBe(2)
    expect(ovClient.instance.get).toHaveBeenCalledWith(
      '/api/v1/agent-evolution/experiences/outcomes',
      { params: undefined },
    )
  })
})
