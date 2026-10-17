// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { HarnessFailureSandboxProbe } from './harness-failure-sandbox-probe'

const mockOvClient = vi.hoisted(() => ({
  instance: {
    post: vi.fn(),
  },
}))

vi.mock('#/lib/ov-client', () => ({
  ovClient: mockOvClient,
}))

describe('HarnessFailureSandboxProbe (Card-90)', () => {
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

  it('renders real chaos drill action buttons', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <HarnessFailureSandboxProbe recentEvents={[]} />
      </QueryClientProvider>
    )

    expect(screen.getByText(/受控混沌演练与自愈韧性探针/i)).toBeDefined()
    expect(screen.getByRole('button', { name: /真实 429 退避自愈/i })).toBeDefined()
    expect(screen.getByRole('button', { name: /Watchdog 超时熔断/i })).toBeDefined()
    expect(screen.getByRole('button', { name: /真实 Merkle 状态树/i })).toBeDefined()
  })

  it('triggers real 429 backoff drill and renders objective metric tiles', async () => {
    mockOvClient.instance.post.mockResolvedValueOnce({
      data: {
        action: 'simulate_transient',
        real_drill_executed: true,
        actual_duration_ms: 68.4,
        drill_success: true,
        attempts_used: 2,
        retry_delays_ms: [45.2],
        backoff_algorithm: 'ExponentialBackoffWithFullJitter',
        healed: true,
      },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <HarnessFailureSandboxProbe recentEvents={[]} />
      </QueryClientProvider>
    )

    const btn = screen.getByRole('button', { name: /真实 429 退避自愈/i })
    fireEvent.click(btn)

    await waitFor(() => {
      expect(mockOvClient.instance.post).toHaveBeenCalledWith(
        '/api/v1/system/failure_taxonomy_probe',
        expect.objectContaining({ action: 'simulate_transient' })
      )
      expect(screen.getByText('68.4 ms')).toBeDefined()
      expect(screen.getByText('PASS (100% 自愈)')).toBeDefined()
      expect(screen.getByText('生产业务 0 污染')).toBeDefined()
    })
  })
})
