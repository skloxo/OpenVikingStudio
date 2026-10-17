import type { TaskTimestamp } from './task-time'

export type TaskStatus =
  | 'completed'
  | 'failed'
  | 'pending'
  | 'running'
  | 'cancelling'
  | 'cancelled'
  | 'unknown'

export type TaskRecord = TaskTimestamp & {
  error?: string | null
  resource_id?: string | null
  result?: unknown
  stage?: string | null
  status?: string
  task_id?: string
  task_type?: string
  meta?: Record<string, any> | null
  created_at?: number | string
  created_at_iso?: string
  updated_at?: number | string
  updated_at_iso?: string
}

export function normalizeTaskRecord(value: unknown): TaskRecord | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined
  }
  return value as TaskRecord
}

export function normalizeTasks(value: unknown): TaskRecord[] {
  if (!Array.isArray(value)) {
    return []
  }
  return value
    .map(normalizeTaskRecord)
    .filter((item): item is TaskRecord => Boolean(item))
}

export function normalizeTaskStatus(
  status: string | undefined,
  error?: string | null,
): TaskStatus {
  if (error && (status === 'running' || status === 'pending')) {
    return 'failed'
  }
  if (
    status === 'completed' ||
    status === 'failed' ||
    status === 'pending' ||
    status === 'running' ||
    status === 'cancelling' ||
    status === 'cancelled'
  ) {
    return status
  }
  return 'unknown'
}

export function hasTaskResult(result: unknown): boolean {
  if (result === null || result === undefined) {
    return false
  }
  if (Array.isArray(result)) {
    return result.length > 0
  }
  if (typeof result === 'object') {
    return Object.keys(result).length > 0
  }
  return true
}

export interface InitiatorInfo {
  isAgent: boolean
  isUser: boolean
  name: string
  raw?: string
}

function formatClientName(client: string): string {
  const map: Record<string, string> = {
    antigravity: 'Antigravity',
    workbuddy: 'WorkBuddy',
    mimocode: 'XiaomiMo',
    xiaomimo: 'XiaomiMo',
    openclaw: 'OpenClaw',
    hermes: 'Hermes',
  }
  const lower = client.toLowerCase()
  if (map[lower]) return map[lower]
  return client.charAt(0).toUpperCase() + client.slice(1)
}

export function parseInitiator(
  raw?: string,
  taskType?: string,
  resourceId?: string | null,
): InitiatorInfo {
  // Extract node hint from resourceId if available
  let inferredNode = ''
  let inferredAgent = ''
  if (resourceId) {
    const lowerRes = resourceId.toLowerCase()
    if (
      lowerRes.includes('3070_sessions') ||
      lowerRes.includes('staging/3070') ||
      lowerRes.includes('@3070')
    ) {
      inferredNode = '[RTX3070]'
    } else if (
      lowerRes.includes('2080ti_sessions') ||
      lowerRes.includes('staging/2080ti') ||
      lowerRes.includes('@2080ti')
    ) {
      inferredNode = '[2080TI]'
    } else if (
      lowerRes.includes('antigravity_sessions') ||
      lowerRes.includes('staging/antigravity')
    ) {
      inferredNode = '[2080TI]'
      inferredAgent = 'Antigravity'
    } else if (
      lowerRes.includes('mac_studio_sessions') ||
      lowerRes.includes('staging/mac_studio') ||
      lowerRes.includes('@mac_studio')
    ) {
      inferredNode = '[MacStudio]'
    }
  }

  if (!raw || raw.toLowerCase() === 'default' || raw.toLowerCase() === 'agent') {
    if (taskType === 'valet_parking' || raw?.toLowerCase() === 'agent') {
      const node = inferredNode || '[2080TI]'
      const agentName = inferredAgent || 'Antigravity'
      return {
        isAgent: true,
        isUser: false,
        name: `${node} ${agentName}`,
        raw: raw || '',
      }
    }
    if (raw?.toLowerCase() === 'default') {
      return { isAgent: false, isUser: true, name: 'default', raw }
    }
    return { isAgent: false, isUser: false, name: '-', raw: '' }
  }

  // Check structured client@node format (e.g. antigravity@2080ti, workbuddy@3070, openclaw.researcher@2080ti)
  if (raw.includes('@') && !raw.startsWith('@') && !raw.endsWith('@')) {
    const [clientPart, nodePart] = raw.split('@')
    const upperNode = nodePart.toUpperCase()
    const normalizedNode = upperNode === '3070' || upperNode === 'RTX3070' ? 'RTX3070' : upperNode
    const nodeTag = `[${normalizedNode}]`
    const isUser = /user|admin/i.test(clientPart)
    if (clientPart.includes('.')) {
      const [baseClient, role] = clientPart.split('.')
      const formattedClient = formatClientName(baseClient)
      const formattedRole = role.charAt(0).toUpperCase() + role.slice(1)
      return {
        isAgent: !isUser,
        isUser,
        name: `${nodeTag} ${formattedClient} (${formattedRole})`,
        raw,
      }
    }
    const formattedClient = formatClientName(clientPart)
    return {
      isAgent: !isUser,
      isUser,
      name: `${nodeTag} ${formattedClient}`,
      raw,
    }
  }

  const isAgent = /agent|antigravity|bot|hook|mcp/i.test(raw)
  const isUser = !isAgent && /user|admin/i.test(raw)
  const match = raw.match(/\((.*?)\)/)
  const cleanName = match ? match[1] : raw.replace(/^(agent|user)\s*/i, '').trim() || (isAgent ? 'Agent' : isUser ? 'User' : raw)
  const finalName = inferredNode && !cleanName.includes('[') ? `${inferredNode} ${cleanName}` : cleanName
  return { isAgent, isUser, name: finalName, raw }
}

