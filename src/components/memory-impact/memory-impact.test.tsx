// @vitest-environment jsdom

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import type {
  UniversalMemoryDiff,
  UniversalMemoryDiffOperation,
} from './types'
import { summarizeOperations, summarizeDiffs } from './types'
import { ImpactCounts, ImpactSummaryCards } from './impact-summary-cards'
import { MemoryDiffItem } from './memory-diff-item'

describe('UniversalMemoryImpact Wheel Unit Tests', () => {
  const mockOperations: UniversalMemoryDiffOperation[] = [
    {
      kind: 'add',
      uri: 'viking://resources/memory/skill_1.md',
      memoryType: 'skill',
      after: 'def test_skill(): pass',
    },
    {
      kind: 'update',
      uri: 'viking://resources/memory/config.json',
      memoryType: 'config',
      before: '{"rate": 0.3}',
      after: '{"rate": 0.5}',
    },
    {
      kind: 'delete',
      uri: 'viking://resources/memory/temp.log',
      memoryType: 'log',
      before: 'temporary log to delete',
    },
  ]

  it('correctly calculates summaries from operations', () => {
    const summary = summarizeOperations(mockOperations)
    expect(summary).toEqual({
      adds: 1,
      updates: 1,
      deletes: 1,
    })
  })

  it('correctly aggregates multiple diffs summary', () => {
    const diffs: UniversalMemoryDiff[] = [
      {
        archiveId: 'commit-1',
        summary: { adds: 3, updates: 1, deletes: 0 },
        operations: [],
      },
      {
        archiveId: 'commit-2',
        summary: { adds: 2, updates: 4, deletes: 1 },
        operations: [],
      },
    ]

    const totals = summarizeDiffs(diffs)
    expect(totals).toEqual({
      adds: 5,
      updates: 5,
      deletes: 1,
    })
  })

  it('renders ImpactCounts pill with cyan, amber and rose text', () => {
    const { container } = render(
      <ImpactCounts totals={{ adds: 3, updates: 2, deletes: 1 }} />,
    )
    expect(container.textContent).toContain('+3')
    expect(container.textContent).toContain('~2')
    expect(container.textContent).toContain('−1')
    expect(container.querySelector('.text-cyan-600')).toBeTruthy()
    expect(container.querySelector('.text-amber-600')).toBeTruthy()
    expect(container.querySelector('.text-rose-600')).toBeTruthy()
  })

  it('renders ImpactSummaryCards with 3 column grid', () => {
    render(
      <ImpactSummaryCards summary={{ adds: 8, updates: 4, deletes: 2 }} />,
    )
    expect(screen.getByText('新增写入')).toBeTruthy()
    expect(screen.getByText('特例演化')).toBeTruthy()
    expect(screen.getByText('失效清理')).toBeTruthy()
    expect(screen.getByText('8')).toBeTruthy()
    expect(screen.getByText('4')).toBeTruthy()
    expect(screen.getByText('2')).toBeTruthy()
  })

  it('renders MemoryDiffItem update comparison block without text below 11px', () => {
    const updateOp: UniversalMemoryDiffOperation = {
      kind: 'update',
      uri: 'viking://resources/test.txt',
      memoryType: 'document',
      before: 'old content line',
      after: 'new content line',
    }

    const { container } = render(<MemoryDiffItem operation={updateOp} />)
    expect(screen.getByText('viking://resources/test.txt')).toBeTruthy()
    expect(screen.getByText('document')).toBeTruthy()
    expect(screen.getByText('old content line')).toBeTruthy()
    expect(screen.getByText('new content line')).toBeTruthy()

    // 严禁存在 text-[8px], text-[9px], text-[10px]
    expect(container.innerHTML).not.toContain('text-[8px]')
    expect(container.innerHTML).not.toContain('text-[9px]')
    expect(container.innerHTML).not.toContain('text-[10px]')
  })
})
