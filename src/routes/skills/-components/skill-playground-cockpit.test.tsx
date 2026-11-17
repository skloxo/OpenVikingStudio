// @vitest-environment jsdom
// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SkillPlaygroundCockpit } from './skill-playground-cockpit'

const postMock = vi.fn(async (url: string) => {
  if (url.endsWith('/hit-test')) {
    return {
      data: {
        status: 'ok',
        query: '抓取网页',
        catalog_size: 20,
        top1_score: 0.91,
        top2_score: 0.42,
        margin: 0.49,
        candidate_match: null,
        matches: [
          {
            skill_name: 'web-harvest-pro',
            domain: 'crawl',
            matched: true,
            score: 0.91,
            best_trigger: '抓取网页正文',
            reason: 'exact',
          },
        ],
        collisions: { has_collision: false, collisions: [] },
        routing_decision: {
          action: 'MERGE',
          target_package: 'crawl',
          top1_candidate: 'web-harvest-pro',
          top1_score: 0.91,
          top2_candidate: 'credential-vault',
          top2_score: 0.42,
          margin: 0.49,
          rationale: 'high margin',
        },
        alias_resolution: {
          type: 'bundle',
          bundle_name: 'web-harvest-pro',
          target_name: 'web-harvest-pro',
          is_virtual: false,
        },
      },
    }
  }
  if (url.endsWith('/compress-simulate')) {
    return {
      data: {
        status: 'ok',
        compression: {
          original_length: 480,
          compressed_length: 260,
          compression_ratio: 0.4583,
          tokens_saved: 55,
          contract_fidelity: 1.0,
          latency_ms: 2.3,
          compressed_content: '# compressed six-tuple',
          six_tuple: {
            interface: 'Inputs',
            workflow: ['step 1'],
            protocol: [],
            rules: [],
            contracts: [],
            evidence: [],
          },
        },
        gate: {
          passed: true,
          multiplier: 1.2,
          recommended_action: 'PASS',
          reason: 'within limit',
        },
      },
    }
  }
  return {
    data: {
      status: 'ok',
      name: 'incident-triage',
      sections: ['Interface', 'Workflow', 'Protocol', 'Rules', 'Contracts', 'Evidence'],
      content: '---\nname: incident-triage\n---\n## 1. Interface\n',
      validation: { valid: true, errors: [], warnings: [] },
    },
  }
})

vi.mock('#/lib/ov-client', () => ({
  ovClient: {
    instance: {
      post: (...args: unknown[]) => postMock(String(args[0])),
    },
  },
}))

vi.mock('#/lib/clipboard', () => ({
  copyTextToClipboard: vi.fn().mockResolvedValue(undefined),
}))

describe('SkillPlaygroundCockpit (Card-167)', () => {
  afterEach(() => {
    cleanup()
    postMock.mockClear()
  })

  function renderWithQuery(ui: React.ReactElement) {
    const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
    return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
  }

  it('runs hit-test, compression benchmark, and scaffold generation workflows', async () => {
    renderWithQuery(<SkillPlaygroundCockpit />)

    expect(screen.getByText(/技能大盘交互测试沙箱与意图试算器/)).toBeDefined()

    fireEvent.click(screen.getByRole('button', { name: /执行意图 Hit-Test/ }))
    await waitFor(() => {
      expect(screen.getByText(/MERGE \(crawl\)/)).toBeDefined()
    })
    expect(screen.getByText(/49\.0%/)).toBeDefined()

    fireEvent.click(screen.getByRole('button', { name: /试算压缩对比/ }))
    await waitFor(() => {
      expect(screen.getByText(/480 ➔ 260/)).toBeDefined()
    })
    expect(screen.getByText(/PASS/)).toBeDefined()

    fireEvent.click(screen.getByRole('button', { name: /生成 6 章节脚手架/ }))
    await waitFor(() => {
      expect(screen.getByText(/格式门禁通过/)).toBeDefined()
    })
  })
})
