import { describe, it, expect } from 'vitest'
import { common as zhCommon } from '#/i18n/locales/zh-CN/common'
import { common as enCommon } from '#/i18n/locales/en/common'
import { retrieval as zhRetrieval } from '#/i18n/locales/zh-CN/retrieval'
import { retrieval as enRetrieval } from '#/i18n/locales/en/retrieval'

describe('Card-UI-EvolutionDecoupling Specification & Retina Tests', () => {
  it('should verify evolution navigation key parity in both zh and en locales', () => {
    // Navigation parity
    expect(zhCommon.appShell.navigation.evolution.title).toBe('技能自演进')
    expect(enCommon.appShell.navigation.evolution.title).toBe('Skill Evolution')

    // Link key parity in retrieval
    expect(zhRetrieval.retrieval.evolutionCenterLink).toBe('技能自演进中心 ➔')
    expect(enRetrieval.retrieval.evolutionCenterLink).toBe('Skill Evolution Center ➔')
  })

  it('should verify evolution 7 tabs domain encapsulation', () => {
    const expectedEvolutionTabs = [
      'evolutionCicd',
      'skillEval',
      'ahe',
      'hermes',
      'rsi',
      'capabilityPages',
      'skillKd',
    ]
    expect(expectedEvolutionTabs).toHaveLength(7)
  })

  it('should verify retrieval decoupled tabs down to 8 core knowledge tabs', () => {
    const expectedRetrievalTabs = [
      'search',
      'bm25',
      'zg',
      'compass',
      'crystallizer',
      'context',
      'valet',
      'llmlingua',
    ]
    expect(expectedRetrievalTabs).toHaveLength(8)
  })
})
