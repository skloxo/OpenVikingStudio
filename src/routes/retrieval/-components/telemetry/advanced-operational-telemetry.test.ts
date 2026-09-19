import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import { retrieval as zhRetrieval } from '#/i18n/locales/zh-CN/retrieval'
import { retrieval as enRetrieval } from '#/i18n/locales/en/retrieval'

describe('Advanced Operational Telemetry Compliance & Safety Gates (Card-Retrieval-AdvancedCards / v1.5.45)', () => {
  const telemetryDir = path.resolve(__dirname)
  const containerFile = path.resolve(__dirname, '../advanced-operational-telemetry.tsx')
  const telemetryFiles = [
    containerFile,
    path.join(telemetryDir, 'bm25-dense-ratio-card.tsx'),
    path.join(telemetryDir, 'rarg-abstention-card.tsx'),
    path.join(telemetryDir, 'knowledge-health-radar-card.tsx'),
  ]

  it('100% enforces NO GREEN EVER across all operational telemetry components', () => {
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

    for (const file of telemetryFiles) {
      expect(fs.existsSync(file)).toBe(true)
      const content = fs.readFileSync(file, 'utf-8')
      for (const pat of greenPatterns) {
        expect(pat.test(content)).toBe(false)
      }
    }
  })

  it('100% enforces minimum typography hard floor >= 12px (Zero Micro-Fonts)', () => {
    const microFontPattern = /text-\[(8|9|10|11)px\]/i

    for (const file of telemetryFiles) {
      const content = fs.readFileSync(file, 'utf-8')
      expect(microFontPattern.test(content)).toBe(false)
    }
  })

  it('enforces single-file golden sweet spot (<= 300 lines) for all components', () => {
    for (const file of telemetryFiles) {
      const content = fs.readFileSync(file, 'utf-8')
      const lineCount = content.split('\n').length
      expect(lineCount).toBeLessThanOrEqual(300)
    }
  })

  it('synchronizes bilingual i18n keys for operationalTelemetry', () => {
    expect(zhRetrieval.retrieval.operationalTelemetry).toBeDefined()
    expect(enRetrieval.retrieval.operationalTelemetry).toBeDefined()

    const zhKeys = Object.keys(zhRetrieval.retrieval.operationalTelemetry)
    const enKeys = Object.keys(enRetrieval.retrieval.operationalTelemetry)

    expect(zhKeys.sort()).toEqual(enKeys.sort())
    expect(zhKeys.length).toBeGreaterThanOrEqual(15)
  })
})
