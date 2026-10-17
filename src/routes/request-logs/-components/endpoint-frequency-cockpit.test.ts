import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

describe('EndpointFrequencyCockpit Governance & Compliance', () => {
  const componentPath = path.resolve(__dirname, 'endpoint-frequency-cockpit.tsx')
  const content = fs.readFileSync(componentPath, 'utf-8')
  const lines = content.split('\n')

  it('strictly enforces NO GREEN EVER law', () => {
    // Prohibited green color patterns
    const prohibitedColors = [
      '#22c55e',
      '#4ade80',
      '#86efac',
      '#16a34a',
      '#15803d',
      'text-green',
      'bg-green',
      'border-green',
      'text-emerald',
      'bg-emerald',
      'border-emerald',
    ]

    for (const color of prohibitedColors) {
      expect(content.toLowerCase()).not.toContain(color.toLowerCase())
    }
  })

  it('strictly enforces minimum font size >= 12px (no micro fonts)', () => {
    const microFonts = [
      'text-[8px]',
      'text-[9px]',
      'text-[10px]',
      'text-[11px]',
      'text-[7px]',
    ]

    for (const mf of microFonts) {
      expect(content).not.toContain(mf)
    }
  })

  it('strictly satisfies single file size limits (100 ~ 300 golden sweet spot, <= 500 hard line)', () => {
    expect(lines.length).toBeGreaterThanOrEqual(100)
    expect(lines.length).toBeLessThanOrEqual(350)
    expect(lines.length).toBeLessThan(500)
  })

  it('ensures cyan theme and neutral muted colors are used for signals', () => {
    expect(content).toContain('cyan-500')
    expect(content).toContain('font-mono')
    expect(content).toContain('tabular-nums')
  })
})
