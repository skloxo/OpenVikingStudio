// @vitest-environment jsdom
// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { B6ProvenanceMultiLedger } from './b6-provenance-multi-ledger'

const mockProvenanceEvents = [
  {
    event_id: 'prov_abc123',
    timestamp: 1729250000,
    action: 'ROUTE',
    skill_name: 'kubernetes-cluster-ops',
    version: '1.0.0',
    receipt_id: 'rcpt_001',
    operator: 'ante-gate-router',
    details: {
      stage: 'SEAM_ROUTED',
      decision: 'MERGE_INTO_EXISTING',
      target_bundle: 'system-fleet-ops',
      message: '归宿决策: 整合进结晶大包 [system-fleet-ops]',
    },
    snapshot_path: '/mock/snapshots/k8s.snap.md',
  },
  {
    event_id: 'prov_def456',
    timestamp: 1729250010,
    action: 'VALIDATE',
    skill_name: 'cadre-room-allocator',
    version: '1.0.0',
    receipt_id: 'rcpt_002',
    operator: 'validator',
    details: {
      stage: 'QUALITY_PASSED',
      is_valid: true,
      opt_score: 92.5,
      message: '门禁质检通过 (评分: 92.5/100)',
    },
  },
]

const mockQueueRecords = [
  {
    receipt_id: 'rcpt_q1',
    skill_name: 'grid-fence-patrol',
    raw_content: '# Grid Fence Patrol',
    author: 'agent-patrol',
    status: 'PENDING',
    status_message: 'Awaiting worker pickup',
    validation_report: {
      opt_score: 88.0,
      routing: {
        action: 'MERGE',
        target_package: 'grid-management',
        top1_score: 0.92,
        margin: 0.15,
      },
    },
    retry_count: 0,
    created_at: 1729250000,
    updated_at: 1729250000,
  },
]

vi.mock('#/lib/ov-client', () => ({
  ovClient: {
    instance: {
      get: vi.fn((url: string) => {
        if (url.includes('/api/v1/skills/ingestion/provenance')) {
          return Promise.resolve({
            data: { status: 'ok', events: mockProvenanceEvents },
          })
        }
        if (url.includes('/api/v1/skills/ingestion/queue')) {
          return Promise.resolve({
            data: {
              status: 'ok',
              queue_depth: {
                total: 5,
                pending: 2,
                validating: 1,
                staged: 1,
                committed: 1,
                rejected: 0,
                error: 0,
              },
              recent_records: mockQueueRecords,
            },
          })
        }
        return Promise.resolve({ data: {} })
      }),
      post: vi.fn().mockResolvedValue({
        data: { status: 'ok' },
      }),
    },
  },
}))

describe('B6ProvenanceMultiLedger (Card-176)', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
  })

  afterEach(() => {
    cleanup()
  })

  function renderLedger() {
    return render(
      <QueryClientProvider client={queryClient}>
        <B6ProvenanceMultiLedger />
      </QueryClientProvider>
    )
  }

  it('renders multi-rail track switcher and defaults to Track 1 (Provenance)', async () => {
    renderLedger()

    expect(screen.getByText(/轨道 1: 黑匣子证据链/)).toBeDefined()
    expect(screen.getByText(/轨道 2: SQLite 准入流水/)).toBeDefined()

    await waitFor(() => {
      expect(screen.getByText('kubernetes-cluster-ops')).toBeDefined()
      expect(screen.getByText('cadre-room-allocator')).toBeDefined()
    })
  })

  it('switches to Track 2 (SQLite Queue) and displays ingestion records', async () => {
    renderLedger()

    const track2Btn = screen.getByText(/轨道 2: SQLite 准入流水/)
    fireEvent.click(track2Btn)

    await waitFor(() => {
      expect(screen.getByText('grid-fence-patrol')).toBeDefined()
      expect(screen.getByText('PENDING')).toBeDefined()
      expect(screen.getByText('88分')).toBeDefined()
    })
  })

  it('filters rows based on search input', async () => {
    renderLedger()

    await waitFor(() => {
      expect(screen.getByText('kubernetes-cluster-ops')).toBeDefined()
    })

    const searchInput = screen.getByPlaceholderText('搜索技能/ID/操作源...')
    fireEvent.change(searchInput, { target: { value: 'cluster' } })

    expect(screen.getByText('kubernetes-cluster-ops')).toBeDefined()
    expect(screen.queryByText('cadre-room-allocator')).toBeNull()
  })

  it('opens detail sheet when clicking on a provenance row', async () => {
    renderLedger()

    await waitFor(() => {
      expect(screen.getByText('kubernetes-cluster-ops')).toBeDefined()
    })

    fireEvent.click(screen.getByText('kubernetes-cluster-ops'))

    await waitFor(() => {
      expect(screen.getByText('黑匣子演变审计证据')).toBeDefined()
      expect(screen.getByText(/Zero-Loss Snapshot/)).toBeDefined()
    })
  })

  it('renders batch processing button with count badge when queue has pending items', async () => {
    renderLedger()

    await waitFor(() => {
      expect(screen.getByText(/批处理 \(2\)/)).toBeDefined()
    })
  })
})
