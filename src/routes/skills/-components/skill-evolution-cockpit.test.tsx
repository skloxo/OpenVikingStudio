// @vitest-environment jsdom

import * as React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SkillEvolutionCockpit } from './skill-evolution-cockpit'

const mockOvClient = vi.hoisted(() => ({
  instance: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

vi.mock('#/lib/ov-client', () => ({
  ovClient: mockOvClient,
}))

describe('SkillEvolutionCockpit', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })

    mockOvClient.instance.get.mockImplementation(async (url: string) => {
      if (url.includes('/pipeline/status')) {
        return {
          data: {
            status: 'ok',
            metrics: {
              intent_collisions: 5,
              total_homogenous_skills: 28,
              average_health_score: 75.0,
              s_grade_ratio: 0.12,
              attempt_pass_rate: 0.88,
            },
          },
        }
      }
      if (url.includes('/pipeline/clusters')) {
        return {
          data: {
            status: 'ok',
            total_clusters: 2,
            clusters: [
              {
                cluster_id: 'feishu-suite',
                domain_name: 'Feishu / Lark 飞书生态',
                cluster_name: 'Feishu / Lark 飞书生态',
                target_slug: 'feishu-hub',
                target_crystallized_slug: 'feishu-hub',
                candidate_slugs: ['feishu-bitable', 'feishu-doc', 'feishu-card'],
                candidate_count: 3,
                reasons: ['Matched domain keywords: feishu, lark'],
                avg_health_score: 72.5,
              },
              {
                cluster_id: 'git-forge',
                domain_name: 'Git & GitHub 版本管理与协作',
                cluster_name: 'Git & GitHub 版本管理与协作',
                target_slug: 'git-forge',
                target_crystallized_slug: 'git-forge',
                candidate_slugs: ['github-pr', 'git-workflow'],
                candidate_count: 2,
                reasons: ['Matched domain keywords: github, git'],
                avg_health_score: 82.0,
              },
            ],
          },
        }
      }
      return { data: {} }
    })

    mockOvClient.instance.post.mockImplementation(async (url: string, body: any) => {
      if (url.includes('/pipeline/run')) {
        return {
          data: {
            status: 'ok',
            dry_run: body?.dry_run ?? true,
            report: {
              total_candidates: 5,
              clusters_identified: 2,
              processed_clusters: 2,
              clusters_crystallized: 2,
              total_crystallized: 2,
              clusters_blocked: 0,
              collisions_before: 5,
              collisions_after: 0,
              avg_health_before: 75.0,
              avg_health_after: 89.0,
              overall_attempt_pass_rate: 1.0,
              results: [
                {
                  cluster_id: 'feishu-suite',
                  domain_name: 'Feishu / Lark 飞书生态',
                  target_slug: 'feishu-hub',
                  success: true,
                  final_judge_score: 92.5,
                  weight_boost: 1.8,
                  absorbed_slugs: ['feishu-bitable', 'feishu-doc'],
                  inherited_files: ['feishu-bitable/scripts/sync.py'],
                  stages: [],
                },
              ],
            },
          },
        }
      }
      if (url.includes('/pipeline/rollback')) {
        return {
          data: {
            status: 'ok',
            restored_skills: 5,
          },
        }
      }
      return { data: {} }
    })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders 4 objective metric tiles correctly', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <SkillEvolutionCockpit />
      </QueryClientProvider>
    )

    // Check titles of the 4 metric tiles
    expect(screen.getByText('意图冲突簇数')).toBeDefined()
    expect(screen.getByText('全域平均健康分')).toBeDefined()
    expect(screen.getByText('S 级特种兵占比')).toBeDefined()
    expect(screen.getByText('Attempt 门禁放行率')).toBeDefined()

    // Wait for async query data
    await waitFor(() => {
      expect(screen.getByText('Feishu / Lark 飞书生态')).toBeDefined()
      expect(screen.getByText('Git & GitHub 版本管理与协作')).toBeDefined()
    })
  })

  it('renders control buttons and triggers dry-run preview', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <SkillEvolutionCockpit />
      </QueryClientProvider>
    )

    const previewBtn = screen.getByRole('button', { name: /扫描影响面清单/i })
    expect(previewBtn).toBeDefined()

    fireEvent.click(previewBtn)

    await waitFor(() => {
      expect(mockOvClient.instance.post).toHaveBeenCalled()
      expect(screen.getByText(/影响面扫描明细/i)).toBeDefined()
    })
  })

  it('allows selecting a cluster to filter target domain', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <SkillEvolutionCockpit />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('Feishu / Lark 飞书生态')).toBeDefined()
    })

    const feishuCard = screen.getByText('Feishu / Lark 飞书生态')
    fireEvent.click(feishuCard)

    // Check clear filter button appears
    await waitFor(() => {
      expect(screen.getByText(/清除过滤/i)).toBeDefined()
    })
  })
})
