// @vitest-environment jsdom
// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { B6RetinaRegressionCockpit } from './b6-retina-regression-cockpit'

const mockEvalSummary = {
  total_cases: 42,
  total_runs: 12,
  global_pass_rate: 0.952,
  last_run_at: '2026-10-18T22:00:00Z',
  skills_evaluated: ['agent-friendly-code-org', 'deepseek-harness-ops'],
  recent_runs: [
    {
      run_id: 'run_retina_001',
      skill_name: 'agent-friendly-code-org',
      started_at: '2026-10-18T22:00:00Z',
      finished_at: '2026-10-18T22:00:05Z',
      total: 3,
      passed: 3,
      failed: 0,
      skipped: 0,
      pass_rate: 1.0,
      status: 'completed',
      results: [
        {
          case_id: 'case_zero_exit_assert',
          skill_name: 'agent-friendly-code-org',
          judge_type: 'exit_code',
          verdict: 'pass',
          actual: 'exit: 0',
          expected: 'exit: 0',
          error: null,
          duration_ms: 12.4,
        },
        {
          case_id: 'case_tool_args_contract',
          skill_name: 'agent-friendly-code-org',
          judge_type: 'tool_call',
          verdict: 'pass',
          actual: 'args: valid',
          expected: 'args: valid',
          error: null,
          duration_ms: 18.2,
        },
      ],
    },
  ],
}

const mockRsiSummary = {
  current_phase: 'daytime_collection',
  phase_switched_at: 1729250000,
  total_trajectories_collected: 180,
  total_turns_collected: 850,
  total_credit_evaluations: 64,
  dual_split_verifications: 28,
  gate_pass_rate: 0.964,
}

vi.mock('#/lib/ov-client', () => ({
  ovClient: {
    instance: {
      get: vi.fn((url: string) => {
        if (url.includes('/api/v1/skill-eval/summary')) {
          return Promise.resolve({ data: mockEvalSummary })
        }
        if (url.includes('/api/v1/rsi/status')) {
          return Promise.resolve({ data: mockRsiSummary })
        }
        return Promise.resolve({ data: {} })
      }),
      post: vi.fn((url: string) => {
        if (url.includes('/api/v1/skill-eval/run')) {
          return Promise.resolve({
            data: {
              run_id: 'run_retina_new',
              skill_name: 'agent-friendly-code-org',
              started_at: '2026-10-18T22:30:00Z',
              finished_at: '2026-10-18T22:30:03Z',
              total: 2,
              passed: 2,
              failed: 0,
              skipped: 0,
              pass_rate: 1.0,
              status: 'completed',
              results: [
                {
                  case_id: 'case_eval_dynamic_run',
                  skill_name: 'agent-friendly-code-org',
                  judge_type: 'contract',
                  verdict: 'pass',
                  actual: 'ok',
                  expected: 'ok',
                  error: null,
                  duration_ms: 8.5,
                },
              ],
            },
          })
        }
        if (url.includes('/api/v1/rsi/gate/verify_split')) {
          return Promise.resolve({
            data: {
              passed: true,
              train_pass_rate: 0.985,
              holdout_pass_rate: 0.962,
              baseline_holdout_pass_rate: 0.95,
              regression_detected: false,
              details: 'Invariants: holdout >= baseline (0.962 >= 0.950) PASS',
            },
          })
        }
        return Promise.resolve({ data: {} })
      }),
    },
  },
}))

describe('B6RetinaRegressionCockpit (Card-177)', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
  })

  afterEach(() => {
    cleanup()
  })

  function renderCockpit() {
    return render(
      <QueryClientProvider client={queryClient}>
        <B6RetinaRegressionCockpit />
      </QueryClientProvider>
    )
  }

  it('renders dual stage tabs and 4 KPI metrics correctly', async () => {
    renderCockpit()

    expect(screen.getByText(/第 7 阶: 技能视网膜沙箱用例评测/)).toBeDefined()
    expect(screen.getByText(/第 8 阶: RSI 零退化回归保护门禁/)).toBeDefined()

    await waitFor(() => {
      expect(screen.getByText('95.2%')).toBeDefined()
      expect(screen.getByText('42')).toBeDefined()
      expect(screen.getByText('28')).toBeDefined()
      expect(screen.getByText('96.4%')).toBeDefined()
    })
  })

  it('renders default Stage 7 results and allows expanding details', async () => {
    renderCockpit()

    await waitFor(() => {
      expect(screen.getByText('case_zero_exit_assert')).toBeDefined()
    })

    const caseBtn = screen.getByText('case_zero_exit_assert')
    fireEvent.click(caseBtn)

    await waitFor(() => {
      expect(screen.getByText(/期望契约:/)).toBeDefined()
      expect(screen.getByText(/实际输出:/)).toBeDefined()
    })
  })

  it('triggers retina sandbox evaluation mutation on button click', async () => {
    renderCockpit()

    const runBtn = screen.getByText(/运行沙箱用例/)
    fireEvent.click(runBtn)

    await waitFor(() => {
      expect(screen.getByText('case_eval_dynamic_run')).toBeDefined()
    })
  })

  it('switches to Stage 8 (RSI Guard) and triggers Dual-Split verification', async () => {
    renderCockpit()

    const rsiTab = screen.getByText(/第 8 阶: RSI 零退化回归保护门禁/)
    fireEvent.click(rsiTab)

    await waitFor(() => {
      expect(screen.getByText(/RSI Dual-Split 零退化比对门禁状态/)).toBeDefined()
    })

    const verifyBtn = screen.getByText(/验证零退化/)
    fireEvent.click(verifyBtn)

    await waitFor(() => {
      expect(screen.getByText(/100% 零退化保障/)).toBeDefined()
      expect(screen.getByText(/holdout >= baseline/)).toBeDefined()
    })
  })
})
