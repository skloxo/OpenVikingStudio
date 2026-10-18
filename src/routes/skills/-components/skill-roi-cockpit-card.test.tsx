// @vitest-environment jsdom
// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SkillRoiCockpitCard } from './skill-roi-cockpit-card'
import { ovClient } from '#/lib/ov-client'

vi.mock('#/lib/ov-client', () => ({
  ovClient: {
    instance: {
      get: vi.fn(),
    },
  },
}))

describe('SkillRoiCockpitCard (Card-166)', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  function renderCard() {
    return render(
      <QueryClientProvider client={queryClient}>
        <SkillRoiCockpitCard />
      </QueryClientProvider>
    )
  }

  it('renders 4 KPI metric tiles with real telemetry data', async () => {
    const mockRoiData = {
      status: 'ok',
      result: {
        summary: {
          total_invocations: 1250,
          total_tokens_saved: 45000,
          avg_success_rate: 0.985,
          active_skills_count: 18,
          dormant_skills_count: 3,
          analyzed_days: 30,
        },
        top_roi_skills: [
          {
            skill_id: 'test-runner',
            bundle_name: 'engineering',
            call_count: 300,
            success_rate: 0.99,
            tokens_saved: 12000,
            avg_latency_ms: 120.5,
            last_used_at: '2026-10-18T10:00:00Z',
            roi_score: 88.5,
          },
        ],
        bundle_rankings: [
          {
            bundle_name: 'engineering',
            call_count: 850,
            success_rate: 0.98,
            tokens_saved: 35000,
            skill_count: 6,
            roi_score: 92.4,
          },
        ],
        dormant_warnings: [
          {
            skill_id: 'legacy-shell',
            days_inactive: 30,
            reason: 'Zero invocations in 30 days',
            suggestion: 'Review for consolidation',
          },
        ],
      },
    }

    vi.mocked(ovClient.instance.get).mockResolvedValueOnce({ data: mockRoiData } as any)

    renderCard()

    await waitFor(() => {
      const invocationsTile = screen.getByTestId('metric-tile-invocations')
      expect(invocationsTile.textContent).toContain('1,250')
      expect(invocationsTile.textContent).toContain('活跃技能覆盖: 18 项')
    })

    const tokensTile = screen.getByTestId('metric-tile-tokens')
    expect(tokensTile.textContent).toContain('45.0k')

    const successTile = screen.getByTestId('metric-tile-success-rate')
    expect(successTile.textContent).toContain('98.5%')

    const dormantTile = screen.getByTestId('metric-tile-dormant')
    expect(dormantTile.textContent).toContain('3')

    // 检查排行榜
    expect(screen.getByText('engineering')).toBeDefined()
    expect(screen.getByText('92.4 分')).toBeDefined()
    expect(screen.getByText('test-runner')).toBeDefined()
    expect(screen.getByText('88.5 分')).toBeDefined()
  })

  it('toggles dormant warnings panel when clicking inspect button', async () => {
    const mockRoiData = {
      status: 'ok',
      result: {
        summary: {
          total_invocations: 10,
          total_tokens_saved: 200,
          avg_success_rate: 1.0,
          active_skills_count: 1,
          dormant_skills_count: 1,
          analyzed_days: 30,
        },
        top_roi_skills: [],
        bundle_rankings: [],
        dormant_warnings: [
          {
            skill_id: 'dormant-alpha',
            days_inactive: 30,
            reason: 'Zero calls',
            suggestion: 'Archive this skill',
          },
        ],
      },
    }

    vi.mocked(ovClient.instance.get).mockResolvedValueOnce({ data: mockRoiData } as any)

    renderCard()

    await waitFor(() => {
      expect(screen.getByText(/检测到 1 项工序在过去 30 天内零唤醒调用/)).toBeDefined()
    })

    // 初始状态下沉睡明细未展开
    expect(screen.queryByText('dormant-alpha')).toBeNull()

    // 点击展开
    const toggleBtn = screen.getByRole('button', { name: /查看沉睡工序/ })
    fireEvent.click(toggleBtn)

    expect(screen.getByText('dormant-alpha')).toBeDefined()
    expect(screen.getByText('Archive this skill')).toBeDefined()

    // 再次点击收起
    const collapseBtn = screen.getByRole('button', { name: /收起明细/ })
    fireEvent.click(collapseBtn)

    expect(screen.queryByText('dormant-alpha')).toBeNull()
  })

  it('fails open and shows default zero state when API fails', async () => {
    vi.mocked(ovClient.instance.get).mockRejectedValueOnce(new Error('Network error'))

    renderCard()

    await waitFor(() => {
      expect(screen.getByTestId('skill-roi-cockpit')).toBeDefined()
    })

    const invocationsTile = screen.getByTestId('metric-tile-invocations')
    expect(invocationsTile.textContent).toContain('0')
    expect(screen.getByText('暂无母包遥测数据')).toBeDefined()
  })

  it('strictly adheres to NO GREEN EVER rule across DOM classes', async () => {
    const mockRoiData = {
      status: 'ok',
      result: {
        summary: {
          total_invocations: 50,
          total_tokens_saved: 1200,
          avg_success_rate: 1.0,
          active_skills_count: 3,
          dormant_skills_count: 0,
          analyzed_days: 30,
        },
        top_roi_skills: [
          {
            skill_id: 'agent-governance',
            bundle_name: 'governance',
            call_count: 50,
            success_rate: 1.0,
            tokens_saved: 1200,
            avg_latency_ms: 80,
            last_used_at: null,
            roi_score: 95.0,
          },
        ],
        bundle_rankings: [
          {
            bundle_name: 'governance',
            call_count: 50,
            success_rate: 1.0,
            tokens_saved: 1200,
            skill_count: 1,
            roi_score: 95.0,
          },
        ],
        dormant_warnings: [],
      },
    }

    vi.mocked(ovClient.instance.get).mockResolvedValueOnce({ data: mockRoiData } as any)

    const { container } = renderCard()

    await waitFor(() => {
      expect(screen.getByText('agent-governance')).toBeDefined()
    })

    const html = container.innerHTML
    expect(html).not.toMatch(/\btext-green-\d+\b/)
    expect(html).not.toMatch(/\bbg-green-\d+\b/)
    expect(html).not.toMatch(/\bborder-green-\d+\b/)
  })
})
