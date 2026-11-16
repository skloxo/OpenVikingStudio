import axios from 'axios'
import i18n from '#/i18n'
import { getOvResult, ovClient, OvClientError } from '#/lib/ov-client'

export const modelKinds = ['vlm', 'embedding'] as const
export type ModelKind = (typeof modelKinds)[number]
export type ModelConfig = Record<string, unknown>

export type RestartStatus = {
  supported: boolean
  instance_id: string
  restarting: boolean
  rolled_back?: boolean
}

export type ConfigFileConfiguration = {
  content: string
  form_readonly?: boolean
  models?: Record<string, { config: ModelConfig }>
  revision: string
  file_path?: string
  writable?: boolean
  restart_required?: boolean
  restart?: RestartStatus
  overrides?: { cluster: string[]; account: string[] }
}

export type AccountConfigSettings = {
  agent_evolution: { enabled: boolean }
  acl?: { enabled: boolean }
}

export type ConnectionAuthInput = {
  accountId: string
  adminApiKey?: string
  apiKey?: string
  baseUrl?: string
}

function adminHeaders(conn: ConnectionAuthInput): Record<string, string> {
  const key = (conn.adminApiKey || conn.apiKey || '').trim()
  return key ? { 'X-API-Key': key } : {}
}

export function isConfigFileObject(content: string): boolean {
  try {
    const parsed: unknown = JSON.parse(
      content
        .trimStart()
        .replace(/"(?:[^"\\]|\\.)*"|\$(?:\{[^}]*\}|[a-zA-Z0-9_]+)/g, (token) =>
          token.startsWith('"') ? token : JSON.stringify(token),
        ),
    )
    return parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed)
  } catch {
    return false
  }
}

export function supportsModelTest(kind: ModelKind, provider: unknown): boolean {
  const allowed =
    kind === 'vlm'
      ? ['openai', 'volcengine', 'azure', 'glm', 'kimi', 'litellm']
      : [
          'openai',
          'azure',
          'volcengine',
          'jina',
          'gemini',
          'voyage',
          'dashscope',
          'minimax',
          'cohere',
          'litellm',
        ]
  return allowed.includes(String(provider || '').toLowerCase())
}

export async function fetchServerConfigFile(
  conn: ConnectionAuthInput,
  signal?: AbortSignal,
): Promise<ConfigFileConfiguration> {
  return getOvResult<ConfigFileConfiguration>(
    ovClient.instance.get('/api/v1/admin/configuration', {
      params: { source: 'file', account_id: conn.accountId },
      headers: adminHeaders(conn),
      signal,
    }),
  )
}

export async function saveServerConfigFile(
  conn: ConnectionAuthInput,
  content: string,
  revision: string,
): Promise<{ revision: string; restart_required: boolean }> {
  return getOvResult<{ revision: string; restart_required: boolean }>(
    ovClient.instance.patch(
      '/api/v1/admin/configuration',
      { revision, content },
      { params: { source: 'file' }, headers: adminHeaders(conn) },
    ),
  )
}

export async function testServerModelConnection(
  conn: ConnectionAuthInput,
  body: {
    kind: ModelKind
    config: ModelConfig
    fallback?: ModelConfig
    thinking?: boolean
    mode?: string
  },
  signal?: AbortSignal,
): Promise<{ ok: boolean; code?: string; ms?: number }> {
  return getOvResult<{ ok: boolean; code?: string; ms?: number }>(
    ovClient.instance.post(
      '/api/v1/admin/configuration/test-model',
      { fallback: {}, mode: 'dense', ...body },
      { headers: adminHeaders(conn), signal, timeout: 30_000 },
    ),
  )
}

export async function triggerServerRestart(
  conn: ConnectionAuthInput,
  revision: string,
): Promise<RestartStatus> {
  return getOvResult<RestartStatus>(
    ovClient.instance.post(
      '/api/v1/admin/restart',
      { revision },
      { headers: adminHeaders(conn) },
    ),
  )
}

export async function waitForServerRestart(
  load: () => Promise<ConfigFileConfiguration>,
  instanceId: string,
  signal: AbortSignal,
  timeoutMs = 120_000,
): Promise<ConfigFileConfiguration> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    signal.throwIfAborted()
    try {
      const result = await load()
      signal.throwIfAborted()
      if (
        result.restart &&
        result.restart.instance_id !== instanceId &&
        !result.restart.restarting
      ) {
        return result
      }
    } catch (error) {
      signal.throwIfAborted()
      if (
        error instanceof OvClientError &&
        (error.statusCode === 401 || error.statusCode === 403)
      ) {
        throw error
      }
      if (
        axios.isAxiosError(error) &&
        (error.response?.status === 401 || error.response?.status === 403)
      ) {
        throw error
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  throw new Error(i18n.t('studio:errors.restartTimeout'))
}

export async function fetchAccountConfiguration(
  conn: ConnectionAuthInput,
  signal?: AbortSignal,
): Promise<{ accountId: string; settings: AccountConfigSettings }> {
  const result = await getOvResult<{
    account_id?: string
    settings: AccountConfigSettings
  }>(
    ovClient.instance.get(
      `/api/v1/admin/accounts/${encodeURIComponent(conn.accountId)}/configuration`,
      { headers: adminHeaders(conn), signal },
    ),
  )
  return {
    accountId: result.account_id || conn.accountId,
    settings: result.settings,
  }
}

export async function patchAccountConfiguration(
  conn: ConnectionAuthInput,
  patch: Record<string, unknown>,
): Promise<{ accountId: string; settings: AccountConfigSettings }> {
  const result = await getOvResult<{
    account_id?: string
    settings: AccountConfigSettings
  }>(
    ovClient.instance.patch(
      `/api/v1/admin/accounts/${encodeURIComponent(conn.accountId)}/configuration`,
      { settings: patch },
      { headers: adminHeaders(conn) },
    ),
  )
  return {
    accountId: result.account_id || conn.accountId,
    settings: result.settings,
  }
}
