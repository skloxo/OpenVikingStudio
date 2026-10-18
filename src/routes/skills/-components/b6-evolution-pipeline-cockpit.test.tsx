// @vitest-environment jsdom
// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { B6EvolutionPipelineCockpit } from './b6-evolution-pipeline-cockpit'
import { B6_PIPELINE_STAGES } from '../-constants/b6-pipeline-stages'

// Mock ovClient
vi.mock('#/lib/ov-client', () => ({
  ovClient: {
    instance: {
      get: vi.fn().mockResolvedValue({
        data: {
          status: 'ok',
          queue_depth: {
            total: 10,
            pending: 2,
            validating: 1,
            staged: 1,
            committed: 6,
            rejected: 0,
            error: 0,
          },
        },
      }),
      post: vi.fn().mockResolvedValue({
        data: { processed_count: 1, results: [] },
      }),
    },
  },
}))

// Mock useSkillEventBus
vi.mock('../-hooks/use-skill-event-bus', () => ({
  useSkillEventBus: () => ({ isConnected: true }),
}))

describe('B6EvolutionPipelineCockpit (Card-175)', () => {
  afterEach(() => {
    cleanup()
  })

  function renderWithQueryClient(ui: React.ReactElement) {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
  }

  it('renders top pulse header and 12-stage lifecycle title', () => {
    renderWithQueryClient(<B6EvolutionPipelineCockpit />)

    expect(screen.getByText(/B6 自主结晶演进流水线与全息运行中枢/)).toBeDefined()
    expect(screen.getByText(/12-Stage Cycle Active/)).toBeDefined()
    expect(screen.getByText(/实时双工已连通/)).toBeDefined()
  })

  it('renders all 12 stages with correct numbers and names', () => {
    renderWithQueryClient(<B6EvolutionPipelineCockpit />)

    expect(B6_PIPELINE_STAGES.length).toBe(12)
    for (const stage of B6_PIPELINE_STAGES) {
      expect(screen.getAllByText(stage.name).length).toBeGreaterThanOrEqual(1)
    }
  })

  it('allows clicking a stage card to switch details and inspect invariants', () => {
    renderWithQueryClient(<B6EvolutionPipelineCockpit />)

    // 点击第 7 阶：技能视网膜行为验收
    const retinaBtn = screen.getByRole('button', { name: /技能视网膜行为验收/ })
    fireEvent.click(retinaBtn)

    // 断言视窗展示其承载引擎与贯彻契约
    expect(screen.getByText(/EvalRunner & SkillEvalEngine/)).toBeDefined()
    expect(screen.getByText(/passed > 0 && failed == 0/)).toBeDefined()
  })

  it('strictly adheres to NO GREEN EVER rule across DOM classes', () => {
    const { container } = renderWithQueryClient(<B6EvolutionPipelineCockpit />)
    const html = container.innerHTML

    expect(html).not.toMatch(/\btext-green-\d+\b/)
    expect(html).not.toMatch(/\bbg-green-\d+\b/)
    expect(html).not.toMatch(/\bborder-green-\d+\b/)
  })
})
