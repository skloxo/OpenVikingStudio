import i18n from '#/i18n'
import { getOvResult, ovClient } from '#/lib/ov-client'
import type { ConnectionAuthInput } from './config-api'

export type BotConnection = {
  id: string
  type?: string
  setup_mode?: string
  onboarding_id?: string
  app_id: string
  bot_name: string
  enabled: boolean
  step: number
  revision: number
  settings?: Record<string, unknown>
  identity_user: string
  status: {
    state: string
    last_received?: string
    last_sent?: string
  }
}

export type OnboardingRun = {
  id: string
  type: string
  state: string
  name: string
  user_id: string
  qr?: string
  expires_at?: number
  error?: string
  can_retry: boolean
  app_id?: string
  connection_id?: string
}

export type PlatformConversation = {
  conversation: string
  latest: number
  title: string
  group_name?: string
  preview?: string
  time?: string
}

export type PlatformMessage = {
  id: number
  role: string
  content: string
  sender: string
  time: string
  status: string
  conversation: string
}

function adminHeaders(conn: ConnectionAuthInput): Record<string, string> {
  const key = (conn.adminApiKey || conn.apiKey || '').trim()
  return key ? { 'X-API-Key': key } : {}
}

export function botAccountBase(accountId: string): string {
  if (!accountId.trim()) {
    throw new Error(i18n.t('studio:errors.botAccountRequired'))
  }
  return `/api/v1/admin/accounts/${encodeURIComponent(accountId)}/bot`
}

export function fetchBotCapabilities(conn: ConnectionAuthInput) {
  return getOvResult<{ enabled: boolean; can_manage: boolean }>(
    ovClient.instance.get('/api/v1/admin/bot/capabilities', {
      headers: adminHeaders(conn),
    }),
  )
}

export function fetchBotConnections(conn: ConnectionAuthInput) {
  return getOvResult<BotConnection[]>(
    ovClient.instance.get(`${botAccountBase(conn.accountId)}/connections`, {
      headers: adminHeaders(conn),
    }),
  )
}

export function createBotConnection(
  conn: ConnectionAuthInput,
  body: {
    type: string
    credentials: Record<string, string>
    settings?: Record<string, unknown>
    user_id: string
  },
) {
  return getOvResult<BotConnection>(
    ovClient.instance.post(`${botAccountBase(conn.accountId)}/connections`, body, {
      headers: adminHeaders(conn),
    }),
  )
}

export function toggleBotConnection(
  conn: ConnectionAuthInput,
  item: BotConnection,
  action: 'pause' | 'resume',
) {
  return getOvResult<BotConnection>(
    ovClient.instance.patch(
      `${botAccountBase(conn.accountId)}/connections/${encodeURIComponent(item.id)}`,
      { enabled: action === 'resume', revision: item.revision },
      { headers: adminHeaders(conn) },
    ),
  )
}

export function verifyBotConnection(
  conn: ConnectionAuthInput,
  item: BotConnection,
) {
  return getOvResult<BotConnection>(
    ovClient.instance.post(
      `${botAccountBase(conn.accountId)}/connections/${encodeURIComponent(item.id)}/verifications`,
      { revision: item.revision },
      { headers: adminHeaders(conn) },
    ),
  )
}

export function deleteBotConnection(
  conn: ConnectionAuthInput,
  item: BotConnection,
) {
  return getOvResult<{ deleted: boolean }>(
    ovClient.instance.delete(
      `${botAccountBase(conn.accountId)}/connections/${encodeURIComponent(item.id)}`,
      { params: { revision: item.revision }, headers: adminHeaders(conn) },
    ),
  )
}

export function startFeishuOnboarding(
  conn: ConnectionAuthInput,
  body: {
    user_id: string
    name: string
    request_id: string
    settings: { thread_require_mention: boolean }
  },
) {
  return getOvResult<OnboardingRun>(
    ovClient.instance.post(
      `${botAccountBase(conn.accountId)}/onboarding-runs`,
      { ...body, type: 'feishu' },
      { headers: adminHeaders(conn) },
    ),
  )
}

export function fetchCurrentFeishuOnboarding(conn: ConnectionAuthInput) {
  return getOvResult<OnboardingRun | null>(
    ovClient.instance.get(
      `${botAccountBase(conn.accountId)}/onboarding-runs/current`,
      { params: { type: 'feishu' }, headers: adminHeaders(conn) },
    ),
  )
}

export function updateFeishuOnboarding(
  conn: ConnectionAuthInput,
  id: string,
  action: 'retry' | 'cancel' | 'manual',
) {
  return getOvResult<OnboardingRun>(
    ovClient.instance.post(
      `${botAccountBase(conn.accountId)}/onboarding-runs/${encodeURIComponent(id)}/actions`,
      { action },
      { headers: adminHeaders(conn) },
    ),
  )
}

export function fetchBotConversations(
  conn: ConnectionAuthInput,
  connectionId: string,
) {
  return getOvResult<PlatformConversation[]>(
    ovClient.instance.get(
      `${botAccountBase(conn.accountId)}/connections/${encodeURIComponent(connectionId)}/conversations`,
      { headers: adminHeaders(conn) },
    ),
  )
}

export function fetchBotMessages(
  conn: ConnectionAuthInput,
  connectionId: string,
  conversation: string,
  before = 0,
) {
  return getOvResult<PlatformMessage[]>(
    ovClient.instance.get(
      `${botAccountBase(conn.accountId)}/connections/${encodeURIComponent(connectionId)}/messages`,
      { params: { conversation, before }, headers: adminHeaders(conn) },
    ),
  )
}
