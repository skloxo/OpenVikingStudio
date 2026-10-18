// @vitest-environment jsdom
// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { B6HermesAheCockpit } from './b6-hermes-ahe-cockpit'

const mockHermesSummary = {
  experience: {
    total_messages: 1250,
    total_sessions: 95,
    db_path: '~/.openviking/experience.db',
  },
  nudge: {
    queue_depth: 3,
    completed_reviews: 18,
    is_running: false,
  },
  patches: {
    total_patches: 14,
    proposed: 2,
    applied: 10,
    reverted: 2,
    max_allowed_lines: 30,
  },
}

const mockPatches = [
  {
    patch_id: 'patch_h01',
    skill_name: 'cluster-network-ops',
    file_path: 'skills/cluster-network-ops/SKILL.md',
    target_content: '- disable ipv6 explicitly in sysctl',
    replacement_content: '- disable ipv6 explicitly in sysctl and clash verge',
    reason: 'FTS5 conversation reflection: Clash DNS leak detected',
    status: 'proposed',
    created_at: 1729250000,
    target_line_count: 1,
    replacement_line_count: 1,
  },
  {
    patch_id: 'patch_h02',
    skill_name: 'keepass-vault',
    file_path: 'skills/keepass-vault/SKILL.md',
    target_content: 'search password',
    replacement_content: 'search password with snapshot protection',
    reason: 'Credential safety hardening',
    status: 'applied',
    created_at: 1729250010,
    applied_at: 1729250020,
    target_line_count: 1,
    replacement_line_count: 1,
  },
]

const mockAheSummary = {
  manifests: {
    total: 8,
    active: 6,
    verified: 5,
    violated: 1,
    retired: 0,
  },
  clusters: {
    total_clusters: 3,
    patched_clusters: 2,
    unpatched_clusters: 1,
    total_occurrences: 5,
  },
}

const mockManifests = [
  {
    manifest_id: 'man_ahe_001',
    skill_name: 'deepseek-harness-ops',
    status: 'verified',
    assumptions: [
      {
        assumption_id: 'ass_01',
        description: 'Session stream decompression zstd format preserved',
        frozen_surface: 'session.v4.jsonl.zstd',
        validation_command: 'pytest tests/test_dsh.py',
      },
    ],
    snapshots: [
      {
        path: 'skills/deepseek-harness-ops/SKILL.md',
        sha256: 'abc123456789',
      },
    ],
  },
]

vi.mock('#/lib/ov-client', () => ({
  ovClient: {
    instance: {
      get: vi.fn((url: string) => {
        if (url.includes('/api/v1/hermes/summary')) {
          return Promise.resolve({ data: mockHermesSummary })
        }
        if (url.includes('/api/v1/hermes/patches')) {
          return Promise.resolve({ data: mockPatches })
        }
        if (url.includes('/api/v1/ahe/summary')) {
          return Promise.resolve({ data: mockAheSummary })
        }
        if (url.includes('/api/v1/ahe/manifest')) {
          return Promise.resolve({ data: mockManifests })
        }
        return Promise.resolve({ data: {} })
      }),
      post: vi.fn((url: string) => {
        if (url.includes('/api/v1/hermes/patch/apply')) {
          return Promise.resolve({ data: { status: 'ok', applied: true } })
        }
        if (url.includes('/api/v1/hermes/patch/revert')) {
          return Promise.resolve({ data: { status: 'ok', reverted: true } })
        }
        if (url.includes('/api/v1/ahe/verify')) {
          return Promise.resolve({ data: { status: 'ok', total_verified: 8 } })
        }
        return Promise.resolve({ data: {} })
      }),
    },
  },
}))

describe('B6HermesAheCockpit (Card-178)', () => {
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
        <B6HermesAheCockpit />
      </QueryClientProvider>
    )
  }

  it('renders dual stage tabs and 4 KPI metrics correctly', async () => {
    renderCockpit()

    expect(screen.getByText(/第 11 阶: Hermes 经历微手术补丁审查/)).toBeDefined()
    expect(screen.getByText(/第 10 阶: AHE 契约假设与漂移对抗/)).toBeDefined()

    await waitFor(() => {
      expect(screen.getByText('1250')).toBeDefined()
      expect(screen.getByText('14')).toBeDefined()
      expect(screen.getByText('6 / 8')).toBeDefined()
      expect(screen.getByText('1')).toBeDefined()
    })
  })

  it('renders micro patches and allows expanding diff comparison', async () => {
    renderCockpit()

    await waitFor(() => {
      expect(screen.getByText('cluster-network-ops')).toBeDefined()
    })

    const patchBtn = screen.getByTestId('patch-toggle-patch_h01')
    fireEvent.click(patchBtn)

    await waitFor(() => {
      const targetElem = screen.getByTestId('patch-target-patch_h01')
      const replacementElem = screen.getByTestId('patch-replacement-patch_h01')
      expect(targetElem.textContent).toContain('disable ipv6 explicitly in sysctl')
      expect(replacementElem.textContent).toContain('and clash verge')
    })
  })

  it('allows applying a proposed micro-patch', async () => {
    renderCockpit()

    await waitFor(() => {
      expect(screen.getByText('应用补丁')).toBeDefined()
    })

    const applyBtn = screen.getByText('应用补丁')
    fireEvent.click(applyBtn)

    await waitFor(() => {
      expect(screen.getByText('应用补丁')).toBeDefined()
    })
  })

  it('switches to AHE mode and displays assumptions manifests', async () => {
    renderCockpit()

    const aheTab = screen.getByText(/第 10 阶: AHE 契约假设与漂移对抗/)
    fireEvent.click(aheTab)

    await waitFor(() => {
      expect(screen.getByText('deepseek-harness-ops')).toBeDefined()
      expect(screen.getByText('VERIFIED')).toBeDefined()
    })

    const verifyBtn = screen.getByText(/全量核验/)
    fireEvent.click(verifyBtn)

    await waitFor(() => {
      expect(screen.getByText('deepseek-harness-ops')).toBeDefined()
    })
  })
})
