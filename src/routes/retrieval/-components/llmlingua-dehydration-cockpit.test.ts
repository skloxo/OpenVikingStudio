import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import { retrieval as zhRetrieval } from '#/i18n/locales/zh-CN/retrieval'
import { retrieval as enRetrieval } from '#/i18n/locales/en/retrieval'

describe('LLMLingua-2 Dehydration Cockpit Gates (Card-LLMLingua-01 / v1.5.46)', () => {
  const cockpitFile = path.resolve(__dirname, 'llmlingua-dehydration-cockpit.tsx')
  const routeFile = path.resolve(__dirname, '../route.tsx')

  it('100% enforces NO GREEN EVER in LLMLingua cockpit component', () => {
    const greenPatterns = [
      /text-emerald-/i,
      /text-green-/i,
      /bg-emerald-/i,
      /bg-green-/i,
      /border-emerald-/i,
      /border-green-/i,
      /#22c55e/i,
      /#16a34a/i,
      /#4ade80/i,
      /#86efac/i,
    ]

    expect(fs.existsSync(cockpitFile)).toBe(true)
    const content = fs.readFileSync(cockpitFile, 'utf-8')
    for (const pat of greenPatterns) {
      expect(pat.test(content)).toBe(false)
    }
  })

  it('100% enforces minimum typography hard floor >= 12px (Zero Micro-Fonts)', () => {
    const microFontPattern = /text-\[(8|9|10|11)px\]/i
    const content = fs.readFileSync(cockpitFile, 'utf-8')
    expect(microFontPattern.test(content)).toBe(false)
  })

  it('enforces single-file golden sweet spot (<= 350 lines)', () => {
    const content = fs.readFileSync(cockpitFile, 'utf-8')
    const lineCount = content.split('\n').length
    expect(lineCount).toBeLessThanOrEqual(350)
  })

  it('verifies route.tsx mounts llmlingua tab and component', () => {
    const routeContent = fs.readFileSync(routeFile, 'utf-8')
    expect(routeContent).toContain("id: 'llmlingua'")
    expect(routeContent).toContain('<LLMLinguaDehydrationCockpit />')
  })

  it('synchronizes bilingual i18n keys for llmlingua', () => {
    const zhKeys = Object.keys(zhRetrieval.retrieval.llmlingua)
    const enKeys = Object.keys(enRetrieval.retrieval.llmlingua)

    expect(zhKeys.length).toBeGreaterThanOrEqual(15)
    expect(zhKeys.sort()).toEqual(enKeys.sort())
  })
})
