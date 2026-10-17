/**
 * app-connection-types.ts
 * 连接状态、角色权限、生成凭据与应用上下文接口契约。
 */
import type { ServerMode } from './use-server-mode'

export type ConnectionRole = 'admin' | 'root' | 'unknown' | 'user'

export type ConnectionDraft = {
  accountId: string
  adminApiKey: string
  apiKey: string
  baseUrl: string
  userId: string
}

export type ConnectionIdentitySummary = {
  labelKey: string
  values?: {
    identity?: string
  }
}

export type GeneratedCredential = {
  accountId?: string
  apiKey: string
  userId?: string
}

export type ConnectionIdentity = {
  accountId: string
  role: ConnectionRole
  userId: string
}

export type AppConnectionContextValue = {
  clearGeneratedCredential: () => void
  connection: ConnectionDraft
  connectionRole: ConnectionRole
  generatedCredential: GeneratedCredential | null
  identityScopeKey: string
  isConnectionRoleLoading: boolean
  openConnectionSettings: () => void
  saveConnection: (next: ConnectionDraft) => void
  setGeneratedCredential: (credential: GeneratedCredential) => void
  serverMode: ServerMode
  switchIdentity: (identity: {
    accountId: string
    allowLegacyIdentityFallback?: boolean
    apiKey: string
    userId: string
  }) => Promise<void>
  switchManagementAccount: (accountId: string) => Promise<void>
}
