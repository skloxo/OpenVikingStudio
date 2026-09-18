import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import { getStatusCodeInfo } from './http-status-chart'

describe('http-status-chart NO GREEN EVER and status code compliance', () => {
  it('maps HTTP 200, 201, 204 and other 2xx to icy cyan shades rather than green', () => {
    const info200 = getStatusCodeInfo(200)
    expect(info200.color).toBe('#06b6d4') // Cyan 500
    expect(info200.color).not.toBe('#22c55e') // Forbidden green-500

    const info201 = getStatusCodeInfo(201)
    expect(info201.color).toBe('#22d3ee') // Cyan 400
    expect(info201.color).not.toBe('#4ade80') // Forbidden green-400

    const info204 = getStatusCodeInfo(204)
    expect(info204.color).toBe('#67e8f9') // Cyan 300
    expect(info204.color).not.toBe('#86efac') // Forbidden green-300

    const info202 = getStatusCodeInfo(202)
    expect(info202.color).toBe('#06b6d4') // General 2xx fallback to Cyan 500
  })

  it('guarantees NO GREEN EVER in all status code mappings', () => {
    const forbiddenGreens = [
      '#22c55e',
      '#4ade80',
      '#86efac',
      '#10b981',
      '#059669',
      '#34d399',
      '#16a34a',
      '#15803d',
    ]

    const testCodes = [200, 201, 202, 204, 206, 301, 302, 304, 400, 401, 403, 404, 500, 502, 503]
    for (const code of testCodes) {
      const info = getStatusCodeInfo(code)
      for (const green of forbiddenGreens) {
        expect(info.color.toLowerCase()).not.toBe(green.toLowerCase())
      }
    }
  })

  it('verifies monitoring route files strictly comply with NO GREEN EVER', () => {
    const monitoringDir = path.resolve(__dirname, '..')
    const filesToScan: string[] = []

    function collectFiles(dir: string) {
      const entries = fs.readdirSync(dir, { withFileTypes: true })
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name)
        if (entry.isDirectory()) {
          collectFiles(fullPath)
        } else if (/\.(tsx|ts)$/.test(entry.name) && !entry.name.endsWith('.test.ts') && !entry.name.endsWith('.test.tsx')) {
          filesToScan.push(fullPath)
        }
      }
    }

    collectFiles(monitoringDir)
    expect(filesToScan.length).toBeGreaterThan(0)

    const greenClassRegex = /\b(text|bg|border|stroke|fill)-(green|emerald)-[0-9]{2,3}\b/i
    const forbiddenHexRegex = /#(22c55e|4ade80|86efac|10b981|059669|34d399|16a34a|15803d)/i

    for (const file of filesToScan) {
      const content = fs.readFileSync(file, 'utf-8')
      const hasGreenClass = greenClassRegex.test(content)
      const hasForbiddenHex = forbiddenHexRegex.test(content)

      expect(hasGreenClass, `File ${file} should not contain green/emerald Tailwind classes`).toBe(false)
      expect(hasForbiddenHex, `File ${file} should not contain green hex colors`).toBe(false)
    }
  })

  it('verifies typography lower bound (>= 12px) across monitoring route components', () => {
    const monitoringDir = path.resolve(__dirname, '..')
    const filesToScan: string[] = []

    function collectFiles(dir: string) {
      const entries = fs.readdirSync(dir, { withFileTypes: true })
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name)
        if (entry.isDirectory()) {
          collectFiles(fullPath)
        } else if (/\.(tsx|ts)$/.test(entry.name) && !entry.name.endsWith('.test.ts') && !entry.name.endsWith('.test.tsx')) {
          filesToScan.push(fullPath)
        }
      }
    }

    collectFiles(monitoringDir)
    const microFontRegex = /text-\[(8|9|10|11)px\]/

    for (const file of filesToScan) {
      const content = fs.readFileSync(file, 'utf-8')
      const match = content.match(microFontRegex)
      expect(match, `File ${file} contains forbidden micro-font: ${match?.[0]}`).toBeNull()
    }
  })
})
