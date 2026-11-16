import { beforeEach, describe, expect, it, vi } from 'vitest'

const { mockGet, mockPatch, mockPost, mockPut, mockDelete } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPatch: vi.fn(),
  mockPost: vi.fn(),
  mockPut: vi.fn(),
  mockDelete: vi.fn(),
}))

vi.mock('#/lib/ov-client', async () => {
  const actual = await vi.importActual<typeof import('#/lib/ov-client/errors')>(
    '#/lib/ov-client/errors',
  )
  return {
    ...actual,
    ovClient: {
      instance: {
        get: mockGet,
        patch: mockPatch,
        post: mockPost,
        put: mockPut,
        delete: mockDelete,
      },
    },
  }
})

import {
  fetchAccountConfiguration,
  isConfigFileObject,
  patchAccountConfiguration,
  supportsModelTest,
  testServerModelConnection,
} from './config-api'
import {
  templateFieldValue,
  withTemplateField,
  type MemoryTemplateSchema,
} from './templates-groups-api'
import { botAccountBase, fetchBotCapabilities } from './vikingbot-api'

describe('admin console API adapters', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('validates ov.conf objects even with unquoted env variables and checks supported test providers', () => {
    expect(isConfigFileObject('{"vlm": {"api_key": $OV_KEY}}')).toBe(true)
    expect(isConfigFileObject('["array"]')).toBe(false)
    expect(supportsModelTest('vlm', 'openai')).toBe(true)
    expect(supportsModelTest('embedding', 'gemini')).toBe(true)
    expect(supportsModelTest('embedding', 'local')).toBe(false)
  })

  it('fetches and patches account agent_evolution config and runs model probe', async () => {
    mockGet.mockResolvedValueOnce({
      status: 200,
      headers: {},
      data: {
        status: 'ok',
        result: { account_id: 'default', settings: { agent_evolution: { enabled: true } } },
      },
    })
    const current = await fetchAccountConfiguration({ accountId: 'default' })
    expect(current.settings.agent_evolution.enabled).toBe(true)

    mockPatch.mockResolvedValueOnce({
      status: 200,
      headers: {},
      data: {
        status: 'ok',
        result: { account_id: 'default', settings: { agent_evolution: { enabled: false } } },
      },
    })
    const patched = await patchAccountConfiguration(
      { accountId: 'default', adminApiKey: 'root-key' },
      { agent_evolution: { enabled: false } },
    )
    expect(patched.settings.agent_evolution.enabled).toBe(false)

    mockPost.mockResolvedValueOnce({
      status: 200,
      headers: {},
      data: { status: 'ok', result: { ok: true, ms: 120 } },
    })
    const probe = await testServerModelConnection(
      { accountId: 'default' },
      { kind: 'vlm', config: { provider: 'openai' } },
    )
    expect(probe).toEqual({ ok: true, ms: 120 })
  })

  it('edits memory template schema fields immutably and builds bot paths', async () => {
    const schema: MemoryTemplateSchema = {
      description: 'Base desc',
      directory: 'profile',
      filename_template: 'profile.md',
      fields: [{ name: 'content', description: 'Field desc' }],
    }
    const updated = withTemplateField(schema, 'fields.content.description', 'Next desc')
    expect(templateFieldValue(updated, 'fields.content.description')).toBe('Next desc')
    expect(templateFieldValue(schema, 'fields.content.description')).toBe('Field desc')

    expect(botAccountBase('acct-1')).toBe('/api/v1/admin/accounts/acct-1/bot')
    mockGet.mockResolvedValueOnce({
      status: 200,
      headers: {},
      data: { status: 'ok', result: { enabled: true, can_manage: true } },
    })
    expect(await fetchBotCapabilities({ accountId: 'acct-1' })).toEqual({
      enabled: true,
      can_manage: true,
    })
  })
})
