import { describe, expect, it } from 'vitest'
import {
  assertMutationBoundary,
  isWithinRoot,
  joinVikingUri,
  mcpServerNameFromToolUri,
  normalizeVikingUri,
  parentVikingUri,
} from './uri'

describe('arranger uri utilities', () => {
  it('normalizes viking URIs and detects hierarchy containment', () => {
    expect(normalizeVikingUri('viking://resources/arranger///')).toBe(
      'viking://resources/arranger',
    )
    expect(isWithinRoot('viking://resources/arranger/sub/doc.md', 'viking://resources/arranger')).toBe(true)
    expect(isWithinRoot('viking://resources/other/doc.md', 'viking://resources/arranger')).toBe(false)
    expect(joinVikingUri('viking://resources/arranger', 'status.md')).toBe(
      'viking://resources/arranger/status.md',
    )
    expect(parentVikingUri('viking://resources/arranger/status.md')).toBe(
      'viking://resources/arranger',
    )
    expect(mcpServerNameFromToolUri('viking://agent/tools/github/get_issue.json')).toBe('github')
  })

  it('enforces mutation boundary invariants', () => {
    expect(() =>
      assertMutationBoundary(
        'viking://resources/arranger',
        'viking://resources/arranger/a',
        'viking://resources/arranger',
      ),
    ).toThrow()

    expect(() =>
      assertMutationBoundary(
        'viking://resources/arranger/folder',
        'viking://resources/arranger/folder/nested',
        'viking://resources/arranger',
      ),
    ).toThrow()

    expect(() =>
      assertMutationBoundary(
        'viking://resources/arranger/doc.md',
        'viking://resources/arranger/copy.md',
        'viking://resources/arranger',
      ),
    ).not.toThrow()
  })
})
