// @vitest-environment jsdom
import * as React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { mockClientGet, mockGetOvResult } = vi.hoisted(() => ({
  mockClientGet: vi.fn(),
  mockGetOvResult: vi.fn(),
}))

vi.mock('#/hooks/use-app-connection', () => ({
  useAppConnection: () => ({
    identityScopeKey: 'default:default',
  }),
}))

vi.mock('#/lib/ov-client', () => ({
  getOvResult: mockGetOvResult,
  ovClient: {
    client: {
      get: mockClientGet,
    },
  },
}))

import { fetchPluginsList, usePluginsData } from './use-plugins'

describe('Card-280 usePluginsData error propagation & category filter', () => {
  beforeEach(() => {
    mockClientGet.mockReset()
    mockGetOvResult.mockReset()
  })

  it('fetchPluginsList propagates backend 500 error instead of returning []', async () => {
    mockClientGet.mockResolvedValueOnce({})
    mockGetOvResult.mockRejectedValueOnce(new Error('HTTP 500 Internal Server Error'))

    await expect(fetchPluginsList()).rejects.toThrow('HTTP 500 Internal Server Error')
  })

  it('usePluginsData surfaces isError when plugin fetch fails', async () => {
    mockClientGet.mockResolvedValue({})
    mockGetOvResult.mockRejectedValue(new Error('Network unavailable'))

    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(QueryClientProvider, { client: qc }, children)

    const { result } = renderHook(() => usePluginsData(), { wrapper })

    await waitFor(
      () => {
        expect(result.current.pluginsQuery.isError).toBe(true)
      },
      { timeout: 4000 },
    )
    expect(result.current.isError).toBe(true)
    expect(result.current.plugins).toEqual([])
  })
})
