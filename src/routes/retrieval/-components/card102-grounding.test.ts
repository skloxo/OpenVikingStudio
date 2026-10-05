// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

describe('Card-102 TokenShift & DSPy Asset Grounding & Persistence Gates', () => {
  const compDir = path.resolve(__dirname)

  it('enforces single-file safety limits (<= 500 lines) for all Card-102 components', () => {
    const files = [
      'tokenshift-cockpit.tsx',
      'tokenshift-kpi-tiles.tsx',
      'code-file-picker.tsx',
      'dspy-compiler-cockpit.tsx',
      'dspy-kpi-tiles.tsx',
      'dspy-signature-insight-card.tsx',
      'prompt-template-picker.tsx',
    ]

    for (const file of files) {
      const fullPath = path.join(compDir, file)
      expect(fs.existsSync(fullPath)).toBe(true)
      const content = fs.readFileSync(fullPath, 'utf-8')
      const lineCount = content.split('\n').length
      expect(lineCount).toBeLessThanOrEqual(500)
    }
  })

  it('100% enforces NO GREEN EVER in Card-102 components', () => {
    const files = [
      'tokenshift-cockpit.tsx',
      'tokenshift-kpi-tiles.tsx',
      'code-file-picker.tsx',
      'dspy-compiler-cockpit.tsx',
      'dspy-kpi-tiles.tsx',
      'dspy-signature-insight-card.tsx',
      'prompt-template-picker.tsx',
    ]

    const greenRegex = /\b(text|bg|border)-(green|emerald)-\d+\b/g

    for (const file of files) {
      const content = fs.readFileSync(path.join(compDir, file), 'utf-8')
      const matches = content.match(greenRegex)
      expect(matches).toBeNull()
    }
  })

  it('100% enforces typography hard floor >= 12px (Zero Micro-Fonts)', () => {
    const files = [
      'tokenshift-cockpit.tsx',
      'tokenshift-kpi-tiles.tsx',
      'code-file-picker.tsx',
      'dspy-compiler-cockpit.tsx',
      'dspy-kpi-tiles.tsx',
      'dspy-signature-insight-card.tsx',
      'prompt-template-picker.tsx',
    ]

    const microFontRegex = /text-\[(8|9|10|11)px\]/g

    for (const file of files) {
      const content = fs.readFileSync(path.join(compDir, file), 'utf-8')
      const matches = content.match(microFontRegex)
      expect(matches).toBeNull()
    }
  })

  it('verifies TokenShift mounts CodeFilePicker and dual persistence endpoints', () => {
    const content = fs.readFileSync(path.join(compDir, 'tokenshift-cockpit.tsx'), 'utf-8')
    expect(content).toContain('CodeFilePicker')
    expect(content).toContain('/api/v1/tokenshift/apply')
    expect(content).toContain('skeleton_file')
    expect(content).toContain('in_place')
  })

  it('verifies DSPy mounts PromptTemplatePicker and dual persistence endpoints', () => {
    const content = fs.readFileSync(path.join(compDir, 'dspy-compiler-cockpit.tsx'), 'utf-8')
    expect(content).toContain('PromptTemplatePicker')
    expect(content).toContain('/api/v1/dspy/apply')
    expect(content).toContain('compiled_file')
    expect(content).toContain('in_place')
  })
})
