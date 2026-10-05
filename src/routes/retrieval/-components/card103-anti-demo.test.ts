// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

describe('Card-103 Anti-Demo & Anti-Dangling Automated Retina Gate', () => {
  const routesDir = path.resolve(__dirname, '../../')

  function getAllTsxFiles(dir: string): string[] {
    let results: string[] = []
    const list = fs.readdirSync(dir, { withFileTypes: true })
    for (const item of list) {
      const fullPath = path.join(dir, item.name)
      if (item.isDirectory()) {
        results = results.concat(getAllTsxFiles(fullPath))
      } else if (item.isFile() && item.name.endsWith('.tsx') && !item.name.endsWith('.test.tsx')) {
        results.push(fullPath)
      }
    }
    return results
  }

  const allComponents = getAllTsxFiles(routesDir)

  it('scans all route components and confirms >= 200 components inspected', () => {
    expect(allComponents.length).toBeGreaterThanOrEqual(200)
  })

  it('100% enforces zero forbidden demo/mock markers in all frontend components', () => {
    const demoMarkerRegex = /(\bDEMO_ONLY\b|@demo-only|MOCK_DATA_ONLY|fake_persistence|mock-apply)/i
    for (const file of allComponents) {
      const content = fs.readFileSync(file, 'utf-8')
      const match = content.match(demoMarkerRegex)
      expect(match, `File ${file} contains forbidden demo marker: ${match?.[0]}`).toBeNull()
    }
  })

  it('100% enforces NO GREEN EVER across all route components', () => {
    const greenRegex = /\b(text|bg|border)-(green|emerald)-\d+\b/g
    for (const file of allComponents) {
      const content = fs.readFileSync(file, 'utf-8')
      const match = content.match(greenRegex)
      expect(match, `File ${file} contains green utility class: ${match?.join(', ')}`).toBeNull()
    }
  })

  it('100% enforces minimum typography hard floor >= 12px (Zero Micro-Fonts)', () => {
    const microFontRegex = /\btext-\[(8|9|10|11)px\]/g
    for (const file of allComponents) {
      const content = fs.readFileSync(file, 'utf-8')
      const match = content.match(microFontRegex)
      expect(match, `File ${file} contains micro-font: ${match?.join(', ')}`).toBeNull()
    }
  })

  it('verifies all *-cockpit.tsx components with presets mount real asset pickers', () => {
    const cockpits = allComponents.filter((f) => path.basename(f).includes('-cockpit.tsx'))
    expect(cockpits.length).toBeGreaterThanOrEqual(10)

    for (const cockpit of cockpits) {
      const content = fs.readFileSync(cockpit, 'utf-8')
      if (content.includes('PRESET')) {
        const isGrounded =
          content.includes('Picker') ||
          content.includes('useQuery') ||
          content.includes('useMutation') ||
          content.includes('ovClient') ||
          content.includes('file_picker') ||
          content.includes('fetch')
        expect(isGrounded, `Cockpit ${cockpit} has presets but lacks real asset picker or backend hook`).toBe(true)
      }
    }
  })
})
