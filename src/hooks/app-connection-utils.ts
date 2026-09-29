/**
 * app-connection-utils.ts
 * 连接凭据规范化、本地存储持久化、哈希计算、请求头组装与身份探测纯函数工具集。
 */
import { fetchAdminAccounts } from '#/lib/admin'
import { isOvClientError, ovClient } from '#/lib/ov-client'

import type {
  ConnectionDraft,
  ConnectionIdentity,
  ConnectionRole,
} from './app-connection-types'
import {
  fetchServerHealth,
  normalizeBaseUrl,
} from './use-server-mode'
import type { ServerMode } from './use-server-mode'

export const CONNECTION_STORAGE_KEY = 'ov_console_connection'
export const AUTH_PROMPT_SUPPRESSION_MS = 10000

export const ENV_BASE_URL =
  typeof import.meta.env.VITE_OV_BASE_URL === 'string'
    ? import.meta.env.VITE_OV_BASE_URL.trim()
    : ''
export const ENV_API_KEY =
  typeof import.meta.env.VITE_OV_API_KEY === 'string'
    ? import.meta.env.VITE_OV_API_KEY.trim()
    : ''
export const ENV_ADMIN_API_KEY =
  typeof import.meta.env.VITE_OV_ADMIN_API_KEY === 'string'
    ? import.meta.env.VITE_OV_ADMIN_API_KEY.trim()
    : ''
export const ENV_ACCOUNT =
  typeof import.meta.env.VITE_OV_ACCOUNT === 'string'
    ? import.meta.env.VITE_OV_ACCOUNT.trim()
    : ''
export const ENV_USER =
  typeof import.meta.env.VITE_OV_USER === 'string'
    ? import.meta.env.VITE_OV_USER.trim()
    : ''

export const DEFAULT_CONNECTION: ConnectionDraft = {
  accountId: ENV_ACCOUNT || 'default',
  adminApiKey: ENV_ADMIN_API_KEY || '',
  apiKey: ENV_API_KEY || '',
  baseUrl: ovClient.getOptions().baseUrl,
  userId: ENV_USER || 'default',
}

export function isBrowser(): boolean {
  return typeof window !== 'undefined'
}

export function isConnectionRole(value: unknown): value is ConnectionRole {
  return (
    value === 'root' ||
    value === 'admin' ||
    value === 'user' ||
    value === 'unknown'
  )
}

export function readStoredConnection(): Partial<ConnectionDraft> {
  if (!isBrowser()) {
    return {}
  }

  try {
    const raw = window.localStorage.getItem(CONNECTION_STORAGE_KEY)
    if (!raw) {
      return {}
    }
    const parsed: unknown = JSON.parse(raw)
    return typeof parsed === 'object' && parsed !== null
      ? (parsed as Partial<ConnectionDraft>)
      : {}
  } catch {
    return {}
  }
}

export function persistConnection(connection: ConnectionDraft): void {
  if (!isBrowser()) {
    return
  }

  try {
    window.localStorage.setItem(
      CONNECTION_STORAGE_KEY,
      JSON.stringify(connection),
    )
  } catch {
    // Ignore localStorage failures in restricted environments.
  }
}

export function normalizeConnectionDraft(
  connection: ConnectionDraft,
): ConnectionDraft {
  return {
    accountId: connection.accountId.trim(),
    adminApiKey: connection.adminApiKey.trim(),
    apiKey: connection.apiKey.trim(),
    baseUrl: connection.baseUrl.trim(),
    userId: connection.userId.trim(),
  }
}

export function hashSecret(value: string): string {
  let hash = 0x811c9dc5
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index)
    hash = Math.imul(hash, 0x01000193)
  }
  return (hash >>> 0).toString(36)
}

export function createIdentityScopeKey(
  connection: ConnectionDraft,
  serverMode: ServerMode,
): string {
  const dataKey = connection.apiKey || connection.adminApiKey
  return [
    normalizeBaseUrl(connection.baseUrl),
    serverMode,
    connection.accountId,
    connection.userId,
    dataKey ? hashSecret(dataKey) : 'none',
  ].join('\u0000')
}

export function createConnectionRoleProbeKey(
  connection: ConnectionDraft,
  serverMode: ServerMode,
): string {
  return [
    normalizeBaseUrl(connection.baseUrl),
    serverMode,
    connection.accountId,
    connection.userId,
    connection.adminApiKey ? hashSecret(connection.adminApiKey) : 'none',
    connection.apiKey ? hashSecret(connection.apiKey) : 'none',
  ].join('\u0000')
}

export function resolveIdentityField(
  envValue: string,
  storedValue: string | undefined,
  defaultValue: string,
): string {
  if (envValue) {
    return envValue
  }
  return storedValue || defaultValue
}

export function resolveInitialApiKey({
  defaultApiKey,
  envApiKey,
  storedApiKey,
}: {
  defaultApiKey: string
  envApiKey: string
  storedApiKey: string | undefined
}): string {
  return envApiKey || storedApiKey || defaultApiKey
}

export function resolveConnectionRoleProbeState({
  apiKey,
  baseUrl,
  serverMode,
}: {
  apiKey: string
  baseUrl: string
  serverMode: ServerMode
}): {
  isLoading: boolean
  role: ConnectionRole
  shouldProbe: boolean
} {
  if (!baseUrl) {
    return { isLoading: false, role: 'unknown', shouldProbe: false }
  }
  if (serverMode === 'dev') {
    return { isLoading: false, role: 'root', shouldProbe: false }
  }
  if (!apiKey) {
    return { isLoading: false, role: 'unknown', shouldProbe: false }
  }
  return { isLoading: true, role: 'unknown', shouldProbe: true }
}

