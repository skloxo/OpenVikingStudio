// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { HarnessHITLOffloadCenter } from './harness-hitl-offload-center'

const mockOvClient = vi.hoisted(() => ({
  instance: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

vi.mock('#/lib/ov-client', () => ({
  ovClient: mockOvClient,
}))

describe('HarnessHITLOffloadCenter (Card-91)', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it('renders high-density objective metric tiles and live suspended indicator', async () => {
    mockOvClient.instance.get.mockResolvedValueOnce({
      data: {
        summary: {
          total_tokens_saved: 125000,
          reduction_ratio_pct: 68.5,
          active_refs_count: 8,
          pending_hitl_count: 1,
          total_interceptions: 5,
          approved_count: 3,
          rejected_count: 1,
          danger_interception_rate_pct: 100.0,
          live_suspended_count: 1,
          avg_resume_latency_ms: 45.2,
          timed_out_count: 0,
          approval_timeout_abort_rate_pct: 0.0,
        },
        read_offload: {
          total_files_offloaded: 12,
          total_raw_tokens: 180000,
          total_offloaded_tokens: 55000,
          active_handles: [],
        },
        hitl_queue: {
          pending: [
            {
              action_id: 'hitl_test123',
              tool_name: 'forget',
              args_summary: "uri='viking://resources/old'",
              danger_reason: "永久物理删除 Viking 资源，操作不可逆",
              phase: 'execution',
              status: 'pending',
              approval_token: 'tok_abc',
              created_at: Date.now() / 1000,
              is_live_suspended: true,
              timeout_seconds: 180,
            },
          ],
          history: [],
        },
      },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <HarnessHITLOffloadCenter />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText(/读 Offload 累计节约/i)).toBeDefined()
      expect(screen.getByText(/物理挂起中协程/i)).toBeDefined()
      expect(screen.getByText(/平均恢复耗时/i)).toBeDefined()
      expect(screen.getByText(/高危操作拦截率/i)).toBeDefined()
      expect(screen.getByText(/协程物理挂起中 ⏳/i)).toBeDefined()
    })
  })

  it('approves live suspended action and displays real resume latency', async () => {
    mockOvClient.instance.get.mockResolvedValue({
      data: {
        summary: {
          total_tokens_saved: 5000,
          reduction_ratio_pct: 50.0,
          active_refs_count: 1,
          pending_hitl_count: 1,
          total_interceptions: 1,
          approved_count: 0,
          rejected_count: 0,
          danger_interception_rate_pct: 100.0,
          live_suspended_count: 1,
          avg_resume_latency_ms: 0,
          timed_out_count: 0,
          approval_timeout_abort_rate_pct: 0.0,
        },
        read_offload: {
          total_files_offloaded: 1,
          total_raw_tokens: 10000,
          total_offloaded_tokens: 5000,
          active_handles: [],
        },
        hitl_queue: {
          pending: [
            {
              action_id: 'hitl_act999',
              tool_name: 'forget',
              args_summary: "uri='viking://resources/demo'",
              danger_reason: "永久物理删除资源",
              phase: 'execution',
              status: 'pending',
              approval_token: 'tok_xyz',
              created_at: Date.now() / 1000,
              is_live_suspended: true,
              timeout_seconds: 180,
            },
          ],
          history: [],
        },
      },
    })

    mockOvClient.instance.post.mockResolvedValueOnce({
      data: {
        status: 'ok',
        action: {
          action_id: 'hitl_act999',
          tool_name: 'forget',
          status: 'approved',
          resume_latency_ms: 12.8,
        },
      },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <HarnessHITLOffloadCenter />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /批准放行执行/i })).toBeDefined()
    })

    fireEvent.click(screen.getByRole('button', { name: /批准放行执行/i }))

    await waitFor(() => {
      expect(mockOvClient.instance.post).toHaveBeenCalledWith(
        '/api/v1/hitl/resolve',
        expect.objectContaining({
          action_id: 'hitl_act999',
          decision: 'approve',
        })
      )
      expect(screen.getByText(/已批准放行高危操作 forget \(恢复耗时 12.8ms\)/i)).toBeDefined()
    })
  })

  it('triggers real suspended drill via probe button', async () => {
    mockOvClient.instance.get.mockResolvedValue({
      data: {
        summary: {
          total_tokens_saved: 0,
          reduction_ratio_pct: 0,
          active_refs_count: 0,
          pending_hitl_count: 0,
          total_interceptions: 0,
          approved_count: 0,
          rejected_count: 0,
          danger_interception_rate_pct: 100.0,
          live_suspended_count: 0,
          avg_resume_latency_ms: 0,
          timed_out_count: 0,
          approval_timeout_abort_rate_pct: 0.0,
        },
        read_offload: {
          total_files_offloaded: 0,
          total_raw_tokens: 0,
          total_offloaded_tokens: 0,
          active_handles: [],
        },
        hitl_queue: {
          pending: [],
          history: [],
        },
      },
    })

    mockOvClient.instance.post.mockResolvedValueOnce({
      data: {
        status: 'ok',
        probe_type: 'real_suspended_drill',
        message: '成功发起高危操作物理挂起演练！任务协程已处于 SUSPENDED 状态',
      },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <HarnessHITLOffloadCenter />
      </QueryClientProvider>
    )

    const drillBtn = screen.getByRole('button', { name: /发起真实挂起演练/i })
    expect(drillBtn).toBeDefined()
    fireEvent.click(drillBtn)

    await waitFor(() => {
      expect(mockOvClient.instance.post).toHaveBeenCalledWith(
        '/api/v1/hitl/probe',
        expect.objectContaining({
          probe_type: 'real_suspended_drill',
        })
      )
      expect(screen.getByText(/任务协程已处于 SUSPENDED 状态/i)).toBeDefined()
    })
  })
})
