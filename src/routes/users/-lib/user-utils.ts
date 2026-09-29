/**
 * user-utils.ts
 * 从 users/route.tsx 提取的纯函数工具
 */
import type { AdminUser, AdminUserRole } from '#/lib/admin'

export const USER_ROLE_OPTIONS: AdminUserRole[] = ['user', 'admin', 'root']

export function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

export function isAdminUserRole(role: string): role is AdminUserRole {
  return USER_ROLE_OPTIONS.includes(role as AdminUserRole)
}

export function maskApiKey(value: string | undefined): string {
  if (!value) {
    return '-'
  }
  if (value.length <= 16) {
    return value
  }
  return `${value.slice(0, 10)}...${value.slice(-6)}`
}

export function resolveKeyLabel(user: AdminUser): string {
  return user.apiKey ? maskApiKey(user.apiKey) : user.keyPrefix || '-'
}
