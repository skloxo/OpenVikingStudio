import { ovClient } from '#/lib/ov-client'

export interface EvolutionOverviewResult {
  total_trajectories: number
  total_experiences: number
  outcomes_summary: {
    success: number
    failure: number
    partial: number
    unknown: number
    unfinished: number
  }
  success_rate: number
  recent_24h_active_count: number
}

export interface UserExperienceItem {
  uri: string
  name: string
  trajectory_count: number
  updated_at: string | null
  size: number
}

export interface UserExperiencesResult {
  items: UserExperienceItem[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface ExperienceTrajectoryItem {
  uri: string
  name: string
  description?: string
  created_at?: string
  updated_at?: string
}

export interface ExperienceTrajectoriesResult {
  experience_uri?: string | null
  items: ExperienceTrajectoryItem[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface OutcomeCountItem {
  outcome: string
  count: number
}

export interface ExperienceOutcomeDistributionResult {
  experience_uri?: string | null
  outcome_distribution: OutcomeCountItem[]
}

export async function fetchAgentEvolutionOverview(): Promise<EvolutionOverviewResult> {
  const response = await ovClient.instance.get<{
    status: string
    result: EvolutionOverviewResult
  }>('/api/v1/agent-evolution/overview')
  return response.data.result
}

export async function fetchUserExperiences(params?: {
  limit?: number
  offset?: number
}): Promise<UserExperiencesResult> {
  const response = await ovClient.instance.get<{
    status: string
    result: UserExperiencesResult
  }>('/api/v1/agent-evolution/experiences', {
    params: {
      limit: params?.limit ?? 50,
      offset: params?.offset ?? 0,
    },
  })
  return response.data.result
}

export async function fetchExperienceTrajectories(params?: {
  experience_uri?: string
  limit?: number
  offset?: number
  start_date?: string
  end_date?: string
}): Promise<ExperienceTrajectoriesResult> {
  const response = await ovClient.instance.get<{
    status: string
    result: ExperienceTrajectoriesResult
  }>('/api/v1/agent-evolution/experiences/trajectories', {
    params,
  })
  return response.data.result
}

export async function fetchExperienceOutcomeDistribution(params?: {
  experience_uri?: string
  start_date?: string
  end_date?: string
}): Promise<ExperienceOutcomeDistributionResult> {
  const response = await ovClient.instance.get<{
    status: string
    result: ExperienceOutcomeDistributionResult
  }>('/api/v1/agent-evolution/experiences/outcomes', {
    params,
  })
  return response.data.result
}
