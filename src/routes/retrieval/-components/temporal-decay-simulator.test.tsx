import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

describe('Memory Temporal Decay & Safe Cold Archive Cockpit Gates (Card-92 / v1.7.46)', () => {
  const cockpitFile = path.resolve(__dirname, 'temporal-decay-simulator.tsx')

  it('100% enforces NO GREEN EVER in temporal decay cockpit', () => {
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

  it('enforces single-file hard safety limits (<= 500 lines)', () => {
    const content = fs.readFileSync(cockpitFile, 'utf-8')
    const lineCount = content.split('\n').length
    expect(lineCount).toBeLessThanOrEqual(500)
  })

  it('contains four real objective metric tiles and non-destructive safety gates', () => {
    const content = fs.readFileSync(cockpitFile, 'utf-8')
    expect(content).toContain('活跃记忆总数')
    expect(content).toContain('安全冷归档记忆')
    expect(content).toContain('日常检索信噪比增益')
    expect(content).toContain('数据防损安全保障')
    expect(content).toContain('100% 安全')
    expect(content).toContain('冷归档安全隔离库')
    expect(content).toContain('安全复活')
  })
})
