import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

describe('Component & Wheel Inventory SSOT Living Mechanism', () => {
  const inventoryPath = path.resolve(
    __dirname,
    '../../docs/architecture/COMPONENT_AND_WHEEL_INVENTORY.md',
  )

  it('ensures COMPONENT_AND_WHEEL_INVENTORY.md exists and is substantive', () => {
    expect(fs.existsSync(inventoryPath)).toBe(true)
    const content = fs.readFileSync(inventoryPath, 'utf-8')
    expect(content.length).toBeGreaterThan(1500)
    expect(content).toContain('查库第一，禁止手搓')
  })

  it('ensures all primitive UI components in src/components/ui are registered in inventory', () => {
    const uiDir = path.resolve(__dirname, 'ui')
    const files = fs.readdirSync(uiDir)
    const inventoryContent = fs.readFileSync(inventoryPath, 'utf-8')

    const ignoredFiles = new Set(['pixel-blast.tsx', 'index.ts'])
    const missingInInventory: string[] = []

    for (const file of files) {
      if (
        file.endsWith('.tsx') &&
        !file.includes('.test.') &&
        !ignoredFiles.has(file)
      ) {
        // e.g. "button.tsx" -> check if "button.tsx" or component name exists in inventory
        const baseName = file.replace('.tsx', '')
        const hasFileRef =
          inventoryContent.includes(file) ||
          inventoryContent.toLowerCase().includes(`\`${baseName}\``) ||
          inventoryContent.toLowerCase().includes(`**${baseName}**`)

        if (!hasFileRef) {
          missingInInventory.push(file)
        }
      }
    }

    expect(
      missingInInventory,
      `The following components in src/components/ui/ are missing in COMPONENT_AND_WHEEL_INVENTORY.md: ${missingInInventory.join(
        ', ',
      )}. Please document them to maintain a living inventory!`,
    ).toEqual([])
  })

  it('ensures core app-level components in src/components are registered in inventory', () => {
    const inventoryContent = fs.readFileSync(inventoryPath, 'utf-8')
    const coreComponents = [
      'app-shell.tsx',
      'current-user-menu.tsx',
      'account-switcher.tsx',
      'server-doctor-dialog.tsx',
      'access-required-gate.tsx',
    ]

    for (const comp of coreComponents) {
      expect(
        inventoryContent.includes(comp),
        `Core component ${comp} must be documented in COMPONENT_AND_WHEEL_INVENTORY.md!`,
      ).toBe(true)
    }
  })

  it('ensures key data clients and utilities in src/lib are registered in inventory', () => {
    const inventoryContent = fs.readFileSync(inventoryPath, 'utf-8')
    const coreUtilities = [
      'ovClient',
      'clipboard.ts',
      'viking-uri.ts',
      'okf-markdown.ts',
      'sse.ts',
      'query-client.ts',
    ]

    for (const util of coreUtilities) {
      expect(
        inventoryContent.includes(util),
        `Core utility ${util} must be documented in COMPONENT_AND_WHEEL_INVENTORY.md!`,
      ).toBe(true)
    }
  })

  it('ensures harvested high-order shared wheels are registered in inventory', () => {
    const inventoryContent = fs.readFileSync(inventoryPath, 'utf-8')
    const sharedWheels = [
      'copy-button.tsx',
      'UnifiedMemoryImpactDrawer',
      'UnifiedMemoryImpactView',
      'formatters.ts',
    ]

    for (const wheel of sharedWheels) {
      expect(
        inventoryContent.includes(wheel),
        `Harvested wheel ${wheel} must be documented in COMPONENT_AND_WHEEL_INVENTORY.md!`,
      ).toBe(true)
    }
  })
})
