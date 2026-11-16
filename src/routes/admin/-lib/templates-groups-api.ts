import { getOvResult, ovClient } from '#/lib/ov-client'
import type { ConnectionAuthInput } from './config-api'

export const editableMemoryTypes = [
  'profile',
  'preferences',
  'entities',
  'events',
  'soul',
  'identity',
] as const

export type EditableMemoryType = (typeof editableMemoryTypes)[number]

export type MemoryTemplateSchema = {
  description: string
  directory: string
  filename_template: string
  fields: Array<{ name: string; description: string; [key: string]: unknown }>
  content_template?: string
  [key: string]: unknown
}

export type MemoryTemplate = {
  memory_type: EditableMemoryType
  status: 'system_default' | 'custom'
  updated_at: string | null
  defaults: MemoryTemplateSchema
  effective: MemoryTemplateSchema
}

function adminHeaders(conn: ConnectionAuthInput): Record<string, string> {
  const key = (conn.adminApiKey || conn.apiKey || '').trim()
  return key ? { 'X-API-Key': key } : {}
}

export function withTemplateField(
  schema: MemoryTemplateSchema,
  field: string,
  value: string,
): MemoryTemplateSchema {
  if (field === 'description' || field === 'content_template') {
    return { ...schema, [field]: value }
  }
  const fieldName = field.split('.')[1]
  return {
    ...schema,
    fields: schema.fields.map((item) =>
      item.name === fieldName ? { ...item, description: value } : item,
    ),
  }
}

export function templateFieldValue(
  schema: MemoryTemplateSchema,
  field: string,
): string {
  if (field === 'description' || field === 'content_template') {
    return String(schema[field] ?? '')
  }
  return (
    schema.fields.find((item) => item.name === field.split('.')[1])
      ?.description ?? ''
  )
}

export async function fetchMemoryTemplates(
  conn: ConnectionAuthInput,
  signal?: AbortSignal,
): Promise<{ account_id: string; templates: MemoryTemplate[] }> {
  return getOvResult<{ account_id: string; templates: MemoryTemplate[] }>(
    ovClient.instance.get(
      `/api/v1/admin/accounts/${encodeURIComponent(conn.accountId)}/memory-templates`,
      { headers: adminHeaders(conn), signal },
    ),
  )
}

export async function updateMemoryTemplate(
  conn: ConnectionAuthInput,
  memoryType: EditableMemoryType,
  schema: MemoryTemplateSchema,
): Promise<{ account_id: string } & MemoryTemplate> {
  return getOvResult<{ account_id: string } & MemoryTemplate>(
    ovClient.instance.put(
      `/api/v1/admin/accounts/${encodeURIComponent(conn.accountId)}/memory-templates/${encodeURIComponent(memoryType)}`,
      schema,
      { headers: adminHeaders(conn) },
    ),
  )
}

export async function resetMemoryTemplate(
  conn: ConnectionAuthInput,
  memoryType: EditableMemoryType,
): Promise<{ account_id: string } & MemoryTemplate> {
  return getOvResult<{ account_id: string } & MemoryTemplate>(
    ovClient.instance.delete(
      `/api/v1/admin/accounts/${encodeURIComponent(conn.accountId)}/memory-templates/${encodeURIComponent(memoryType)}`,
      { headers: adminHeaders(conn) },
    ),
  )
}

export type GroupSummary = {
  group_id: string
  member_count?: number
}

export async function fetchAdminGroups(
  conn: ConnectionAuthInput,
  signal?: AbortSignal,
): Promise<GroupSummary[]> {
  const result = await getOvResult<unknown>(
    ovClient.instance.get(
      `/api/v1/admin/accounts/${encodeURIComponent(conn.accountId)}/groups`,
      { headers: adminHeaders(conn), signal },
    ),
  )
  const rawList = Array.isArray(result)
    ? result
    : result && typeof result === 'object' && 'groups' in result
      ? (result as { groups: unknown[] }).groups
      : []
  return rawList.map((item) =>
    typeof item === 'string'
      ? { group_id: item }
      : {
          group_id: String((item as { group_id?: string }).group_id || ''),
          member_count:
            typeof (item as { member_count?: number }).member_count === 'number'
              ? (item as { member_count: number }).member_count
              : undefined,
        },
  )
}

export async function createAdminGroup(
  conn: ConnectionAuthInput,
  groupId: string,
): Promise<void> {
  await getOvResult(
    ovClient.instance.post(
      `/api/v1/admin/accounts/${encodeURIComponent(conn.accountId)}/groups`,
      { group_id: groupId.trim() },
      { headers: adminHeaders(conn) },
    ),
  )
}

export async function deleteAdminGroup(
  conn: ConnectionAuthInput,
  groupId: string,
): Promise<void> {
  await getOvResult(
    ovClient.instance.delete(
      `/api/v1/admin/accounts/${encodeURIComponent(conn.accountId)}/groups/${encodeURIComponent(groupId)}`,
      { headers: adminHeaders(conn) },
    ),
  )
}

export async function fetchGroupMembers(
  conn: ConnectionAuthInput,
  groupId: string,
): Promise<string[]> {
  const res = await getOvResult<{ group_id: string; members: string[] }>(
    ovClient.instance.get(
      `/api/v1/admin/accounts/${encodeURIComponent(conn.accountId)}/groups/${encodeURIComponent(groupId)}/members`,
      { headers: adminHeaders(conn) },
    ),
  )
  return Array.isArray(res.members) ? res.members : []
}

export async function addGroupMember(
  conn: ConnectionAuthInput,
  groupId: string,
  userId: string,
): Promise<void> {
  await getOvResult(
    ovClient.instance.put(
      `/api/v1/admin/accounts/${encodeURIComponent(conn.accountId)}/groups/${encodeURIComponent(groupId)}/members`,
      { user_ids: [userId.trim()] },
      { headers: adminHeaders(conn) },
    ),
  )
}

export async function removeGroupMember(
  conn: ConnectionAuthInput,
  groupId: string,
  userId: string,
): Promise<void> {
  await getOvResult(
    ovClient.instance.delete(
      `/api/v1/admin/accounts/${encodeURIComponent(conn.accountId)}/groups/${encodeURIComponent(groupId)}/members`,
      { data: { user_ids: [userId.trim()] }, headers: adminHeaders(conn) },
    ),
  )
}
