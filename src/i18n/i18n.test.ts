import { describe, expect, it } from 'vitest'
import { defaultLanguage, resources, supportedLanguages } from './resources'

describe('i18n configuration and modular dictionary parity', () => {
  it('supports defaultLanguage as zh-CN and includes en and zh-CN', () => {
    expect(defaultLanguage).toBe('zh-CN')
    expect(supportedLanguages).toContain('zh-CN')
    expect(supportedLanguages).toContain('en')
    expect(resources['zh-CN']).toBeDefined()
    expect(resources['en']).toBeDefined()
  })

  it('contains all 18 required top-level namespaces in both languages', () => {
    const requiredNamespaces = [
      'versionTimeline',
      'appShell',
      'monitoringPage',
      'skillsPage',
      'tasksPage',
      'accountSwitcher',
      'common',
      'connection',
      'settings',
      'home',
      'operations',
      'requestLogs',
      'addResource',
      'resources',
      'retrieval',
      'sessions',
      'oauth',
      'playground',
    ]

    const zhKeys = Object.keys(resources['zh-CN'])
    const enKeys = Object.keys(resources['en'])

    for (const ns of requiredNamespaces) {
      expect(zhKeys).toContain(ns)
      expect(enKeys).toContain(ns)
    }

    expect(zhKeys.sort()).toEqual(enKeys.sort())
  })

  it('ensures deep key consistency between zh-CN and en for critical namespaces', () => {
    const differences: string[] = []
    const checkDeepKeys = (zhObj: Record<string, unknown>, enObj: Record<string, unknown>, path = '') => {
      const zhSubKeys = Object.keys(zhObj).sort()
      const enSubKeys = Object.keys(enObj).sort()
      
      for (const k of zhSubKeys) {
        if (!enSubKeys.includes(k)) {
          differences.push(`Missing in en: ${path ? `${path}.${k}` : k}`)
        } else {
          const zhVal = zhObj[k]
          const enVal = enObj[k]
          if (typeof zhVal === 'object' && zhVal !== null && !Array.isArray(zhVal)) {
            checkDeepKeys(
              zhVal as Record<string, unknown>,
              enVal as Record<string, unknown>,
              path ? `${path}.${k}` : k
            )
          }
        }
      }

      for (const k of enSubKeys) {
        if (!zhSubKeys.includes(k)) {
          differences.push(`Missing in zh-CN: ${path ? `${path}.${k}` : k}`)
        }
      }
    }

    checkDeepKeys(
      resources['zh-CN'],
      resources['en']
    )

    if (differences.length > 0) {
      console.log('Found i18n differences:\n' + differences.join('\n'))
    }
    expect(differences).toEqual([])
  })

  it('enforces single file size limit <= 500 lines for all i18n files', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')

    const checkDir = (dirPath: string) => {
      const entries = fs.readdirSync(dirPath, { withFileTypes: true })
      for (const entry of entries) {
        const fullPath = path.join(dirPath, entry.name)
        if (entry.isDirectory()) {
          checkDir(fullPath)
        } else if (entry.isFile() && entry.name.endsWith('.ts')) {
          const content = fs.readFileSync(fullPath, 'utf-8')
          const lines = content.split('\n').length
          expect(
            lines,
            `File ${entry.name} has ${lines} lines, exceeding 500 lines limit`
          ).toBeLessThanOrEqual(500)
        }
      }
    }

    checkDir(path.resolve(__dirname, 'locales'))
  })
})