export function shouldRedirectToLoginOnApiError(
  error: unknown,
  isClientError: (value: unknown) => boolean = isOvClientError,
): boolean {
  if (!isClientError(error)) {
    return false
  }

  const clientError = error as { code?: string; statusCode?: number }
  return (
    clientError.statusCode === 401 || clientError.code === 'UNAUTHENTICATED'
  )
}

export function applyConnection(
  connection: ConnectionDraft,
  serverMode: ServerMode,
): void {
  ovClient.setOptions({
    baseUrl: connection.baseUrl,
  })
  ovClient.setConnection({
    accountId: connection.accountId || 'default',
    adminApiKey: connection.adminApiKey,
    apiKey: connection.apiKey,
    identityHeaders: serverMode === 'trusted' || serverMode === 'checking',
    userId: connection.userId || 'default',
  })
}

export function synchronizeConnectionRuntime(
  connection: ConnectionDraft,
  serverMode: ServerMode,
): ConnectionDraft {
  const normalized = normalizeConnectionDraft(connection)
  applyConnection(normalized, serverMode)
  persistConnection(normalized)
  return normalized
}

export function createConnectionHealthHeaders(
  connection: ConnectionDraft,
  credential: 'control' | 'data' = 'control',
): Record<string, string> {
  const headers: Record<string, string> = {}
  const apiKey =
    credential === 'data'
      ? connection.apiKey || connection.adminApiKey
      : connection.adminApiKey || connection.apiKey
  if (apiKey) {
    headers['X-API-Key'] = apiKey
  }
  return headers
}

export async function canListAccounts(
  connection: ConnectionDraft,
): Promise<boolean> {
  if (!connection.adminApiKey) {
    return false
  }

  try {
    await fetchAdminAccounts({
      accountId: connection.accountId,
      apiKey: connection.adminApiKey,
      baseUrl: connection.baseUrl,
      userId: connection.userId,
    })
    return true
  } catch {
    return false
  }
}

export async function detectConnectionIdentity(
  connection: ConnectionDraft,
  credential: 'control' | 'data' = 'control',
  serverMode?: ServerMode,
): Promise<ConnectionIdentity> {
  const data = await fetchServerHealth(
    connection.baseUrl,
    createConnectionHealthHeaders(connection, credential),
  )

  const healthRole = isConnectionRole(data.role) ? data.role : 'unknown'
  const isDev = serverMode === 'dev' || data.auth_mode === 'dev'
  const isTrusted = serverMode === 'trusted' || data.auth_mode === 'trusted'
  const role = isDev
    ? 'root'
    : credential === 'control' &&
        connection.adminApiKey &&
        (await canListAccounts(connection))
      ? 'root'
      : healthRole !== 'unknown'
        ? healthRole
        : isTrusted
          ? 'user'
          : 'unknown'

  return {
    accountId: typeof data.account_id === 'string' ? data.account_id : '',
    role,
    userId: typeof data.user_id === 'string' ? data.user_id : '',
  }
}

export function synchronizeResolvedDataIdentity(
  connection: ConnectionDraft,
  identity: ConnectionIdentity,
): ConnectionDraft | null {
  if (
    (identity.role !== 'admin' && identity.role !== 'user') ||
    !identity.accountId ||
    !identity.userId ||
    (connection.accountId === identity.accountId &&
      connection.userId === identity.userId)
  ) {
    return null
  }

  return {
    ...connection,
    accountId: identity.accountId,
    userId: identity.userId,
  }
}

export function resolveSwitchedIdentity(
  requested: Pick<ConnectionDraft, 'accountId' | 'userId'>,
  identity: ConnectionIdentity,
  allowLegacyIdentityFallback = false,
): Pick<ConnectionDraft, 'accountId' | 'userId'> | null {
  if (
    (identity.role === 'unknown' && !allowLegacyIdentityFallback) ||
    (identity.accountId && identity.accountId !== requested.accountId) ||
    (identity.userId &&
      requested.userId &&
      identity.userId !== requested.userId)
  ) {
    return null
  }

  return {
    accountId: identity.accountId || requested.accountId,
    userId: identity.userId || requested.userId,
  }
}

export function createManagementAccountConnection(
  connection: ConnectionDraft,
  accountId: string,
): ConnectionDraft {
  return {
    ...connection,
    accountId: accountId.trim(),
    apiKey: '',
    userId: '',
  }
}

export function readInitialConnection(): ConnectionDraft {
  const storedConnection = readStoredConnection()
  const adminApiKey =
    ENV_ADMIN_API_KEY ||
    storedConnection.adminApiKey ||
    DEFAULT_CONNECTION.adminApiKey
  const apiKey = resolveInitialApiKey({
    defaultApiKey: DEFAULT_CONNECTION.apiKey,
    envApiKey: ENV_API_KEY,
    storedApiKey: storedConnection.apiKey,
  })
  return normalizeConnectionDraft({
    ...DEFAULT_CONNECTION,
    ...storedConnection,
    accountId: resolveIdentityField(
      ENV_ACCOUNT,
      storedConnection.accountId,
      DEFAULT_CONNECTION.accountId,
    ),
    adminApiKey,
    apiKey,
    baseUrl: storedConnection.baseUrl || ENV_BASE_URL || DEFAULT_CONNECTION.baseUrl,
    userId: resolveIdentityField(
      ENV_USER,
      storedConnection.userId,
      DEFAULT_CONNECTION.userId,
    ),
  })
}
